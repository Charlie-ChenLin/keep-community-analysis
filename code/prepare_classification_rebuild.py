"""Prepare outcome-blind development/calibration/holdout material.

Only observed body text is coded. No likes, old dictionary predictions, NMF
weights, or platform tags appear in annotator inputs. Row-level text stays local.
The holdout packet is released only after a codebook and recognizer are frozen.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'validation/classification_rebuild'
PRIVATE=QA/'private'
SEED=2026102901


def clean(value):
    s='' if pd.isna(value) else str(value)
    s=s.replace('\\n','\n').replace('\\r',' ')
    s=re.sub(r'https?://\S+',' ',s)
    s=re.sub(r'Ⓚ[^Ⓚ]*Ⓚ',' ',s)
    s=re.sub(r'\[[^\[\]]{1,12}\]',' ',s)
    return re.sub(r'\s+',' ',s).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emit(frame, split, name):
    rows=[]
    for i,row in enumerate(frame.itertuples(),1):
        rows.append({'sample_id':f'{split[:1].upper()}{i:03d}','text':row.clean_text})
    path=PRIVATE/name
    path.write_text('\n'.join(json.dumps(x,ensure_ascii=False)for x in rows)+'\n')
    ids=pd.DataFrame({'sample_id':[x['sample_id']for x in rows],'postId':frame.postId.to_numpy(),'author':frame.author.to_numpy(),'split':split,'clean_text':frame.clean_text.to_numpy()})
    ids.to_csv(PRIVATE/(split+'_keys.csv'),index=False,encoding='utf-8-sig')
    return {'n':len(frame),'authors':int(frame.author.nunique()),'packet_sha256':digest(path),'body_length_quantiles':{str(q):float(frame.length.quantile(q))for q in [.25,.5,.75,.95]}}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--release-holdout',action='store_true')
    args=parser.parse_args()
    PRIVATE.mkdir(parents=True,exist_ok=True)
    assert not (QA/'freeze_record.json').exists(),'Frozen packets cannot be regenerated in place.'
    if args.release_holdout:
        codebook=ROOT/'code/classification_codebook_v1.json'
        rules=ROOT/'code/classification_recognizer_v1.json'
        assert codebook.is_file()and rules.is_file(),'Freeze both definitions and recognition rules before releasing holdout.'
        frozen={'codebook_sha256':digest(codebook),'recognizer_sha256':digest(rules),'holdout_packet_released':True,
                'interpretation':'Frozen before this newly selected packet was opened for coding; retrospective exploratory work, not a preregistered confirmatory study.'}
        artifacts=['code/classify_rebuilt_posts.py','validation/classification_rebuild/private/classifier_v1.joblib',
                   'validation/classification_rebuild/private/development_blind.jsonl','validation/classification_rebuild/private/development_coding.json',
                   'validation/classification_rebuild/private/calibration_blind.jsonl','validation/classification_rebuild/private/calibration_coding.json',
                   'validation/classification_rebuild/private/selected_holdout.csv','validation/classification_rebuild/private/body_population.csv']
        frozen['artifacts']={p:digest(ROOT/p) for p in artifacts}
        from datetime import datetime,timezone
        frozen['frozen_at_utc']=datetime.now(timezone.utc).isoformat()
        plan=json.loads((ROOT/'results/classification_rebuild_protocol.json').read_text())
        selected=pd.read_csv(PRIVATE/'selected_holdout.csv',dtype={'postId':str},keep_default_na=False)
        frozen['holdout']=emit(selected,'holdout','holdout_blind.jsonl')
        (QA/'freeze_record.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(frozen,ensure_ascii=False,indent=2));return
    raw_path=ROOT/'2026Data/Keep Data/sample_post_2022.csv'
    feature_path=ROOT/'results/post_features.csv'
    raw=pd.read_csv(raw_path,dtype={'postId':str})
    features=pd.read_csv(feature_path,dtype={'postId':str})
    p=features[['postId','author','contentTypeStr','has_text','has_tag','length']].merge(raw[['postId','content']],on='postId',validate='one_to_one')
    p['clean_text']=p.content.map(clean)
    assert p.clean_text.str.replace(r'\s','',regex=True).str.len().eq(p.length).all()
    p['template']=p.clean_text.map(lambda s:re.sub(r'\s+','',s).lower())
    rng=np.random.default_rng(SEED)
    authors=np.array(sorted(p.author.unique()))
    rng.shuffle(authors)
    roles={a:('development'if i<60 else'calibration'if i<80 else'holdout')for i,a in enumerate(authors)}
    p['role']=p.author.map(roles)
    p.to_csv(PRIVATE/'body_population.csv',index=False,encoding='utf-8-sig')
    # Historically exposed excerpts are barred from the new evaluation packets.
    exposed=set()
    for path,col in [(ROOT/'validation/teacher_feedback/label_review_private.csv','clean_text'),(ROOT/'results/text_coding_review.csv','text'),(ROOT/'results/extension_topic_examples.csv','text')]:
        if path.is_file():
            exposed.update(pd.read_csv(path).get(col,pd.Series(dtype=str)).dropna().map(lambda s:re.sub(r'\s+','',clean(s)).lower()))
    pools={r:p.loc[p.role.eq(r)&p.length.gt(0)].copy()for r in ['development','calibration','holdout']}
    # Discovery has deliberate author diversity and length diversity. It is not
    # used for corpus prevalence or out-of-sample performance claims.
    pool=pools['development'].drop_duplicates('template').copy()
    balanced=[]
    for author,frame in pool.groupby('author',sort=True):
        balanced.extend(frame.sample(min(2,len(frame)),random_state=SEED).index.tolist())
    first=pool.loc[balanced]
    first=first.sample(min(100,len(first)),random_state=SEED)
    remainder=pool.drop(first.index)
    extra=[]
    for low,high,count in [(0,15,20),(15,80,25),(80,float('inf'),15)]:
        frame=remainder.loc[remainder.length.gt(low)&remainder.length.le(high)]
        extra.extend(frame.sample(min(count,len(frame)),random_state=SEED+int(low)).index.tolist())
    discovery=pd.concat([first,remainder.loc[extra]]).drop_duplicates('template')
    if len(discovery)<160:
        rest=pool.drop(discovery.index)
        discovery=pd.concat([discovery,rest.sample(min(160-len(discovery),len(rest)),random_state=SEED+5)])
    discovery=discovery.sort_values('postId')
    known=exposed|set(pools['development'].template)
    # Calibration and holdout target new authors and exact texts not present in
    # development; denominators are explicitly this harder observed-text scope.
    cal=pools['calibration'].loc[~pools['calibration'].template.isin(known)].drop_duplicates('template')
    cal=cal.sample(min(80,len(cal)),random_state=SEED+6).sort_values('postId')
    known.update(pools['calibration'].template)
    hold=pools['holdout'].loc[~pools['holdout'].template.isin(known)].drop_duplicates('template')
    hold=hold.sample(min(160,len(hold)),random_state=SEED+7).sort_values('postId')
    meta={'development':emit(discovery,'development','development_blind.jsonl'),'calibration':emit(cal,'calibration','calibration_blind.jsonl')}
    hold[['postId','author','clean_text','length']].to_csv(PRIVATE/'selected_holdout.csv',index=False,encoding='utf-8-sig')
    # Separate missing-body cases are controls, never silently five/six zeros.
    empty=p.loc[p.role.eq('development')&p.length.eq(0)].sample(12,random_state=SEED+8).sort_values('postId')
    meta['observation_controls']=emit(empty,'observation_controls','observation_controls_blind.jsonl')
    counts=p.groupby('role').agg(posts=('postId','size'),authors=('author','nunique'),nonempty=('length',lambda s:int(s.gt(0).sum()))).reset_index().to_dict('records')
    out={'stage':'development packets prepared; holdout sealed','seed':SEED,'population_posts':len(p),'nonempty_body_posts':int(p.length.gt(0).sum()),
         'split_unit':'author; 60 development / 20 calibration / 20 holdout, assigned without any engagement outcome',
         'split_counts':counts,'packets':meta,'holdout_selected_n':len(hold),'holdout_eligible_unique_n':int(len(pools['holdout'].loc[~pools['holdout'].template.isin(known)].drop_duplicates('template'))),
         'outcome_fields_excluded':['likes','log_likes','views','comments','old_dictionary_predictions','old_NMF_weights','raw_hashTags'],
         'annotation_unit':'Full cleaned body only; category absence is not inferred from missing or insufficient body. Multi-label content domains and communication functions are developed separately.',
         'sampling_scope':'Discovery deliberately diversifies authors and text length; evaluation samples are random from held-out authors with exact templates unseen in earlier roles or historical inspected excerpts. Evaluation is not a representative sample of all posts.',
         'validation_design':'Independent-context AI annotation is a provisional screening exercise using the same base model; not independent human validation and not a human gold standard. Human blind packets and a validator will be provided.',
         'analysis_commitment':'No likes or regression significance will choose category count, names, terms, thresholds or rules. Record discoveries, freeze definitions/recognizer, then open the held-out packet once. No final real-topic effect claims from AI-only validation.',
         'source_sha256':{str(f.relative_to(ROOT)):digest(f)for f in [raw_path,feature_path]},
         'checks':{'author_roles_disjoint':all(set(p.loc[p.role.eq(a),'author']).isdisjoint(set(p.loc[p.role.eq(b),'author']))for a,b in [('development','calibration'),('development','holdout'),('calibration','holdout')]),
                   'development_calibration_templates_disjoint':set(discovery.template).isdisjoint(set(cal.template)),
                   'all_three_packet_templates_disjoint':set(hold.template).isdisjoint(set(discovery.template)|set(cal.template)),
                   'historical_excerpts_excluded_from_evaluation':not(set(cal.template)|set(hold.template))&exposed}}
    (ROOT/'results/classification_rebuild_protocol.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
