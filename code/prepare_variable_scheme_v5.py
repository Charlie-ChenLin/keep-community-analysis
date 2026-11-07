#!/usr/bin/env python3
"""Freeze rules and source hashes before releasing new outcome-blind packets."""
from pathlib import Path
from collections import Counter
import csv, hashlib, importlib.util, json, random, shutil

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'validation/classification_rebuild/private'
DEST = PRIVATE / 'variable_scheme_v5'

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def js(path): return json.loads(Path(path).read_text())
def jl(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def csvs(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))
def dump(path, obj): path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')

def exclusions(texts, mapping):
    spec = importlib.util.spec_from_file_location('previous_review', ROOT/'code/prepare_v3_independent_review.py')
    prev = importlib.util.module_from_spec(spec); spec.loader.exec_module(prev)
    pid = {r['postId']: r['sample_id'] for r in mapping if r['sample_id']}
    thash = {hashlib.sha256(t.encode()).hexdigest(): sid for sid,t in texts.items()}
    excluded = set(prev.PREVIOUS_SPOTCHECK)
    for p in prev.PREVIOUS:
        for r in csvs(p):
            if r.get('postId') in pid: excluded.add(pid[r['postId']])
            for key in ('clean_text', 'text'):
                h = hashlib.sha256(r.get(key, '').encode()).hexdigest()
                if h in thash: excluded.add(thash[h])
    for p in prev.PRIOR_BLINDS: excluded.update(r['sample_id'] for r in jl(p))
    legacy = {r['sample_id']:r['postId'] for f in ('development_keys.csv','calibration_keys.csv','holdout_keys.csv') for r in csvs(PRIVATE/f)}
    for r in js(prev.DESIGN)['rows']:
        candidates = {pid[r['postId']]} if r.get('postId') in pid else set()
        if r.get('sample_id') in legacy and legacy[r['sample_id']] in pid: candidates.add(pid[legacy[r['sample_id']]])
        if r.get('sample_id') in texts: candidates.add(r['sample_id'])
        if r.get('text_sha256') in thash: candidates.add(thash[r['text_sha256']])
        if len(candidates) != 1: raise ValueError('Cannot resolve earlier development text')
        excluded.update(candidates)
    excluded.update(r['v2_sample_id'] for r in csvs(prev.DEST/'private_key.csv'))
    excluded.update(r['sample_id'] for r in jl(PRIVATE/'variable_scheme_exploration/design_sample.jsonl'))
    if len(excluded) != 903: raise ValueError('v4 exclusion population changed')
    excluded.update(r['source_id'] for r in csvs(PRIVATE/'multiaxis_v4_pilot/private_key.csv'))
    return excluded

def main():
    if DEST.exists(): raise ValueError('Frozen v5 sample exists; do not overwrite or resample')
    protocol = js(ROOT/'code/variable_scheme_v5_protocol.json')
    src = PRIVATE/'v2_direct_batches'; manifest = js(src/'manifest.json'); texts={}; source_paths=[]
    for batch in manifest['batches']:
        p = src/'inputs'/batch['name']; rows=jl(p)
        if sha(p) != batch['sha256'] or len(rows) != batch['rows']: raise ValueError('Changed source batch')
        if any(r['sample_id'] in texts for r in rows): raise ValueError('Duplicate source ID')
        texts.update({r['sample_id']:r['text'] for r in rows}); source_paths.append(p)
    mapping = csvs(src/'id_map.csv')
    if len(texts)!=4156 or len(set(texts.values()))!=4156 or len(mapping)!=9532 or len({r['postId'] for r in mapping})!=9532:
        raise ValueError('Source units changed')
    multiplicity=Counter(r['sample_id'] for r in mapping if r['sample_id'])
    if sum(multiplicity.values())!=5414 or set(multiplicity)!=set(texts): raise ValueError('Nonempty population changed')
    excluded=exclusions(texts,mapping)
    if excluded-set(texts): raise ValueError('Exclusions outside corpus')
    v2path=src/'merged_unique.jsonl';v3path=PRIVATE/'v3_refined_batches/merged_unique.jsonl'
    v3={r['sample_id']:r for r in jl(v3path)}
    if set(v3)!=set(texts): raise ValueError('v3 universe differs')
    DEST.mkdir()
    shutil.copyfile(ROOT/'正文多维测量方案_v5_编码手册.md', DEST/'frozen_codebook.md')
    shutil.copyfile(ROOT/'code/variable_scheme_v5_protocol.json', DEST/'frozen_protocol.json')
    paths=[*source_paths, src/'manifest.json', src/'id_map.csv', v2path, v3path,
      PRIVATE/'multiaxis_v4_pilot/private_key.csv', PRIVATE/'variable_scheme_exploration/design_sample.jsonl']
    dump(DEST/'freeze.json', {'status':'rules_protocol_and_sources_frozen_before_sampling',
      'codebook_sha256':sha(DEST/'frozen_codebook.md'), 'protocol_sha256':sha(DEST/'frozen_protocol.json'),
      'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths},
      'n_excluded':len(excluded),'excluded_ids_sha256':hashlib.sha256('\n'.join(sorted(excluded)).encode()).hexdigest()})
    eligible=sorted(set(texts)-excluded);rng=random.Random(protocol['seed'])
    random_ids=rng.sample(eligible,protocol['random_unique_texts'])
    targeted_pool=[s for s in eligible if s not in random_ids and not v3[s]['positive_labels']]
    target_ids=rng.sample(targeted_pool,protocol['targeted_no_v3_positive_unique_texts'])
    keys=[];blind=[]
    for i,(sid,part) in enumerate([(s,'random') for s in random_ids]+[(s,'targeted_no_v3_positive') for s in target_ids],1):
        anon=f'V5X{i:04d}'
        keys.append({'sample_id':anon,'source_id':sid,'partition':part,'post_multiplicity':multiplicity[sid]})
        blind.append({'sample_id':anon,'text':texts[sid]})
    with (DEST/'private_key.csv').open('x', encoding='utf-8', newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(keys[0]));w.writeheader();w.writerows(keys)
    payload=''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in blind)
    for who in ('a','b'): (DEST/f'blind_{who}.jsonl').write_text(payload)
    dump(DEST/'excluded_ids.json',sorted(excluded))
    meta={'n_corpus_unique':len(texts),'n_nonempty_posts':5414,'n_excluded':len(excluded),
      'n_eligible':len(eligible),'n_random':len(random_ids),'n_targeted':len(target_ids),
      'n_targeted_pool_after_random':len(targeted_pool),'seed':protocol['seed'],
      'random_inclusion_probability':len(random_ids)/len(eligible),
      'represented_posts_by_partition':{p:sum(int(r['post_multiplicity']) for r in keys if r['partition']==p) for p in ('random','targeted_no_v3_positive')},
      'sampling_unit':'Exact unique cleaned text, random from documented design-excluded pool; targeted sample separate.',
      'prior_exposure':'Whole corpus coded by earlier models; this is separate from documented development and prior validation, not a never-seen corpus.',
      'blind_sha256':sha(DEST/'blind_a.jsonl'),'private_key_sha256':sha(DEST/'private_key.csv')}
    dump(DEST/'sample_metadata.json',meta)
    print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
