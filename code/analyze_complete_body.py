"""Check how the text association depends on actual body-text availability."""
from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
TERMS = ['log_length', 'self_discipline', 'social_address', 'positive_expression', 'question']
RHS = ' + '.join(TERMS + ['has_tag', 'emoji_count', 'course_ref']) + ' + C(contentTypeStr) + C(type) + C(time_bin) + C(author) + C(date)'


def main():
    source = ROOT / 'results/post_features.csv'
    p = pd.read_csv(source)
    saved = pd.read_csv(ROOT / 'results/regression_coefficients.csv')
    results = []
    independent = []
    for name, data, rhs in [
        ('original_all_posts', p, RHS + ' + has_text'),
        ('raw_body_available', p.loc[p.has_text.eq(1)].copy(), RHS),
        ('nonempty_clean_body_only', p.loc[p.length.gt(0)].copy(), RHS),
    ]:
        f = smf.ols('log_likes ~ ' + rhs, data=data).fit(cov_type='cluster', cov_kwds={'groups': data.author, 'use_correction': True, 'df_correction': True}, use_t=True)
        q = multipletests([f.pvalues[t] for t in TERMS], method='fdr_bh')[1]
        ci = f.conf_int()
        result = {'model': name, 'n': int(f.nobs), 'authors': int(data.author.nunique()),
                  'joint_five_p': float(f.wald_test(' = 0, '.join(TERMS) + ' = 0', scalar=True).pvalue),
                  'r_squared': float(f.rsquared),
                  'terms': [{'term': t, 'coef': float(f.params[t]), 'se_cluster': float(f.bse[t]), 'p': float(f.pvalues[t]), 'q_bh': float(qq), 'ci_low': float(ci.loc[t, 0]), 'ci_high': float(ci.loc[t, 1])} for t, qq in zip(TERMS, q)]}
        if name != 'nonempty_clean_body_only':
            prefix = 'M3_' if name == 'original_all_posts' else 'R1_'
            old = saved.loc[saved.model.str.startswith(prefix)].set_index('term')
            assert all(np.isclose(f.params[t], old.loc[t, 'coef'], atol=1e-10) for t in TERMS)
        else:
            # Independent least squares and manual author-clustered sandwich.
            x, y = f.model.exog, f.model.endog
            b = np.linalg.lstsq(x, y, rcond=None)[0]
            codes, authors = pd.factorize(data.author, sort=True)
            scores = np.zeros((len(authors), x.shape[1]))
            np.add.at(scores, codes, x * (y - x @ b)[:, None])
            bread = np.linalg.inv(x.T @ x)
            g, n, k = len(authors), len(y), x.shape[1]
            cov = bread @ (scores.T @ scores) @ bread * g / (g - 1) * (n - 1) / (n - k)
            ix = [f.model.exog_names.index(t) for t in TERMS]
            se = np.sqrt(np.diag(cov))
            joint = (b[ix] @ np.linalg.solve(cov[np.ix_(ix, ix)], b[ix])) / len(ix)
            joint_p = float(stats.f.sf(joint, len(ix), g - 1))
            assert np.allclose(b[ix], f.params.loc[TERMS], atol=1e-10)
            assert np.allclose(se[ix], f.bse.loc[TERMS], atol=1e-10)
            assert np.isclose(joint_p, result['joint_five_p'], atol=1e-10)
            independent = {'method': 'independent numpy least squares and manually aggregated author sandwich, t/F df=G-1', 'max_focal_coefficient_error': float(np.max(np.abs(b[ix] - f.params.loc[TERMS]))), 'max_focal_se_error': float(np.max(np.abs(se[ix] - f.bse.loc[TERMS]))), 'joint_p_error': abs(joint_p - result['joint_five_p'])}
        results.append(result)
    out = {'models': results, 'definition_note': 'has_text marks raw visible body; length>0 marks nonempty cleaned body. Neither filtering nor a missingness indicator recovers unrecorded text. These fits compare different observed populations and do not establish causality.',
           'multiple_testing_note': 'BH applied to five focal coefficients separately within each specification; no correction over all exploratory specifications. Do not select a model by significance.',
           'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'independent_verification': independent}
    (ROOT / 'results/teacher_complete_body_model.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
