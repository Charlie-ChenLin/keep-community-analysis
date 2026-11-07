#!/usr/bin/env python3
"""Historical scope and fixed pilot comparisons after a complete fresh reread."""
from pathlib import Path
import csv,hashlib,importlib.util,json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'
RUN=PRIVATE/'variable_scheme_v5_production'
TRIAL=PRIVATE/'variable_scheme_v5'
spec=importlib.util.spec_from_file_location('v5',ROOT/'code/evaluate_variable_scheme_v5.py')
v5=importlib.util.module_from_spec(spec);spec.loader.exec_module(v5)
def js(p):return json.loads(Path(p).read_text())
def jl(p):return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def csvs(p):
    with Path(p).open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def compare_binary_coverage(old,new):
    return {'old_positive':int(old.sum()),'new_positive':int(new.sum()),'both_positive':int((old&new).sum()),
      'new_only_positive':int((~old&new).sum()),'old_only_positive':int((old&~new).sum()),'neither_positive':int((~old&~new).sum()),
      'note':'Historical predictions and changed definitions: transitions are not validated error corrections.'}

def main():
    summary=js(RUN/'merge_summary.json');freeze=js(RUN/'full_run_freeze.json');old_trial=js(ROOT/'results/variable_scheme_v5_evaluation.json')
    if sha(RUN/'merged_unique.jsonl')!=summary['merged_unique_sha256'] or sha(ROOT/'results/variable_scheme_v5_evaluation.json')!=freeze['pilot_evaluation_sha256']:
        raise ValueError('Full labels or frozen pilot evaluation changed')
    production={r['sample_id']:r for r in jl(RUN/'merged_unique.jsonl')};key=csvs(RUN/'private_key.csv');trial_key=csvs(TRIAL/'private_key.csv')
    trial_to_prod={r['trial_sample_id']:r['sample_id'] for r in key if r['trial_sample_id']}
    if set(trial_to_prod)!={r['sample_id'] for r in trial_key}:raise ValueError('Trial to production mismatch')
    trial_a={r['sample_id']:r for r in jl(TRIAL/'coder_a.jsonl')};trial_b={r['sample_id']:r for r in jl(TRIAL/'coder_b.jsonl')}
    for who in ('a','b'):
        if sha(TRIAL/f'coder_{who}.jsonl')!=old_trial['coder_output_sha256'][who]:raise ValueError('Original coder output changed')
    protocol=js(TRIAL/'frozen_protocol.json');comparisons={}
    for part in ('random','targeted_no_v3_positive'):
        ids=[r['sample_id'] for r in trial_key if r['partition']==part];prod=[production[trial_to_prod[s]] for s in ids]
        comparisons[part]={'n':len(ids),'production':v5.coverage(prod),
          'against_pilot_a':v5.agreement(prod,[trial_a[s] for s in ids],protocol['consistency_screen']),
          'against_pilot_b':v5.agreement(prod,[trial_b[s] for s in ids],protocol['consistency_screen']),
          'limit':'Production vs previously frozen same-base pilot codings. Not a new independent human validation or unseen-text holdout.'}
        for side in ('against_pilot_a','against_pilot_b'):
            # These comparisons diagnose transport of the frozen scheme, not
            # new screening thresholds selected after the production results.
            for d in comparisons[part][side]['per_label'].values():d.pop('screen_state_if_random_partition',None)
    full=pd.read_csv(RUN/'post_labels.csv',dtype={'postId':str},keep_default_na=False).set_index('postId')
    full=full.loc[full.input_status.eq('needs_model')];new=full[[c for c in v5.EXPRESSIONS if c!='S_OTHER']].eq('1').any(axis=1)
    old2=pd.read_csv(PRIVATE/'v2_direct_batches/post_labels.csv',dtype={'postId':str},keep_default_na=False).set_index('postId').loc[full.index]
    old3=pd.read_csv(PRIVATE/'v3_refined_batches/post_labels.csv',dtype={'postId':str},keep_default_na=False).set_index('postId').loc[full.index]
    p2=old2.expression_labels.map(lambda x:bool(set(json.loads(x) if x else [])-{'F_OTHER'}))
    codes3=list(js(ROOT/'code/classification_schema_v3.json')['labels']);p3=old3[codes3].eq('1').any(axis=1)
    posts=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str}).set_index('postId').loc[full.index]
    lexical=posts[['self_discipline','social_address','positive_expression','question']].gt(0).any(axis=1)
    expression_codes=[c for c in v5.EXPRESSIONS if c!='S_OTHER']
    known=full[expression_codes].isin(['0','1']);all_unknown=~known.any(axis=1)
    no_positive_details={}
    for name,old in [('legacy_four_lexical',lexical),('v2_named_expression',p2),('v3_nine_expression',p3)]:
        losses=old&~new
        no_positive_details[name]={'old_positive_new_no_positive':int(losses.sum()),
          'v5_all_ten_unknown':int((losses&all_unknown).sum()),
          'v5_all_ten_known_negative':int((losses&known.all(axis=1)).sum()),
          'v5_mixed_known_and_unknown_without_positive':int((losses&~all_unknown&~known.all(axis=1)).sum()),
          'limit':'New unknown/negative states describe the changed measurement; they do not identify the true cause of disagreement or prove historical errors.'}
    result={'status':'full_scope_and_same_base_measurement_consistency_comparison_not_accuracy','n_nonempty_posts':len(full),
      'historical_same_post_population':{'legacy_four_lexical':compare_binary_coverage(lexical,new),
        'v2_named_expression':compare_binary_coverage(p2,new),'v3_nine_expression':compare_binary_coverage(p3,new)},
      'fixed_pilot_comparisons':comparisons,'input_sha256':{'full_merged':sha(RUN/'merged_unique.jsonl'),'full_post_labels':sha(RUN/'post_labels.csv'),
        'pilot_evaluation':sha(ROOT/'results/variable_scheme_v5_evaluation.json')},
      'no_new_expression_positive_among_historical_positives':no_positive_details,
      'human_accuracy_established':False,'new_independent_human_reviews':0}
    out=ROOT/'results/v5_full_measurement_comparison.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'output':str(out),'historical':result['historical_same_post_population'],
      'pilot':{part:{'n':p['n'],'production_positive':p['production']['axes']['expression']['any_positive'],
      'strict_set_agreement_a':p['against_pilot_a']['expression_positive_and_unknown_set_exact'],
      'strict_set_agreement_b':p['against_pilot_b']['expression_positive_and_unknown_set_exact']} for part,p in comparisons.items()}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
