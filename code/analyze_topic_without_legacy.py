#!/usr/bin/env python3
"""Retrospective NMF weight regressions without the four legacy word rules.

Frozen NMF weights and sample are reused; no topic model is re-estimated and
no outcome is used to select text features. Output is exploratory and is not
a validated semantic category effect.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/topic_continuous_without_legacy.json'
TOPICS=[f'topic_{i}' for i in range(5)]
TERMS=['topic_0','topic_1','topic_3','topic_4']


def main():
    posts=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str})
    topics=pd.read_csv(ROOT/'results/extension_post_topics.csv',dtype={'postId':str})
    assert posts.postId.is_unique and topics.postId.is_unique
    authors=posts[['postId','author']].merge(topics[['postId','author']],on='postId',validate='one_to_one',suffixes=('_post','_topic'))
    # Different pipeline stages use different pseudonyms; check bijection
    # rather than requiring identical strings.
    assert authors.groupby('author_post').author_topic.nunique().max()==1
    assert authors.groupby('author_topic').author_post.nunique().max()==1
    frame=posts.merge(topics.drop(columns='author'),on='postId',validate='one_to_one')
    assert len(frame)==2470 and frame.author.nunique()==86
    weights=frame[TOPICS].to_numpy(dtype=float)
    assert np.isfinite(weights).all() and (weights>=0).all()
    err=float(np.max(np.abs(weights.sum(axis=1)-1)))
    assert err<1e-8
    counts=frame.groupby('author').size()
    rhs=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
         ' + C(time_bin) + C(author) + C(date) + '+' + '.join(TERMS))
    results=[]
    for cutoff in [1,2,5,10]:
        data=frame.loc[frame.author.isin(counts.index[counts.ge(cutoff)])].copy()
        model=smf.ols('log_likes ~ '+rhs,data=data,missing='raise')
        rank=int(np.linalg.matrix_rank(model.exog))
        if rank!=model.exog.shape[1]:raise ValueError(f'Cutoff {cutoff}: rank deficient')
        fit=model.fit(cov_type='cluster',cov_kwds={'groups':data.author,'use_correction':True,'df_correction':True},use_t=True)
        ci=fit.conf_int();q=multipletests([fit.pvalues[x] for x in TERMS],method='fdr_bh')[1]
        joint=fit.wald_test(' = 0, '.join(TERMS)+' = 0',scalar=True)
        results.append({'minimum_topic_posts_per_author':cutoff,'n':int(fit.nobs),
                        'authors':int(data.author.nunique()),'rank':rank,'parameters':len(fit.params),
                        'joint_topic_p':float(joint.pvalue),'r_squared':float(fit.rsquared),
                        'coefficients':[{'term':x,'coef':float(fit.params[x]),'se_cluster':float(fit.bse[x]),
                         'p':float(fit.pvalues[x]),'q_bh':float(qq),'ci_low':float(ci.loc[x,0]),
                         'ci_high':float(ci.loc[x,1])} for x,qq in zip(TERMS,q)]})
    prior=json.loads((ROOT/'results/teacher_topic_author_support.json').read_text())
    prior_models={str(x['minimum_topic_posts_per_author']):{'n':x['n'],'authors':x['authors'],
                  'joint_topic_p':x['joint_topic_p']} for x in prior['models']}
    out={'status':'retrospective_exploratory','n_topics':5,'reference_topic':2,
         'n_posts':len(frame),'n_authors':int(frame.author.nunique()),
         'author_pseudonym_mapping_bijective':True,
         'max_normalized_weight_sum_error':err,'formula':'log_likes ~ '+rhs,
         'old_four_lexical_indicators_in_model':False,'covariance':'author-clustered finite-sample correction, t/F inference',
         'coefficient_interpretation':'Shift weight from topic 2 to topic k holding the other weights and covariates fixed; 0.1 units is 10 percentage points.',
         'models':results,'prior_with_legacy_controls':prior_models,
         'limitations':['Observed nonempty text sample; missing exposure and observation window.',
                        'NMF components are not verified semantic categories.',
                        'Confidence intervals condition on fitted weights and exclude topic-model estimation uncertainty.',
                        'BH is applied to four terms within each model, not across all explored models.']}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'max_weight_sum_error':err,
          'models':[{k:v for k,v in x.items() if k!='coefficients'} for x in results]},ensure_ascii=False))

if __name__=='__main__':main()
