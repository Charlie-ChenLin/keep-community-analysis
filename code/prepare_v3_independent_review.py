#!/usr/bin/env python3
"""Freeze and draw an outcome-blind review sample for the v3 codebook.

The source corpus has already been seen by earlier AI coding. The held-out
sample is independent only of the documented v3 design and earlier validation
packets; blind re-coding by model contexts is not human validation or accuracy.
All inputs containing texts, IDs or individual judgements remain under the
git-ignored ``classification_rebuild/private`` directory.

Example, once codebook/schema/design provenance are final:
  python code/prepare_v3_independent_review.py freeze --codebook ... --schema ...
  python code/prepare_v3_independent_review.py sample
No sample is drawn by freeze. Frozen inputs cannot be overwritten in place.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = (ROOT / 'validation/classification_rebuild/private').resolve()
V2 = PRIVATE / 'v2_direct_batches'
DEST = PRIVATE / 'v3_independent_validation'
DESIGN = PRIVATE / 'v3_design_trace/read_sample_provenance.json'
OUT = ROOT / 'results/v3_independent_ai_agreement.json'
PREVIOUS = [
    PRIVATE/'development_keys.csv', PRIVATE/'calibration_keys.csv', PRIVATE/'holdout_keys.csv',
    PRIVATE/'feature_rationale_review/private_key.csv', ROOT/'results/text_coding_review.csv',
    ROOT/'validation/teacher_feedback/label_review_private.csv',
    ROOT/'results/extension_topic_examples.csv',
]
PRIOR_BLINDS = [PRIVATE/f'v2_fresh_blind_check/blind_{i}.jsonl' for i in (1, 2, 3)]
# These anonymous IDs are texts displayed during prior manual spot-checks.
PREVIOUS_SPOTCHECK = {'P001644','P000172','P000035','P001679','P002868','P001827','P003086','P001784',
                      'P002382','P002221','P000247','P000186'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def readcsv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def jsonl(path):
    with path.open(encoding='utf-8') as f:
        return [json.loads(line) for line in f if line.strip()]


def dump(path, obj):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def freeze(args):
    codebook = Path(args.codebook).resolve()
    schema = Path(args.schema).resolve()
    if DEST.exists():
        raise ValueError('v3 review directory already exists; never overwrite a frozen packet')
    required = [codebook, schema, DESIGN, V2/'manifest.json', V2/'id_map.csv', *PREVIOUS, *PRIOR_BLINDS]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise ValueError('required frozen/exclusion sources are missing: ' + ', '.join(missing))
    scheme = json.loads(schema.read_text(encoding='utf-8'))
    if not isinstance(scheme, dict):
        raise ValueError('schema must be a JSON object')
    design = json.loads(DESIGN.read_text(encoding='utf-8'))
    if not isinstance(design, dict) or not isinstance(design.get('rows'), list):
        raise ValueError('design provenance must provide rows')
    if args.n <= 0:
        raise ValueError('sample size must be positive')
    DEST.mkdir(parents=True)
    shutil.copyfile(codebook, DEST/'frozen_codebook.md')
    shutil.copyfile(schema, DEST/'frozen_schema.json')
    shutil.copyfile(DESIGN, DEST/'frozen_design_provenance.json')
    source_hashes = {str(p.relative_to(ROOT)): sha(p) for p in required
                     if p not in (codebook, schema, DESIGN)}
    record = {
        'status': 'frozen_before_sample',
        'sample_n': args.n,
        'random_seed': args.seed,
        'sample_unit': 'unique exact cleaned text, simple random without replacement',
        'probability': 'sample_n / eligible unique texts, calculated after exclusions',
        'purpose': 'Two isolated same-base AI contexts independently label the same new v3-design holdout; not human accuracy.',
        'prior_exposure': 'All nonempty texts were previously AI coded under v2; no claim that model has never seen the corpus.',
        'data_boundary': 'Only anonymous ID and full cleaned text go to each blind coder; no author, likes, tag, old labels or first coder results.',
        'frozen_codebook_sha256': sha(DEST/'frozen_codebook.md'),
        'frozen_schema_sha256': sha(DEST/'frozen_schema.json'),
        'frozen_design_provenance_sha256': sha(DEST/'frozen_design_provenance.json'),
        'source_sha256': source_hashes,
        'no_reuse_rule': 'If labels, definitions, thresholds, exclusions or sample design are revised using this packet, it becomes development data and a new independent packet must be drawn.',
    }
    dump(DEST/'freeze.json', record)
    print(json.dumps({'status': record['status'], 'sample_n': args.n,
                      'codebook_sha256': record['frozen_codebook_sha256']}, ensure_ascii=False))


def verify_freeze():
    record = json.loads((DEST/'freeze.json').read_text(encoding='utf-8'))
    for name, key in [('frozen_codebook.md','frozen_codebook_sha256'),
                      ('frozen_schema.json','frozen_schema_sha256'),
                      ('frozen_design_provenance.json','frozen_design_provenance_sha256')]:
        if sha(DEST/name) != record[key]:
            raise ValueError('frozen artifact changed: ' + name)
    for relative, digest in record['source_sha256'].items():
        p = ROOT/relative
        if not p.is_file() or sha(p) != digest:
            raise ValueError('frozen source changed: ' + relative)
    return record


def sample(args):
    record = verify_freeze()
    if (DEST/'sample_metadata.json').exists():
        raise ValueError('sample already released; do not resample or overwrite')
    source_manifest = json.loads((V2/'manifest.json').read_text(encoding='utf-8'))
    if sha(V2/'id_map.csv') != source_manifest['id_map_sha256']:
        raise ValueError('v2 ID map differs from manifest')
    postmap = readcsv(V2/'id_map.csv')
    post_to_sid = {r['postId']:r['sample_id'] for r in postmap if r['sample_id']}
    post_counts = Counter(r['sample_id'] for r in postmap if r['sample_id'])
    texts = {}
    for batch in source_manifest['batches']:
        p = V2/'inputs'/batch['name']
        if sha(p) != batch['sha256']:
            raise ValueError('input batch changed: ' + batch['name'])
        for row in jsonl(p):
            sid = row['sample_id']
            if sid in texts:
                raise ValueError('duplicate unique-text ID')
            texts[sid] = row['text']
    if len(texts) != source_manifest['nonempty_unique_texts']:
        raise ValueError('unique input count mismatch')
    if set(texts) != set(post_counts):
        raise ValueError('post-to-text mapping mismatch')
    hash_to_sid = {}
    for sid,text in texts.items():
        digest = text_sha(text)
        if digest in hash_to_sid:
            raise ValueError('v2 unique texts are not unique by exact SHA-256')
        hash_to_sid[digest] = sid

    excluded = set(PREVIOUS_SPOTCHECK)
    reasons = {'manual_spotchecks': len(excluded)}
    for path in PREVIOUS:
        hit = set()
        for row in readcsv(path):
            pid = row.get('postId', '')
            if pid and pid in post_to_sid:
                hit.add(post_to_sid[pid])
            for column in ('clean_text','text'):
                raw = row.get(column, '')
                if raw and text_sha(raw) in hash_to_sid:
                    hit.add(hash_to_sid[text_sha(raw)])
        reasons[str(path.relative_to(ROOT))] = len(hit)
        excluded.update(hit)
    for path in PRIOR_BLINDS:
        hit = {r['sample_id'] for r in jsonl(path)}
        if hit-set(texts):
            raise ValueError('prior blind sample not in v2 population')
        reasons[str(path.relative_to(ROOT))] = len(hit)
        excluded.update(hit)

    design = json.loads((DEST/'frozen_design_provenance.json').read_text(encoding='utf-8'))
    known_legacy = {}
    for fname in ('development_keys.csv','calibration_keys.csv','holdout_keys.csv'):
        known_legacy.update({r['sample_id']:r['postId'] for r in readcsv(PRIVATE/fname)})
    design_hits = set()
    for row in design['rows']:
        candidates = []
        if row.get('postId') in post_to_sid:
            candidates.append(post_to_sid[row['postId']])
        if row.get('sample_id') in known_legacy and known_legacy[row['sample_id']] in post_to_sid:
            candidates.append(post_to_sid[known_legacy[row['sample_id']]])
        if row.get('sample_id') in texts:
            candidates.append(row['sample_id'])
        if row.get('text_sha256') in hash_to_sid:
            candidates.append(hash_to_sid[row['text_sha256']])
        if not candidates or len(set(candidates)) != 1:
            raise ValueError('unresolvable or inconsistent v3 design provenance')
        design_hits.add(candidates[0])
    excluded.update(design_hits)
    reasons['v3_design_provenance'] = len(design_hits)
    if excluded-set(texts):
        raise ValueError('a listed exclusion is absent from source')
    eligible = sorted(set(texts)-excluded)
    if len(eligible) < record['sample_n']:
        raise ValueError('too few eligible unique texts')
    chosen = random.Random(record['random_seed']).sample(eligible, record['sample_n'])
    keyrows = []
    blindrows = []
    for index, sid in enumerate(chosen, 1):
        anonymous = f'V3E{index:04d}'
        keyrows.append({'review_id':anonymous, 'v2_sample_id':sid,
                        'text_sha256':text_sha(texts[sid]), 'post_multiplicity':post_counts[sid]})
        blindrows.append({'sample_id':anonymous, 'text':texts[sid]})
    with (DEST/'private_key.csv').open('x',encoding='utf-8',newline='') as f:
        w = csv.DictWriter(f,fieldnames=list(keyrows[0]));w.writeheader();w.writerows(keyrows)
    payload = ''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in blindrows)
    # Separate files have identical content but do not reveal the other coder.
    (DEST/'blind_a.jsonl').write_text(payload, encoding='utf-8')
    (DEST/'blind_b.jsonl').write_text(payload, encoding='utf-8')
    chunk_hashes = {}
    # Matching partitions allow separate annotators to work in parallel while
    # each text is still independently coded by both A and B contexts.
    for part in range(4):
        subset = blindrows[part::4]
        if not subset:
            continue
        chunk = ''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in subset)
        for coder in ('a','b'):
            name = f'blind_{coder}_part_{part+1:02d}.jsonl'
            (DEST/name).write_text(chunk,encoding='utf-8')
            chunk_hashes[name] = sha(DEST/name)
    metadata = {'status':'released_after_freeze', 'n_population_unique_texts':len(texts),
        'n_excluded_unique_texts':len(excluded), 'exclusion_hits_overlap':reasons,
        'n_eligible_unique_texts':len(eligible), 'n_sampled_unique_texts':len(chosen),
        'per_unique_text_inclusion_probability':len(chosen)/len(eligible),
        'sampling_unit':'unique exact cleaned text', 'sampling_seed':record['random_seed'],
        'n_represented_posts':sum(post_counts[sid] for sid in chosen),
        'post_multiplicity_is_not_a_sampling_probability':'raw sample is not a post-weighted sample',
        'frozen_codebook_sha256':record['frozen_codebook_sha256'],
        'blind_a_sha256':sha(DEST/'blind_a.jsonl'), 'blind_b_sha256':sha(DEST/'blind_b.jsonl'),
        'blind_partition_sha256':chunk_hashes,
        'private_key_sha256':sha(DEST/'private_key.csv'),
        'warnings':['Data already seen in v2 coding; this is a v3 design holdout, not an untouched corpus.',
                    'Two same-base AI contexts provide consistency, not human accuracy.',
                    'Small and rare labels require independent human validation.']}
    dump(DEST/'sample_metadata.json',metadata)
    print(json.dumps(metadata,ensure_ascii=False,indent=2))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--codebook',required=True);f.add_argument('--schema',required=True)
    f.add_argument('--n',type=int,default=120);f.add_argument('--seed',type=int,default=20261106)
    sub.add_parser('sample')
    args=parser.parse_args()
    try:
        if args.command=='freeze':freeze(args)
        else:sample(args)
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('ERROR:',exc,file=sys.stderr);return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
