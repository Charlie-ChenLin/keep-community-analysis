#!/usr/bin/env python3
"""Independent full-run count and clustered-inference recalculation.

Uses no analysis/validator functions. Raw text, source IDs and original post IDs
are never copied into the public audit.
"""
from pathlib import Path
from collections import Counter
import csv,hashlib,json
import numpy as np
import pandas as pd
from patsy import dmatrix
from scipy.stats import t

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5_production'
TOPICS=['T_ACTIVITY','T_BODY','T_FOOD','T_LIFE','T_TOOLS','T_OTHER']
EXPR=['S_PRESENT','S_EXPERIENCE','S_APPRAISAL','S_FUTURE','S_EXHORT','S_REFLECTION','S_GUIDANCE','S_SOCIAL','S_REQUEST','S_OFFER','S_OTHER']
CONTROLS='log_length + has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type) + C(time_bin) + C(author) + C(date)'
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def value(r,c):
    group='topic' if c.startswith('T_') else 'expression'
    return 1 if c in r[group+'_positive'] else None if c in r[group+'_uncertain'] else 0
def coverage(rows):
    result={}
    for name,codes in [('expression',EXPR[:-1]),('topic',TOPICS[:-1]),('either',EXPR[:-1]+TOPICS[:-1])]:
        result[name]={'any_positive':sum(any(value(r,c)==1 for c in codes) for r in rows),
          'two_or_more_positive':sum(sum(value(r,c)==1 for c in codes)>1 for r in rows),
          'all_known':sum(all(value(r,c) is not None for c in codes) for r in rows),
          'all_negative':sum(all(value(r,c)==0 for c in codes) for r in rows),
          'no_positive_some_unknown':sum(not any(value(r,c)==1 for c in codes) and any(value(r,c) is None for c in codes) for r in rows)}
    return result

def independent_inference(frame,reported,codes,weighted=False,families=None):
    controls=dmatrix(CONTROLS,frame,return_type='dataframe',NA_action='raise')
    drop=reported.get('dropped_redundant_control_columns',[])
    Xframe=pd.concat([controls.drop(columns=drop),frame[codes].astype(float)],axis=1)
    X=Xframe.to_numpy();y=frame.log_likes.to_numpy();n,k=X.shape
    assert np.linalg.matrix_rank(X)==k==reported['rank']
    if weighted:
        weights=1/frame.groupby('author')['author'].transform('size').to_numpy();scale=np.sqrt(weights)
        Xw=X*scale[:,None];yw=y*scale
    else:Xw=X;yw=y
    beta=np.linalg.lstsq(Xw,yw,rcond=None)[0];residual=yw-Xw@beta
    inv=np.linalg.inv(Xw.T@Xw);meat=np.zeros((k,k));groups=frame.author.to_numpy();unique=np.unique(groups);G=len(unique)
    for g in unique:
        idx=groups==g;score=Xw[idx].T@residual[idx];meat+=np.outer(score,score)
    covariance=(G/(G-1))*((n-1)/(n-k))*(inv@meat@inv)
    se=np.sqrt(np.diag(covariance));critical=t.ppf(.975,G-1);checked={}
    for code in codes:
        j=Xframe.columns.get_loc(code);p=2*t.sf(abs(beta[j]/se[j]),G-1)
        direct={'beta':float(beta[j]),'se_cluster':float(se[j]),'p':float(p),'ci_low':float(beta[j]-critical*se[j]),'ci_high':float(beta[j]+critical*se[j])}
        row=reported['coefficients'][code]
        for key,val in direct.items():assert np.isclose(val,row[key],rtol=1e-7,atol=1e-8),(code,key)
        checked[code]=direct
    for family in families or [codes]:
        if not family:continue
        pvalues=np.array([checked[c]['p'] for c in family]);order=np.argsort(pvalues);m=len(order)
        adjusted=np.minimum.accumulate((pvalues[order]*m/np.arange(1,m+1))[::-1])[::-1].clip(0,1);q=np.empty(m);q[order]=adjusted
        for code,qvalue in zip(family,q):assert np.isclose(qvalue,reported['coefficients'][code]['q_bh_within_family'],rtol=1e-7,atol=1e-8)
    return {'n':n,'authors':G,'rank':k,'coefficients_standard_errors_p_ci_and_BH_verified':True,'direct_coefficients':checked}

