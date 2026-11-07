#!/usr/bin/env python3
"""Audit frozen v5 annotations and outcome-blind pilot diagnostics.

No likes, outcomes or old labels are visible to either coder. The evaluator uses
old labels only for within-sample retrospective coverage comparisons.
"""
from pathlib import Path
from collections import Counter
import csv, hashlib, importlib.util, json
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5'
OUT=ROOT/'results/variable_scheme_v5_evaluation.json'
TOPICS=['T_ACTIVITY','T_BODY','T_FOOD','T_LIFE','T_TOOLS','T_OTHER']
EXPRESSIONS=['S_PRESENT','S_EXPERIENCE','S_APPRAISAL','S_FUTURE','S_EXHORT','S_REFLECTION','S_GUIDANCE','S_SOCIAL','S_REQUEST','S_OFFER','S_OTHER']
ATTRS=['event_assertion','plan','goal','greeting','thanks','positive_tone','negative_tone']
FIELDS={'sample_id','topic_positive','topic_uncertain','expression_positive','expression_uncertain','evidence',
        *ATTRS,'other_topic','other_expression','all_labels_reviewed'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def js(p): return json.loads(Path(p).read_text())
def jl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))
def val(r,c):
    prefix='topic' if c in TOPICS else 'expression'
    return 1 if c in r[prefix+'_positive'] else None if c in r[prefix+'_uncertain'] else 0
def parent_state(r,field):
    if field=='event_assertion': return val(r,'S_PRESENT')
    if field in ('plan','goal'): return val(r,'S_FUTURE')
    if field in ('greeting','thanks'): return val(r,'S_SOCIAL')
    states=[val(r,c) for c in ('S_EXPERIENCE','S_APPRAISAL')]
    return 1 if 1 in states else None if None in states else 0

def validate(path,texts):
    rows=jl(path)
    if len(rows)!=len(texts) or len({r.get('sample_id') for r in rows})!=len(rows) or {r['sample_id'] for r in rows}!=set(texts):
        raise ValueError(path.name+': row/ID mismatch')
    for r in rows:
        sid=r['sample_id']
        if set(r)!=FIELDS or r['all_labels_reviewed'] is not True: raise ValueError(sid+': fields/review flag')
        positives=[]
        for prefix,codes in [('topic',TOPICS),('expression',EXPRESSIONS)]:
            p,u=r[prefix+'_positive'],r[prefix+'_uncertain']
            if any(not isinstance(x,list) or len(x)!=len(set(x)) or set(x)-set(codes) for x in (p,u)) or set(p)&set(u):
                raise ValueError(sid+': invalid/disjoint label sets')
            positives+=p
            other='T_OTHER' if prefix=='topic' else 'S_OTHER'
            explanation=r['other_topic' if prefix=='topic' else 'other_expression']
            if not isinstance(explanation,str) or (other in p and not explanation.strip()): raise ValueError(sid+': other explanation')
        for field in ATTRS:
            allowed={'asserted','not_asserted','uncertain','not_applicable'} if field=='event_assertion' else {'yes','no','uncertain','not_applicable'}
            x=r[field];pv=parent_state(r,field)
            if x not in allowed or (pv==1 and x=='not_applicable') or (pv==0 and x!='not_applicable') or (pv is None and x!='uncertain'):
                raise ValueError(sid+': parent/attribute violation '+field)
        for field,code in [('positive_tone','A_POSITIVE_TONE'),('negative_tone','A_NEGATIVE_TONE')]:
            if r[field]=='yes': positives.append(code)
        if not isinstance(r['evidence'],dict) or set(r['evidence'])!=set(positives): raise ValueError(sid+': evidence keys')
        for code,quote in r['evidence'].items():
            if not isinstance(quote,str) or not quote.strip() or quote not in texts[sid]: raise ValueError(sid+': nonverbatim evidence '+code)
    return {r['sample_id']:r for r in rows}

