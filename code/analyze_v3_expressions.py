#!/usr/bin/env python3
"""Exploratory separate-label models of fully reread v3 AI annotations.

The nine-label definitions are frozen before re-coding. Unknown labels are
excluded per variable, not coded as zero. No labels are selected by outcomes or
p-values. All estimates remain retrospective and lack independent human gold.
"""
from pathlib import Path
from collections import Counter
import hashlib,json

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'validation/classification_rebuild/private/v3_refined_batches'
OUT=ROOT/'results/v3_expression_analysis.json'
CONTROLS=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
          ' + C(time_bin) + C(author) + C(date)')
MIN_COUNT=40; MIN_AUTHORS=10

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def support(df,code):
    pos=int(df[code].eq(1).sum()); neg=int(df[code].eq(0).sum())
    vary=int(df.groupby('author')[code].nunique().gt(1).sum())
    return {'n':len(df),'authors':int(df.author.nunique()),'n_positive':pos,'n_negative':neg,
            'authors_within_variation':vary,'eligible':bool(pos>=MIN_COUNT and neg>=MIN_COUNT and vary>=MIN_AUTHORS)}

def fit(df,code,weighted=False):
    s=support(df,code)
    if not s['eligible']:return {**s,'status':'insufficient_support'}
    formula='log_likes ~ '+CONTROLS+' + '+code
    weights=1/df.groupby('author')['author'].transform('size') if weighted else None
    model=smf.wls(formula,data=df,weights=weights,missing='raise') if weighted else smf.ols(formula,data=df,missing='raise')
    rank=int(np.linalg.matrix_rank(model.exog));columns=int(model.exog.shape[1])
    if rank!=columns:return {**s,'status':'rank_deficient','rank':rank,'design_columns':columns}
    result=model.fit(cov_type='cluster',cov_kwds={'groups':df.author,'use_correction':True,'df_correction':True},use_t=True)
    ci=result.conf_int()
    return {**s,'status':'estimated_exploratory','beta':float(result.params[code]),
            'se_cluster':float(result.bse[code]),'p':float(result.pvalues[code]),
            'ci_low':float(ci.loc[code,0]),'ci_high':float(ci.loc[code,1]),
            'rank':rank,'design_columns':columns,'author_equal_weight':weighted}

def bh(items):
    valid=[x for x in items.values() if x['status']=='estimated_exploratory']
    if valid:
        for row,q in zip(valid,multipletests([x['p'] for x in valid],method='fdr_bh')[1]):
            row['q_bh_within_v3_family']=float(q)

