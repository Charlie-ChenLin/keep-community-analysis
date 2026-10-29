"""Consolidate outcome-blind open coding into an explicit draft codebook.

This is a documented research-task aggregation, not discovery of a unique or
natural partition. All 15 open content leaves and 12 functions remain traceable.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json

import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'validation/classification_rebuild'
PRIVATE=QA/'private'

DOMAIN_MAP={
    'exercise':'d_exercise','body':'d_body','weight':'d_body','food':'d_food',
    'life':'d_life','weather':'d_life','culture':'d_life','outing':'d_life',
    'social':'d_life','family':'d_life','work_study':'d_life','appearance':'d_life',
    'festival':'d_life','religion':'d_life','platform':'d_tools',
}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    content_path=PRIVATE/'development_content_open.json'
    function_path=PRIVATE/'development_function_open.json'
    content=json.loads(content_path.read_text())
    functions=json.loads(function_path.read_text())
    texts={x['sample_id']:x['text']for name in ['development_blind.jsonl','observation_controls_blind.jsonl']for x in map(json.loads,(PRIVATE/name).read_text().splitlines())}
    a={x['sample_id']:x for x in content['records']}
    b={x['sample_id']:x for x in functions['records']}
    assert set(a)==set(b)==set(texts)
    domains=[
        {'code':'d_exercise','label':'运动与身体活动','definition':'正文明确讨论身体活动、具体运动、训练、运动方法或体育活动；不要求活动主体就是作者。','include':['跑步、骑行、步行、力量、拉伸等项目作为子类','明确的一般运动或身体活动讨论'],'exclude':['孤立的打卡、练、汗或品牌名','不能推断活动真实完成或作者自律人格'],'merge_reason':'项目属于同一讨论对象，保留项目差异为子类；不与上位运动类平级作互斥归类。'},
        {'code':'d_body','label':'身体状态、体重与外形','definition':'正文明确讨论身体感觉、症状、休息、体力或体重与身体形态的状态、改变或管理。','include':['身体感受/健康休息与体重/减脂是两个保留的细分','可以同运动或饮食共现'],'exclude':['只有情绪词而无身体对象','只提训练部位且未谈身体状态或外形'],'merge_reason':'按身体这一讨论对象作展示层归并；健康疲累与体重管理不被当作同一构念，叶类分别保留。'},
        {'code':'d_food','label':'饮食、食物与营养','definition':'正文以食物、用餐、食材、膳食安排、营养或饮食欲望为有实质指涉的讨论对象。','include':['餐食、食谱、买菜、食物评价及饮食计划'],'exclude':['不能因食物出现在Keep就认定减脂目的或健康质量','背景类比中的食物不自动计入'],'merge_reason':'语料中独立出现且不必依附训练或减脂，作为独立内容对象保留。'},
        {'code':'d_life','label':'生活、关系与社会文化话题','definition':'正文对人生处世提出实质命题，或明确讨论家庭关系、工作学习、阅读艺术媒体、天气、出行、衣着装饰、节庆或宗教活动。','include':['保留11个开发细分，可与运动共现','人生感悟需能复述其命题，具体生活场景需有直接文本证据'],'exclude':['不能作为没有命中运动词的剩余兜底类','早安、开心、加油、生活二字本身不足以判定内容域','不推断作者身份、信仰或关系性质'],'merge_reason':'为研究任务作广义展示归并，不声称内部同质或与运动互斥；所有细分频数和边界保留，避免丢弃低频真实主题。'},
        {'code':'d_tools','label':'工具、服务与记录奖励机制','definition':'正文明确讨论应用/工具功能、投屏、记录、等级或奖励等具体机制，不擅自补出提供者。','include':['功能问题或机制、等级奖励本身成为主题'],'exclude':['仅出现品牌名、课程分享标记、数字或打卡','不凭机制推断实际运动'],'merge_reason':'开发中虽少但与其他讨论对象不同，作为稀疏候选保留，不因频数少强并或据此回归。'},
        {'code':'d_other','label':'其他明确内容','definition':'正文有可复述的具体内容，但上述开发内容域不能覆盖；必须在note写出具体遗漏对象。','include':['留出和后续编码中出现的新内容对象'],'exclude':['空正文、符号或不能判断领域','不得通过其他类掩盖边界不清'],'merge_reason':'开放残余编码槽，而非开发阶段已经验证的新增类别；单独检查其占比和实例。'},
    ]
    funcdefs=[]
    for item in functions['proposed_functions']:
        x=dict(item);x['source_open_code']=x['code'];x['code']='f_'+x['code']
        x['basis']='开发语料开放归纳；仅编码可观察表达行为，不测潜在人格、真实心理状态或支持效果。'
        x['literature_connection']=('wang2015_support: 区分呈报/自述、征询与支持提供，仅借鉴区分原则'if item['code']in ['activity_update','experience_report','reader_response_request']else'开发语料中的重复表达行为；不冒充既有验证量表')
        funcdefs.append(x)
    records=[]
    function_codes=[x['code']for x in funcdefs]
    for sid in sorted(texts):
        ca,fb=a[sid],b[sid]
        astate=ca['state'];bstate=fb['state']
        empty=not texts[sid]
        readable=(not empty)and(astate=='explicit_content'or bstate=='interpretable')
        obs='empty'if empty else'readable'if readable else'insufficient'
        dstate='specified'if astate=='explicit_content'else'unspecified'if astate=='domain_unspecified'else'unavailable'
        dlabels=sorted({DOMAIN_MAP[x]for x in ca['domains']})
        flabels=['f_'+x for x in fb['functions']]
        evidence={}
        for leaf,span in ca.get('evidence',{}).items():
            code=DOMAIN_MAP[leaf]
            evidence.setdefault(code,span)
        evidence.update({'f_'+k:v for k,v in fb.get('evidence',{}).items()})
        for label in dlabels+flabels:
            span=evidence[label]
            assert isinstance(span,str)and span and span in texts[sid],(sid,label,span)
        records.append({'sample_id':sid,'observation_state':obs,'domain_state':dstate,'domains':dlabels,'functions':flabels,
                        'uncertain_domains':[],'uncertain_functions':function_codes if bstate!='interpretable'and obs=='readable'else[],
                        'evidence':evidence,'note':'内容与功能由两个不同任务的AI开发编码合并；不是两名编码员对同一变量的一致性验证。 '+ca.get('note','')+' '+fb.get('note','')})
    parent_count=Counter(c for x in records if x['sample_id'].startswith('D')for c in x['domains'])
    function_count=Counter(c for x in records if x['sample_id'].startswith('D')for c in x['functions'])
    keys=pd.read_csv(PRIVATE/'development_keys.csv').set_index('sample_id')
    for definition in domains+funcdefs:
        code=definition['code'];axis='domains'if code.startswith('d_')else'functions'
        ids=[x['sample_id']for x in records if x['sample_id'].startswith('D')and code in x[axis]]
        definition['development_posts']=len(ids)
        definition['development_authors']=len({keys.loc[sid,'author']for sid in ids})
        definition['development_example_ids']=ids[:8]
        definition['status']='sparse_candidate'if len(ids)<5 else'development_supported_candidate'
    codebook={'version':'draft_from_open_coding_1','status':'由开发语料形成的待校准、待独立人工验证编码方案；不得称完整真实主题分类。',
              'unit':'单条可观察清理正文；不使用原始tag、图像想象、作者身份、点赞或旧模型权重补语义。',
              'axes':{'domains':'讨论什么内容；多标签；父类是研究任务展示聚合，不是唯一自然分区。','functions':'做出什么可观察表达行为；多标签；不推测真实心理、意图实现或互动效果。'},
              'domains':domains,'functions':funcdefs,'content_subdomains':content['proposed_domains'],'subdomain_to_parent':DOMAIN_MAP,
              'parent_aggregation_note':'15个开发细分整理为5个观察到的父域，另留其他槽；父域计数为帖子并集，不将叶类次数相加。不因回归、模型性能或显著性决定合并。',
              'states':{'observation_state':['readable','insufficient','empty'],'domain_state':['specified','unspecified','uncertain','unavailable'],
                        'domain_unspecified':'正文可表达感受/寒暄/动员，但没有足够内容对象；不等于五/六域已知均不存在。',
                        'insufficient':'符号、数字、片段等不足以解释；不能强行归入题注/其他。'},
              'coding_rules':['仅编码正文可直接指出的语义；所有阳性标签必须带原文证据片段。','同帖可多域、多功能；一个轴可判断不表示另一个轴也可判断。','未知、缺失与未检出不是一回事。','转引、格言或解释可按其表达内容编码，但不认定作者信念、人格或知识真实。','稀疏候选可保留在人审codebook中，不保证可以自动识别或用于回归。','不新增test中观察到的标签后再回头重算同一留出测试。'],
              'limitations':['开发阶段每轴由一个AI任务编码，不是人工双人编码；后续同模型不同上下文AI盲测仍不能替代人工效度。','父类聚合用于呈现与筛查，不假设其成员对点赞作用相同。'],
              'evidence_sources':{'content_open_sha256':sha(content_path),'function_open_sha256':sha(function_path),'literature':'code/classification_rebuild_literature.json'},
              'calibration_changes':[]}
    (ROOT/'code/classification_codebook_draft.json').write_text(json.dumps(codebook,ensure_ascii=False,indent=2)+'\n')
    (PRIVATE/'development_coding.json').write_text(json.dumps({'stage':'AI_development_consolidation','records':records},ensure_ascii=False,indent=2)+'\n')
    summary={'development_nonempty_posts':160,'development_authors':55,'empty_controls':12,'observed_content_leaves':15,'observed_parent_domains':5,'open_residual_slots':1,'observed_functions':12,
             'parent_counts':dict(parent_count),'function_counts':dict(function_count),'codebook_status':'draft; not independently human validated','raw_annotation_paths_are_private':True,
             'aggregation_decisions':[{k:x[k]for k in ['code','label','merge_reason','development_posts','development_authors','status']}for x in domains],
             'source_sha256':{'content_open':sha(content_path),'function_open':sha(function_path)}}
    (ROOT/'results/classification_codebook_development.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    for axis in ['content','function']:
        src=QA/'results'/f'classification_{axis}_discovery.json'
        if src.is_file():(ROOT/'results'/src.name).write_bytes(src.read_bytes())
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
