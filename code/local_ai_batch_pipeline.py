#!/usr/bin/env python3
"""Private, offline, inspectable direct-AI coding handoff for Keep post text.

prepare creates anonymized deduplicated input batches; it never invokes a model.
check validates completed batches; merge requires every batch, and maps results
back to the full input population. All text and record-level outputs are confined
to the git-ignored classification_rebuild/private directory. Model results are
unvalidated candidates, not a human gold standard. Never paste raw post content
into chat, commit it, or send it to an external service without authorization.
"""
from pathlib import Path
import argparse, csv, hashlib, json, random, shutil, sys
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
PRIVATE_ROOT=(ROOT/'validation/classification_rebuild/private').resolve()
SOURCE=PRIVATE_ROOT/'body_population.csv'
DEFAULT_SCHEMA=ROOT/'code/classification_schema_v2.json'
DEFAULT_RUN=PRIVATE_ROOT/'v2_direct_batches'


def digest(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def file_write(path,text):
 tmp=path.with_name(path.name+'.tmp')
 tmp.write_text(text,encoding='utf-8');tmp.replace(path)

def dump_json(path,obj):file_write(path,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def lines(path):
 rows=[]
 with path.open(encoding='utf-8') as f:
  for n,line in enumerate(f,1):
   if line.strip():
    try: rows.append(json.loads(line))
    except (json.JSONDecodeError,ValueError) as e:raise ValueError(f'{path.name} line {n}: invalid JSON') from e
 return rows

def private_path(p):
 p=Path(p).resolve()
 if p==PRIVATE_ROOT or not p.is_relative_to(PRIVATE_ROOT):raise ValueError('Run directory must be a child of the ignored private directory')
 return p

def prepare(path,schema_path,batch_size,seed):
 path=private_path(path);schema_path=Path(schema_path).resolve()
 if path.exists():raise ValueError('Run directory exists; use a new run directory to preserve frozen inputs')
 schema=json.loads(schema_path.read_text(encoding='utf-8'))
 for k in ('content_labels','expression_labels','observation_state','domain_state'):
  if k not in schema:raise ValueError(f'schema missing {k}')
 with SOURCE.open(encoding='utf-8-sig',newline='') as f: records=list(csv.DictReader(f))
 if not records or len({r['postId'] for r in records})!=len(records):raise ValueError('source post IDs missing or not unique')
 texts={}; states=Counter()
 for r in records:
  text=r['clean_text']; length=int(r['length']);has_text=int(r['has_text'])
  if length>0:
   if not text.strip():raise ValueError('source length>0 but cleaned text is blank')
   key=hashlib.sha256(text.encode('utf-8')).hexdigest()
   if key in texts and texts[key]!=text:raise ValueError('SHA256 collision')
   texts[key]=text;r['_key']=key;r['_status']='needs_model'
  else:
   if text.strip():raise ValueError('source length=0 but cleaned text is nonblank')
   r['_key']='';r['_status']='cleaned_empty' if has_text else 'raw_body_unavailable'
  states[r['_status']]+=1
 keys=sorted(texts);random.Random(seed).shuffle(keys)
 anon={k:f'P{i:06d}' for i,k in enumerate(keys,1)}
 (path/'inputs').mkdir(parents=True);(path/'outputs').mkdir()
 shutil.copyfile(schema_path,path/'frozen_schema.json')
 with (path/'id_map.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f);w.writerow(['postId','sample_id','input_status'])
  for r in records:w.writerow([r['postId'],anon.get(r['_key'],''),r['_status']])
 batches=[]
 for first in range(0,len(keys),batch_size):
  chosen=keys[first:first+batch_size];name=f'batch_{first//batch_size+1:04d}.jsonl';target=path/'inputs'/name
  file_write(target,''.join(json.dumps({'sample_id':anon[k],'text':texts[k]},ensure_ascii=False)+'\n' for k in chosen))
  batches.append({'name':name,'rows':len(chosen),'sha256':digest(target)})
 manifest={'purpose':'offline preparation only, no model invocation or validation claims',
  'schema_version':schema['schema_version'],'schema_sha256':digest(path/'frozen_schema.json'),
  'source_sha256':digest(SOURCE),'id_map_sha256':digest(path/'id_map.csv'),'seed':seed,'batch_size':batch_size,
  'total_posts':len(records),'source_states':dict(states),'nonempty_unique_texts':len(keys),'batch_count':len(batches),'batches':batches}
 dump_json(path/'manifest.json',manifest)
 print(json.dumps({k:v for k,v in manifest.items() if k!='batches'},ensure_ascii=False,indent=2))

def check_row(row,text,schema):
 required={'sample_id','observation_state','domain_state','content_labels','expression_labels','uncertain_content','uncertain_expression','evidence','other_note'}
 if not isinstance(row,dict) or not required.issubset(row):raise ValueError('missing required fields')
 if not isinstance(row['sample_id'],str):raise ValueError('invalid sample_id')
 obs=row['observation_state'];ds=row['domain_state']
 if obs not in schema['observation_state'] or ds not in schema['domain_state']:raise ValueError('invalid state')
 groups=[('content_labels','uncertain_content','content_labels'),('expression_labels','uncertain_expression','expression_labels')]
 positives=[]
 for positive,uncertain,codes in groups:
  p=row[positive];u=row[uncertain]
  if not isinstance(p,list) or not isinstance(u,list) or any(not isinstance(x,str) for x in p+u):raise ValueError('labels must be lists of strings')
  if len(p)!=len(set(p)) or len(u)!=len(set(u)):raise ValueError('duplicate labels')
  if (set(p)|set(u))-set(schema[codes]):raise ValueError('illegal label')
  if set(p)&set(u):raise ValueError('positive/uncertain overlap')
  positives.extend(p)
 if obs!='readable' and (positives or row['uncertain_content'] or row['uncertain_expression']):raise ValueError('nonreadable text cannot receive labels')
 if obs=='insufficient' and ds!='unavailable':raise ValueError('insufficient must use unavailable domain')
 if ds=='unavailable' and (obs!='insufficient' or row['content_labels'] or row['uncertain_content']):raise ValueError('unavailable must use insufficient observation and no content labels')
 if ds=='specified' and not row['content_labels']:raise ValueError('specified must contain content label')
 if ds=='unspecified' and (row['content_labels'] or row['uncertain_content']):raise ValueError('unspecified cannot have content labels or uncertain content')
 if ds=='uncertain' and not row['uncertain_content']:raise ValueError('uncertain needs uncertain content')
 evidence=row['evidence']
 if not isinstance(evidence,dict) or set(evidence)!=set(positives):raise ValueError('evidence keys must exactly match positive labels')
 for value in evidence.values():
  if not isinstance(value,str) or not value.strip() or value not in text:raise ValueError('evidence must be an exact nonempty substring')
 if not isinstance(row['other_note'],str) or not isinstance(row.get('note',''),str):raise ValueError('notes must be strings')
 if {'C_OTHER','F_OTHER'}&set(positives) and not row['other_note'].strip():raise ValueError('other requires explanation')
 return row

def verify_inputs(path):
 manifest=json.loads((path/'manifest.json').read_text());schema_path=path/'frozen_schema.json'
 if digest(schema_path)!=manifest['schema_sha256'] or digest(path/'id_map.csv')!=manifest['id_map_sha256']:raise ValueError('frozen schema or ID map changed')
 if manifest.get('codebook_file') and digest(path/manifest['codebook_file'])!=manifest.get('codebook_sha256'):raise ValueError('frozen codebook changed')
 if digest(SOURCE)!=manifest['source_sha256']:raise ValueError('source changed after preparation')
 return manifest,json.loads(schema_path.read_text())

def check_batch(path,batch,schema):
 input_path=path/'inputs'/batch['name'];output_path=path/'outputs'/batch['name']
 if digest(input_path)!=batch['sha256']:raise ValueError(f'{batch["name"]}: input changed')
 if not output_path.exists():raise ValueError(f'{batch["name"]}: output missing')
 input_rows=lines(input_path);out=lines(output_path)
 original={x['sample_id']:x['text'] for x in input_rows}
 if len(original)!=len(input_rows) or len(input_rows)!=batch['rows']:raise ValueError(f'{batch["name"]}: duplicate or unexpected inputs')
 ids=[x.get('sample_id') if isinstance(x,dict) else None for x in out]
 if len(ids)!=len(set(ids)) or set(ids)!=set(original):raise ValueError(f'{batch["name"]}: missing, unexpected, or duplicate output IDs')
 for i,r in enumerate(out,1):
  try:check_row(r,original[r['sample_id']],schema)
  except ValueError as e:raise ValueError(f'{batch["name"]} row {i}: {e}') from e
 return out

def check(path,batch_name=None,merge=False):
 path=private_path(path);manifest,schema=verify_inputs(path)
 chosen=[b for b in manifest['batches'] if not batch_name or b['name']==batch_name]
 if not chosen:raise ValueError('batch not found')
 allrows=[];errors=[]
 for batch in chosen:
  try:allrows.extend(check_batch(path,batch,schema))
  except (ValueError,OSError,KeyError,TypeError) as e:errors.append(str(e))
 if errors:
  print(json.dumps({'status':'incomplete_or_invalid','checked_batches':len(chosen),'valid_batches':len(chosen)-len(errors),'errors':errors},ensure_ascii=False,indent=2));return 1
 if not merge:
  print(json.dumps({'status':'valid','checked_batches':len(chosen),'rows':len(allrows)},ensure_ascii=False));return 0
 if batch_name:raise ValueError('merge requires all batches')
 if len(allrows)!=manifest['nonempty_unique_texts'] or len({r['sample_id'] for r in allrows})!=len(allrows):raise ValueError('duplicate or missing across batches')
 byid={r['sample_id']:r for r in allrows}
 with (path/'id_map.csv').open(encoding='utf-8',newline='') as f: mapping=list(csv.DictReader(f))
 if set(r['sample_id'] for r in mapping if r['sample_id'])!=set(byid):raise ValueError('ID mapping does not match annotations')
 file_write(path/'merged_unique.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in allrows))
 out=path/'post_labels.csv';tmp=out.with_name(out.name+'.tmp')
 fields=['postId','sample_id','input_status','observation_state','domain_state','content_labels','expression_labels','uncertain_content','uncertain_expression']
 with tmp.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in mapping:
   v=byid.get(r['sample_id'],{});o={k:r.get(k,'') for k in fields}
   for k in fields[3:]:
    val=v.get(k,'');o[k]=json.dumps(val,ensure_ascii=False) if isinstance(val,list) else val
   w.writerow(o)
 tmp.replace(out)
 states=Counter();contents=Counter();expressions=Counter()
 for r in mapping:
  if not r['sample_id']:continue
  v=byid[r['sample_id']];states[v['observation_state']]+=1;contents.update(v['content_labels']);expressions.update(v['expression_labels'])
 summary={'warning':'AI-generated labels only; do not treat as validated truth, causal effects, or error rates. Multi-label counts may overlap.','n_posts':len(mapping),'n_nonempty':sum(bool(r['sample_id']) for r in mapping),'n_unique_coded':len(byid),'post_weighted_observation_states':dict(states),'post_weighted_content_candidates':dict(contents),'post_weighted_expression_candidates':dict(expressions),'output_hashes':{name:digest(path/name) for name in ('merged_unique.jsonl','post_labels.csv')}}
 dump_json(path/'merge_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2));return 0

def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='cmd',required=True)
 p=sub.add_parser('prepare');p.add_argument('--run-dir',default=str(DEFAULT_RUN));p.add_argument('--schema',default=str(DEFAULT_SCHEMA));p.add_argument('--batch-size',type=int,default=50);p.add_argument('--seed',type=int,default=20261104)
 for cmd in ('check','merge'):
  p=sub.add_parser(cmd);p.add_argument('--run-dir',default=str(DEFAULT_RUN))
  if cmd=='check':p.add_argument('--batch')
 args=parser.parse_args()
 try:
  if args.cmd=='prepare':
   if args.batch_size<=0:raise ValueError('batch size must be positive')
   prepare(args.run_dir,args.schema,args.batch_size,args.seed);return 0
  return check(args.run_dir,getattr(args,'batch',None),args.cmd=='merge')
 except (ValueError,OSError,KeyError,TypeError) as e:print('ERROR:',e,file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
