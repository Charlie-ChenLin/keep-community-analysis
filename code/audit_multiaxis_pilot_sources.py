#!/usr/bin/env python3
"""Post-sampling source-integrity audit; does not change frozen samples/rules."""
from pathlib import Path
from collections import Counter
import csv, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'multiaxis_v4_pilot'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    src=PRIVATE/'v2_direct_batches';manifest=js(src/'manifest.json');texts={};batch_checks={}
    for b in manifest['batches']:
        p=src/'inputs'/b['name'];rows=jl(p)
        if sha(p)!=b['sha256'] or len(rows)!=b['rows']:raise ValueError('Source batch changed')
        if any(r['sample_id'] in texts or not r['text'].strip() for r in rows):raise ValueError('Invalid source text')
        texts.update({r['sample_id']:r['text'] for r in rows});batch_checks[b['name']]=sha(p)
    rows=csvs(src/'id_map.csv');mapped={r['sample_id'] for r in rows if r['sample_id']}
    if len(texts)!=4156 or len(set(texts.values()))!=4156 or len(rows)!=9532 or len({r['postId'] for r in rows})!=9532 or mapped!=set(texts):
        raise ValueError('Input population/mapping mismatch')
    if sum(r['input_status']=='needs_model' for r in rows)!=5414 or sha(src/'id_map.csv')!=manifest['id_map_sha256']:
        raise ValueError('Source map differs from frozen manifest')
    freeze=js(RUN/'freeze.json');meta=js(RUN/'sample_metadata.json');keys=csvs(RUN/'private_key.csv')
    for p,k in [(src/'id_map.csv','source_map_sha256'),(src/'manifest.json','source_manifest_sha256'),
      (RUN/'frozen_codebook.md','codebook_sha256'),(PRIVATE/'variable_scheme_exploration/design_sample.jsonl','design_sample_sha256')]:
        if sha(p)!=freeze[k]:raise ValueError('Pilot source hash mismatch')
    if sha(RUN/'private_key.csv')!=meta['private_key_sha256']:raise ValueError('Pilot key changed')
    v3path=PRIVATE/'v3_refined_batches/merged_unique.jsonl';v3={r['sample_id']:r for r in jl(v3path)}
    if set(v3)!=set(texts):raise ValueError('v3 corpus mismatch')
    design={r['sample_id'] for r in jl(PRIVATE/'variable_scheme_exploration/design_sample.jsonl')}
    prior={r['v2_sample_id'] for r in csvs(PRIVATE/'v3_independent_validation/private_key.csv')}
    selected={r['source_id'] for r in keys}
    if len(keys)!=160 or len(selected)!=160 or selected&(design|prior):raise ValueError('Pilot overlap')
    if Counter(r['partition'] for r in keys)!={'random':120,'targeted_no_v3_positive':40}:raise ValueError('Partition size mismatch')
    for r in keys:
        if r['partition']=='targeted_no_v3_positive' and v3[r['source_id']]['positive_labels']:raise ValueError('Targeted source not as declared')
    for who in ('a','b'):
        blind=jl(RUN/f'blind_{who}.jsonl');d={r['sample_id']:r['text'] for r in blind}
        if len(blind)!=160 or len(d)!=160 or sha(RUN/f'blind_{who}.jsonl')!=meta['blind_sha256']:raise ValueError('Blind sample changed')
        if any(d[r['sample_id']]!=texts[r['source_id']] for r in keys):raise ValueError('Blind-to-source mismatch')
    result={'status':'passed_post_sampling_read_only_source_audit','n_source_unique':4156,'n_posts':9532,'n_nonempty':5414,
      'n_batches':len(batch_checks),'n_pilot_unique':160,'partition_counts':dict(Counter(r['partition'] for r in keys)),
      'source_batch_sha256':batch_checks,'v3_merged_unique_sha256_checked_after_sampling':sha(v3path),
      'limits':'This is a retrospective integrity check. The v3 merged-label hash was not frozen before pilot sampling; current consistency cannot prove an unrecorded earlier state.',
      'frozen_codebook_sha256':sha(RUN/'frozen_codebook.md'),'private_key_sha256':sha(RUN/'private_key.csv')}
    out=ROOT/'results/multiaxis_v4_source_audit.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_batch_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
