#!/usr/bin/env python3
"""Analyze uniformly reread v5 labels under the frozen full-run protocol.

Controls, support screens, contrasts and sensitivity families are fixed before
full-corpus results. Semantic unknown and structural NA are never filled zero.
"""
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
from patsy import dmatrix
from scipy.linalg import qr
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'validation/classification_rebuild/private/variable_scheme_v5_production'
OUT=ROOT/'results/v5_full_analysis.json'
CONTROLS=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
          ' + C(time_bin) + C(author) + C(date)')
NAMES={'S_PRESENT':'记录与展示','S_EXPERIENCE':'自身体验','S_APPRAISAL':'对象评价','S_FUTURE':'未来安排与目标',
 'S_EXHORT':'鼓励与提醒','S_REFLECTION':'观点与感悟','S_GUIDANCE':'解释与方法建议','S_SOCIAL':'问候祝愿与致谢',
 'S_REQUEST':'征询与邀请','S_OFFER':'供给告知','S_OTHER':'其他明确表达',
 'T_ACTIVITY':'运动训练','T_BODY':'身体健康','T_FOOD':'饮食营养','T_LIFE':'具体生活','T_TOOLS':'工具服务','T_OTHER':'其他明确对象'}
ALL_CODES=list(NAMES)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def support(data,code):
    known=data.loc[data[code].notna()];pos=int(known[code].eq(1).sum());neg=int(known[code].eq(0).sum())
    authors=known.groupby('author')[code].nunique();vary=int(authors.gt(1).sum())
    positive_by_author=known.loc[known[code].eq(1)].groupby('author').size()
    return {'n_known':len(known),'n_positive':pos,'n_negative':neg,'n_authors':int(known.author.nunique()),
      'authors_within_variation':vary,'positive_authors':int(len(positive_by_author)),
      'largest_author_share_of_positives':float(positive_by_author.max()/pos) if pos else None,
      'passes_support':bool(pos>=40 and neg>=40 and vary>=10)}

def stable_candidates(data,candidates):
    initial={c:support(data,c) for c in candidates};selected=[c for c in candidates if initial[c]['passes_support']];steps=[]
    while selected:
        common=data.dropna(subset=selected).copy();info={c:support(common,c) for c in selected}
        failed=[c for c in selected if not info[c]['passes_support']]
        steps.append({'selected':selected.copy(),'n_common':len(common),'support':info,'removed_for_common_support':failed})
        if not failed:break
        selected=[c for c in selected if c not in failed]
    common=data.dropna(subset=selected).copy() if selected else data.iloc[:0].copy()
    return selected,common,{'initial_support':initial,'steps':steps,'selected':selected,'n_common':len(common),
      'excluded_candidates':[c for c in candidates if c not in selected]}

def control_design(data):
    design=dmatrix(CONTROLS,data=data,return_type='dataframe',NA_action='raise')
    values=design.to_numpy(dtype=float);rank=int(np.linalg.matrix_rank(values));dropped=[]
    if rank!=values.shape[1]:
        # Intercept is retained; pivoted QR acts only on centered controls.
        assert design.columns[0]=='Intercept'
        centered=values[:,1:]-values[:,1:].mean(axis=0)
        _,r,pivot=qr(centered,mode='economic',pivoting=True)
        rank_centered=int(np.linalg.matrix_rank(centered));keep=[0]+sorted(int(j)+1 for j in pivot[:rank_centered])
        dropped=[c for i,c in enumerate(design.columns) if i not in keep];design=design.iloc[:,keep]
        if np.linalg.matrix_rank(design.to_numpy())!=design.shape[1]:raise ValueError('Control rank repair failed')
    return design,dropped

def design_matrix(data,codes):
    controls,dropped=control_design(data)
    if data[codes].isna().any().any():raise ValueError('Unknown focal value passed to model')
    focal=data[codes].astype(float);design=pd.concat([controls,focal],axis=1)
    if design.columns.duplicated().any():raise ValueError('Duplicate design names')
    return design,dropped