def main():
    if not (RUN/'merge_summary.json').is_file():raise ValueError('Full validated v3 merge required')
    schema=json.loads((RUN/'frozen_schema.json').read_text());codes=list(schema['labels'])
    p=ROOT/'results/post_features.csv'; labels_path=RUN/'post_labels.csv'
    posts=pd.read_csv(p,dtype={'postId':str});labels=pd.read_csv(labels_path,dtype={'postId':str},keep_default_na=False)
    data=posts.merge(labels,on='postId',validate='one_to_one')
    if len(data)!=len(posts) or len(data)!=9532:raise ValueError('Population mismatch')
    for code in codes:
        if not data[code].isin(['0','1','']).all():raise ValueError('Invalid three-state code: '+code)
        data[code]=pd.to_numeric(data[code].replace('',np.nan),errors='raise')
    nonempty=data.loc[data.length.gt(0)].copy();readable=nonempty.loc[nonempty.observation_state.eq('readable')]
    known_count=nonempty[codes].notna().sum(axis=1);positive_count=nonempty[codes].eq(1).sum(axis=1)
    coverage={'n_nonempty':len(nonempty),'at_least_one_positive':int(positive_count.ge(1).sum()),
              'at_least_two_positive':int(positive_count.ge(2).sum()),'all_nine_known':int(known_count.eq(9).sum()),
              'no_positive_all_known':int((positive_count.eq(0)&known_count.eq(9)).sum()),
              'no_positive_has_unknown':int((positive_count.eq(0)&known_count.lt(9)).sum()),
              'positive_count_distribution':{str(k):int(v) for k,v in positive_count.value_counts().sort_index().items()},
              'note':'Positive coverage is model tagging and must not be interpreted as classification accuracy.'}
    # Preserve prior auxiliary expressions as a separate historical signal,
    # never as newly coded v3 labels or a substitute for an unknown v3 value.
    prior_path=ROOT/'validation/classification_rebuild/private/v2_direct_batches/post_labels.csv'
    prior=pd.read_csv(prior_path,dtype={'postId':str},keep_default_na=False)[['postId','expression_labels']]
    cross=nonempty.merge(prior,on='postId',validate='one_to_one')
    cross_positive=cross[codes].eq(1).any(axis=1)
    aux={'F_REFLECTION','F_GUIDANCE','F_CAPTION'}
    prior_aux=cross.expression_labels.map(lambda s:bool(set(json.loads(s) if s else []) & aux))
    recovered=(~cross_positive)&prior_aux
    cross_round={'prior_v2_auxiliary_codes':sorted(aux),'n_with_any_prior_aux':int(prior_aux.sum()),
                 'n_without_v3_positive_but_with_prior_aux':int(recovered.sum()),
                 'of_these_v3_readable':int((recovered & cross.observation_state.eq('readable')).sum()),
                 'of_these_v3_insufficient':int((recovered & cross.observation_state.eq('insufficient')).sum()),
                 'n_either_v3_or_prior_aux':int((cross_positive|prior_aux).sum()),
                 'note':'Cross-round AI labels have different definitions; conflicts and unknowns are not resolved or zero-filled.'}
    summary={};models={'main':{},'drop_top_1_percent_likes':{},'authors_min_10_in_base_sample':{},'author_equal_weight':{}}
    for code,label in schema['labels'].items():
        eligible=data.loc[data[code].notna()].copy();eligible[code]=eligible[code].astype(int)
        s=support(eligible,code);positive_author=eligible.loc[eligible[code].eq(1)].groupby('author').size()
        summary[code]={**s,'label':label,'n_unknown_all_posts':int(data[code].isna().sum()),
                       'n_unknown_nonempty':int(nonempty[code].isna().sum()),
                       'largest_author_share_of_positives':float(positive_author.max()/s['n_positive']) if s['n_positive'] else None}
        models['main'][code]=fit(eligible,code)
        cutoff=float(eligible.likes.quantile(.99)); trimmed=eligible.loc[eligible.likes.le(cutoff)].copy()
        models['drop_top_1_percent_likes'][code]={**fit(trimmed,code),'likes_cutoff':cutoff,'excluded_posts':len(eligible)-len(trimmed)}
        author_n=eligible.groupby('author').size();selected=eligible.loc[eligible.author.isin(author_n.index[author_n.ge(10)])].copy()
        models['authors_min_10_in_base_sample'][code]={**fit(selected,code),'excluded_posts':len(eligible)-len(selected)}
        models['author_equal_weight'][code]=fit(eligible,code,weighted=True)
    for spec in models.values():bh(spec)
    counts=Counter(readable.loc[readable.V3_EXHORT.eq(1),'exhortation_target'])
    result={'status':'retrospective_exploratory_not_human_validated',
            'n_total':len(data),'input_status':data.input_status.value_counts().to_dict(),
            'observation_state_nonempty':nonempty.observation_state.value_counts().to_dict(),
            'coverage':coverage,'prior_auxiliary_comparison':cross_round,'variables':summary,'models':models,
            'exhortation_target_among_exhort_positive':dict(counts),
            'controls':CONTROLS,'legacy_four_used_as_controls':False,
            'support_thresholds':{'positive_and_negative':MIN_COUNT,'authors_within_variation':MIN_AUTHORS},
            'model_structure':'one separate model per label; eligible sample is label-specific; labels can overlap',
            'limits':['AI predictions are not independent human ground truth.',
              'Definitions chosen after earlier exploratory analyses; no p-value-based feature selection.',
              'BH controls within the estimated v3 labels separately per specification, not all historical explorations.',
              'Missing exposure and observation-window variation remain unmeasured.',
              'Multicollinearity in a simultaneous design is a separate diagnostic, not the single-label model.'],
            'input_sha256':{'post_features.csv':sha(p),'v3_post_labels.csv':sha(labels_path),
                            'v2_post_labels.csv':sha(prior_path)}}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'n_total':len(data),'coverage':coverage,
                      'main_status':{k:v['status'] for k,v in models['main'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
