#!/usr/bin/env python3
"""Validate and summarize two blind v3 AI codings, never produce accuracy claims.

Expected private results: coder_{a,b}_part_{01..04}.jsonl, matching the
corresponding frozen blind inputs. Public output contains aggregate counts only.
"""
from pathlib import Path
from collections import Counter
import hashlib
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT/'validation/classification_rebuild/private/v3_independent_validation'
OUT = ROOT/'results/v3_independent_ai_agreement.json'
spec = importlib.util.spec_from_file_location('v3_pipeline',ROOT/'code/v3_incremental_pipeline.py')
pipe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipe)
spec2 = importlib.util.spec_from_file_location('v3_prepare',ROOT/'code/prepare_v3_independent_review.py')
prepare = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(prepare)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def labels(row,code):
    if row['observation_state'] != 'readable':return None
    if code in row['positive_labels']:return 1
    if code in row['uncertain_labels']:return None
    return 0


def check_target(row,schema):
    """Enforce target missingness even if the shared validator is older."""
    if 'exhortation_target' not in row:
        raise ValueError('exhortation_target missing')
    target=row['exhortation_target']
    allowed=set(schema['exhortation_target_values'])
    if target not in allowed:
        raise ValueError('invalid exhortation target')
    yes='V3_EXHORT' in row['positive_labels']
    uncertain='V3_EXHORT' in row['uncertain_labels']
    if row['observation_state'] == 'insufficient' or uncertain:
        expected={'uncertain'}
    elif yes:
        expected={'self','others','both','unspecified','uncertain'}
    else:
        expected={'not_applicable'}
    if target not in expected:
        raise ValueError('exhortation target conflicts with observation and label')


def main():
    frozen=prepare.verify_freeze()
    meta=json.loads((PRIVATE/'sample_metadata.json').read_text())
    schema=json.loads((PRIVATE/'frozen_schema.json').read_text())
    if meta['frozen_codebook_sha256'] != frozen['frozen_codebook_sha256']:
        raise ValueError('codebook hash mismatch')
    if sha(PRIVATE/'private_key.csv') != meta['private_key_sha256']:
        raise ValueError('private key changed after sample release')
    all_coder={}
    source_all={}
    for coder in ('a','b'):
        answers={}
        sources={}
        for part in range(1,5):
            name=f'blind_{coder}_part_{part:02d}.jsonl'
            path=PRIVATE/name
            if name not in meta['blind_partition_sha256']:
                continue
            if sha(path)!=meta['blind_partition_sha256'][name]:
                raise ValueError('blind partition changed: '+name)
            blind=pipe.read_jsonl(path)
            data={x['sample_id']:x['text'] for x in blind}
            if len(data)!=len(blind) or set(data)&set(sources):
                raise ValueError('duplicate input IDs')
            output=PRIVATE/f'coder_{coder}_part_{part:02d}.jsonl'
            rows=pipe.read_jsonl(output)
            ids=[r.get('sample_id') for r in rows]
            if len(ids)!=len(set(ids)) or set(ids)!=set(data):
                raise ValueError('coder ID coverage mismatch: '+output.name)
            for row in rows:
                pipe.check_row(row,data[row['sample_id']],schema)
                check_target(row,schema)
                answers[row['sample_id']]=row
            sources.update(data)
        if len(answers)!=meta['n_sampled_unique_texts']:
            raise ValueError('incomplete coder '+coder)
        all_coder[coder]=answers
        source_all[coder]=sources
    if source_all['a'] != source_all['b']:
        raise ValueError('A and B did not review identical texts')
    ids=sorted(all_coder['a'])
    if set(ids)!=set(all_coder['b']):
        raise ValueError('A and B review IDs differ')
    a,b=all_coder['a'],all_coder['b']
    result={
        'status':'same_base_AI_agreement_not_human_accuracy',
        'n_unique_texts':len(ids),
        'sampling_unit':meta['sampling_unit'],
        'n_eligible_unique_texts':meta['n_eligible_unique_texts'],
        'inclusion_probability':meta['per_unique_text_inclusion_probability'],
        'n_represented_original_posts':meta['n_represented_posts'],
        'codebook_sha256':meta['frozen_codebook_sha256'],
        'observation_state_exact_agreement':sum(a[i]['observation_state']==b[i]['observation_state'] for i in ids),
        'positive_label_set_exact_agreement':sum(set(a[i]['positive_labels'])==set(b[i]['positive_labels']) for i in ids),
        'strict_exact_agreement_including_state_and_unknown':sum(
            a[i]['observation_state']==b[i]['observation_state'] and
            set(a[i]['positive_labels'])==set(b[i]['positive_labels']) and
            set(a[i]['uncertain_labels'])==set(b[i]['uncertain_labels']) for i in ids),
        'variables':[],
        'warnings':['Two AI contexts are not human reviewers and may share errors.',
                    'Unique-text sample excludes prior design packets; all texts were previously seen in v2 model coding.',
                    'The sample is not post-weighted or author-isolated; small positive support makes estimates unstable.',
                    'Unclear, insufficient and explicit unknowns are excluded from pairwise measures, not coded as negatives.'],
    }
    for code,label in schema['labels'].items():
        count=Counter()
        for sid in ids:
            av,bv=labels(a[sid],code),labels(b[sid],code)
            count['a_positive' if av==1 else 'a_negative' if av==0 else 'a_unknown']+=1
            count['b_positive' if bv==1 else 'b_negative' if bv==0 else 'b_unknown']+=1
            if av is None or bv is None:
                count['excluded_unknown']+=1
            elif av and bv:count['both_positive']+=1
            elif av:count['a_positive_only']+=1
            elif bv:count['b_positive_only']+=1
            else:count['both_negative']+=1
        tp,fn,fp,tn=(count[x] for x in ('both_positive','a_positive_only','b_positive_only','both_negative'))
        comparable=tp+fn+fp+tn; pdenom=2*tp+fn+fp
        result['variables'].append({'code':code,'label':label,
            'n_total':len(ids),'n_pairwise_comparable':comparable,
            'n_excluded_unknown':count['excluded_unknown'],
            'coder_a_positive':count['a_positive'],'coder_a_negative':count['a_negative'],'coder_a_unknown':count['a_unknown'],
            'coder_b_positive':count['b_positive'],'coder_b_negative':count['b_negative'],'coder_b_unknown':count['b_unknown'],
            'both_positive':tp,'a_positive_only':fn,'b_positive_only':fp,'both_negative':tn,
            'overall_agreement':(tp+tn)/comparable if comparable else None,
            'positive_agreement':2*tp/pdenom if pdenom else None,
            'positive_union_support':tp+fn+fp,
            'low_positive_support':tp+fn+fp<10})
    target_rows=[]
    for sid in ids:
        if labels(a[sid],'V3_EXHORT')==1 and labels(b[sid],'V3_EXHORT')==1:
            target_rows.append((a[sid]['exhortation_target'],b[sid]['exhortation_target']))
    result['exhortation_target']={'both_coders_identified_exhort':len(target_rows),
        'target_exact_agreement':sum(x==y for x,y in target_rows),
        'note':'Target agreement is conditional on both coders identifying exhortation; unspecified/uncertain are retained.'}
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='variables'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('ERROR:',exc,file=sys.stderr);raise SystemExit(2)
