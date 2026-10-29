"""Apply documented calibration decisions, before any holdout release."""
from pathlib import Path
from copy import deepcopy
from collections import Counter
import hashlib
import json

from evaluate_rebuilt_classification import load_codebook,load_annotations,load_blind

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'validation/classification_rebuild'
PRIVATE=QA/'private'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert not(QA/'freeze_record.json').exists(),'Frozen version cannot be retuned.'
    draft=json.loads((ROOT/'code/classification_codebook_draft.json').read_text())
    book=deepcopy(draft)
    book['version']='1.0_frozen_after_development_and_calibration'
    book['status']='开发与校准完成、留出检验前冻结；尚未经独立人工验证。'
    book['content_subdomains'].extend([
        {'code':'commerce','label':'消费、交易与商业处境','definition':'有明确文字指涉的选购、购买、付费、售卖、价格条款、红包金钱利益获取或商家处境。','include':['食品实际采购可与饮食共标','商家反应可作为商业处境，不补出具体事件或原因'],'exclude':['商品或品牌名本身','购买力比喻、价钱背景例举不机械增标签'],'example_ids':['D003','D128','C001','C006','C007','C071'],'status':'added_from_calibration_then_development_rechecked'},
        {'code':'home_housing','label':'居家环境与装修','definition':'居住环境、住房或装修本身成为具体讨论内容。','include':['装修安排和住宅环境问题'],'exclude':['居家训练的场所词、地板动作条件、不明场景不机械增标签'],'example_ids':['C078'],'status':'sparse_candidate_added_from_calibration'},
    ])
    book['subdomain_to_parent'].update(commerce='d_life',home_housing='d_life')
    life=next(x for x in book['domains']if x['code']=='d_life')
    life['definition']+='校准新增消费、交易、商业处境和居住装修细分；仍需具体对象证据，不把无法归类的表达当生活。'
    life['include'].append('17个内容叶中社会文化、生活及新增消费/居住对象为展示聚合；并非运动的互斥补集。')
    book['parent_aggregation_note']='开发15叶，校准补2叶，共17个可追溯内容细分，按研究任务展示为5个观察父组并保留其他槽；父组不是唯一自然分区或同质构念。计数取帖子并集。'
    newfuncs=[
        {'code':'f_gratitude','label':'明确感谢表达','definition':'正文对对象执行感谢或感恩表达，观察该话语形式，不推断真诚、实际获助或心理感激。','include':['明确感谢/感恩且有对象','幽默表达仍可含感谢话语，但须备注语境'],'exclude':['只有赞美、喜欢、致敬或问候','感谢不能证明已收到社会支持'],'example_ids':['C037','C075'],'nearest_confusion':'appraisal是褒贬；greeting_wish是祝愿；本类需要感谢表达。'},
        {'code':'f_sale_offer','label':'商品服务供给与交易告知','definition':'明确给出商品/服务供给、售卖、价格或交易条款。','include':['商品报价、退换条款等交易内容'],'exclude':['只推荐既有课程或食品用途','不由产品名推收费广告、作者职业或成交'],'example_ids':['C007'],'nearest_confusion':'explanation是可泛化说明；practical_guidance是如何操作；本类是具体供给/条款。'},
        {'code':'f_other_expression','label':'其他可辨识表达行为','definition':'存在当前既有功能不能表达的具体话语行为，如明确的谐音段子、幻想叙事；必须在note描述缺口。可与另有证据的功能并列。','include':['校准出现的想象段子/反转叙事/谐音双关'],'exclude':['不可解释片段、空正文和纯符号','不能因所有文本都有修辞就普遍加其他','已有格言/体验/记录足够覆盖时不重复归入'],'example_ids':['C006','C030','C044','C080'],'nearest_confusion':'activity_update只指被呈报为已发生/当下的事件框架，不把假设情景当实际经历。'},
    ]
    for x in newfuncs:
        x.update(development_posts=0,development_authors=0,status='sparse_candidate_added_from_calibration',basis='校准中的真实遗漏行为；回查160条开发正文仍无明确阳性，不为训练凑样本。')
    book['functions'].extend(newfuncs)
    book['coding_rules'].extend([
        '内容主题可依据假想、梦境、否定或转引中明确对象编码，但这不证明真实经历、婚姻、体重或运动发生。',
        'f_activity_update仅编码被当作已发生/当下事件呈报的文本框架；梦中/假设片段不转为实际身体体验或未来承诺。',
        'f_practical_guidance须给出具体对象下可执行办法，超过一般努力口号；f_explanation不因具体商品价格而自动增加。',
        'f_relational_bid须有面向他人的联系或共同参与邀请；单独@、一起的叙事或商业保证不够。',
        '本版不编码真实心理情绪的正负程度；体验、评价、动员与感谢分开，均不冒充积极人格或社会支持效果。',
    ])
    changes=[
        {'issue':'开发内容遗漏消费交易和装修','evidence_ids':['D003','D128','C001','C006','C007','C071','C078'],'decision':'增加commerce/home_housing叶并明确归d_life的展示聚合；原开发与严格draft校准不覆盖，另保存v1编码。'},
        {'issue':'感谢、供给交易和虚构段子不被12功能覆盖','evidence_ids':['C007','C037','C075','C006','C030','C044','C080'],'decision':'新增3个明确行为/开放残余；开发回查阳性仍0，标低支持、不承诺可自动识别。'},
        {'issue':'谐音愿望和梦中体验易误推实际状态','evidence_ids':['C006','C030','C044','C080'],'decision':'撤C006未来意愿、C030身体体验；添加具体其他行为并清理已解决的不确定项。'},
        {'issue':'领域/行为与真实事实必须分开','evidence_ids':['C030','C044','C048','C078','C080'],'decision':'内容对象允许虚构/否定；不据此推断实际行动、疾病、人格、关系或支持。'},
    ]
    book['calibration_changes']=changes
    book['evidence_sources']['calibration_content_sha256']=digest(PRIVATE/'calibration_content.json')
    book['evidence_sources']['calibration_functions_sha256']=digest(PRIVATE/'calibration_functions.json')
    book['evidence_sources']['function_change_review_sha256']=digest(PRIVATE/'function_v1_change_proposals.json')
    dev0=json.loads((PRIVATE/'development_coding.json').read_text())
    dev=deepcopy(dev0)
    for row in dev['records']:
        if row['sample_id']=='D128':
            row['domains']=sorted(set(row['domains'])|{'d_life'})
            row['evidence']['d_life']='买菜回家'
            row['note']+=' v1新增购物叶，依据明确采购动作补生活对象；不推断所有食物都发生采购。'
    content={x['sample_id']:x for x in json.loads((PRIVATE/'calibration_content.json').read_text())['records']}
    functions={x['sample_id']:x for x in json.loads((PRIVATE/'calibration_functions.json').read_text())['records']}
    texts=load_blind(PRIVATE/'calibration_blind.jsonl')
    function_codes=[x['code']for x in book['functions']]
    rows=[]
    for sid,text in texts.items():
        ca,fb=deepcopy(content[sid]),deepcopy(functions[sid])
        obs='empty'if not text.strip()else'readable'if ca['observation_state']=='readable'or fb['observation_state']=='readable'else'insufficient'
        evidence={**ca['evidence'],**fb['evidence']}
        row={'sample_id':sid,'observation_state':obs,'domain_state':ca['domain_state'],'domains':ca['domains'],'functions':fb['functions'],'uncertain_domains':ca.get('uncertain_domains',[]),
             'uncertain_functions':fb.get('uncertain_functions',[])if fb['observation_state']=='readable'else function_codes if obs=='readable'else[],
             'evidence':evidence,'note':ca.get('note','')+' '+fb.get('note','')}
        if sid in ['C001','C006','C007','C071','C078']:
            row['domains']=sorted((set(row['domains'])-{'d_other'})|{'d_life'})
            row['evidence']['d_life']=ca['evidence'].get('d_life',ca['evidence'].get('d_other'))
            row['evidence'].pop('d_other',None)
            row['domain_state']='specified'
            row['note']+=' v1校准：新增消费/商业或装修叶后按明确内容对象归生活展示组。'
        rows.append(row)
    proposed=json.loads((PRIVATE/'function_v1_change_proposals.json').read_text())
    indexed={x['sample_id']:x for x in rows}
    for patch in proposed['calibration_changes']:
        row=indexed[patch['sample_id']]
        for code in patch['remove_functions']:
            if code in row['functions']:row['functions'].remove(code)
            row['evidence'].pop(code,None)
        for code in patch['add_functions']:
            if code not in row['functions']:row['functions'].append(code)
            row['evidence'][code]=patch['evidence'][code]
        for code in patch['resolve_uncertain']:
            if code in row['uncertain_functions']:row['uncertain_functions'].remove(code)
            if code not in row['functions']:row['evidence'].pop(code,None)
        row['note']+=' v1变更：'+patch['rationale']
    # Preserve the prior consolidation and controls; model fit sees exactly D001–160.
    (PRIVATE/'development_coding_draft_archive.json').write_text(json.dumps(dev0,ensure_ascii=False,indent=2)+'\n')
    controls=[x for x in dev['records']if not x['sample_id'].startswith('D')]
    dev['records']=[x for x in dev['records']if x['sample_id'].startswith('D')]
    (PRIVATE/'observation_controls_coding.json').write_text(json.dumps({'records':controls},ensure_ascii=False,indent=2)+'\n')
    dev['stage']='AI_development_v1_after_documented_calibration'
    cal={'stage':'AI_calibration_v1; not independent validation','records':rows}
    for target,data in [('development_coding.json',dev),('calibration_coding.json',cal)]:
        (PRIVATE/target).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    # Fill evidence counts without treating the deliberately sampled packets as prevalence.
    for axis in ['domains','functions']:
        for definition in book[axis]:
            code=definition['code']
            definition['development_posts']=sum(code in x[axis]for x in dev['records'])
            definition['calibration_posts']=sum(code in x[axis]for x in rows)
            definition['calibration_example_ids']=[x['sample_id']for x in rows if code in x[axis]][:6]
    target=ROOT/'code/classification_codebook_v1.json'
    target.write_text(json.dumps(book,ensure_ascii=False,indent=2)+'\n')
    axes=load_codebook(target)
    load_annotations(PRIVATE/'development_coding.json',load_blind(PRIVATE/'development_blind.jsonl'),axes)
    load_annotations(PRIVATE/'calibration_coding.json',texts,axes)
    summary={'codebook_sha256':digest(target),'development_n':len(dev['records']),'calibration_n':len(rows),'content_leaf_count':len(book['content_subdomains']),'domain_parent_codes':[x['code']for x in book['domains']],
             'function_count':len(book['functions']),'changes':changes,'holdout_has_not_been_released':not(PRIVATE/'holdout_blind.jsonl').exists(),
             'counts':{axis:[{k:x[k]for k in ['code','label','development_posts','calibration_posts']}for x in book[axis]]for axis in ['domains','functions']}}
    (ROOT/'results/classification_codebook_calibration.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
