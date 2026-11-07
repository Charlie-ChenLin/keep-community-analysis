#!/usr/bin/env python3
"""Audit v3 label coexistence and full-design collinearity, not validity.

Nine labels are complete-case assessed. Nonconstant predictors with at least
one author showing within-author variation enter the joint diagnostic; sparse
support is flagged separately. Unknown is never silently replaced by zero.
"""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from patsy import dmatrix

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'validation/classification_rebuild/private/v3_refined_batches'
OUT=ROOT/'results/v3_collinearity_audit.json'
CONTROLS=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
          ' + C(time_bin) + C(author) + C(date)')
REGRESSION_MIN_COUNT=40; REGRESSION_MIN_AUTHORS=10

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if not (RUN/'merge_summary.json').is_file():raise ValueError('Validated complete v3 merge required')
    schema=json.loads((RUN/'frozen_schema.json').read_text());codes=list(schema['labels'])
    posts_path=ROOT/'results/post_features.csv'; labels_path=RUN/'post_labels.csv'
    posts=pd.read_csv(posts_path,dtype={'postId':str});labels=pd.read_csv(labels_path,dtype={'postId':str},keep_default_na=False)
    d=posts.merge(labels,on='postId',validate='one_to_one')
    if len(d)!=len(posts) or len(d)!=9532:raise ValueError('Post population mismatch')
    for c in codes:
        if not d[c].isin(['0','1','']).all():raise ValueError('Invalid three-state column: '+c)
        d[c]=pd.to_numeric(d[c].replace('',np.nan),errors='raise')
    complete=d.dropna(subset=codes).copy();n=len(complete)
    if not n:raise ValueError('No complete cases')
    selected=[];support=[]
    for c in codes:
        if not complete[c].isin([0,1]).all():raise ValueError('Nonbinary complete case')
        complete[c]=complete[c].astype(int)
        pos=int(complete[c].sum());neg=n-pos;vary=int(complete.groupby('author')[c].nunique().gt(1).sum())
        eligible=pos>0 and neg>0 and vary>0
        sparse=pos<REGRESSION_MIN_COUNT or neg<REGRESSION_MIN_COUNT or vary<REGRESSION_MIN_AUTHORS
        if eligible:selected.append(c)
        support.append({'code':c,'label':schema['labels'][c], 'positive_posts':pos,
                        'negative_posts':neg,'authors_with_within_variation':vary,'included':eligible,
                        'low_support_for_regression':sparse})
    if not selected:raise ValueError('No labels have sufficient support')
    matrix=dmatrix(CONTROLS+' + '+' + '.join(selected),data=complete,return_type='dataframe',NA_action='raise')
    controls=dmatrix(CONTROLS,data=complete,return_type='dataframe',NA_action='raise')
    X=matrix.to_numpy(dtype=float);rank=int(np.linalg.matrix_rank(X))
    binary=complete[selected];raw_corr=binary.corr()
    cx=controls.to_numpy(dtype=float)
    residual=binary.to_numpy(dtype=float)-cx@np.linalg.lstsq(cx,binary.to_numpy(dtype=float),rcond=None)[0]
    residual_corr=pd.DataFrame(residual,columns=selected).corr()
    pairs=[]
    for i,a in enumerate(selected):
        for b in selected[i+1:]:
            pairs.append({'first':a,'second':b,'joint_positive_posts':int((binary[a].eq(1)&binary[b].eq(1)).sum()),
                          'phi':float(raw_corr.loc[a,b]),'correlation_after_controls':float(residual_corr.loc[a,b])})
    vifs={};condition=None
    if rank==X.shape[1]:
        values=matrix.drop(columns=['Intercept']).to_numpy(dtype=float);scales=values.std(axis=0)
        if np.any(scales<=0):raise ValueError('Unexpected constant predictor')
        z=(values-values.mean(axis=0))/scales;correlation=(z.T@z)/n;inv=np.linalg.inv(correlation)
        col=matrix.drop(columns=['Intercept']).columns
        singular=np.linalg.svd(z,compute_uv=False);condition=float(singular[0]/singular[-1])
        for c in selected:
            vif=float(inv[col.get_loc(c),col.get_loc(c)])
            index=matrix.columns.get_loc(c);y=X[:,index];other=np.delete(X,index,axis=1)
            residual=y-other@np.linalg.lstsq(other,y,rcond=None)[0]
            direct=float(np.sum((y-y.mean())**2)/np.sum(residual**2))
            if not np.isclose(vif,direct,atol=1e-7,rtol=1e-7):raise ValueError('VIF check failed '+c)
            vifs[c]=vif
    for r in support:r['vif_full_design']=vifs.get(r['code'])
    npos=complete[codes].sum(axis=1)
    result={'scope':'Nine v3 AI-assisted expression variables: post-level, complete across all nine; not human-validated',
            'n_total':len(d),'n_nonempty_body':int(d.length.gt(0).sum()),'n_complete_all_nine':n,
            'n_excluded_any_unknown':int(len(d)-n),'n_authors':int(complete.author.nunique()),
            'diagnostic_thresholds':{'positive_and_negative':1,'authors_within_variation':1},
            'regression_support_flag_thresholds':{'positive_and_negative':REGRESSION_MIN_COUNT,'authors_within_variation':REGRESSION_MIN_AUTHORS},
            'coexistence_distribution':{str(k):int(v) for k,v in npos.value_counts().sort_index().items()},
            'at_least_two_positive':int(npos.ge(2).sum()),'variables':support,'pairs':pairs,
            'max_absolute_phi':max([abs(p['phi']) for p in pairs],default=None),
            'max_absolute_residual_correlation':max([abs(p['correlation_after_controls']) for p in pairs],default=None),
            'design_matrix':{'rows':n,'columns':X.shape[1],'rank':rank,'full_rank':rank==X.shape[1],
                             'condition_number_standardized':condition},
            'controls':CONTROLS,'outcome_used':False,
            'limitations':['Simultaneous model is a diagnostic, not the separately fitted regressions.',
             'Low VIF does not validate semantics or remove unmeasured confounding.',
             'AI annotations are not human gold labels.',
             'Complete-case sample and rare-label thresholds limit scope.'],
            'source_hashes':{'post_features.csv':digest(posts_path),'post_labels.csv':digest(labels_path)}}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'n':n,'authors':result['n_authors'],
                      'full_rank':result['design_matrix']['full_rank'],'variables':support},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