def coverage(rows):
    out={'n':len(rows),'axes':{}}
    for axis,codes in [('expression',EXPRESSIONS[:-1]),('topic',TOPICS[:-1]),('either',EXPRESSIONS[:-1]+TOPICS[:-1])]:
        out['axes'][axis]={'any_positive':sum(any(val(r,c)==1 for c in codes) for r in rows),
          'two_or_more_positive':sum(sum(val(r,c)==1 for c in codes)>=2 for r in rows),
          'all_known':sum(all(val(r,c) is not None for c in codes) for r in rows),
          'all_negative':sum(all(val(r,c)==0 for c in codes) for r in rows),
          'no_positive_some_unknown':sum(not any(val(r,c)==1 for c in codes) and any(val(r,c) is None for c in codes) for r in rows)}
    out['variables']={c:dict(Counter('positive' if val(r,c)==1 else 'negative' if val(r,c)==0 else 'unknown' for r in rows)) for c in TOPICS+EXPRESSIONS}
    out['attributes_given_parent_positive']={field:dict(Counter(r[field] for r in rows if parent_state(r,field)==1)) for field in ATTRS}
    subjects=[r for r in rows if parent_state(r,'positive_tone')==1]
    tone_complete=[r for r in subjects if all(r[f] in ('yes','no') for f in ('positive_tone','negative_tone'))]
    out['polarity']={'parent_positive':len(subjects),'both_attributes_known':len(tone_complete),
      'combination_counts':dict(Counter(('positive' if r['positive_tone']=='yes' else 'no_positive')+'_'+('negative' if r['negative_tone']=='yes' else 'no_negative') for r in tone_complete)),
      'parent_not_applicable':sum(parent_state(r,'positive_tone')==0 for r in rows),'parent_unknown':sum(parent_state(r,'positive_tone') is None for r in rows)}
    out['all_dimensions_and_attributes_complete']=sum(all(val(r,c) is not None for c in TOPICS[:-1]+EXPRESSIONS[:-1]) and all(r[f]!='uncertain' for f in ATTRS) for r in rows)
    return out

