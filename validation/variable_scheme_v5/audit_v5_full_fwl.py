#!/usr/bin/env python3
"""Independent full-v5 Frisch-Waugh-Lovell inference verification.

Reads the ignored private post labels and public post features, but exports only
aggregate counts and inference differences. No raw text or row/author identifiers
are written. Does not import the production analysis or independent-audit helpers.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from patsy import dmatrix
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'validation/classification_rebuild/private/variable_scheme_v5_production'
analysis=json.loads((ROOT/'results/v5_full_analysis.json').read_text())
summary=json.loads((ROOT/'results/v5_full_coding_summary.json').read_text())
features=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str})
labels=pd.read_csv(RUN/'post_labels.csv',dtype={'postId':str},keep_default_na=False)
assert len(features)==len(labels)==9532
data=features.merge(labels,on='postId',validate='one_to_one')
allcodes=list(analysis['variables'])
for code in allcodes:
    assert data[code].isin(['0','1','']).all()
    data[code]=pd.to_numeric(data[code].replace('',np.nan))
data=data[data.length.gt(0)].copy()
assert len(data)==5414
CONTROLS='log_length+has_tag+emoji_count+course_ref+C(contentTypeStr)+C(type)+C(time_bin)+C(author)+C(date)'

def bh(p):
    p=np.array(p);order=np.argsort(p);rank=np.arange(1,len(p)+1)
    ordered=np.minimum.accumulate((p[order]*len(p)/rank)[::-1])[::-1].clip(0,1)
    q=np.empty(len(p));q[order]=ordered
    return q

def check(frame,reported,weighted=False):
    codes=reported['codes']
    controls=dmatrix(CONTROLS,frame,return_type='dataframe',NA_action='raise').drop(columns=reported['dropped_redundant_control_columns'])
    F=frame[codes].to_numpy(dtype=float);y=frame.log_likes.to_numpy(dtype=float);Xc=controls.to_numpy(dtype=float)
    n=len(y);k=Xc.shape[1]+len(codes);G=frame.author.nunique()
    assert n==reported['n'] and G==reported['n_authors'] and k==reported['design_columns']==reported['rank']
    if weighted:
        w=1/frame.groupby('author')['author'].transform('size').to_numpy()
        scale=np.sqrt(w);Xc=Xc*scale[:,None];F=F*scale[:,None];y=y*scale
    Q,_=np.linalg.qr(Xc,mode='reduced')
    R=F-Q@(Q.T@F);v=y-Q@(Q.T@y)
    beta=np.linalg.lstsq(R,v,rcond=None)[0];u=v-R@beta
    H=np.linalg.inv(R.T@R);meat=np.zeros((len(codes),len(codes)))
    groups=frame.author.to_numpy()
    for g in np.unique(groups):
        score=R[groups==g].T@u[groups==g]
        meat+=np.outer(score,score)
    covariance=G/(G-1)*(n-1)/(n-k)*(H@meat@H)
    se=np.sqrt(np.diag(covariance));p=2*t.sf(abs(beta/se),G-1);crit=t.ppf(.975,G-1)
    maxdiff=0.
    for j,code in enumerate(codes):
        for field,value in [('beta',beta[j]),('se_cluster',se[j]),('p',p[j]),('ci_low',beta[j]-crit*se[j]),('ci_high',beta[j]+crit*se[j])]:
            expected=reported['coefficients'][code][field]
            assert np.isclose(value,expected,atol=1e-8,rtol=1e-7),(code,field,value,expected)
            maxdiff=max(maxdiff,abs(value-expected))
    return {'n':n,'n_authors':int(G),'full_columns':k,'t_df':int(G-1),'max_absolute_inference_difference':maxdiff}

maincodes=analysis['main']['codes'];main=data.dropna(subset=maincodes)
checks={'main_fwl':check(main,analysis['main'])}
for spec in ['separate_largest_samples','separate_same_main_sample']:
    checked={}
    for code,reported in analysis[spec].items():
        frame=(data.dropna(subset=[code]) if spec=='separate_largest_samples' else main)
        checked[code]=check(frame,reported)
    models=analysis[spec]
    qs=bh([models[c]['coefficients'][c]['p'] for c in maincodes])
    assert all(np.isclose(q,models[c]['coefficients'][c]['q_bh_within_family']) for c,q in zip(maincodes,qs))
    checks[spec]=checked

topic=analysis['topic_adjustment'];topiccodes=topic['with_topics']['codes'];tsample=data.dropna(subset=topiccodes)
checks['topic_expression_only']=check(tsample,topic['expression_only_same_sample'])
checks['topic_with_contents']=check(tsample,topic['with_topics'])
assert len(tsample)==topic['n'] and len(main)-len(tsample)==187
for fam in [maincodes,[c for c in topiccodes if c.startswith('T_')]]:
    qs=bh([topic['with_topics']['coefficients'][c]['p'] for c in fam])
    assert all(np.isclose(q,topic['with_topics']['coefficients'][c]['q_bh_within_family']) for c,q in zip(fam,qs))

counts=main.groupby('author').size();cut=main.likes.quantile(.99)
for name,frame,weighted in [('drop_top_1_percent_likes',main[main.likes.le(cut)],False),('authors_min_10',main[main.author.isin(counts.index[counts.ge(10)])],False),('author_equal_weight',main,True)]:
    checks[name]=check(frame,analysis['robustness'][name],weighted)

parent=data.S_EXPERIENCE.eq(1)|data.S_APPRAISAL.eq(1)
pol=data[parent&data.positive_tone.isin(['yes','no'])&data.negative_tone.isin(['yes','no'])].copy()
pol['polarity_group']=np.select([pol.positive_tone.eq('yes')&pol.negative_tone.eq('no'),pol.positive_tone.eq('no')&pol.negative_tone.eq('yes'),pol.positive_tone.eq('yes')&pol.negative_tone.eq('yes')],['positive_only','negative_only','mixed'],default='neither')
assert int(parent.sum())==1396 and len(pol)==1377
for code in analysis['polarity']['model']['codes']:pol[code]=pol.polarity_group.eq(code.removeprefix('POL_')).astype(int)
checks['conditional_polarity']=check(pol,analysis['polarity']['model'])

for reported in [analysis['main'],*analysis['robustness'].values(),topic['expression_only_same_sample'],analysis['polarity']['model']]:
    codes=reported['codes'];qs=bh([reported['coefficients'][c]['p'] for c in codes])
    assert all(np.isclose(q,reported['coefficients'][c]['q_bh_within_family']) for c,q in zip(codes,qs))

control=np.asarray(dmatrix(CONTROLS,main,return_type='dataframe'))
F=main[maincodes].to_numpy();X=np.column_stack([control,F])
vifcheck={}
for j,code in enumerate(maincodes,control.shape[1]):
    resid=F[:,j-control.shape[1]]-np.delete(X,j,axis=1)@np.linalg.lstsq(np.delete(X,j,axis=1),X[:,j],rcond=None)[0]
    vif=float(np.sum((X[:,j]-X[:,j].mean())**2)/np.sum(resid**2))
    assert np.isclose(vif,analysis['main_collinearity']['vif'][code],atol=1e-10)
    vifcheck[code]=vif

coverage={}
for axis,codes in [('expression',[c for c in allcodes if c.startswith('S_') and c!='S_OTHER']),('topic',[c for c in allcodes if c.startswith('T_') and c!='T_OTHER'])]:
    z=data[codes]
    coverage[axis]={'any_positive':int(z.eq(1).any(axis=1).sum()),'all_known':int(z.notna().all(axis=1).sum()),'all_negative':int(z.eq(0).all(axis=1).sum()),'no_positive_some_unknown':int((~z.eq(1).any(axis=1)&z.isna().any(axis=1)).sum())}
    assert all(summary['post_coverage']['axes'][axis][k]==v for k,v in coverage[axis].items())
out={'algorithm':'Frisch-Waugh-Lovell QR residualization, focal cluster scores, CR1 and t(G-1); no production analysis/audit helpers imported','checks':checks,'main_full_design_vif':vifcheck,'coverage':coverage,'parent_positive':int(parent.sum()),'both_polarity_known':len(pol),'no_raw_text_ids_or_authors_exported':True}
(ROOT/'validation/variable_scheme_v5/full_run_method_fwl_recalculation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed_model_checks':len(checks)-2+len(checks['separate_largest_samples'])+len(checks['separate_same_main_sample']),'main':checks['main_fwl'],'topic_n':len(tsample),'polarity_n':len(pol),'coverage':coverage,'main_vif_min':min(vifcheck.values()),'main_vif_max':max(vifcheck.values())},ensure_ascii=False))
