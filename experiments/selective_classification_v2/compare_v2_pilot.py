#!/usr/bin/env python3
"""Audit 30-row direct-AI pilot against text, then compare two blind coders.

Historical holdout reused; two coders share a model base. Agreement is neither
human reliability nor accuracy. No text, row ID or evidence is exported.
"""
from collections import Counter
from pathlib import Path
import csv, importlib.util, json

ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'validation/classification_rebuild/private'
OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pipeline',ROOT/'code/local_ai_batch_pipeline.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
schema=json.loads((P/'v2_pilot/schema_v2.json').read_text())
blind=m.lines(P/'holdout_blind.jsonl')[:30]
a=m.lines(P/'v2_pilot/coder_a.jsonl');b=m.lines(P/'v2_pilot/coder_b.jsonl')
texts={x['sample_id']:x['text'] for x in blind}
def index(rows,name):
 d={r['sample_id']:r for r in rows}
 if len(rows)!=30 or len(d)!=30 or set(d)!=set(texts):raise ValueError(name+' has invalid ID coverage')
 errors=[]
 for i,r in d.items():
  try:m.check_row(r,texts[i],schema)
  except (ValueError,TypeError,KeyError) as e:errors.append({'id':i,'message':str(e)})
 return d,errors
A,ae=index(a,'A');B,be=index(b,'B')
# IDs are retained in private validation only, never in aggregate deliverable.
(P/'v2_pilot/validation_errors.json').write_text(json.dumps({'A':ae,'B':be},ensure_ascii=False,indent=2)+'\n')
if ae or be:
 print(json.dumps({'status':'invalid','A_errors':len(ae),'B_errors':len(be),'A_messages':dict(Counter(x['message'] for x in ae)),'B_messages':dict(Counter(x['message'] for x in be))},ensure_ascii=False,indent=2));raise SystemExit(1)
summary={'n':len(texts),'validation':'Both raters: schema, exact evidence substrings, complete and unique IDs valid','observation_exact':sum(A[i]['observation_state']==B[i]['observation_state'] for i in texts),'domain_state_exact':sum(A[i]['domain_state']==B[i]['domain_state'] for i in texts),'content_set_exact_all':sum(set(A[i]['content_labels'])==set(B[i]['content_labels']) for i in texts),'expression_set_exact_all':sum(set(A[i]['expression_labels'])==set(B[i]['expression_labels']) for i in texts),'both_readable':sum(A[i]['observation_state']==B[i]['observation_state']=='readable' for i in texts),'statuses':{x:{field:dict(Counter(d[i][field] for i in texts)) for field in ['observation_state','domain_state']} for x,d in [('A',A),('B',B)]},'warning':'Same-base model blind-coder agreement on 30 historical holdout posts, not independent human review or accuracy; holdout already exposed; no population representativeness assumed.'}
rows=[]
for axis,labels,poskey,unckey in [('content',schema['content_labels'],'content_labels','uncertain_content'),('expression',schema['expression_labels'],'expression_labels','uncertain_expression')]:
 for code,label in labels.items():
  # Exclude any unreadable text, content domain uncertain/unavailable, and per-code uncertainty.
  pairs=[]
  for i in texts:
   x,y=A[i],B[i]
   if x['observation_state']!='readable' or y['observation_state']!='readable':continue
   if axis=='content' and (x['domain_state'] not in ('specified','unspecified') or y['domain_state'] not in ('specified','unspecified')):continue
   if code in x[unckey] or code in y[unckey]:continue
   pairs.append((int(code in x[poskey]),int(code in y[poskey])))
  counts=Counter(pairs);p11=counts[(1,1)];p10=counts[(1,0)];p01=counts[(0,1)];p00=counts[(0,0)];den=2*p11+p10+p01
  rows.append({'axis':axis,'code':code,'label':label,'eligible':len(pairs),'a_yes':p11+p10,'b_yes':p11+p01,'both_yes':p11,'a_only':p10,'b_only':p01,'both_no':p00,'positive_agreement':2*p11/den if den else None,'flag_low_positive':min(p11+p10,p11+p01)<5})
(OUT/'v2_pilot_agreement.json').write_text(json.dumps({'summary':summary,'labels':rows},ensure_ascii=False,indent=2)+'\n')
with (OUT/'v2_pilot_agreement.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps(summary,ensure_ascii=False,indent=2))
for r in rows:print(r['code'],'n=',r['eligible'],'A/B=',r['a_yes'],r['b_yes'],'joint=',r['both_yes'],'positive_agreement=',r['positive_agreement'],'low=',r['flag_low_positive'])
