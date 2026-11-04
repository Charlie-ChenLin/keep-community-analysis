#!/usr/bin/env python3
"""Check a new sample's two independent AI coding contexts (not accuracy)."""
from pathlib import Path
from collections import Counter
import hashlib, importlib.util, json

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'v2_direct_batches'; REVIEW=PRIVATE/'v2_fresh_blind_check'
OUT=ROOT/'results/v2_fresh_blind_agreement.json'
spec=importlib.util.spec_from_file_location('local_pipeline',ROOT/'code/local_ai_batch_pipeline.py')
pipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(pipe)

def read(path):return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    metadata=json.loads((REVIEW/'metadata.json').read_text())
    manifest,schema=pipe.verify_inputs(RUN)
    if manifest['codebook_sha256']!=metadata['codebook_sha256']:raise ValueError('Codebook differs')
    all_first={r['sample_id']:r for r in read(RUN/'merged_unique.jsonl')}
    pairs=[]
    for batch in (1,2,3):
        blind=REVIEW/f'blind_{batch}.jsonl';output=REVIEW/f'coder_{batch}.jsonl'
        if sha(blind)!=metadata['blind_sha256'][blind.name]:raise ValueError('Blind input modified')
        source={r['sample_id']:r['text'] for r in read(blind)}
        rows=read(output);ids=[r['sample_id'] for r in rows]
        if len(ids)!=30 or len(set(ids))!=30 or set(ids)!=set(source):raise ValueError('ID mismatch')
        for r in rows:
            pipe.check_row(r,source[r['sample_id']],schema)
            if r['sample_id'] not in all_first:raise ValueError('Missing first code')
            pairs.append((all_first[r['sample_id']],r))
    if len({x['sample_id'] for x,_ in pairs})!=90:raise ValueError('Duplicate review IDs')
    summary={'n':len(pairs),'basis':'90 unique cleaned texts; uniformly sampled after excluding previous 400 and earlier rule-review records',
             'caveat':'Same-base AI contexts; not independent human review, correctness, accuracy, or a post-weighted population estimate. For per-label comparisons, unspecified means no explicit label, not that a semantic topic is truly absent; explicitly uncertain and nonreadable cases are excluded.',
             'state_agreement':{},'positive_label_set_agreement':{},'strict_agreement':{},'per_label':[]}
    for f in ['observation_state','domain_state']:
        summary['state_agreement'][f]=sum(a[f]==b[f] for a,b in pairs)
    for axis,field,unknown in [('content','content_labels','uncertain_content'),('expression','expression_labels','uncertain_expression')]:
        summary['positive_label_set_agreement'][axis]=sum(set(a[field])==set(b[field]) for a,b in pairs)
        summary['strict_agreement'][axis]=sum(
            a['observation_state']==b['observation_state'] and
            (axis!='content' or a['domain_state']==b['domain_state']) and
            set(a[field])==set(b[field]) and set(a[unknown])==set(b[unknown])
            for a,b in pairs)
        for code,label in schema[field].items():
            count=Counter()
            for a,b in pairs:
                if (a['observation_state']!='readable' or b['observation_state']!='readable'
                    or code in a[unknown] or code in b[unknown]):
                    count['excluded']+=1;continue
                av=code in a[field];bv=code in b[field]
                count['both' if av and bv else 'first_only' if av else 'second_only' if bv else 'neither']+=1
            n=count['both']*2+count['first_only']+count['second_only']
            summary['per_label'].append({'axis':axis,'code':code,'label':label,
                'both_positive':count['both'],'first_only':count['first_only'],
                'second_only':count['second_only'],'both_negative':count['neither'],
                'excluded':count['excluded'],'positive_agreement':2*count['both']/n if n else None,
                'low_support':count['both']+count['first_only']+count['second_only']<5})
    OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k!='per_label'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