def bh(model):
    rows=list(model.get('coefficients',{}).values())
    if rows:
        for r,q in zip(rows,multipletests([r['p'] for r in rows],method='fdr_bh')[1]):r['q_bh_within_family']=float(q)
    return model

def fit(data,codes,weighted=False,check_support=True):
    if not len(data) or not codes:return {'status':'insufficient_design','n':len(data),'codes':codes}
    info={c:support(data,c) for c in codes}
    if check_support and any(not v['passes_support'] for v in info.values()):return {'status':'insufficient_support','n':len(data),'support':info,'codes':codes}
    design,dropped=design_matrix(data,codes);X=design.to_numpy(dtype=float);rank=int(np.linalg.matrix_rank(X))
    base={'n':len(data),'n_authors':int(data.author.nunique()),'n_dates':int(data.date.nunique()),'codes':codes,
      'support':info,'design_columns':design.shape[1],'rank':rank,'dropped_redundant_control_columns':dropped,'author_equal_weight':weighted}
    if rank!=X.shape[1]:return {**base,'status':'focal_rank_deficient_no_silent_focal_drop'}
    y=data.log_likes.to_numpy(dtype=float)
    weights=1/data.groupby('author')['author'].transform('size') if weighted else None
    result=(sm.WLS(y,design,weights=weights) if weighted else sm.OLS(y,design)).fit(
      cov_type='cluster',cov_kwds={'groups':data.author,'use_correction':True,'df_correction':True},use_t=True)
    ci=result.conf_int();coef={}
    for c in codes:
        coef[c]={'label':NAMES.get(c,c),'beta':float(result.params[c]),'se_cluster':float(result.bse[c]),
          'p':float(result.pvalues[c]),'ci_low':float(ci.loc[c,0]),'ci_high':float(ci.loc[c,1])}
    return bh({**base,'status':'estimated_retrospective_exploratory','coefficients':coef,'r_squared':float(result.rsquared)})

def vif(data,codes):
    if not codes or not len(data):return {'status':'insufficient_design'}
    design,dropped=design_matrix(data,codes);X=design.to_numpy(dtype=float);rank=int(np.linalg.matrix_rank(X))
    out={'n':len(data),'n_authors':int(data.author.nunique()),'codes':codes,'rank':rank,'columns':design.shape[1],
      'controls':CONTROLS,'dropped_redundant_control_columns':dropped}
    if rank!=X.shape[1]:return {**out,'status':'rank_deficient'}
    no_intercept=design.drop(columns='Intercept');V=no_intercept.to_numpy(dtype=float);Z=(V-V.mean(axis=0))/V.std(axis=0)
    inverse=np.linalg.inv(Z.T@Z/len(data));vifs={};direct={}
    for c in codes:
        j=design.columns.get_loc(c);y=X[:,j];other=np.delete(X,j,axis=1);resid=y-other@np.linalg.lstsq(other,y,rcond=None)[0]
        direct[c]=float(np.sum((y-y.mean())**2)/np.sum(resid**2));vifs[c]=float(inverse[no_intercept.columns.get_loc(c),no_intercept.columns.get_loc(c)])
        if not np.isclose(direct[c],vifs[c],atol=1e-7,rtol=1e-7):raise ValueError('VIF residual check failed')
    binary=data[codes];raw=binary.corr();ctrl,_=control_design(data);cx=ctrl.to_numpy(dtype=float)
    residual=binary.to_numpy(dtype=float)-cx@np.linalg.lstsq(cx,binary.to_numpy(dtype=float),rcond=None)[0]
    rc=np.corrcoef(residual,rowvar=False) if len(codes)>1 else np.array([[1.]])
    pairs=[]
    for i,a in enumerate(codes):
        for j,b in enumerate(codes[i+1:],i+1):pairs.append({'first':a,'second':b,'phi':float(raw.loc[a,b]),
          'both_positive':int((binary[a].eq(1)&binary[b].eq(1)).sum()),'correlation_after_controls':float(rc[i,j])})
    return {**out,'status':'full_rank_full_control_design','vif':vifs,'vif_independent_residual':direct,
      'min_vif':min(vifs.values()),'max_vif':max(vifs.values()),'vif_ge_5':[c for c,v in vifs.items() if v>=5],
      'top_absolute_phi_pairs':sorted(pairs,key=lambda p:abs(p['phi']),reverse=True)[:12]}