def main():
    summary=js(ROOT/'results/v5_full_coding_summary.json');analysis=js(ROOT/'results/v5_full_analysis.json');manifest=js(RUN/'manifest.json');freeze=js(RUN/'full_run_freeze.json')
    rows=[];ids=[];alltexts={};batch_hashes={}
    for b in manifest['batches']:
        inp=jl(RUN/'inputs'/b['name']);out=jl(RUN/'outputs'/b['name'])
        assert sha(RUN/'inputs'/b['name'])==b['sha256'];assert len(inp)==len(out)==b['rows']
        texts={r['sample_id']:r['text'] for r in inp};coded={r['sample_id']:r for r in out}
        assert set(texts)==set(coded) and len(coded)==len(out)
        for sid,row in coded.items():
            p=row['topic_positive']+row['expression_positive'];u=row['topic_uncertain']+row['expression_uncertain']
            assert not set(p)&set(u) and row['all_labels_reviewed'] is True
            assert set(row['evidence'])==set(p)|({'A_POSITIVE_TONE'} if row['positive_tone']=='yes' else set())|({'A_NEGATIVE_TONE'} if row['negative_tone']=='yes' else set())
            assert all(isinstance(x,str) and x.strip() and x in texts[sid] for x in row['evidence'].values())
            for field,parents in [('event_assertion',['S_PRESENT']),('plan',['S_FUTURE']),('goal',['S_FUTURE']),('greeting',['S_SOCIAL']),('thanks',['S_SOCIAL']),('positive_tone',['S_EXPERIENCE','S_APPRAISAL']),('negative_tone',['S_EXPERIENCE','S_APPRAISAL'])]:
                state=[value(row,c) for c in parents];parent=1 if 1 in state else None if None in state else 0
                assert (row[field]!='not_applicable' if parent==1 else row[field]=='not_applicable' if parent==0 else row[field]=='uncertain')
        ids.extend(texts);alltexts.update(texts);rows.extend(coded[s] for s in texts);batch_hashes[b['name']]=sha(RUN/'outputs'/b['name'])
    assert len(ids)==len(set(ids))==len(set(alltexts.values()))==4156 and batch_hashes==summary['output_batch_sha256']
    mapping=csvs(RUN/'post_map.csv');byid={r['sample_id']:r for r in rows};repeated=[byid[p['sample_id']] for p in mapping if p['sample_id']]
    assert len(mapping)==len({p['postId'] for p in mapping})==9532 and len(repeated)==5414
    uc=coverage(rows);pc=coverage(repeated)
    assert uc==summary['unique_text_coverage']['axes'] and pc==summary['post_coverage']['axes']
    assert dict(Counter(p['input_status'] for p in mapping))==summary['source_states']
    labels=pd.read_csv(RUN/'post_labels.csv',dtype={'postId':str},keep_default_na=False).set_index('postId')
    for p in mapping:
        mapped=labels.loc[p['postId']]
        for code in TOPICS+EXPR:
            expected=value(byid[p['sample_id']],code) if p['sample_id'] else None
            assert mapped[code]==('' if expected is None else str(expected))
        for field in ['event_assertion','plan','goal','greeting','thanks','positive_tone','negative_tone']:
            expected=byid[p['sample_id']][field] if p['sample_id'] else 'unobserved_body'
            assert mapped[field]==expected
    posts=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str})
    data=posts.merge(labels.reset_index(),on='postId',validate='one_to_one')
    assert len(data)==9532 and np.allclose(data.log_likes,np.log1p(data.likes))
    for code in TOPICS+EXPR:data[code]=pd.to_numeric(data[code].replace('',np.nan))
    nonempty=data.loc[data.length.gt(0)].copy();codes=analysis['main_selection']['selected'];main=nonempty.dropna(subset=codes)
    assert len(main)==analysis['main']['n']
    for code in codes:
        assert main[code].eq(1).sum()>=40 and main[code].eq(0).sum()>=40 and main.groupby('author')[code].nunique().gt(1).sum()>=10
    checks={'main':independent_inference(main,analysis['main'],codes)}
    robust=analysis['robustness'];cut=main.likes.quantile(.99);trim=main.loc[main.likes.le(cut)]
    counts=main.groupby('author').size();auth=main.loc[main.author.isin(counts.index[counts.ge(10)])]
    for name,frame,weighted in [('drop_top_1_percent_likes',trim,False),('authors_min_10',auth,False),('author_equal_weight',main,True)]:
        if robust[name].get('status')=='estimated_retrospective_exploratory':checks[name]=independent_inference(frame,robust[name],codes,weighted)
    topic=analysis['topic_adjustment']
    if topic['status']=='evaluated':
        tcodes=topic['selection']['selected'];tsample=nonempty.dropna(subset=tcodes)
        assert len(tsample)==topic['n']
        for key,used,families in [('expression_only_same_sample',codes,None),('with_topics',tcodes,[codes,[c for c in tcodes if c not in codes]])]:
            if topic[key].get('status')=='estimated_retrospective_exploratory':checks['topic_'+key]=independent_inference(tsample,topic[key],used,families=families)
    polarity=analysis['polarity']
    if polarity.get('status')=='estimated_retrospective_exploratory':
        sample=nonempty.loc[(nonempty.S_EXPERIENCE.eq(1)|nonempty.S_APPRAISAL.eq(1))&nonempty.positive_tone.isin(['yes','no'])&nonempty.negative_tone.isin(['yes','no'])].copy()
        sample['polarity_group']=[('mixed' if p=='yes' and n=='yes' else 'positive_only' if p=='yes' else 'negative_only' if n=='yes' else 'neither') for p,n in zip(sample.positive_tone,sample.negative_tone)]
        assert sample.polarity_group.value_counts().to_dict()==polarity['counts']
        sample=sample.loc[sample.polarity_group.isin(polarity['retained_levels'])].copy()
        focal=polarity['model']['codes']
        for code in focal:sample[code]=sample.polarity_group.eq(code.removeprefix('POL_')).astype(int)
        assert len(sample)==polarity['n_retained']
        checks['conditional_polarity']=independent_inference(sample,polarity['model'],focal)
    assert sha(ROOT/'code/v5_full_analysis_protocol.json')==freeze['analysis_protocol_sha256']
    assert sha(ROOT/'results/post_features.csv')==freeze['post_features_sha256']
    result={'status':'passed_independent_direct_recalculation','n_batches':84,'n_unique_texts':4156,'n_total_posts':9532,'n_nonempty_posts':5414,
      'unique_text_coverage':uc,'post_coverage':pc,'all_output_evidence_and_parent_constraints_verified':True,'full_post_mapping_values_verified':True,
      'cluster_sandwich_direct_recalculations':checks,'frozen_protocol_and_outcome_source_unchanged':True,
      'human_accuracy_established':False,'n_independent_human_reviews':0,'limits':'This independently checks coding structure, source mapping, calculations and inference, not semantic truth or causal identification.',
      'input_sha256':{'coding_summary':sha(ROOT/'results/v5_full_coding_summary.json'),'analysis':sha(ROOT/'results/v5_full_analysis.json')}}
    out=ROOT/'results/v5_full_independent_audit.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['cluster_sandwich_direct_recalculations','unique_text_coverage','post_coverage']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
