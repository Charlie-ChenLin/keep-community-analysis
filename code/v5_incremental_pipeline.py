#!/usr/bin/env python3
"""Validate each outcome-blind production batch and map a complete v5 corpus.

Never performs semantic classification or imports previous labels. Row-level
outputs are written only into the ignored production directory.
"""
from pathlib import Path
from collections import Counter
import argparse, csv, hashlib, importlib.util, json, shutil

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5_production'
OUT=ROOT/'results/v5_full_coding_summary.json'
spec=importlib.util.spec_from_file_location('v5_validator',ROOT/'code/evaluate_variable_scheme_v5.py')
validator=importlib.util.module_from_spec(spec);spec.loader.exec_module(validator)

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def check_sources():
    m=js(RUN/'manifest.json')
    if sha(RUN/'frozen_codebook.md')!=m['frozen_codebook_sha256'] or sha(ROOT/'正文多维测量方案_v5_编码手册.md')!=m['frozen_codebook_sha256']:
        raise ValueError('Codebook changed after freeze')
    if sha(RUN/'frozen_protocol.json')!=m['frozen_protocol_sha256'] or sha(ROOT/'code/variable_scheme_v5_protocol.json')!=m['frozen_protocol_sha256']:
        raise ValueError('Base protocol changed after freeze')
    for name,key in [('private_key.csv','private_key_sha256'),('post_map.csv','post_map_sha256'),('source_integrity.json','source_integrity_sha256')]:
        if sha(RUN/name)!=m[key]:raise ValueError('Production source integrity failed: '+name)
    if len(m['batches'])!=84 or m['n_unique_texts']!=4156:raise ValueError('Manifest population mismatch')
    return m

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--merge',action='store_true');args=parser.parse_args()
    manifest=check_sources();missing=[];rows=[];hashes={};expected_ids=[]
    for b in manifest['batches']:
        src=RUN/'inputs'/b['name'];inp=jl(src)
        if sha(src)!=b['sha256'] or len(inp)!=b['rows']:raise ValueError('Input batch changed')
        texts={r['sample_id']:r['text'] for r in inp}
        if len(texts)!=len(inp):raise ValueError('Input duplicate IDs')
        expected_ids.extend(texts)
        path=RUN/'outputs'/b['name']
        if not path.exists():missing.append(b['name']);continue
        coded=validator.validate(path,texts)
        rows.extend(coded[sid] for sid in texts);hashes[b['name']]=sha(path)
    progress={'validated_batches':len(hashes),'required_batches':84,'validated_unique_texts':len(rows),'required_unique_texts':4156,
      'missing_batches':missing,'complete':not missing}
    if len(expected_ids)!=4156 or len(set(expected_ids))!=4156 or len({r['sample_id'] for r in rows})!=len(rows):raise ValueError('Corpus ID mismatch')
    if not args.merge:
        print(json.dumps(progress,ensure_ascii=False,indent=2));return
    if missing:raise ValueError('Cannot merge incomplete coding: '+str(progress))
    if (RUN/'resumption_001.json').exists():
        old_hashes=js(RUN/'resumption_001.json')['previous_output_sha256']
        if any(hashes.get(name)!=old_sha for name,old_sha in old_hashes.items()):raise ValueError('A completed pre-interruption output changed')
    extra=set(p.name for p in (RUN/'outputs').glob('batch_*.jsonl'))-set(hashes)
    if extra:raise ValueError('Unexpected output files')
    rows_by_id={r['sample_id']:r for r in rows};mapping=csvs(RUN/'post_map.csv')
    if len(mapping)!=9532 or len({r['postId'] for r in mapping})!=9532 or sum(bool(r['sample_id']) for r in mapping)!=5414:
        raise ValueError('Whole-post mapping mismatch')
    output_rows=[]
    for p in mapping:
        sid=p['sample_id'];r=rows_by_id.get(sid)
        row={'postId':p['postId'],'sample_id':sid,'input_status':p['input_status']}
        for c in validator.TOPICS+validator.EXPRESSIONS:row[c]='' if r is None or validator.val(r,c) is None else validator.val(r,c)
        for f in validator.ATTRS:row[f]=r[f] if r else 'unobserved_body'
        row['topic_positive_count']=sum(validator.val(r,c)==1 for c in validator.TOPICS[:-1]) if r else ''
        row['expression_positive_count']=sum(validator.val(r,c)==1 for c in validator.EXPRESSIONS[:-1]) if r else ''
        row['topic_known_count']=sum(validator.val(r,c) is not None for c in validator.TOPICS[:-1]) if r else ''
        row['expression_known_count']=sum(validator.val(r,c) is not None for c in validator.EXPRESSIONS[:-1]) if r else ''
        output_rows.append(row)
    (RUN/'merged_unique.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    with (RUN/'post_labels.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(output_rows[0]));w.writeheader();w.writerows(output_rows)
    repeated=[rows_by_id[p['sample_id']] for p in mapping if p['sample_id']]
    unique_coverage=validator.coverage(rows);post_coverage=validator.coverage(repeated)
    freeze=js(RUN/'full_run_freeze.json')
    if sha(RUN/'frozen_full_analysis_protocol.json')!=freeze['analysis_protocol_sha256'] or sha(ROOT/'code/v5_full_analysis_protocol.json')!=freeze['analysis_protocol_sha256']:
        raise ValueError('Full analysis protocol changed')
    summary={'status':'all_unique_texts_reread_and_structurally_validated_not_human_accuracy',**{k:v for k,v in progress.items() if k!='missing_batches'},
      'n_total_posts':9532,'n_nonempty_posts':5414,'n_unique_texts':4156,'source_states':dict(Counter(p['input_status'] for p in mapping)),
      'unique_text_coverage':unique_coverage,'post_coverage':post_coverage,
      'all_positive_evidence_exact_substrings_checked':True,'all_attribute_parent_constraints_checked':True,
      'old_or_trial_labels_used_as_production_answers':False,'n_independent_human_reviews':0,
      'codebook_sha256':manifest['frozen_codebook_sha256'],'analysis_protocol_sha256':freeze['analysis_protocol_sha256'],
      'input_manifest_sha256':sha(RUN/'manifest.json'),'assignment_sha256':sha(RUN/'full_run_assignment.json'),
      'output_batch_sha256':hashes,'merged_unique_sha256':sha(RUN/'merged_unique.jsonl'),'post_labels_sha256':sha(RUN/'post_labels.csv'),
      'resumption_manifest_sha256':sha(RUN/'resumption_001.json') if (RUN/'resumption_001.json').exists() else None,
      'transcription_corrections_sha256':sha(RUN/'transcription_corrections_001.json') if (RUN/'transcription_corrections_001.json').exists() else None,
      'n_coder_reported_recording_corrections':len(js(RUN/'transcription_corrections_001.json')['corrections']) if (RUN/'transcription_corrections_001.json').exists() else 0,
      'semantic_boundary_flags_sha256':sha(RUN/'semantic_boundary_flags_001.json') if (RUN/'semantic_boundary_flags_001.json').exists() else None,
      'n_coder_reported_boundary_flags':len(js(RUN/'semantic_boundary_flags_001.json')['flags']) if (RUN/'semantic_boundary_flags_001.json').exists() else 0,
      'n_coder_reported_unresolved_boundary_flags':sum(not f.get('status','').startswith('resolved_') for f in js(RUN/'semantic_boundary_flags_001.json')['flags']) if (RUN/'semantic_boundary_flags_001.json').exists() else 0,
      'limits':['One new production coding per distinct text across separate reading contexts, with fresh contexts for unfinished batches after interruption; this is not full-corpus dual coding.',
        'Same-base AI semantic predictions lack independent human gold validation.',
        'Positive coverage is tagging breadth, not accuracy or total regression utilization.']}
    dump(OUT,summary);dump(RUN/'merge_summary.json',summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['post_coverage','unique_text_coverage','output_batch_sha256']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
