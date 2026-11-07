#!/usr/bin/env python3
"""Audit collinearity of the *previous* five AI-coded expression groups.

This deliberately uses complete cases across all five tri-state variables and
the complete author/date fixed-effect design. It is not a v3 nine-label audit.
Only aggregated counts and diagnostics leave the private directory.
"""
from pathlib import Path
import importlib.util
import json
import hashlib

import numpy as np
import pandas as pd
from patsy import dmatrix

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT/'validation/classification_rebuild/private/v2_direct_batches'
OUTPUT = ROOT/'results/five_expression_collinearity_audit.json'
spec = importlib.util.spec_from_file_location('groups', ROOT/'code/analyze_rebuilt_expression_groups.py')
groups = importlib.util.module_from_spec(spec)
spec.loader.exec_module(groups)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    posts_path = ROOT/'results/post_features.csv'
    labels_path = RUN/'post_labels.csv'
    if not (RUN/'merge_summary.json').is_file():
        raise ValueError('Full validated v2 merge is required')
    posts = pd.read_csv(posts_path, dtype={'postId': str})
    labels = pd.read_csv(labels_path, dtype={'postId': str}, keep_default_na=False)
    d = posts.merge(labels, on='postId', how='inner', validate='one_to_one')
    if len(d) != len(posts) or len(d) != 9532:
        raise ValueError('Population mismatch')
    for key in ['expression_labels', 'uncertain_expression']:
        d[key] = d[key].map(lambda value: json.loads(value) if value else [])
    codes = list(groups.GROUPS)
    for code, group in groups.GROUPS.items():
        d[code] = [groups.tri_state(obs, pos, unc, group['components']) for obs, pos, unc in
                   zip(d.observation_state, d.expression_labels, d.uncertain_expression)]
    complete = d.dropna(subset=codes).copy()
    for code in codes:
        complete[code] = complete[code].astype(int)
        if not complete[code].isin([0, 1]).all():
            raise ValueError('Nonbinary data in complete cases')
    n = len(complete)
    if not n:
        raise ValueError('No complete cases')
    matrix = dmatrix(groups.CONTROLS+' + '+' + '.join(codes), data=complete,
                     return_type='dataframe', NA_action='raise')
    controls = dmatrix(groups.CONTROLS, data=complete, return_type='dataframe', NA_action='raise')
    X = np.asarray(matrix, dtype=float)
    rank = int(np.linalg.matrix_rank(X))
    if rank != X.shape[1]:
        raise ValueError(f'Full design is rank deficient: {rank}/{X.shape[1]}; VIF undefined')
    # An intercept is present. Center/scaling the explanatory columns yields a
    # correlation matrix whose inverse diagonal is the standard VIF.
    without_intercept = matrix.drop(columns=['Intercept'])
    values = without_intercept.to_numpy(dtype=float)
    scales = values.std(axis=0)
    if np.any(scales <= 0):
        raise ValueError('A constant predictor exists in the design')
    Z = (values-values.mean(axis=0))/scales
    corr = (Z.T @ Z)/n
    inverse = np.linalg.inv(corr)
    vif = {code: float(inverse[without_intercept.columns.get_loc(code),
                               without_intercept.columns.get_loc(code)]) for code in codes}
    # Independent per-variable least-squares check on the full original design.
    direct = {}
    for code in codes:
        index = matrix.columns.get_loc(code)
        y = X[:, index]
        other = np.delete(X, index, axis=1)
        residual = y - other@np.linalg.lstsq(other, y, rcond=None)[0]
        denominator = np.sum((y-y.mean())**2)
        direct[code] = float(denominator/np.sum(residual**2))
        if not np.isclose(vif[code], direct[code], atol=1e-7, rtol=1e-7):
            raise ValueError(f'VIF cross-check mismatch for {code}')
    singular_values = np.linalg.svd(Z, compute_uv=False)
    condition = float(singular_values[0]/singular_values[-1])
    binary = complete[codes]
    raw_corr = binary.corr()
    control_X = controls.to_numpy(dtype=float)
    if np.linalg.matrix_rank(control_X) != control_X.shape[1]:
        raise ValueError('Control-only design is rank deficient')
    residuals = binary.to_numpy(dtype=float) - control_X@np.linalg.lstsq(control_X, binary.to_numpy(dtype=float), rcond=None)[0]
    residual_corr = pd.DataFrame(residuals, columns=codes).corr()
    pair_rows=[]
    for i, a in enumerate(codes):
        for b in codes[i+1:]:
            pair_rows.append({'first':a, 'second':b,
                'joint_positive_posts':int((binary[a].eq(1)&binary[b].eq(1)).sum()),
                'phi':float(raw_corr.loc[a,b]),
                'correlation_after_controls':float(residual_corr.loc[a,b])})
    support=[]
    for code in codes:
        support.append({'code':code,'label':groups.GROUPS[code]['label'],
            'positive_posts':int(binary[code].sum()),
            'negative_posts':int(n-binary[code].sum()),
            'authors_with_within_variation':int(complete.groupby('author')[code].nunique().gt(1).sum()),
            'vif_full_design':vif[code], 'vif_direct_check':direct[code]})
    count_of_positives=binary.sum(axis=1)
    result={
        'scope':'Retrospective audit of old five grouped v2 expression variables; not the v3 nine-variable audit.',
        'n_total':int(len(d)),'n_nonempty_body':int(d.length.gt(0).sum()),
        'n_complete_for_all_five':n,'n_excluded_due_to_any_unknown_or_unavailable':int(len(d)-n),
        'n_authors':int(complete.author.nunique()),'outcome_used':False,
        'coexistence':{'no_positive':int(count_of_positives.eq(0).sum()),
                       'one_positive':int(count_of_positives.eq(1).sum()),
                       'at_least_two_positive':int(count_of_positives.ge(2).sum()),
                       'distribution':{str(k):int(v) for k,v in count_of_positives.value_counts().sort_index().items()}},
        'controls':groups.CONTROLS,'variables':support,'pairs':pair_rows,
        'max_absolute_phi':max(abs(x['phi']) for x in pair_rows),
        'max_absolute_correlation_after_controls':max(abs(x['correlation_after_controls']) for x in pair_rows),
        'design_matrix':{'rows':X.shape[0],'columns_including_intercept':X.shape[1],
                         'rank':rank,'controls_only_columns':control_X.shape[1],
                         'condition_number_centered_standardized_predictors':condition},
        'method':'VIF_i = 1/(1 - R²) regressing predictor i on all other five-group predictors and all controls, including author/date fixed effects. Cross-checked with direct least-squares residualization. Pair phi is Pearson correlation of binary labels.',
        'limitations':['Complete-case sample differs from each previously reported per-variable model.',
                       'AI labels are unvalidated semantic classifications. Low numerical collinearity does not establish semantic independence or measurement validity.',
                       'Full-design VIF may reflect correlation with any included control, not just the other four groups.',
                       'This assesses the previous five groups, not the new v3 nine categories.'],
        'input_sha256':{'post_features.csv':sha256(posts_path),'post_labels.csv':sha256(labels_path)},
    }
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUTPUT),'n':n,'authors':result['n_authors'],
                      'rank':rank,'columns':X.shape[1],
                      'at_least_two_positive':result['coexistence']['at_least_two_positive'],
                      'max_abs_phi':result['max_absolute_phi'],
                      'max_vif':max(vif.values()),'variables':support},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
