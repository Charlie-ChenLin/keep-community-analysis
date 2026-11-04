#!/usr/bin/env python3
"""Prepare a fresh, outcome-blind, same-model consistency check locally."""
from pathlib import Path
import csv, hashlib, json, random

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'v2_direct_batches'
DEST=PRIVATE/'v2_fresh_blind_check'
SEED=20261105

def readcsv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    if DEST.exists():raise SystemExit('Check directory exists; do not overwrite')
    manifest=json.loads((RUN/'manifest.json').read_text())
    exclude_postids=set()
    for path in [PRIVATE/'development_keys.csv', PRIVATE/'calibration_keys.csv', PRIVATE/'holdout_keys.csv',
                 PRIVATE/'feature_rationale_review/private_key.csv', ROOT/'results/text_coding_review.csv']:
        exclude_postids.update(row['postId'] for row in readcsv(path) if row.get('postId'))
    mappings=readcsv(RUN/'id_map.csv')
    excluded_ids={r['sample_id'] for r in mappings if r['postId'] in exclude_postids and r['sample_id']}
    eligible=[]
    for batch in manifest['batches']:
        p=RUN/'inputs'/batch['name']
        if sha(p)!=batch['sha256']:raise ValueError('source input batch changed')
        for line in p.read_text().splitlines():
            row=json.loads(line)
            if row['sample_id'] not in excluded_ids:eligible.append(row)
    if len(eligible)<90:raise ValueError('not enough independent eligible text')
    selected=random.Random(SEED).sample(eligible,90)
    DEST.mkdir(parents=True)
    for i in range(3):
        out=DEST/f'blind_{i+1}.jsonl'
        out.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in selected[i*30:(i+1)*30]))
    meta={'purpose':'Independent-context same-model blind second coding, not human validity or model accuracy',
          'seed':SEED, 'sampling_unit':'unique cleaned text, uniformly sampled without replacement',
          'excluded_ids':'all 400 old development/calibration/holdout, 64 rule-check sample and historical text coding review; duplicate bodies also excluded',
          'n_eligible_unique':len(eligible),'sample_unique':90,'per_reader':30,
          'codebook_sha256':manifest['codebook_sha256'],
          'blind_sha256':{f'blind_{i}.jsonl':sha(DEST/f'blind_{i}.jsonl') for i in (1,2,3)}}
    (DEST/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(meta,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