def label_models(data,codes):
    result={}
    for c in codes:
        single=fit(data.dropna(subset=[c]),[c]);result[c]=single
    estimated=[m['coefficients'][c] for c,m in result.items() if m.get('status')=='estimated_retrospective_exploratory']
    if estimated:
        for row,q in zip(estimated,multipletests([r['p'] for r in estimated],method='fdr_bh')[1]):row['q_bh_within_family']=float(q)
    return result

def polarity_model(data):
    eligible=data.loc[(data.S_EXPERIENCE.eq(1)|data.S_APPRAISAL.eq(1)) & data.positive_tone.isin(['yes','no']) & data.negative_tone.isin(['yes','no'])].copy()
    eligible['polarity_group']=np.select([eligible.positive_tone.eq('yes')&eligible.negative_tone.eq('no'),
      eligible.positive_tone.eq('no')&eligible.negative_tone.eq('yes'),eligible.positive_tone.eq('yes')&eligible.negative_tone.eq('yes')],
      ['positive_only','negative_only','mixed'],default='neither')
    counts={k:int(v) for k,v in eligible.polarity_group.value_counts().items()}
    levels=sorted(counts);codes={level:'POL_'+level for level in levels}
    for level,code in codes.items():eligible[code]=eligible.polarity_group.eq(level).astype(int)
    info={level:support(eligible,code) for level,code in codes.items()};selected=[x for x in levels if info[x]['passes_support']]
    retained=eligible.loc[eligible.polarity_group.isin(selected)].copy()
    final_info={level:support(retained,codes[level]) for level in selected}
    selected=[level for level in selected if final_info[level]['passes_support']]
    retained=retained.loc[retained.polarity_group.isin(selected)].copy()
    summary={'parent_positive':int((data.S_EXPERIENCE.eq(1)|data.S_APPRAISAL.eq(1)).sum()),'n_known_both_polarity':len(eligible),
      'counts':counts,'support_initial':info,'retained_levels':selected,'excluded_levels':[x for x in levels if x not in selected],
      'n_retained':len(retained),'population':'Only explicit experience/appraisal parents, both attributes known, retained supported polarity groups.'}
    if len(selected)<2:return {**summary,'status':'insufficient_group_support'}
    reference='positive_only' if 'positive_only' in selected else sorted(selected,key=lambda x:(-counts[x],x))[0]
    focal=[codes[x] for x in selected if x!=reference]
    names={'positive_only':'仅显性正向','negative_only':'仅显性负向','mixed':'正负并存','neither':'均无显性方向'}
    for x in selected:NAMES[codes[x]]=names[x]+'（参照：'+names[reference]+'）'
    estimated=fit(retained,focal);diag=vif(retained,focal)
    return {**summary,'reference':reference,'model':estimated,'collinearity':diag,'status':estimated['status']}

