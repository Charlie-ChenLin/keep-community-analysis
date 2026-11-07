#!/usr/bin/env python3
"""Compare a frozen supplemental blind AI review with completed production.

This measures same-base coding consistency, never human accuracy. No production
labels are changed and no regression candidate is selected by this comparison.
"""
from pathlib import Path
import csv, hashlib, importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5_production'
REVIEW=PRIVATE/'v5_full_independent_review'
spec=importlib.util.spec_from_file_location('v5',ROOT/'code/evaluate_variable_scheme_v5.py')
v5=importlib.util.module_from_spec(spec);spec.loader.exec_module(v5)
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    meta=js(REVIEW/'metadata.json');summary=js(RUN/'merge_summary.json')
    for name,key in [('blind.jsonl','blind_sha256'),('private_key.csv','private_key_sha256'),('frozen_codebook.md','codebook_sha256')]:
        if sha(REVIEW/name)!=meta[key]:raise ValueError('Frozen additional review source changed: '+name)
    if sha(RUN/'manifest.json')!=meta['production_manifest_sha256'] or sha(RUN/'merged_unique.jsonl')!=summary['merged_unique_sha256']:
        raise ValueError('Production source changed')
    texts={r['sample_id']:r['text'] for r in jl(REVIEW/'blind.jsonl')}
    coded=v5.validate(REVIEW/'coder.jsonl',texts)
    with (REVIEW/'private_key.csv').open(newline='',encoding='utf-8') as f:key=list(csv.DictReader(f))
    prod={r['sample_id']:r for r in jl(RUN/'merged_unique.jsonl')}
    if len(key)!=80 or set(texts)!=set(coded) or set(texts)!={r['sample_id'] for r in key}:
        raise ValueError('Additional review population mismatch')
    a=[prod[r['production_sample_id']] for r in key];b=[coded[r['sample_id']] for r in key]
    comparison=v5.agreement(a,b,js(RUN/'frozen_protocol.json')['consistency_screen'])
    for row in comparison['per_label'].values():row.pop('screen_state_if_random_partition',None)
    result={'status':'supplemental_blind_same_base_AI_consistency_not_accuracy','sampling_metadata':meta,
      'n':80,'production':v5.coverage(a),'review':v5.coverage(b),'agreement':comparison,
      'n_independent_human_reviews':0,'production_labels_changed':False,
      'input_sha256':{'review_coding':sha(REVIEW/'coder.jsonl'),'review_metadata':sha(REVIEW/'metadata.json'),
        'production_merged':sha(RUN/'merged_unique.jsonl')},
      'limits':['Sample frozen during partial production, before annotation distribution and outcome analysis; not part of the original v5 pilot.',
        'Excludes documented previous development and review texts; prior whole-corpus coding means it is not a never-seen corpus.',
        'Fresh contexts with the same model base can share errors. Do not interpret agreement as accuracy.',
        'Do not pool this 80-text review with the original 200 random or 60 targeted diagnostics to estimate full-corpus coverage.']}
    out=ROOT/'results/v5_full_additional_ai_review.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'n':80,'expression_positive_and_unknown_set_exact':comparison['expression_positive_and_unknown_set_exact'],
      'same_expression':comparison['at_least_one_same_named_expression'],'per_label':comparison['per_label']},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
