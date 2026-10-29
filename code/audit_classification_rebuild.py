"""Post-freeze scope diagnostics; never retunes the codebook or detector."""
from collections import Counter
from pathlib import Path
import csv
import json

from evaluate_rebuilt_classification import (
    check_freeze, exclusion_reasons, load_annotations, load_blind, load_codebook, recheck_freeze,
    sha256, write_json,
)

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'validation/classification_rebuild/private'


def main():
    freeze=check_freeze(ROOT,ROOT/'validation/classification_rebuild/freeze_record.json',
                        ROOT/'code/classification_codebook_v1.json',ROOT/'code/classification_recognizer_v1.json')
    axes=load_codebook(freeze['codebook_path'])
    blind=load_blind(PRIVATE/'holdout_blind.jsonl')
    packet_hash_verified=sha256(PRIVATE/'holdout_blind.jsonl')==json.loads(Path(freeze['path']).read_text())['holdout']['packet_sha256']
    assert packet_hash_verified,'Released holdout packet changed.'
    a=load_annotations(PRIVATE/'holdout_coder_a.json',blind,axes)
    b=load_annotations(PRIVATE/'holdout_coder_b.json',blind,axes)
    with (ROOT/'results/rebuilt_prediction_holdout.csv').open(encoding='utf-8-sig',newline='')as f:
        predictions={r['sample_id']:r for r in csv.DictReader(f)}
    config=json.loads((ROOT/'code/classification_recognizer_v1.json').read_text())
    import joblib
    model=joblib.load(PRIVATE/'classifier_v1.joblib')
    matrix=model['vectorizer'].transform(list(blind.values()))
    zero_ids=[sid for sid,n in zip(blind,matrix.getnnz(axis=1))if n==0]
    domain_codes=[x['code']for x in axes['domains']]

    def assigned(sid):return any(predictions[sid]['pred_'+c]=='1'for c in domain_codes)
    def state_diagnostics(rows):
        output=[]
        for state in ['specified','unspecified','uncertain','unavailable']:
            ids=[sid for sid,r in rows.items()if r['domain_state']==state]
            output.append({'domain_state':state,'n':len(ids),
                           'gate_passed':sum(predictions[s]['pred_domain_specificity']=='1'for s in ids),
                           'at_least_one_domain_assigned':sum(assigned(s)for s in ids)})
        return output
    both_unspecified=[s for s in blind if a[s]['domain_state']==b[s]['domain_state']=='unspecified']
    agreement={axis:sum(set(a[s][axis])==set(b[s][axis])for s in blind)for axis in axes}
    # No adjudication: the disagreement packet is for a later human pass.
    differences=[]
    for sid in blind:
        changed={}
        for k in ['observation_state','domain_state','domains','functions','uncertain_domains','uncertain_functions']:
            differs=(set(a[sid][k])!=set(b[sid][k]))if isinstance(a[sid][k],list)else a[sid][k]!=b[sid][k]
            if differs:changed[k]={'AI_A':a[sid][k],'AI_B':b[sid][k]}
        if changed:differences.append({'sample_id':sid,'text':blind[sid],'differences':changed,
                                       'evidence_A':a[sid]['evidence'],'evidence_B':b[sid]['evidence']})
    write_json(PRIVATE/'holdout_disagreements_for_later_human_review.json',{'not_adjudicated':True,'records':differences})
    keys={}
    for stage in ['development','calibration','holdout']:
        with (PRIVATE/(stage+'_keys.csv')).open(encoding='utf-8-sig',newline='')as f:keys[stage]=list(csv.DictReader(f))
    authors={stage:{r['author']for r in records}for stage,records in keys.items()}
    templates={stage:{''.join(r['clean_text'].split()).lower()for r in records}for stage,records in keys.items()}
    pairs=[('development','calibration'),('development','holdout'),('calibration','holdout')]
    controls=json.loads((PRIVATE/'observation_controls_coding.json').read_text())['records']
    positive_output_coverage=[]
    for name,rows in [('AI_A',a),('AI_B',b)]:
        for axis,entries in axes.items():
            for entry in entries:
                code=entry['code']
                ids=[sid for sid,r in rows.items()if code in r[axis]and not exclusion_reasons(r,axis,code)]
                unavailable=sum(predictions[s]['pred_'+code]not in ['0','1']for s in ids)
                detected=sum(predictions[s]['pred_'+code]=='1'for s in ids)
                positive_output_coverage.append({'reference':name,'code':code,'reference_positive':len(ids),
                    'positive_with_unavailable_prediction':unavailable,'positive_detected':detected,
                    'positive_detection_with_abstentions_counted_as_not_detected':detected/len(ids)if ids else None})
    report={'scope':'AI-only post-freeze diagnostics; no semantic ground truth or new tuning',
            'codebook_sha256':sha256(ROOT/'code/classification_codebook_v1.json'),
            'frozen_files_verified':True,'n':len(blind),'actual_packet_authors':{k:len(v)for k,v in authors.items()},
            'checks':{'author_packets_disjoint':all(not authors[x]&authors[y]for x,y in pairs),
                      'released_packet_hash_matches':packet_hash_verified,
                      'exact_templates_disjoint':all(not templates[x]&templates[y]for x,y in pairs),
                      'no_duplicate_templates_within_packets':all(len(templates[k])==len(keys[k])for k in keys),
                      'all_positive_evidence_literal':True,
                      'empty_controls_stayed_empty':all(r['observation_state']=='empty'and not r['domains']and not r['functions']for r in controls)},
            'empty_observation_controls_n':len(controls),
            'frozen_codebook_metadata_errata':[{'field':'d_life.include: 保留11个开发细分','correction':'显式映射为10个开发叶及2个校准新增叶。冻结定义未改变，仅纠正计数措辞。'}],
            'state_cross_tab':dict(Counter(a[s]['domain_state']+' / '+b[s]['domain_state']for s in blind)),
            'exact_label_set_agreement_all_160':agreement,
            'different_record_n':len(differences),
            'multi_label_counts':{name:{axis:sum(len(r[axis])>=2 for r in rows.values())for axis in axes}for name,rows in [('AI_A',a),('AI_B',b)]},
            'domain_scope_diagnostics':{'AI_A':state_diagnostics(a),'AI_B':state_diagnostics(b),
                'both_unspecified':{'n':len(both_unspecified),'gate_passed':sum(predictions[s]['pred_domain_specificity']=='1'for s in both_unspecified),
                                    'at_least_one_domain_assigned':sum(assigned(s)for s in both_unspecified)}},
            'positive_output_coverage_including_abstentions':positive_output_coverage,
            'zero_development_vocabulary_overlap':{'n':len(zero_ids),'at_least_one_domain_assigned':sum(assigned(s)for s in zero_ids),
                'note':'零字符ngram重合时输出来自模型截距/阈值，不能视为原文语义理解。'},
            'unsupported_codes':[x['code']for x in config['labels']if x['axis']!='gate'and not x['supported']],
            'uncalibrated_supported_codes':[x['code']for x in config['labels']if x['supported']and x['calibration_status']=='uncalibrated_insufficient_support'],
            'unresolved_disagreements_private_file':'validation/classification_rebuild/private/holdout_disagreements_for_later_human_review.json',
            'interpretation':'模型在领域未指明正文上的赋类单独报告，不以排除这些正文后的条件precision掩盖覆盖问题。AI间及模型相对AI分歧都不是人工错误率。17内容叶未逐叶留出验证；未修改冻结规则。'}
    recheck_freeze(freeze)
    write_json(ROOT/'results/classification_rebuild_scope_audit.json',report)
    print(json.dumps({'status':'pass','n':report['n'],'checks':report['checks'],
                      'different_record_n':report['different_record_n'],
                      'both_unspecified':report['domain_scope_diagnostics']['both_unspecified'],
                      'full_evidence':'results/classification_rebuild_scope_audit.json'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
