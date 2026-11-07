#!/usr/bin/env python3
"""Explore five substantive expression groupings from frozen v2 AI codes.

Grouping is based on the research question, not association significance.
The group definition is retrospective, and AI-generated labels have not been
human-validated. Data, text, and per-post labels remain in the private folder.
"""
from pathlib import Path
from collections import Counter
import importlib.util
import json
import hashlib

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'v2_direct_batches'
REVIEW=PRIVATE/'v2_fresh_blind_check'
OUT=ROOT/'results/rebuilt_expression_groups.json'
GROUPS={
    'R_RECORD':{'label':'记录或呈现','components':['F_UPDATE','F_CAPTION']},
    'R_EVALUATE':{'label':'体验或评价','components':['F_EXPERIENCE_EVALUATION']},
    'R_PLAN_ENCOURAGE':{'label':'计划、期待或鼓励','components':['F_FUTURE','F_EXHORT']},
    'R_SOCIAL':{'label':'问候、感谢或邀请交流','components':['F_GREETING_GRATITUDE','F_INVITE_ASK']},
    'R_REFLECT':{'label':'感悟或观点','components':['F_REFLECTION']},
}
MIN_COUNT=40
MIN_AUTHORS=10
CONTROLS=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
          ' + C(time_bin) + C(author) + C(date)')

def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def tri_state(observation, positive, unknown, components):
    if observation!='readable':return None
    # A definite positive overrides an uncertain companion component.
    if any(c in positive for c in components):return 1
    if any(c in unknown for c in components):return None
    return 0

def support(df, code):
    pos=int(df[code].eq(1).sum());neg=int(df[code].eq(0).sum())
    vary=int(df.groupby('author')[code].nunique().gt(1).sum())
    return {'n':len(df),'authors':int(df.author.nunique()),'n_positive':pos,'n_negative':neg,
            'authors_within_variation':vary,'eligible':bool(pos>=MIN_COUNT and neg>=MIN_COUNT and vary>=MIN_AUTHORS)}

def fit(df, code, author_equal_weight=False):
    s=support(df,code)
    if not s['eligible']:
        return {**s,'status':'insufficient_support'}
    formula='log_likes ~ '+CONTROLS+' + '+code
    if author_equal_weight:
        weights=1/df.groupby('author')['author'].transform('size')
        model=smf.wls(formula,data=df,weights=weights,missing='raise')
    else:
        model=smf.ols(formula,data=df,missing='raise')
    rank=int(np.linalg.matrix_rank(model.exog));cols=int(model.exog.shape[1])
    if rank!=cols:
        return {**s,'status':'rank_deficient','rank':rank,'design_columns':cols}
    fit=model.fit(cov_type='cluster',cov_kwds={'groups':df.author,'use_correction':True,'df_correction':True},use_t=True)
    ci=fit.conf_int()
    return {**s,'status':'estimated_exploratory','beta':float(fit.params[code]),
            'se_cluster':float(fit.bse[code]),'p':float(fit.pvalues[code]),
            'ci_low':float(ci.loc[code,0]),'ci_high':float(ci.loc[code,1]),
            'rank':rank,'design_columns':cols,'author_equal_weight':author_equal_weight}

def apply_bh(models):
    valid=[v for v in models.values() if v['status']=='estimated_exploratory']
    if valid:
        for v,q in zip(valid,multipletests([v['p'] for v in valid],method='fdr_bh')[1]):
            v['q_bh_within_five_groups']=float(q)

def blind_agreement():
    # Validate immutable blind sample and model outputs before comparing.
    spec=importlib.util.spec_from_file_location('local_pipeline',ROOT/'code/local_ai_batch_pipeline.py')
    pipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipe)
    manifest,schema=pipe.verify_inputs(RUN)
    meta=json.loads((REVIEW/'metadata.json').read_text())
    if manifest['codebook_sha256']!=meta['codebook_sha256']:raise ValueError('Codebook differs')
    orig=read_jsonl(RUN/'merged_unique.jsonl');first={r['sample_id']:r for r in orig}
    pairs=[]
    for i in (1,2,3):
        sample=REVIEW/f'blind_{i}.jsonl';answers=REVIEW/f'coder_{i}.jsonl'
        if hashlib.sha256(sample.read_bytes()).hexdigest()!=meta['blind_sha256'][sample.name]:raise ValueError('Sample changed')
        source={r['sample_id']:r['text'] for r in read_jsonl(sample)}
        rows=read_jsonl(answers)
        if len(rows)!=30 or len({r['sample_id'] for r in rows})!=30 or set(source)!={r['sample_id'] for r in rows}:
            raise ValueError('Blind review IDs incomplete')
        for row in rows:
            pipe.check_row(row,source[row['sample_id']],schema)
            if row['sample_id'] not in first:raise ValueError('First coding unavailable')
            pairs.append((first[row['sample_id']],row))
    if len(pairs)!=90 or len({a['sample_id'] for a,b in pairs})!=90:raise ValueError('Blind sample duplicate')
    result={}
    for code,group in GROUPS.items():
        counter=Counter()
        for a,b in pairs:
            x=tri_state(a['observation_state'],a['expression_labels'],a['uncertain_expression'],group['components'])
            y=tri_state(b['observation_state'],b['expression_labels'],b['uncertain_expression'],group['components'])
            if x is None or y is None:counter['one_or_both_unknown']+=1;continue
            counter['both_positive' if x==1 and y==1 else 'first_only' if x==1 else 'second_only' if y==1 else 'both_negative']+=1
        tp=counter['both_positive'];fp=counter['first_only'];fn=counter['second_only'];tn=counter['both_negative'];valid=tp+fp+fn+tn
        result[code]={'label':group['label'],'n_coded':valid,'n_unknown':counter['one_or_both_unknown'],
                      'both_positive':tp,'first_only':fp,'second_only':fn,'both_negative':tn,
                      'raw_agreement':(tp+tn)/valid if valid else None,
                      'positive_agreement':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                      'low_positive_support':tp+fp+fn<5}
    return {'n_unique_texts':90,'basis':meta['sampling_unit'],
            'limitation':'same-base independent contexts, not human ground truth or post-weighted prevalence',
            'per_group':result}

