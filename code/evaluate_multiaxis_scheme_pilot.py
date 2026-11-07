#!/usr/bin/env python3
"""Validate frozen blind annotations and compare scheme pilots, without likes.

Agreement is reported as same-base model consistency, never accuracy. The
random and targeted partitions are never pooled as population coverage.
"""
from pathlib import Path
from collections import Counter
import csv, hashlib, json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'multiaxis_v4_pilot'
OUT=ROOT/'results/multiaxis_v4_pilot_evaluation.json'
TOPICS=['T_ACTIVITY','T_BODY','T_FOOD','T_LIFE','T_TOOLS','T_OTHER']
EXPRESSIONS=['S_PRESENT','S_EXPERIENCE','S_APPRAISAL','S_FUTURE','S_EXHORT','S_REFLECTION','S_GUIDANCE','S_SOCIAL','S_REQUEST','S_OFFER','S_OTHER']
FIELDS={'sample_id','topic_positive','topic_uncertain','expression_positive','expression_uncertain','evidence',
        'event_assertion','plan','goal','greeting','thanks','other_topic','other_expression','all_labels_reviewed'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def val(r,c):
    prefix='topic' if c in TOPICS else 'expression'
    return 1 if c in r[prefix+'_positive'] else None if c in r[prefix+'_uncertain'] else 0

def validate(path,texts):
    rows=jl(path)
    if len(rows)!=len(texts) or len({r.get('sample_id') for r in rows})!=len(rows) or {r['sample_id'] for r in rows}!=set(texts):
        raise ValueError(path.name+': ID/row mismatch')
    for r in rows:
        sid=r['sample_id']
        if set(r)!=FIELDS or r['all_labels_reviewed'] is not True:raise ValueError(sid+': fields/review flag')
        positive=[]
        for prefix,codes in [('topic',TOPICS),('expression',EXPRESSIONS)]:
            p,u=r[prefix+'_positive'],r[prefix+'_uncertain']
            if any(not isinstance(x,list) or len(x)!=len(set(x)) or set(x)-set(codes) for x in (p,u)) or set(p)&set(u):
                raise ValueError(sid+': invalid/disjoint label lists')
            positive+=p
            if prefix=='topic' and 'T_OTHER' in p and not r['other_topic'].strip():raise ValueError(sid+': missing other topic')
            if prefix=='expression' and 'S_OTHER' in p and not r['other_expression'].strip():raise ValueError(sid+': missing other expression')
        if set(r['evidence'])!=set(positive):raise ValueError(sid+': missing/extra evidence')
        for c,quote in r['evidence'].items():
            if not isinstance(quote,str) or not quote.strip() or quote not in texts[sid]:raise ValueError(sid+': nonverbatim evidence '+c)
        attributes={'event_assertion':('S_PRESENT',{'asserted','not_asserted','uncertain','not_applicable'}),
          'plan':('S_FUTURE',{'yes','no','uncertain','not_applicable'}),'goal':('S_FUTURE',{'yes','no','uncertain','not_applicable'}),
          'greeting':('S_SOCIAL',{'yes','no','uncertain','not_applicable'}),'thanks':('S_SOCIAL',{'yes','no','uncertain','not_applicable'})}
        for field,(parent,allowed) in attributes.items():
            x=r[field];pv=val(r,parent)
            if x not in allowed or (pv==1 and x=='not_applicable') or (pv==0 and x!='not_applicable') or (pv is None and x!='uncertain'):
                raise ValueError(sid+': invalid parent/attribute '+field)
    return {r['sample_id']:r for r in rows}

def coverage(rows):
    res={'n':len(rows)}
    for name,codes in [('named_expression',EXPRESSIONS[:-1]),('named_topic',TOPICS[:-1]),('both_axes_named',EXPRESSIONS[:-1]+TOPICS[:-1])]:
        npos=[sum(val(r,c)==1 for c in codes) for r in rows]
        res[name]={'at_least_one_positive':sum(n>0 for n in npos),'at_least_two_positive':sum(n>1 for n in npos),
          'positive_rate':sum(n>0 for n in npos)/len(rows),'all_variables_known':sum(all(val(r,c) is not None for c in codes) for r in rows),
          'no_positive_some_unknown':sum(n==0 and any(val(r,c) is None for c in codes) for n,r in zip(npos,rows))}
    res['other_only_expressions']=sum(bool(r['expression_positive']) and set(r['expression_positive'])=={'S_OTHER'} for r in rows)
    res['variables']={c:dict(Counter('positive' if val(r,c)==1 else 'negative' if val(r,c)==0 else 'unknown' for r in rows)) for c in TOPICS+EXPRESSIONS}
    res['attributes_on_parent_positive']={f:dict(Counter(r[f] for r in rows if val(r,p)==1)) for f,p in
      [('event_assertion','S_PRESENT'),('plan','S_FUTURE'),('goal','S_FUTURE'),('greeting','S_SOCIAL'),('thanks','S_SOCIAL')]}
    return res

def agreement(a,b):
    n=len(a);out={'n':n,'per_label':{}}
    for prefix in ('topic','expression'):
        out[prefix+'_positive_set_exact']=sum(set(x[prefix+'_positive'])==set(y[prefix+'_positive']) for x,y in zip(a,b))
        out[prefix+'_strict_positive_and_unknown_set_exact']=sum(set(x[prefix+'_positive'])==set(y[prefix+'_positive']) and set(x[prefix+'_uncertain'])==set(y[prefix+'_uncertain']) for x,y in zip(a,b))
    for c in TOPICS+EXPRESSIONS:
        xy=[(val(x,c),val(y,c)) for x,y in zip(a,b)]
        tp=sum(x==y==1 for x,y in xy);fp=sum(x==1 and y==0 for x,y in xy);fn=sum(x==0 and y==1 for x,y in xy);tn=sum(x==y==0 for x,y in xy)
        valid=tp+fp+fn+tn;denom=2*tp+fp+fn
        out['per_label'][c]={'both_positive':tp,'a_only_positive_among_known':fp,'b_only_positive_among_known':fn,'both_negative':tn,
          'one_or_both_unknown':n-valid,'three_state_exact':sum(x==y for x,y in xy),
          'positive_agreement_known_only':2*tp/denom if denom else None,'low_positive_support':tp+fp+fn<5}
    out['at_least_one_same_named_expression_positive']=sum(any(val(x,c)==val(y,c)==1 for c in EXPRESSIONS[:-1]) for x,y in zip(a,b))
    out['at_least_one_same_named_topic_or_expression_positive']=sum(any(val(x,c)==val(y,c)==1 for c in TOPICS[:-1]+EXPRESSIONS[:-1]) for x,y in zip(a,b))
    out['attributes_on_both_parent_positive']={}
    for field,parent in [('event_assertion','S_PRESENT'),('plan','S_FUTURE'),('goal','S_FUTURE'),('greeting','S_SOCIAL'),('thanks','S_SOCIAL')]:
        xy=[(x[field],y[field]) for x,y in zip(a,b) if val(x,parent)==val(y,parent)==1]
        out['attributes_on_both_parent_positive'][field]={'n':len(xy),'exact':sum(x==y for x,y in xy),
          'either_uncertain':sum('uncertain' in (x,y) for x,y in xy)}
    return out

def main():
    meta=js(RUN/'sample_metadata.json');freeze=js(RUN/'freeze.json')
    if sha(RUN/'frozen_codebook.md')!=freeze['codebook_sha256'] or sha(RUN/'private_key.csv')!=meta['private_key_sha256']:
        raise ValueError('Frozen rules/key modified')
    if sha(PRIVATE/'variable_scheme_exploration/design_sample.jsonl')!=freeze['design_sample_sha256']:
        raise ValueError('Design sample changed')
    for who in ('a','b'):
        if sha(RUN/f'blind_{who}.jsonl')!=meta['blind_sha256']:raise ValueError('Blind inputs modified')
    texts={r['sample_id']:r['text'] for r in jl(RUN/'blind_a.jsonl')}
    a=validate(RUN/'coder_a.jsonl',texts);b=validate(RUN/'coder_b.jsonl',texts);keys=csvs(RUN/'private_key.csv')
    v2={r['sample_id']:r for r in jl(PRIVATE/'v2_direct_batches/merged_unique.jsonl')}
    v3={r['sample_id']:r for r in jl(PRIVATE/'v3_refined_batches/merged_unique.jsonl')}
    out={'status':'same_base_AI_pilot_not_human_accuracy_not_full_corpus_classification','outcome_used':False,
      'sample_metadata':meta,'partitions':{},'source_hashes':{p.name:sha(p) for p in [RUN/'coder_a.jsonl',RUN/'coder_b.jsonl',OUT.parent/'variable_scheme_independent_audit.json']},
      'limitations':['Unique-text random sample is from the design-excluded pool, not a post-weighted sample of all 5414 posts.',
        'Targeted no-v3-positive sample must not be pooled to estimate overall coverage.',
        'Same-base contexts share model biases; consistency and higher tagging coverage do not establish accuracy.',
        'Earlier AI coding has seen these texts; this is only separate from documented development/review packets.',
        'No full-corpus v4 relabeling or new likes regressions have been performed.']}
    for part in ('random','targeted_no_v3_positive'):
        k=[r for r in keys if r['partition']==part];aa=[a[r['sample_id']] for r in k];bb=[b[r['sample_id']] for r in k]
        old2=[bool(set(v2[r['source_id']]['expression_labels'])-{'F_OTHER'}) for r in k]
        old3=[bool(v3[r['source_id']]['positive_labels']) for r in k]
        comparable={'n':len(k),'v2_named_expression_positive':sum(old2),'v3_nine_expression_positive':sum(old3)}
        for who,rows in [('a',aa),('b',bb)]:
            positive=[bool(set(r['expression_positive'])-{'S_OTHER'}) for r in rows]
            comparable[f'coder_{who}_gain_among_no_v3_positive']=sum(x and not y for x,y in zip(positive,old3))
            comparable[f'coder_{who}_loss_among_v3_positive']=sum(not x and y for x,y in zip(positive,old3))
        out['partitions'][part]={'coder_a':coverage(aa),'coder_b':coverage(bb),'agreement':agreement(aa,bb),'same_sample_historical_comparison':comparable}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'partitions':{p:{'n':r['coder_a']['n'],
      'a_expression_positive':r['coder_a']['named_expression']['at_least_one_positive'],
      'b_expression_positive':r['coder_b']['named_expression']['at_least_one_positive'],
      'historical':r['same_sample_historical_comparison'],'agreement':{k:v for k,v in r['agreement'].items() if k!='per_label'}} for p,r in out['partitions'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
