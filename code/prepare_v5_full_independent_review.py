#!/usr/bin/env python3
"""Freeze an additional outcome-blind 80-text AI review during production.

This supplements, never replaces, the original v5 200+60 pilot comparisons.
It is new to documented development/review packets, not an unseen corpus.
"""
from pathlib import Path
import csv,hashlib,json,random,shutil
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5_production'
DEST=PRIVATE/'v5_full_independent_review'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def main():
    if DEST.exists():raise ValueError('Independent review already frozen; do not overwrite')
    manifest=js(RUN/'manifest.json');texts={}
    for item in manifest['batches']:
        p=RUN/'inputs'/item['name']
        if sha(p)!=item['sha256']:raise ValueError('Production input changed')
        texts.update({r['sample_id']:r['text'] for r in jl(p)})
    keys=csvs(RUN/'private_key.csv');excluded=set(js(PRIVATE/'variable_scheme_v5/excluded_ids.json'))
    eligible=sorted(r['sample_id'] for r in keys if r['source_id'] not in excluded and not r['trial_sample_id'])
    if len(eligible)!=2833 or len(texts)!=4156:raise ValueError('Additional review pool differs')
    selected=random.Random(2026110523).sample(eligible,80)
    DEST.mkdir();shutil.copyfile(RUN/'frozen_codebook.md',DEST/'frozen_codebook.md')
    blind=[{'sample_id':f'V5R{i:04d}','text':texts[sid]} for i,sid in enumerate(selected,1)]
    key=[{'sample_id':f'V5R{i:04d}','production_sample_id':sid} for i,sid in enumerate(selected,1)]
    (DEST/'blind.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in blind))
    with (DEST/'private_key.csv').open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(key[0]));w.writeheader();w.writerows(key)
    outputs=list((RUN/'outputs').glob('batch_*.jsonl'))
    meta={'status':'additional_AI_review_sample_frozen_during_partial_production_before_outcome_analysis',
      'seed':2026110523,'n_unique':80,'n_eligible_unique':len(eligible),'n_documented_prior_dev_and_review_excluded':4156-len(eligible),
      'production_batches_present_at_freeze':len(outputs),'codebook_sha256':sha(DEST/'frozen_codebook.md'),
      'blind_sha256':sha(DEST/'blind.jsonl'),'private_key_sha256':sha(DEST/'private_key.csv'),
      'production_manifest_sha256':sha(RUN/'manifest.json'),
      'purpose':'A fresh independent context reads 80 random unique texts outside documented earlier development and review packets. Coder sees only anonymous text and manual.',
      'limits':'Supplemental same-base AI operational consistency, not human accuracy or never-seen-corpus validation. Sampling was frozen after partial production had begun; no annotation distribution or likes used.'}
    dump(DEST/'metadata.json',meta);print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