def main():
    if not (RUN/'merge_summary.json').is_file():raise ValueError('Complete validated v5 merge required')
    summary=js(RUN/'merge_summary.json');freeze=js(RUN/'full_run_freeze.json');protocol=js(RUN/'frozen_full_analysis_protocol.json')
    if sha(ROOT/'code/v5_full_analysis_protocol.json')!=freeze['analysis_protocol_sha256'] or sha(ROOT/'results/post_features.csv')!=freeze['post_features_sha256']:
        raise ValueError('Frozen protocol/outcome source changed')
    if sha(RUN/'post_labels.csv')!=summary['post_labels_sha256']:raise ValueError('Production labels changed')
    posts=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str});labels=pd.read_csv(RUN/'post_labels.csv',dtype={'postId':str},keep_default_na=False)
    data=posts.merge(labels,on='postId',validate='one_to_one')
    if len(data)!=9532 or data.postId.duplicated().any():raise ValueError('Population or join mismatch')
    if not np.allclose(data.log_likes,np.log1p(data.likes)) or not np.isfinite(data.log_likes).all():raise ValueError('Outcome transform mismatch')
    for c in ALL_CODES:
        if not data[c].isin(['0','1','']).all():raise ValueError('Invalid binary/unknown code')
        data[c]=pd.to_numeric(data[c].replace('',np.nan),errors='raise')
    nonempty=data.loc[data.length.gt(0)].copy()
    if len(nonempty)!=5414 or not nonempty.input_status.eq('needs_model').all():raise ValueError('Semantic population mismatch')
    variables={c:{'label':NAMES[c],**support(nonempty,c),'n_unknown_nonempty':int(nonempty[c].isna().sum())} for c in ALL_CODES}
    main_codes,main_data,selection=stable_candidates(nonempty,protocol['main_candidate_parents'])
    main_model=fit(main_data,main_codes);main_vif=vif(main_data,main_codes)
    separate_max=label_models(nonempty,main_codes);separate_common=label_models(main_data,main_codes)
    topic_codes,topic_data,topic_selection=stable_candidates(nonempty,main_codes+protocol['topic_candidates'])
    if set(main_codes)-set(topic_codes):
        topic={'status':'main_parent_support_lost_in_topic_sample','selection':topic_selection}
    else:
        topic={'status':'evaluated','selection':topic_selection,'n':len(topic_data),'n_excluded_from_main':len(main_data)-len(topic_data),
          'expression_only_same_sample':fit(topic_data,main_codes),'with_topics':fit(topic_data,topic_codes),'collinearity':vif(topic_data,topic_codes)}
        # Adjust expression tests and topic tests as separate predeclared families.
        if topic['with_topics'].get('coefficients'):
            for family in [main_codes,[c for c in topic_codes if c not in main_codes]]:
                if family:
                    vals=[topic['with_topics']['coefficients'][c] for c in family]
                    for row,q in zip(vals,multipletests([x['p'] for x in vals],method='fdr_bh')[1]):row['q_bh_within_family']=float(q)
    cutoff=float(main_data.likes.quantile(.99));trim=main_data.loc[main_data.likes.le(cutoff)].copy()
    counts=main_data.groupby('author').size();atleast10=main_data.loc[main_data.author.isin(counts.index[counts.ge(10)])].copy()
    robust={'drop_top_1_percent_likes':{**fit(trim,main_codes),'likes_cutoff':cutoff,'excluded_posts':len(main_data)-len(trim)},
      'authors_min_10':{**fit(atleast10,main_codes),'excluded_posts':len(main_data)-len(atleast10)},'author_equal_weight':fit(main_data,main_codes,weighted=True)}
    polarity=polarity_model(nonempty)
    result={'status':'full_v5_retrospective_exploratory_AI_measurement_not_human_validated','n_total':9532,'n_nonempty':5414,
      'n_unique_texts':4156,'variables':variables,'main_selection':selection,'main':main_model,'main_collinearity':main_vif,
      'separate_largest_samples':separate_max,'separate_same_main_sample':separate_common,'topic_adjustment':topic,
      'polarity':polarity,'robustness':robust,'controls':CONTROLS,'legacy_four_used_as_controls':False,
      'outcome':'log(1+likes)','clustering':'author','n_independent_human_reviews':0,
      'input_sha256':{'post_features':sha(ROOT/'results/post_features.csv'),'post_labels':sha(RUN/'post_labels.csv'),
        'analysis_protocol':sha(RUN/'frozen_full_analysis_protocol.json'),'coding_summary':sha(ROOT/'results/v5_full_coding_summary.json')},
      'limits':protocol['limits']}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'main_codes':main_codes,'main_n':len(main_data),'main_status':main_model['status'],
      'main_vif':{k:main_vif.get(k) for k in ['status','min_vif','max_vif']},'main_coefficients':main_model.get('coefficients'),
      'polarity_status':polarity['status']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
