#!/usr/bin/env python3
"""Selective semantic-label pilot. Frozen historical split; AI reference, never human truth.

Training and threshold selection run before holdout is read. Predictions and
row-level inputs remain under the existing ignored private directory.
"""
from pathlib import Path
import csv, json, hashlib
from collections import Counter
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity

ROOT=Path(__file__).resolve().parents[2]
PRIVATE=ROOT/'validation/classification_rebuild/private'
OUT=Path(__file__).resolve().parent
SEED=20261029
MIN_DEV_POS=5; MIN_DEV_NEG=5; MIN_CAL_POS=3; MIN_CAL_PRED=3
MIN_CAL_PRECISION=.80; MIN_SIMILARITY=.20
THRESHOLDS=[.50,.60,.70,.80,.90,.95]

def jread(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def read_blind(name):
 rows=[json.loads(l) for l in (PRIVATE/name).read_text().splitlines() if l.strip()]
 d={r['sample_id']:r['text'] for r in rows};assert len(d)==len(rows);return d
def rows(blind, annotations, axis, code):
 ans=[]
 for r in annotations['records']:
  if r['observation_state']!='readable' or code in r['uncertain_'+axis]: continue
  if axis=='domains' and r['domain_state'] not in ('specified','unspecified'):continue
  ans.append((r['sample_id'],int(code in r[axis])))
 assert len({a for a,b in ans})==len(ans)
 return ans

def score(model, matrix, posmat):
 if not len(matrix.indptr)-1: return np.array([]),np.array([])
 probs=model.predict_proba(matrix)[:,1]
 sim=cosine_similarity(matrix,posmat).max(axis=1) if posmat.shape[0] else np.zeros(matrix.shape[0])
 return probs,sim

def metrics(n11,n10,n01,n00):
 return {'TP':n11,'FP':n10,'FN':n01,'TN':n00,
 'precision':n11/(n11+n10) if n11+n10 else None,
 'recall':n11/(n11+n01) if n11+n01 else None,
 'support':n11+n01,'predicted_positive':n11+n10}

def main():
 cb=jread(ROOT/'code/classification_codebook_v1.json')
 labels=[(axis,e['code'],e['label']) for axis in ('domains','functions') for e in cb[axis]]
 dev=read_blind('development_blind.jsonl');cal=read_blind('calibration_blind.jsonl')
 ad=jread(PRIVATE/'development_coding.json');ac=jread(PRIVATE/'calibration_coding.json')
 ids=list(dev);v=TfidfVectorizer(analyzer='char',ngram_range=(2,4),min_df=2,sublinear_tf=True,max_features=16000)
 X=v.fit_transform([dev[i] for i in ids]);did={sid:i for i,sid in enumerate(ids)}
 cids=list(cal); XC=v.transform([cal[i] for i in cids]);cid={sid:i for i,sid in enumerate(cids)}
 trained={}; decisions=[]
 for axis,code,label in labels:
  dr=rows(dev,ad,axis,code);cr=rows(cal,ac,axis,code)
  di=[did[sid] for sid,y in dr];dy=np.array([y for sid,y in dr]);ci=[cid[sid] for sid,y in cr];cy=np.array([y for sid,y in cr])
  rec={'axis':axis,'code':code,'label':label,'development_positive':int(dy.sum()),'development_negative':int(len(dy)-dy.sum()),'calibration_positive':int(cy.sum()),'calibration_negative':int(len(cy)-cy.sum()),'status':'unsupported','threshold':None}
  if dy.sum()<MIN_DEV_POS or len(dy)-dy.sum()<MIN_DEV_NEG or cy.sum()<MIN_CAL_POS:
   rec['reason']='insufficient_dev_or_calibration_support';decisions.append(rec);continue
  model=LogisticRegression(C=1.0,solver='liblinear',random_state=SEED,max_iter=1000)
  model.fit(X[di],dy);positive=X[[di[i] for i,y in enumerate(dy) if y]]
  probs,sim=score(model,XC[ci],positive); trials=[]
  for t in THRESHOLDS:
   pred=(probs>=t)&(sim>=MIN_SIMILARITY); n=int(pred.sum());tp=int((pred&cy.astype(bool)).sum());prec=tp/n if n else None
   trials.append({'threshold':t,'n_pred':n,'TP':tp,'precision':prec,'positive_recall':tp/int(cy.sum())})
  candidates=[r for r in trials if r['n_pred']>=MIN_CAL_PRED and r['precision']>=MIN_CAL_PRECISION]
  rec['calibration_trials']=trials
  if not candidates:rec['reason']='no_threshold_reaches_calibration_criteria';decisions.append(rec);continue
  best=max(candidates,key=lambda z:(z['positive_recall'],z['precision'],z['threshold']))
  rec.update(status='supported_for_pilot',threshold=best['threshold'],calibration_result=best)
  trained[code]=(model,positive,best['threshold']);decisions.append(rec)
 # Important: Freeze all decisions before reading the historical holdout.
 model_info={'method':'char TF-IDF on dev, unweighted logistic regression; per-code threshold chosen on calibration only; positive similarity guard','seed':SEED,'min_positive_cosine_similarity':MIN_SIMILARITY,'candidate_thresholds':THRESHOLDS,'min_cal_positive':MIN_CAL_POS,'min_cal_predicted_positive':MIN_CAL_PRED,'calibration_precision_requirement':MIN_CAL_PRECISION,'interpretation':'Predicted positives are candidates only; no prediction is semantic zero. No human ground truth. Historical holdout already inspected in prior research, so this is not a fresh external test.','decisions':decisions}
 (OUT/'frozen_calibration.json').write_text(json.dumps(model_info,ensure_ascii=False,indent=2)+'\n')
 hold=read_blind('holdout_blind.jsonl');HA=jread(PRIVATE/'holdout_coder_a.json');HB=jread(PRIVATE/'holdout_coder_b.json')
 hids=list(hold);XH=v.transform([hold[i] for i in hids]);hid={sid:i for i,sid in enumerate(hids)}
 preds={sid:{} for sid in hids}; sims={}
 for axis,code,label in labels:
  if code not in trained:continue
  m,posmat,t=trained[code];p,s=score(m,XH,posmat);pred=(p>=t)&(s>=MIN_SIMILARITY)
  sims[code]=s
  for i,sid in enumerate(hids):preds[sid][code]=int(pred[i])
 # Export no text; to ignored private location only.
 private_out=PRIVATE/'selective_v2';private_out.mkdir(exist_ok=True)
 with (private_out/'holdout_candidates.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.writer(f);w.writerow(['sample_id']+[code for code in trained]);w.writerows([[sid]+[preds[sid][code] for code in trained] for sid in hids])
 results=[]
 for rec in decisions:
  code=rec['code'];axis=rec['axis'];entry={k:rec[k] for k in ('axis','code','label','status','threshold')}
  entry['references']={}
  for name,reference in [('AI_A',HA),('AI_B',HB)]:
   valid=rows(hold,reference,axis,code)
   if code not in trained:
    entry['references'][name]={'eligible':len(valid),'support':sum(y for sid,y in valid),'status':'no_predictions'};continue
   z=Counter((preds[sid][code],y) for sid,y in valid)
   entry['references'][name]=dict(eligible=len(valid),**metrics(z[(1,1)],z[(1,0)],z[(0,1)],z[(0,0)]))
  results.append(entry)
 # Describe genuine zero-vector and both-AI-unspecified states, no filtering domain statuses.
 da={r['sample_id']:r for r in HA['records']};db={r['sample_id']:r for r in HB['records']}
 unspecified=[sid for sid in hids if da[sid]['domain_state']==db[sid]['domain_state']=='unspecified']
 domain_codes=[x['code'] for x in decisions if x['axis']=='domains' and x['status']=='supported_for_pilot']
 anydomain=lambda sid:any(preds[sid][c] for c in domain_codes)
 zeroids=[sid for i,sid in enumerate(hids) if XH[i].nnz==0]
 coverage={'n_holdout':len(hids),'supported_codes':list(trained),'unique_zero_vector_count':len(zeroids),'zero_vector_any_domain_candidate':sum(anydomain(sid) for sid in zeroids),'both_ai_unspecified_count':len(unspecified),'both_ai_unspecified_with_any_domain_candidate':sum(anydomain(sid) for sid in unspecified),'any_domain_candidate':sum(anydomain(sid) for sid in hids),'no_domain_candidate_or_unavailable':sum(not anydomain(sid) for sid in hids),'both_ai_readable_n':sum(da[sid]['observation_state']==db[sid]['observation_state']=='readable' for sid in hids),'candidate_counts_by_code':{code:sum(preds[sid][code] for sid in hids) for code in trained}}
 result={'sample':'historical 160-row AI-labelled holdout; prior work examined; no human labels','warning':model_info['interpretation'],'coverage':coverage,'per_label':results}
 (OUT/'holdout_evaluation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(coverage,ensure_ascii=False,indent=2));print('Calibration-supported codes:',len(trained))
if __name__=='__main__': main()