def agreement(a,b,screen):
    n=len(a);out={'n':n,'per_label':{},'attributes':{}}
    for prefix in ('topic','expression'):
        out[prefix+'_positive_set_exact']=sum(set(x[prefix+'_positive'])==set(y[prefix+'_positive']) for x,y in zip(a,b))
        out[prefix+'_positive_and_unknown_set_exact']=sum(set(x[prefix+'_positive'])==set(y[prefix+'_positive']) and set(x[prefix+'_uncertain'])==set(y[prefix+'_uncertain']) for x,y in zip(a,b))
    for c in TOPICS+EXPRESSIONS:
        pairs=[(val(x,c),val(y,c)) for x,y in zip(a,b)]
        tp=sum(x==y==1 for x,y in pairs);fp=sum(x==1 and y==0 for x,y in pairs);fn=sum(x==0 and y==1 for x,y in pairs);tn=sum(x==y==0 for x,y in pairs)
        unknown=sum(x is None or y is None for x,y in pairs);pos_union=tp+fp+fn
        pa=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
        exact=sum(x==y for x,y in pairs)
        ak=sum(x is not None for x,y in pairs);bk=sum(y is not None for x,y in pairs)
        if pos_union<screen['min_comparable_positive_union']: state='insufficient_positive_support'
        elif pa>=screen['min_positive_agreement_known_only'] and min(ak,bk)/n>=screen['min_known_fraction_each_coder'] and exact/n>=screen['min_three_state_exact_fraction']: state='passes_predeclared_consistency_screen_not_accuracy'
        else: state='needs_boundary_review'
        out['per_label'][c]={'both_positive':tp,'a_only_positive_known':fp,'b_only_positive_known':fn,'both_negative':tn,
          'either_unknown':unknown,'comparable_positive_union':pos_union,'positive_agreement_known_only':pa,'three_state_exact':exact,
          'a_known':ak,'b_known':bk,'screen_state_if_random_partition':state}
    for name,codes in [('expression',EXPRESSIONS[:-1]),('either',TOPICS[:-1]+EXPRESSIONS[:-1])]:
        out['at_least_one_same_named_'+name]=sum(any(val(x,c)==val(y,c)==1 for c in codes) for x,y in zip(a,b))
    for field in ATTRS:
        eligible=[(x,y) for x,y in zip(a,b) if parent_state(x,field)==parent_state(y,field)==1]
        pairs=[(x[field],y[field]) for x,y in eligible];known=[(x,y) for x,y in pairs if 'uncertain' not in (x,y)]
        d={'both_parent_positive':len(pairs),'either_uncertain':sum('uncertain' in (x,y) for x,y in pairs),
          'exact_including_unknown':sum(x==y for x,y in pairs),'both_known':len(known),'exact_known':sum(x==y for x,y in known)}
        if field!='event_assertion':
            tp=sum(x==y=='yes' for x,y in known);fp=sum(x=='yes' and y=='no' for x,y in known);fn=sum(x=='no' and y=='yes' for x,y in known)
            d.update(both_yes=tp,a_only_yes=fp,b_only_yes=fn,comparable_positive_union=tp+fp+fn,
              positive_agreement_known_only=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
        out['attributes'][field]=d
    eligible=[(x,y) for x,y in zip(a,b) if parent_state(x,'positive_tone')==parent_state(y,'positive_tone')==1]
    bothknown=[(x,y) for x,y in eligible if all(z[f] in ('yes','no') for z in (x,y) for f in ('positive_tone','negative_tone'))]
    out['joint_polarity']={'both_parent_positive':len(eligible),'both_coders_both_attributes_known':len(bothknown),
      'exact_combination_on_known':sum(all(x[f]==y[f] for f in ('positive_tone','negative_tone')) for x,y in bothknown),
      'parent_set_disagreement':sum(parent_state(x,'positive_tone')!=parent_state(y,'positive_tone') for x,y in zip(a,b))}
    return out

def numeric_diagnostics(rows):
    # A small, unique-text pilot cannot supply population fixed-effect VIF.
    # This transparent diagnostic uses only expression parents with >=10
    # positives and >=10 negatives on their own observed rows.
    codes=[c for c in EXPRESSIONS[:-1] if sum(val(r,c)==1 for r in rows)>=10 and sum(val(r,c)==0 for r in rows)>=10]
    complete=[r for r in rows if all(val(r,c) is not None for c in codes)]
    out={'scope':'Random unique-text pilot, expression indicators only. No controls, author/date fixed effects or outcomes; not full-corpus VIF.',
      'support_rule':'At least 10 positive and 10 negative known unique texts per candidate before listwise deletion, used only as a pilot design diagnostic.',
      'codes':codes,'n_complete':len(complete),'full_corpus_regression_support_tested':False}
    if len(codes)<2 or not complete: return {**out,'status':'insufficient'}
    values=np.array([[val(r,c) for c in codes] for r in complete],dtype=float)
    if np.any(values.std(axis=0)==0): return {**out,'status':'constant_in_complete_sample'}
    corr=np.corrcoef(values,rowvar=False);pairs=[]
    for i,a in enumerate(codes):
        for j in range(i+1,len(codes)): pairs.append({'first':a,'second':codes[j],'phi':float(corr[i,j]),'both_positive':int(np.sum((values[:,i]==1)&(values[:,j]==1)))})
    design=np.column_stack([np.ones(len(values)),values]);rank=int(np.linalg.matrix_rank(design))
    out.update(rank=rank,columns=design.shape[1],top_absolute_phi_pairs=sorted(pairs,key=lambda p:abs(p['phi']),reverse=True)[:6])
    if rank!=design.shape[1]: return {**out,'status':'rank_deficient'}
    vif={};direct={}
    inverse=np.linalg.inv(corr)
    for j,c in enumerate(codes):
        y=values[:,j];others=np.delete(design,j+1,axis=1);residual=y-others@np.linalg.lstsq(others,y,rcond=None)[0]
        direct[c]=float(np.sum((y-y.mean())**2)/np.sum(residual**2));vif[c]=float(inverse[j,j])
        if not np.isclose(vif[c],direct[c],atol=1e-9): raise ValueError('VIF cross-check failed')
    out.update(status='full_rank_pilot_expression_only',vif=vif,vif_residual_crosscheck=direct,min_vif=min(vif.values()),max_vif=max(vif.values()))
    return out

def main():
    meta=js(RUN/'sample_metadata.json');freeze=js(RUN/'freeze.json');protocol=js(RUN/'frozen_protocol.json')
    for p,key in [(RUN/'frozen_codebook.md','codebook_sha256'),(RUN/'frozen_protocol.json','protocol_sha256')]:
        if sha(p)!=freeze[key]: raise ValueError('Frozen rule/protocol modified')
    if sha(ROOT/'正文多维测量方案_v5_编码手册.md')!=freeze['codebook_sha256'] or sha(ROOT/'code/variable_scheme_v5_protocol.json')!=freeze['protocol_sha256']:
        raise ValueError('Public rule/protocol differs from frozen tested version')
    for p,h in freeze['source_sha256'].items():
        if sha(ROOT/p)!=h: raise ValueError('Frozen source modified: '+p)
    if sha(RUN/'private_key.csv')!=meta['private_key_sha256']: raise ValueError('Key modified')
    for who in ('a','b'):
        if sha(RUN/f'blind_{who}.jsonl')!=meta['blind_sha256']: raise ValueError('Blind input modified')
    keys=csvs(RUN/'private_key.csv');texts={r['sample_id']:r['text'] for r in jl(RUN/'blind_a.jsonl')}
    if len(keys)!=260 or len({r['source_id'] for r in keys})!=260: raise ValueError('Keys not unique')
    excluded=set(js(RUN/'excluded_ids.json'))
    if hashlib.sha256('\n'.join(sorted(excluded)).encode()).hexdigest()!=freeze['excluded_ids_sha256'] or excluded&{r['source_id'] for r in keys}:
        raise ValueError('Exclusion integrity failed')
    source={r['sample_id']:r['text'] for p in sorted((PRIVATE/'v2_direct_batches/inputs').glob('*.jsonl')) for r in jl(p)}
    if any(texts[r['sample_id']]!=source[r['source_id']] for r in keys): raise ValueError('Blind source mismatch')
    a=validate(RUN/'coder_a.jsonl',texts);b=validate(RUN/'coder_b.jsonl',texts)
    v2={r['sample_id']:r for r in jl(PRIVATE/'v2_direct_batches/merged_unique.jsonl')}
    v3={r['sample_id']:r for r in jl(PRIVATE/'v3_refined_batches/merged_unique.jsonl')}
    out={'status':'frozen_multi_axis_scheme_pilot_not_full_corpus_reclassification','outcome_used':False,
      'sample_metadata':meta,'freeze':{k:v for k,v in freeze.items() if k!='source_sha256'},'partitions':{},
      'coder_output_sha256':{who:sha(RUN/f'coder_{who}.jsonl') for who in ('a','b')},
      'limits':['Same-base AI contexts can share mistakes; consistency is not human accuracy.',
        'The random sample is from a design-excluded unique-text population, not all posts or unseen authors.',
        'Do not pool targeted and random samples or extrapolate their positive rates to all 5414 posts.',
        'v4/v5 use different validation samples; raw agreement differences are not causal estimates of improvement.',
        'No new full-corpus semantic labels, population full-design VIF or likes regressions are claimed.']}
    for part in ('random','targeted_no_v3_positive'):
        k=[r for r in keys if r['partition']==part];aa=[a[r['sample_id']] for r in k];bb=[b[r['sample_id']] for r in k]
        old2=[bool(set(v2[r['source_id']]['expression_labels'])-{'F_OTHER'}) for r in k]
        old3=[bool(v3[r['source_id']]['positive_labels']) for r in k]
        if part=='targeted_no_v3_positive' and any(old3): raise ValueError('Targeted partition inconsistent')
        historical={'n':len(k),'v2_named_expression_positive':sum(old2),'v3_nine_positive':sum(old3)}
        for who,rows in [('a',aa),('b',bb)]:
            new=[any(val(r,c)==1 for c in EXPRESSIONS[:-1]) for r in rows]
            historical[f'{who}_gain_from_v3_no_positive']=sum(x and not y for x,y in zip(new,old3))
            historical[f'{who}_loss_from_v3_positive']=sum(not x and y for x,y in zip(new,old3))
            historical[f'{who}_gain_from_v2_no_positive']=sum(x and not y for x,y in zip(new,old2))
            historical[f'{who}_loss_from_v2_positive']=sum(not x and y for x,y in zip(new,old2))
        part_result={'a':coverage(aa),'b':coverage(bb),'agreement':agreement(aa,bb,protocol['consistency_screen']),'historical_same_sample':historical}
        if part=='random': part_result['numerical_design']={who:numeric_diagnostics(rows) for who,rows in [('a',aa),('b',bb)]}
        else:
            for d in part_result['agreement']['per_label'].values(): d.pop('screen_state_if_random_partition')
        out['partitions'][part]=part_result
    screened=[c for c in EXPRESSIONS[:-1] if out['partitions']['random']['agreement']['per_label'][c]['screen_state_if_random_partition'].startswith('passes_')]
    out['measurement_decision']={'main_parent_candidates':screened,
      'descriptive_candidates_needing_more_positive_review':[c for c in EXPRESSIONS[:-1] if c not in screened],
      'status':'Consistency-screened measurement candidates, not final full-corpus regressors or human-validated categories.',
      'full_corpus_support_and_full_design_checks_still_required':True}
    for part in ('random','targeted_no_v3_positive'):
        k=[r for r in keys if r['partition']==part]
        out['partitions'][part]['main_candidate_availability']={who:{
          'n_all_candidate_parents_known':sum(all(val(coded[r['sample_id']],c) is not None for c in screened) for r in k),
          'n_any_candidate_positive':sum(any(val(coded[r['sample_id']],c)==1 for c in screened) for r in k),
          'scope':'Only the main parent candidates from the predeclared consistency screen. Known negatives remain eligible; no outcome model is fitted.'}
          for who,coded in [('a',a),('b',b)]}
    OUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(OUT),'partitions':{p:{'n':r['a']['n'],
      'a_expression_positive':r['a']['axes']['expression']['any_positive'],'b_expression_positive':r['b']['axes']['expression']['any_positive'],
      'same_expression_positive':r['agreement']['at_least_one_same_named_expression'],'history':r['historical_same_sample'],
      'polarity':r['agreement']['joint_polarity']} for p,r in out['partitions'].items()}},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
