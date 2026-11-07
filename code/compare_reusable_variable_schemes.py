#!/usr/bin/env python3
"""Outcome-blind reusable scheme comparison with explicit historical conflicts.

No coding is changed or reconciled. Cross-round unions are diagnostic only.
All inputs remain private; only aggregate metadata and diagnostics are saved.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd
from patsy import dmatrix
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
OUT=ROOT/'results/reusable_variable_scheme_comparison.json'
CONTROLS=('log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)'
          ' + C(time_bin) + C(author) + C(date)')
MIN_COUNT=40;MIN_AUTHORS=10
SPEC=importlib.util.spec_from_file_location('historical',ROOT/'code/audit_variable_scheme_history.py')
historical=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(historical)


def supported(x,authors):
    known=x.notna();pos=int(x.eq(1).sum());neg=int(x.eq(0).sum())
    vary=int(x.loc[known].groupby(authors.loc[known]).nunique().gt(1).sum())
    return {'n_known':int(known.sum()),'n_positive':pos,'n_negative':neg,
        'authors_within_variation':vary,'passes_support_threshold':pos>=MIN_COUNT and neg>=MIN_COUNT and vary>=MIN_AUTHORS}


def collinearity(mat,posts):
    support={c:supported(mat[c],posts.author) for c in mat}
    codes=[c for c,s in support.items() if s['passes_support_threshold']]
    data=posts.join(mat,validate='one_to_one').dropna(subset=codes).copy()
    full_support={c:supported(data[c],data.author) for c in codes}
    result={'outcome_used':False,'controls':CONTROLS,
        'selection':'Only previous fixed thresholds: >=40 positives, >=40 negatives, >=10 authors with within-author variation on label-specific known rows. No outcome or p-value used.',
        'all_label_specific_support':support,'diagnostic_labels':codes,
        'excluded_labels':[c for c in mat if c not in codes],
        'n_complete_for_diagnostic_labels':len(data),
        'complete_rate_all_nonempty':len(data)/len(posts),
        'n_authors':int(data.author.nunique()),'support_in_common_diagnostic_sample':full_support,
        'labels_failing_threshold_in_common_sample':[c for c,s in full_support.items() if not s['passes_support_threshold']]}
    if len(codes)<2 or not len(data):return {**result,'status':'insufficient_diagnostic_design'}
    design=dmatrix(CONTROLS+' + '+' + '.join(codes),data=data,return_type='dataframe',NA_action='raise')
    X=design.to_numpy(dtype=float)
    rank=int(np.linalg.matrix_rank(X));p=X.shape[1]
    result['design']={'rows':len(data),'columns_including_intercept':p,'rank':rank}
    raw=data[codes].corr()
    pairs=[]
    for i,a in enumerate(codes):
        for b in codes[i+1:]:pairs.append({'first':a,'second':b,'phi':float(raw.loc[a,b]),
            'joint_positive':int((data[a].eq(1)&data[b].eq(1)).sum())})
    result['max_absolute_phi']=float(max(abs(x['phi']) for x in pairs))
    result['top_phi_pairs']=sorted(pairs,key=lambda x:abs(x['phi']),reverse=True)[:10]
    if rank!=p:return {**result,'status':'rank_deficient_vif_undefined'}
    without_intercept=design.drop(columns='Intercept')
    values=without_intercept.to_numpy(dtype=float)
    Z=(values-values.mean(axis=0))/values.std(axis=0)
    inverse=np.linalg.inv(Z.T@Z/len(data))
    vif={c:float(inverse[without_intercept.columns.get_loc(c),without_intercept.columns.get_loc(c)]) for c in codes}
    # Independent residual-regression check, done in the same full design.
    direct={}
    for c in codes:
        j=design.columns.get_loc(c);y=X[:,j];other=np.delete(X,j,axis=1)
        residual=y-other@np.linalg.lstsq(other,y,rcond=None)[0]
        direct[c]=float(np.sum((y-y.mean())**2)/np.sum(residual**2))
        if not np.isclose(vif[c],direct[c],atol=1e-7,rtol=1e-7):raise ValueError('VIF independent check failed')
    result.update(status='diagnostic_complete_full_rank',vif_full_design=vif,vif_direct_check=direct,
        max_vif=max(vif.values()),min_vif=min(vif.values()))
    return result


def main():
    paths={'posts':ROOT/'results/post_features.csv','v2':PRIVATE/'v2_direct_batches/post_labels.csv',
        'v3':PRIVATE/'v3_refined_batches/post_labels.csv'}
    posts=pd.read_csv(paths['posts'],dtype={'postId':str}).drop(columns=['likes','log_likes'])
    posts=posts.loc[posts.length.gt(0)].set_index('postId')
    v2=pd.read_csv(paths['v2'],dtype={'postId':str},keep_default_na=False).set_index('postId').loc[posts.index]
    v3=pd.read_csv(paths['v3'],dtype={'postId':str},keep_default_na=False).set_index('postId').loc[posts.index]
    if len(posts)!=5414 or not v2.sample_id.equals(v3.sample_id):raise ValueError('Population or mapping mismatch')
    for c in ['content_labels','expression_labels','uncertain_content','uncertain_expression']:v2[c]=v2[c].map(historical.jarray)
    schema2=json.loads((ROOT/'code/classification_schema_v2.json').read_text())
    schema3=json.loads((ROOT/'code/classification_schema_v3.json').read_text())
    expnames={c:n for c,n in schema2['expression_labels'].items() if c!='F_OTHER'}
    connames=schema2['content_labels'];names3=schema3['labels']
    exp=pd.DataFrame(index=posts.index);con=pd.DataFrame(index=posts.index)
    for mat,names,pc,uc in [(exp,expnames,'expression_labels','uncertain_expression'),(con,connames,'content_labels','uncertain_content')]:
        for c in names:mat[c]=[historical.tristate(obs,pos,unc,[c]) for obs,pos,unc in zip(v2.observation_state,v2[pc],v2[uc])]
    fine=v3[list(names3)].apply(lambda c:pd.to_numeric(c.replace('',np.nan)))
    # Includes explicit F_OTHER only as a documented residual label, never
    # counted as a substantive recovery without a separate statistic.
    auxiliary_codes=['F_REFLECTION','F_GUIDANCE','F_CAPTION','F_SALE','F_OTHER']
    auxiliary=pd.DataFrame(index=posts.index)
    for c in auxiliary_codes:auxiliary[c]=[historical.tristate(obs,pos,unc,[c]) for obs,pos,unc in zip(v2.observation_state,v2.expression_labels,v2.uncertain_expression)]
    candidates={
        'v2_ten_non_other':{'description':'v2十个有名表达类型，F_SALE保留描述但样本稀少；是历史重用，尚未新增人工验证。','mat':exp,'names':expnames},
        'v2_content6_expression10_parallel':{'description':'同一轮v2的六内容轴与十表达轴并行；可分别缺失，不强制互斥或为每条提供具体内容。','mat':con.join(exp),'names':{**connames,**expnames}},
        'mixed_v3_nine_v2_five_auxiliary':{'description':'不可直接采用的跨轮拼接试验；含F_OTHER的14项，保留每轮逐项未知，不自动解决可读性或定义冲突。','mat':fine.join(auxiliary),'names':{**names3,**{c:schema2['expression_labels'][c] for c in auxiliary_codes}}}}
    result={'status':'historical_candidate_diagnostics_not_new_semantic_classification',
        'n_nonempty':len(posts),'n_unique_texts':int(v2.sample_id.nunique()),'outcome_used':False,
        'support_thresholds':{'positive':40,'negative':40,'authors_within_variation':10},'candidates':{}}
    for key,candidate in candidates.items():
        mat=candidate['mat'];agg=historical.audit(mat,posts.author,candidate['names'],v2.sample_id)
        agg['description']=candidate['description'];agg['collinearity']=collinearity(mat,posts)
        result['candidates'][key]=agg
    ep=exp.eq(1).any(axis=1);cp=con.eq(1).any(axis=1)
    result['parallel_axes']={'expression_positive':int(ep.sum()),'content_positive':int(cp.sum()),
        'either_axis_positive':int((ep|cp).sum()),'either_axis_positive_rate':float((ep|cp).mean()),
        'both_axes_positive':int((ep&cp).sum()),'expression_only_positive':int((ep&~cp).sum()),
        'content_only_positive':int((~ep&cp).sum()),'neither_axis_positive':int((~ep&~cp).sum()),
        'content_axis_complete':int(con.notna().all(axis=1).sum()),'expression_axis_complete':int(exp.notna().all(axis=1).sum()),
        'both_axes_complete':int(con.join(exp).notna().all(axis=1).sum())}
    state_conflict=v2.observation_state.ne(v3.observation_state)
    result['cross_round_observation']={'n_state_conflict':int(state_conflict.sum()),
        'v2_readable_v3_insufficient':int((v2.observation_state.eq('readable')&v3.observation_state.eq('insufficient')).sum()),
        'v2_insufficient_v3_readable':int((v2.observation_state.eq('insufficient')&v3.observation_state.eq('readable')).sum())}
    # Hierarchy is gating, not relabeling: subattributes are only available
    # under an observed positive parent, and each child must itself be known.
    families=[('F_UPDATE',['V3_ACTION']),('F_FUTURE',['V3_PLAN','V3_GOAL']),
        ('F_EXHORT',['V3_EXHORT']),('F_EXPERIENCE_EVALUATION',['V3_EXPERIENCE','V3_APPRAISAL']),
        ('F_GREETING_GRATITUDE',['V3_GREETING','V3_THANKS']),('F_INVITE_ASK',['V3_REQUEST'])]
    hierarchy=[]
    gated=pd.DataFrame(index=posts.index)
    for parent,children in families:
        px=exp[parent];cx=fine[children]
        anypos=cx.eq(1).any(axis=1);allzero=cx.eq(0).all(axis=1);someunknown=cx.isna().any(axis=1)
        item={'parent':parent,'children':children,'n_parent_positive':int(px.eq(1).sum()),
            'n_parent_negative_child_positive':int((px.eq(0)&anypos).sum()),
            'n_parent_unknown_child_positive':int((px.isna()&anypos).sum()),
            'n_parent_positive_children_all_zero':int((px.eq(1)&allzero).sum()),
            'n_parent_positive_children_all_unknown':int((px.eq(1)&cx.isna().all(axis=1)).sum()),
            'n_parent_positive_children_no_positive_some_unknown':int((px.eq(1)&~anypos&someunknown).sum()),
            'n_parent_positive_any_child_positive':int((px.eq(1)&anypos).sum()),
            'n_parent_positive_all_children_known':int((px.eq(1)&~someunknown).sum()),
            'n_parent_positive_state_conflict':int((px.eq(1)&state_conflict).sum()),
            'children_available_given_parent_positive':{}}
        for child in children:
            gx=fine[child].where(px.eq(1))
            gated[child]=gx
            item['children_available_given_parent_positive'][child]=supported(gx,posts.author)
        hierarchy.append(item)
    result['hierarchical_parent10_child_attributes']={
        'description':'保留v2十父标签为总体描述；v3只作父阳性正文内的子属性。父不阳性时子属性不适用，不能把不适用填0。跨轮矛盾均显式保留，不能视为经验证的分类继承。',
        'parent_positive_coverage':result['candidates']['v2_ten_non_other']['n_any_positive'],
        'parent_coverage_rate':result['candidates']['v2_ten_non_other']['any_positive_rate'],
        'parents_collinearity':'Same parent-only design as v2_ten_non_other; do not include a parent and exhaustive child dummy set together.',
        'families':hierarchy,
        'gated_subattribute_known_counts':{c:int(gated[c].notna().sum()) for c in gated},
        'note':'Subattribute negative is interpretable only among parent-positive and child-known rows. A single pooled VIF across all conditional children is not meaningful because there are structural not-applicable states.'}
    mixed=result['candidates']['mixed_v3_nine_v2_five_auxiliary']
    mixedmat=candidates['mixed_v3_nine_v2_five_auxiliary']['mat']
    substantive=mixedmat.drop(columns='F_OTHER').eq(1).any(axis=1)
    positive=mixedmat.eq(1).any(axis=1)
    mixed['substantive_positive_without_other']=int(substantive.sum())
    mixed['substantive_positive_without_other_rate']=float(substantive.mean())
    mixed['n_positive_on_state_conflict_rows']=int((positive&state_conflict).sum())
    mixed['n_positive_with_legacy_aux_but_v3_insufficient']=int((auxiliary.eq(1).any(axis=1)&v3.observation_state.eq('insufficient')).sum())
    result['limits']=[
        'All semantic labels are historical AI predictions; no candidate is human-validated.',
        'Cross-round unions overstate resolved classification if observation or family conflicts are ignored.',
        'Full-design VIF diagnoses numerical dependence in complete cases; it does not establish valid categories or independence of meanings.',
        'Content and expression are parallel measurements with different scope; content-unspecified can be a valid semantic state.',
        'Rare types remain in descriptive coverage but are excluded from simultaneous diagnostics by fixed support thresholds.',
        'The design includes author/date fixed effects and observed text/media controls; no outcome data or associations were used.']
    result['input_sha256']={k:historical.sha(v) for k,v in paths.items()}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'candidates':{k:{'positive':v['n_any_positive'],'coverage':v['any_positive_rate'],
        'all_known':v['n_complete_all_variables'],'diagnostic_n':v['collinearity']['n_complete_for_diagnostic_labels'],
        'vif_min':v['collinearity'].get('min_vif'),'vif_max':v['collinearity'].get('max_vif'),
        'rank_status':v['collinearity']['status'],'diagnostic_labels':v['collinearity']['diagnostic_labels']}
        for k,v in result['candidates'].items()},'parallel':result['parallel_axes'],
        'global_conflicts':result['cross_round_observation'],'hierarchy':hierarchy},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
