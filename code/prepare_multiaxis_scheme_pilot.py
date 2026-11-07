#!/usr/bin/env python3
"""Freeze v4 exploratory rules, then sample without releasing old labels.

Does not classify, and never writes raw text outside the ignored private area.
"""
from pathlib import Path
from collections import Counter
import csv, hashlib, importlib.util, json, random, shutil

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
DEST=PRIVATE/'multiaxis_v4_pilot'
SEED=2026110419

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p): return json.loads(Path(p).read_text())
def jl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def main():
    if DEST.exists(): raise ValueError('Frozen pilot already exists; never overwrite/resample')
    codebook=ROOT/'多轴分层变量试点_编码手册_v4.md'
    design=PRIVATE/'variable_scheme_exploration/design_sample.jsonl'
    spec=importlib.util.spec_from_file_location('previous_review',ROOT/'code/prepare_v3_independent_review.py')
    prev=importlib.util.module_from_spec(spec);spec.loader.exec_module(prev)
    src=PRIVATE/'v2_direct_batches'
    text={r['sample_id']:r['text'] for p in sorted((src/'inputs').glob('*.jsonl')) for r in jl(p)}
    rows=csvs(src/'id_map.csv'); pid={r['postId']:r['sample_id'] for r in rows if r['sample_id']}
    thash={hashlib.sha256(t.encode()).hexdigest():sid for sid,t in text.items()}
    excluded=set(prev.PREVIOUS_SPOTCHECK)
    for p in prev.PREVIOUS:
        for r in csvs(p):
            if r.get('postId') in pid:excluded.add(pid[r['postId']])
            for key in ('clean_text','text'):
                h=hashlib.sha256(r.get(key,'').encode()).hexdigest()
                if h in thash:excluded.add(thash[h])
    for p in prev.PRIOR_BLINDS:excluded.update(r['sample_id'] for r in jl(p))
    legacy={r['sample_id']:r['postId'] for f in ('development_keys.csv','calibration_keys.csv','holdout_keys.csv') for r in csvs(PRIVATE/f)}
    for r in js(prev.DESIGN)['rows']:
        candidates={pid[r['postId']]} if r.get('postId') in pid else set()
        if r.get('sample_id') in legacy and legacy[r['sample_id']] in pid:candidates.add(pid[legacy[r['sample_id']]])
        if r.get('sample_id') in text:candidates.add(r['sample_id'])
        if r.get('text_sha256') in thash:candidates.add(thash[r['text_sha256']])
        if len(candidates)!=1:raise ValueError('Cannot identify previous design text')
        excluded.update(candidates)
    excluded.update(r['v2_sample_id'] for r in csvs(prev.DEST/'private_key.csv'))
    excluded.update(r['sample_id'] for r in jl(design))
    if excluded-set(text): raise ValueError('Unresolvable exclusion IDs')
    DEST.mkdir()
    shutil.copyfile(codebook,DEST/'frozen_codebook.md')
    freeze={'status':'rules_frozen_before_sample_release','seed':SEED,'n_random':120,'n_targeted':40,
      'codebook_sha256':sha(codebook),'design_sample_sha256':sha(design),'prior_v3_key_sha256':sha(prev.DEST/'private_key.csv'),
      'source_map_sha256':sha(src/'id_map.csv'),'source_manifest_sha256':sha(src/'manifest.json'),
      'purpose':'Outcome-blind alternative-scheme pilot; not human validation; no full-corpus v4 claims.'}
    dump(DEST/'freeze.json',freeze)
    eligible=sorted(set(text)-excluded);rng=random.Random(SEED);chosen=rng.sample(eligible,120)
    v3={r['sample_id']:r for r in jl(PRIVATE/'v3_refined_batches/merged_unique.jsonl')}
    targeted_pool=[s for s in eligible if s not in chosen and not v3[s]['positive_labels']]
    targeted=rng.sample(targeted_pool,40)
    counts=Counter(r['sample_id'] for r in rows if r['sample_id']); keys=[];blind=[]
    for i,(sid,part) in enumerate([(s,'random') for s in chosen]+[(s,'targeted_no_v3_positive') for s in targeted],1):
        anonymous=f'MAX{i:04d}'
        keys.append({'sample_id':anonymous,'source_id':sid,'partition':part,'post_multiplicity':counts[sid]})
        blind.append({'sample_id':anonymous,'text':text[sid]})
    with (DEST/'private_key.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(keys[0]));w.writeheader();w.writerows(keys)
    payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in blind)
    for who in ('a','b'):(DEST/f'blind_{who}.jsonl').write_text(payload)
    meta={**freeze,'n_unique_source':len(text),'n_excluded':len(excluded),'n_eligible':len(eligible),
      'n_targeted_pool_after_random':len(targeted_pool),'random_inclusion_probability':120/len(eligible),
      'n_random_represented_posts':sum(counts[s] for s in chosen),
      'sampling_unit':'unique exact cleaned text, simple random from documented design-excluded pool; targeted set separate',
      'blind_sha256':sha(DEST/'blind_a.jsonl'),'private_key_sha256':sha(DEST/'private_key.csv'),
      'prior_exposure':'The corpus has already been coded by previous models; the new sample is excluded from documented design/review packets, not a never-seen corpus.'}
    dump(DEST/'sample_metadata.json',meta)
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