def main():
    if not (RUN/'merge_summary.json').is_file():raise ValueError('Full validated merge required')
    posts=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str})
    labels=pd.read_csv(RUN/'post_labels.csv',dtype={'postId':str},keep_default_na=False)
    data=posts.merge(labels,on='postId',validate='one_to_one')
    if len(data)!=len(posts) or len(data)!=9532:raise ValueError('Post counts do not reconcile')
    for k in ('expression_labels','uncertain_expression'):
        data[k]=data[k].map(lambda v:json.loads(v) if v else [])
    for code,group in GROUPS.items():
        data[code]=[tri_state(obs,pos,unc,group['components']) for obs,pos,unc in
                    zip(data.observation_state,data.expression_labels,data.uncertain_expression)]
    overall={};models={'main':{},'drop_top_1_percent_likes':{},'authors_min_10_in_base_sample':{},'author_equal_weight':{}}
    for code,group in GROUPS.items():
        eligible=data.loc[data[code].notna()].copy();eligible[code]=eligible[code].astype(int)
        sup=support(eligible,code)
        positive_authors=eligible.loc[eligible[code].eq(1)].groupby('author').size()
        overall[code]={**group,**sup,
             'positive_authors':int(len(positive_authors)),
             'largest_author_share_of_positives':float(positive_authors.max()/sup['n_positive']) if sup['n_positive'] else None,
             'n_unknown_all_posts':int(data[code].isna().sum()),
             'n_unknown_nonempty':int((data.length.gt(0)&data[code].isna()).sum())}
        main=fit(eligible,code)
        # Threshold is computed separately in this variable's eligible sample;
        # ties at the cutoff remain. No label or specification is chosen by p.
        quantile=float(eligible.likes.quantile(.99))
        trimmed=eligible.loc[eligible.likes.le(quantile)].copy()
        robust_outlier=fit(trimmed,code)
        robust_outlier.update(likes_cutoff=quantile,excluded_posts=len(eligible)-len(trimmed))
        author_sizes=eligible.groupby('author').size()
        selected=eligible.loc[eligible.author.isin(author_sizes.index[author_sizes.ge(10)])].copy()
        robust_authors=fit(selected,code)
        robust_authors.update(author_min_posts=10,excluded_posts=len(eligible)-len(selected))
        # Each author has equal total weight within this group's eligible sample.
        robust_weight=fit(eligible,code,author_equal_weight=True)
        models['main'][code]=main;models['drop_top_1_percent_likes'][code]=robust_outlier
        models['authors_min_10_in_base_sample'][code]=robust_authors
        models['author_equal_weight'][code]=robust_weight
    for model in models.values():apply_bh(model)
    readable=data.loc[data.observation_state.eq('readable')]
    guidance={'label':'信息解释或可执行建议','n_positive':int(readable.expression_labels.map(lambda v:'F_GUIDANCE' in v).sum()),
              'n_explicit_uncertain':int(readable.uncertain_expression.map(lambda v:'F_GUIDANCE' in v).sum()),
              'model_role':'descriptive_only_due_to_limited_same_model_agreement_and_support'}
    out={'status':'retrospective_exploratory_not_human_validated','n_posts':len(data),
         'n_nonempty_body':int(data.length.gt(0).sum()),'group_definitions':GROUPS,
         'grouping_rationale':'Research question and interpretability; frozen after examining an earlier pilot; not selected by regression p values.',
         'tri_state_rule':'any child positive => 1; otherwise any child uncertain => NA; otherwise 0; nonreadable => NA',
         'controls':CONTROLS,'legacy_four_used_as_model_controls':False,
         'support_thresholds':{'positive':MIN_COUNT,'negative':MIN_COUNT,'within_author_variation':MIN_AUTHORS},
         'summary':overall,'guidance_descriptive':guidance,'models':models,'blind_90_consistency':blind_agreement(),
         'limitations':['AI-generated labels are not human gold standard.',
                        'Multiple groups may coexist; each coefficient comes from a separate model, not adjusted for other groups.',
                        'Author/date fixed effects cannot eliminate time-varying exposure or observation-window differences.',
                        'The five-variable grouping and checks are retrospective; same-base AI agreement is not accuracy.',
                        'Five-label BH is per model specification; does not account for all studies and exploratory choices.']}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'n_posts':len(data),
        'main':{c:{k:v for k,v in m.items() if k in ['n','authors','n_positive','n_negative','beta','p','q_bh_within_five_groups','status']} for c,m in models['main'].items()}},ensure_ascii=False))

if __name__=='__main__':main()
