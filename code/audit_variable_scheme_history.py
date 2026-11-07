#!/usr/bin/env python3
"""Outcome-blind, post-aligned historical expression scheme audit.

Reads private labels, writes aggregate counts only. Does not modify predictions
or treat cross-version label unions as reconciled semantic classifications.
"""
from pathlib import Path
import hashlib,json
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
OUT=ROOT/'results/variable_scheme_independent_audit.json'
LEXICAL={'self_discipline':'自律或目标词','social_address':'称呼或互助词','positive_expression':'积极表达词','question':'问号或问句规则'}
GROUPS={
'R_RECORD':{'label':'记录或呈现','components':['F_UPDATE','F_CAPTION']},
'R_EVALUATE':{'label':'体验或评价','components':['F_EXPERIENCE_EVALUATION']},
'R_PLAN_ENCOURAGE':{'label':'计划、期待或鼓励','components':['F_FUTURE','F_EXHORT']},
'R_SOCIAL':{'label':'问候、感谢或邀请交流','components':['F_GREETING_GRATITUDE','F_INVITE_ASK']},
'R_REFLECT':{'label':'感悟或观点','components':['F_REFLECTION']}}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jarray(v):return json.loads(v) if v else []
def tristate(obs,pos,unc,components):
    if obs!='readable':return np.nan
    if set(components)&set(pos):return 1.
    if set(components)&set(unc):return np.nan
    return 0.

def audit(values,authors,names,post_sample_ids):
    positive=values.eq(1).sum(axis=1)
    known=values.notna().sum(axis=1)
    complete=known.eq(values.shape[1])
    out={'n_nonempty':len(values),'n_variables':values.shape[1],
         'n_any_positive':int(positive.gt(0).sum()),
         'any_positive_rate':float(positive.gt(0).mean()),
         'n_at_least_two_positive':int(positive.ge(2).sum()),
         'overlap_rate_all_nonempty':float(positive.ge(2).mean()),
         'overlap_rate_among_positive':float(positive.ge(2).sum()/positive.gt(0).sum()) if positive.gt(0).any() else None,
         'n_complete_all_variables':int(complete.sum()),
         'complete_rate':float(complete.mean()),
         'n_any_known_variable':int(known.gt(0).sum()),
         'n_no_positive_all_known':int((positive.eq(0)&complete).sum()),
         'n_no_positive_some_unknown':int((positive.eq(0)&~complete).sum()),
         'n_all_variables_unknown':int(known.eq(0).sum()),
         'positive_count_distribution':{str(k):int(v) for k,v in positive.value_counts().sort_index().items()},
         'variables':{}}
    for code in values:
        x=values[code]; valid=x.notna()
        pos=x.eq(1);neg=x.eq(0)
        rates=x.loc[valid].groupby(authors.loc[valid]).mean()
        positive_author_counts=authors.loc[pos].value_counts()
        within_variation=int(x.loc[valid].groupby(authors.loc[valid]).nunique().gt(1).sum())
        out['variables'][code]={'label':names[code],
            'n_known':int(valid.sum()),'known_rate':float(valid.mean()),'n_positive':int(pos.sum()),
            'n_negative':int(neg.sum()),'n_unknown':int(x.isna().sum()),
            'positive_rate_known':float(x.loc[valid].mean()),
            'positive_rate_all_nonempty':float(pos.mean()),
            'authors_known':int(authors.loc[valid].nunique()),'authors_positive':int(authors.loc[pos].nunique()),
            'authors_within_variation':within_variation,
            'largest_author_share_of_positives':float(positive_author_counts.max()/pos.sum()) if pos.any() else None,
            'author_equal_mean_positive_known':float(rates.mean()),
            'passes_previous_support_thresholds':bool(pos.sum()>=40 and neg.sum()>=40 and within_variation>=10)}
    unique=values.copy();unique['_sample_id']=post_sample_ids.values
    unique=unique.drop_duplicates('_sample_id').drop(columns='_sample_id')
    upos=unique.eq(1).sum(axis=1)
    out['unique_text_weighting']={'n':len(unique),'n_any_positive':int(upos.gt(0).sum()),
        'any_positive_rate':float(upos.gt(0).mean()),'n_at_least_two_positive':int(upos.ge(2).sum()),
        'n_complete':int(unique.notna().all(axis=1).sum())}
    return out

