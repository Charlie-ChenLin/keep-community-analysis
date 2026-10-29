"""Check author support within the actual NMF regression subsample."""
from pathlib import Path
import json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
FOCAL = ['log_length', 'self_discipline', 'social_address', 'positive_expression', 'question']


def main():
    p = pd.read_csv(ROOT/'results/post_features.csv')
    t = pd.read_csv(ROOT/'results/extension_post_topics.csv').drop(columns='author')
    data = p.merge(t, on='postId', how='inner', validate='one_to_one')
    counts = data.groupby('author').size()
    terms = ['topic_0', 'topic_1', 'topic_3', 'topic_4']
    rhs = ' + '.join(FOCAL+['has_tag','emoji_count','course_ref']) + ' + C(contentTypeStr) + C(type) + C(time_bin) + C(author) + C(date) + ' + ' + '.join(terms)
    models = []
    for cutoff in [1,2,5,10]:
        frame = data.loc[data.author.isin(counts.index[counts.ge(cutoff)])].copy()
        fit = smf.ols('log_likes ~ '+rhs, data=frame).fit(cov_type='cluster', cov_kwds={'groups':frame.author,'use_correction':True,'df_correction':True}, use_t=True)
        ci=fit.conf_int()
        q=multipletests([fit.pvalues[x] for x in terms],method='fdr_bh')[1]
        rank=int(np.linalg.matrix_rank(fit.model.exog))
        assert rank==len(fit.params)
        models.append({'minimum_topic_posts_per_author':cutoff,'n':int(fit.nobs),'authors':int(frame.author.nunique()),'rank':rank,'parameters':len(fit.params),
                       'joint_topic_p':float(fit.wald_test(' = 0, '.join(terms)+' = 0',scalar=True).pvalue),
                       'coefficients':[{'term':x,'coef':float(fit.params[x]),'p':float(fit.pvalues[x]),'q_bh':float(qq),'ci_low':float(ci.loc[x,0]),'ci_high':float(ci.loc[x,1])}for x,qq in zip(terms,q)]})
    old=pd.read_csv(ROOT/'results/extension_topic_regression.csv')
    baseline={x['term']:x['coef'] for x in models[0]['coefficients']}
    assert all(np.isclose(baseline[f'topic_{int(x.topic)}'],x.coef,atol=1e-10)for x in old.itertuples())
    out={'topic_documents':len(data),'topic_authors':len(counts),'author_count_min':int(counts.min()),'author_count_median':float(counts.median()),'author_count_max':int(counts.max()),
         'small_author_counts':[{'at_most_topic_posts':k,'authors':int(counts.le(k).sum()),'posts':int(counts[counts.le(k)].sum())}for k in [1,2,5,10]],
         'models':models,'note':'Author counts are recomputed inside the 2470-post topic subset, not carried over from all 9532 posts. Frozen topics and reference topic 2 retained. These are estimator diagnostics; low semantic validity of the original component names is not repaired by author exclusions.'}
    (ROOT/'results/teacher_topic_author_support.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items()if k!='models'},ensure_ascii=False))
    print(json.dumps([{k:v for k,v in x.items()if k!='coefficients'}for x in models],ensure_ascii=False))


if __name__=='__main__':
    main()
