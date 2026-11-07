#!/usr/bin/env python3
"""Analyze new AI-assisted post codes without the legacy four lexical controls.

The analysis is exploratory: direct AI annotations are not human gold labels.
Requires a complete validated merge from local_ai_batch_pipeline.py. Individual
labels and source texts remain in the ignored private directory.
"""
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'validation/classification_rebuild/private/v2_direct_batches'
OUT = ROOT / 'results/v2_primary_classification_summary.json'
MIN_GROUP = 40
MIN_VARYING_AUTHORS = 10


def parse(value):
    return json.loads(value) if isinstance(value, str) and value else []


def main():
    # A merge exists only after every batch and every evidence span validates.
    merge = RUN / 'merge_summary.json'
    labels_path = RUN / 'post_labels.csv'
    if not merge.exists() or not labels_path.exists():
        raise SystemExit('Complete and validate all batches before analysis.')
    schema = json.loads((RUN / 'frozen_schema.json').read_text())
    manifest = json.loads((RUN / 'manifest.json').read_text())
    labels = pd.read_csv(labels_path, dtype={'postId': str}, keep_default_na=False)
    source = pd.read_csv(ROOT / 'results/post_features.csv', dtype={'postId': str})
    data = source.merge(labels, on='postId', how='inner', validate='one_to_one')
    if len(data) != len(source) or len(data) != manifest['total_posts']:
        raise ValueError('Post population changed or merge lost records')
    for key in ['content_labels', 'expression_labels', 'uncertain_content', 'uncertain_expression']:
        data[key] = data[key].map(parse)
    readable = data.loc[data.observation_state.eq('readable')].copy()
    nonempty = data.loc[data.length.gt(0)].copy()
    old_codes = ['self_discipline', 'social_address', 'positive_expression', 'question']
    nonempty['old_any'] = nonempty[old_codes].sum(axis=1).gt(0)
    nonempty['ai_content'] = nonempty.content_labels.map(len).gt(0)
    nonempty['ai_expression'] = nonempty.expression_labels.map(len).gt(0)
    nonempty['ai_any'] = nonempty.ai_content | nonempty.ai_expression
    old_missed = nonempty.loc[~nonempty.old_any]
    summary = {
        'status': 'exploratory_AI_annotations_not_human_validated',
        'n_total': len(data),
        'n_nonempty': int(data.length.gt(0).sum()),
        'input_status': data.input_status.value_counts().to_dict(),
        'observation_state_nonempty': data.loc[data.length.gt(0), 'observation_state'].value_counts().to_dict(),
        'domain_state_nonempty': data.loc[data.length.gt(0), 'domain_state'].value_counts().to_dict(),
        'coverage_comparison': {
            'population': 'cleaned nonempty posts',
            'old_no_literal_match': int((~nonempty.old_any).sum()),
            'old_at_least_one_literal_match': int(nonempty.old_any.sum()),
            'ai_at_least_one_content': int(nonempty.ai_content.sum()),
            'ai_at_least_one_expression': int(nonempty.ai_expression.sum()),
            'ai_multiple_content': int(nonempty.content_labels.map(len).ge(2).sum()),
            'ai_multiple_expression': int(nonempty.expression_labels.map(len).ge(2).sum()),
            'ai_any_content_or_expression': int(nonempty.ai_any.sum()),
            'ai_no_positive_content_or_expression': int((~nonempty.ai_any).sum()),
            'old_missed_with_ai_any': int(old_missed.ai_any.sum()),
            'old_missed_with_ai_content': int(old_missed.ai_content.sum()),
            'old_missed_with_ai_expression': int(old_missed.ai_expression.sum()),
            'old_missed_without_ai_any': int((~old_missed.ai_any).sum()),
            'note': 'AI-positive includes either axis; its coverage is not semantic accuracy or gold validation.',
        },
        'ai_codebook_sha256': manifest.get('codebook_sha256'),
        'model_revision': 'New content and expression features are the focal variables; the old four lexical indicators are excluded from the primary models and retained only for coverage comparisons.',
        'descriptive': {},
        'regression': {},
        'limitations': [
            'Single-pass AI-assisted annotations; not human-verified true labels.',
            'No claim that assigned or unassigned labels are error-free.',
            'Only cleaned text is classified; content in images and video is unobserved.',
            'Multi-label counts can overlap and do not add to the sample size.',
            'Regression associations are observational and sensitive to the selected observable population.',
        ],
    }
    for family, positive, uncertain in [('content', 'content_labels', 'uncertain_content'),
                                        ('expression', 'expression_labels', 'uncertain_expression')]:
        codes = schema[family + '_labels']
        pop = readable.loc[readable.domain_state.eq('specified')].copy() if family == 'content' else readable.copy()
        # For descriptive results use all nonempty posts as the disclosed base.
        rows = []
        for code, label in codes.items():
            rows.append({'code': code, 'label': label,
                         'post_count': int(readable[positive].map(lambda x: code in x).sum()),
                         'uncertain_count': int(readable[uncertain].map(lambda x: code in x).sum())})
        summary['descriptive'][family] = rows

        # Never turn explicitly uncertain codes into zeros; complete-case
        # comparison is conditional on readable/explicitly specified text.
        complete = pop.loc[pop[uncertain].map(len).eq(0)].copy()
        included = []
        support = []
        for code, label in codes.items():
            complete[code] = complete[positive].map(lambda x: int(code in x))
            count = int(complete[code].sum())
            vary = int(complete.groupby('author')[code].nunique().gt(1).sum())
            eligible = (code not in {'C_OTHER', 'F_OTHER'} and count >= MIN_GROUP
                        and len(complete) - count >= MIN_GROUP and vary >= MIN_VARYING_AUTHORS)
            support.append({'code': code, 'label': label, 'positive_posts': count,
                            'negative_posts': len(complete) - count,
                            'authors_within_variation': vary, 'included': bool(eligible)})
            if eligible:
                included.append(code)
        details = {'population': ('readable and domain explicitly specified' if family == 'content'
                                   else 'readable text'),
                   'complete_case_n': len(complete), 'n_authors': int(complete.author.nunique()),
                   'support_thresholds': {'positive_and_negative': MIN_GROUP,
                                          'authors_within_variation': MIN_VARYING_AUTHORS},
                   'support': support, 'coefficients': []}
        if not included:
            details['status'] = 'insufficient_support'
            summary['regression'][family] = details
            continue
        controls = ('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
                    ' + C(time_bin) + C(author) + C(date)')
        # Estimate each label separately. Other eligible texts can themselves
        # contain multiple different labels. This does not isolate the effect
        # of one category from all other categories.
        skipped = []
        for code in included:
            formula = 'log_likes ~ ' + controls + ' + ' + code
            model = smf.ols(formula, data=complete, missing='raise')
            rank = int(np.linalg.matrix_rank(model.exog))
            if rank < model.exog.shape[1]:
                skipped.append({'code':code, 'reason':'rank_deficient'})
                continue
            fit = model.fit(cov_type='cluster', cov_kwds={'groups': complete.author,
                            'use_correction': True, 'df_correction': True}, use_t=True)
            ci = fit.conf_int()
            details['coefficients'].append({'code': code, 'label': codes[code],
                'beta': float(fit.params[code]), 'se_cluster': float(fit.bse[code]),
                'ci_low': float(ci.loc[code, 0]), 'ci_high': float(ci.loc[code, 1]),
                'p': float(fit.pvalues[code]), 'n_positive': int(complete[code].sum()),
                'n_without_label': int(len(complete)-complete[code].sum()),
                'design_rank':rank, 'design_columns':model.exog.shape[1]})
        if details['coefficients']:
            qvalues=multipletests([x['p'] for x in details['coefficients']],method='fdr_bh')[1]
            for row,q in zip(details['coefficients'],qvalues):row['q_bh_within_family']=float(q)
        details.update(status='estimated_exploratory' if details['coefficients'] else 'rank_deficient_not_estimated',
                       n=len(complete), n_authors=int(complete.author.nunique()), skipped=skipped,
                       model_structure='one separate model per label; other eligible labels may overlap',
                       adjustment='log_length, has_tag, emoji_count, course_ref, media form, type, time of day, author and date fixed effects; old four lexical indicators not included',
                       qualification='Author-clustered SE; q correction only within this family; not causal or human validated')
        summary['regression'][family] = details
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'output': str(OUT), 'n_nonempty': summary['n_nonempty'],
                      'regression_status': {k:v['status'] for k,v in summary['regression'].items()}}, ensure_ascii=False))


if __name__ == '__main__':
    main()