def main():
    paths={'post_features':ROOT/'results/post_features.csv',
        'v2_labels':PRIVATE/'v2_direct_batches/post_labels.csv',
        'v3_labels':PRIVATE/'v3_refined_batches/post_labels.csv'}
    posts=pd.read_csv(paths['post_features'],dtype={'postId':str}).drop(columns=['likes','log_likes'])
    all_v2=pd.read_csv(paths['v2_labels'],dtype={'postId':str},keep_default_na=False)
    all_v3=pd.read_csv(paths['v3_labels'],dtype={'postId':str},keep_default_na=False)
    if any(len(x)!=9532 or not x.postId.is_unique for x in (posts,all_v2,all_v3)):raise ValueError('population')
    p=posts.loc[posts.length.gt(0)].copy().set_index('postId')
    v2=all_v2.set_index('postId').loc[p.index].copy();v3=all_v3.set_index('postId').loc[p.index].copy()
    if not v2.sample_id.equals(v3.sample_id):raise ValueError('unique-text mapping mismatch')
    for col in ['expression_labels','uncertain_expression','content_labels','uncertain_content']:v2[col]=v2[col].map(jarray)
    schema2=json.loads((ROOT/'code/classification_schema_v2.json').read_text())
    schema3=json.loads((ROOT/'code/classification_schema_v3.json').read_text())
    matrices={'legacy_four_lexical':p[list(LEXICAL)].astype(float)}
    names={'legacy_four_lexical':LEXICAL}
    for key,defs in [('v2_five_groups',GROUPS),('v2_all_11_expression',{code:{'label':label,'components':[code]} for code,label in schema2['expression_labels'].items()}),
                     ('v2_substantive_10_without_other',{code:{'label':label,'components':[code]} for code,label in schema2['expression_labels'].items() if code!='F_OTHER'}),
                     ('v2_six_content',{code:{'label':label,'components':[code]} for code,label in schema2['content_labels'].items()})]:
        mat=pd.DataFrame(index=p.index)
        content=key=='v2_six_content'
        pc='content_labels' if content else 'expression_labels';uc='uncertain_content' if content else 'uncertain_expression'
        for code,definition in defs.items():mat[code]=[tristate(obs,pos,unc,definition['components']) for obs,pos,unc in zip(v2.observation_state,v2[pc],v2[uc])]
        matrices[key]=mat;names[key]={k:d['label'] for k,d in defs.items()}
    matrices['v3_nine']=v3[list(schema3['labels'])].apply(lambda c:pd.to_numeric(c.replace('',np.nan)))
    names['v3_nine']=schema3['labels']
    # This historical union is diagnostic only: different observation states and
    # definitions have deliberately not been reconciled by a new model reading.
    v3pos=matrices['v3_nine'].eq(1).any(axis=1)
    v2pos=matrices['v2_five_groups'].eq(1).any(axis=1)
    v2allpos=matrices['v2_all_11_expression'].eq(1).any(axis=1)
    aux=matrices['v2_all_11_expression'][['F_REFLECTION','F_GUIDANCE','F_CAPTION','F_SALE']].eq(1)
    omitted=~v3pos
    lost=v2pos&~v3pos; gained=v3pos&~v2pos
    status=pd.crosstab(v2.observation_state,v3.observation_state)
    cross={'n_v2_five_positive_but_v3_no_positive':int(lost.sum()),
           'n_v3_positive_but_v2_five_no_positive':int(gained.sum()),
           'v2_v3_observation_state_table':status.to_dict(),
           'v3_no_positive':int(omitted.sum()),
           'v3_no_positive_with_omitted_v2_expression_any':int((omitted&aux.any(axis=1)).sum()),
           'v3_no_positive_with_omitted_v2_expression_readable_in_v3':int((omitted&aux.any(axis=1)&v3.observation_state.eq('readable')).sum()),
           'v3_no_positive_with_omitted_v2_expression_insufficient_in_v3':int((omitted&aux.any(axis=1)&v3.observation_state.eq('insufficient')).sum()),
           'omitted_v2_positive_by_label':{c:int((omitted&aux[c]).sum()) for c in aux},
           'v3_no_positive_with_v2_any_expression':int((omitted&v2allpos).sum()),
           'v3_all_nine_negative_with_v2_any_expression':int(((matrices['v3_nine'].eq(0).all(axis=1))&v2allpos).sum()),
           'note':'Different versions measure different scopes. Cross-round positives are diagnostic evidence, not validated recovered v3 positives.'}
    # V2 child -> v3 leaf-family cross-round disagreement quantifies whether
    # derived historical groups can be treated as identical (they cannot).
    family=[('F_UPDATE',['V3_ACTION']),('F_FUTURE',['V3_PLAN','V3_GOAL']),('F_EXHORT',['V3_EXHORT']),
            ('F_EXPERIENCE_EVALUATION',['V3_EXPERIENCE','V3_APPRAISAL']),
            ('F_GREETING_GRATITUDE',['V3_GREETING','V3_THANKS']),('F_INVITE_ASK',['V3_REQUEST'])]
    cross['cross_round_family_comparisons']=[]
    for old,children in family:
        oldx=matrices['v2_all_11_expression'][old]
        newmat=matrices['v3_nine'][children]
        newx=pd.Series(np.where(newmat.eq(1).any(axis=1),1.,np.where(newmat.isna().any(axis=1),np.nan,0.)),index=p.index)
        both=oldx.notna()&newx.notna()
        cross['cross_round_family_comparisons'].append({'v2':old,'v3':children,
            'both_known':int(both.sum()),'both_positive':int((oldx.eq(1)&newx.eq(1)).sum()),
            'v2_only_positive_among_both_known':int((both&oldx.eq(1)&newx.eq(0)).sum()),
            'v3_only_positive_among_both_known':int((both&oldx.eq(0)&newx.eq(1)).sum()),
            'agreement_both_known':float(oldx[both].eq(newx[both]).mean())})
    result={'status':'historical_outcome_blind_audit_not_human_semantic_validation',
        'n_total_posts':len(posts),'n_nonempty_body':len(p),'n_empty_or_unavailable':len(posts)-len(p),
        'n_unique_nonempty':int(v2.sample_id.nunique()),
        'input_status':all_v2.input_status.value_counts().to_dict(),
        'schemes':{key:audit(mat,p.author,names[key],v2.sample_id) for key,mat in matrices.items()},
        'cross_version':cross,
        'evaluation_criteria':[
            'Use the same 5,414 nonempty posts as denominator; separately report total 9,532 and 4,156 unique texts.',
            'Report substantive positive coverage separately from known-negative and unknown status.',
            'Report complete-case retention and per-label known positive+negative sample sizes.',
            'Count overlap as valid multi-label expression; diagnose semantic ambiguity and numerical collinearity separately.',
            'Require interpretable definitions, negative examples and literal evidence; do not optimize only label union coverage.',
            'Keep rare types descriptively even when they fail minimum model support; do not merge unrelated types only to exceed thresholds.',
            'Compare post-weighted, unique-text-weighted and author-equal descriptive rates.',
            'Validate scope and decisions on independent blinded text rereading; AI agreement is not human accuracy.',
            'Freeze outcome-blind definitions before any re-estimated outcome association; never choose a scheme from significant p-values.',
            'Separate descriptive broad families from finer explanatory variables, and preserve unknowns.'],
        'findings':[
            'The v3 scheme narrows expression scope: reflection, guidance, caption/scene depiction and sales notices have no direct v3 label.',
            'The v3 codebook explicitly disclaims completeness, so treating its 70% positive coverage as overall dataset utilization is a measurement framing error.',
            'Old v2 merged-label positives cannot be automatically split into v3 leaves; historical disagreements indicate changes beyond simple refinement.',
            'All-zero observed rows remain valid comparators. All-unknown rows supply no semantic discrimination.',
            'A scheme with an other label can report near-universal assignment while adding little substantive interpretability.',
            'No coverage result establishes category validity; independent human validation remains missing.'],
        'outcome_used':False,'input_sha256':{k:sha(v) for k,v in paths.items()}}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'schemes':{k:{kk:v[kk] for kk in ['n_any_positive','any_positive_rate','n_at_least_two_positive','n_complete_all_variables','n_all_variables_unknown']} for k,v in result['schemes'].items()},'cross_version':cross},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
