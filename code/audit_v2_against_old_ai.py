#!/usr/bin/env python3
"""Compare new direct AI codes with historical AI codes; no human gold standard.

Historical holdout results have already been inspected during v2 design, so this
is a retrospective consistency diagnostic, not a fresh independent test.
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'validation/classification_rebuild/private'
RUN = PRIVATE / 'v2_direct_batches'
OUTPUT = ROOT / 'results/v2_historical_ai_comparison.json'
CONTENT = {'C_EXERCISE': ['d_exercise'], 'C_BODY': ['d_body'],
           'C_FOOD': ['d_food'], 'C_LIFE': ['d_life'],
           'C_TOOLS': ['d_tools'], 'C_OTHER': ['d_other']}
FUNCTION = {'F_UPDATE':['f_activity_update'],
 'F_EXPERIENCE_EVALUATION':['f_experience_report','f_appraisal'],
 'F_FUTURE':['f_future_intention'], 'F_EXHORT':['f_exhortation'],
 'F_GUIDANCE':['f_explanation','f_practical_guidance'], 'F_REFLECTION':['f_reflection'],
 'F_GREETING_GRATITUDE':['f_greeting_wish','f_gratitude'],
 'F_INVITE_ASK':['f_relational_bid','f_reader_response_request'],
 'F_CAPTION':['f_caption'], 'F_SALE':['f_sale_offer'], 'F_OTHER':['f_other_expression']}


def old_value(record, codes, positive, uncertain):
    if any(c in record[positive] for c in codes):
        return 1
    if any(c in record[uncertain] for c in codes):
        return None
    return 0


def main():
    if not (RUN / 'merge_summary.json').exists():
        raise SystemExit('Full validated classification merge is required')
    mapping = pd.read_csv(PRIVATE/'holdout_keys.csv', dtype={'postId':str})[['sample_id','postId']].rename(columns={'sample_id':'old_id'})
    current = pd.read_csv(RUN/'post_labels.csv', dtype={'postId':str}, keep_default_na=False)
    data = mapping.merge(current, on='postId', how='left', validate='one_to_one')
    if len(data) != 160 or data.observation_state.eq('').any():
        raise ValueError('Historical holdout mapping is incomplete')
    historical = {name:{r['sample_id']:r for r in json.loads((PRIVATE/f'holdout_coder_{name}.json').read_text())['records']}
                  for name in ('a','b')}
    output={'description':'Retrospective consistency of model-assisted classifications against two prior same-base AI encodings; not accuracy, human validation or a fresh held-out test.',
            'n_prior_holdout':len(data), 'comparisons':{}}
    for rater in ('a','b'):
        ref=historical[rater]
        rows=[]
        for axis, codes, new_field, new_uncertain, old_field, old_uncertain in [
            ('content',CONTENT,'content_labels','uncertain_content','domains','uncertain_domains'),
            ('expression',FUNCTION,'expression_labels','uncertain_expression','functions','uncertain_functions')]:
            for code, old_codes in codes.items():
                tp=fp=fn=tn=excluded=0
                for r in data.itertuples(index=False):
                    old=ref[r.old_id]
                    reason=(r.observation_state!='readable' or old['observation_state']!='readable')
                    if axis=='content':
                        reason = reason or r.domain_state!='specified' or old['domain_state']!='specified'
                    new_pos=json.loads(getattr(r,new_field));new_unknown=json.loads(getattr(r,new_uncertain))
                    ov=old_value(old,old_codes,old_field,old_uncertain)
                    if reason or code in new_unknown or ov is None:
                        excluded+=1;continue
                    nv=int(code in new_pos)
                    if nv and ov:tp+=1
                    elif nv:fp+=1
                    elif ov:fn+=1
                    else:tn+=1
                denom=2*tp+fp+fn
                rows.append({'axis':axis,'code':code,'n_compared':tp+fp+fn+tn,'excluded':excluded,
                             'both_positive':tp,'current_only':fp,'previous_only':fn,'both_negative':tn,
                             'positive_agreement':2*tp/denom if denom else None,
                             'low_support':tp+fp+fn<5})
        output['comparisons'][rater]=rows
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(OUTPUT)

if __name__=='__main__':main()
