#!/usr/bin/env python3
"""Summarize historical AI-coded bodies without extrapolating or refitting.

Uses original frozen labels and private linkage locally. Outputs only aggregate counts;
no raw text, author identifiers, sample IDs or post IDs. Never recodes labels.
"""
from pathlib import Path
import json, hashlib
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'validation/classification_rebuild/private'
OUT = ROOT / 'results/existing_ai_coding_descriptive.json'
REPORT = ROOT / '既有AI正文编码_描述性分析.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_coding(name):
    with (PRIVATE / name).open() as f:
        data = json.load(f)
    rows = data['records']
    assert len({r['sample_id'] for r in rows}) == len(rows)
    return {r['sample_id']: r for r in rows}


def count_scope(records, keys, feature_by_post, definitions):
    assert set(keys.sample_id) == set(records)
    results = []
    for axis in ('domains','functions'):
        for entry in definitions[axis]:
            code=entry['code']
            known_pos=uncertain=0
            for r in records.values():
                known_pos += int(code in r[axis])
                uncertain += int(code in r.get('uncertain_'+axis, []))
            results.append({'axis':axis,'code':code,'label':entry['label'],
                            'positive':known_pos,'uncertain':uncertain,
                            'all_sample_n':len(records)})
    keys=keys.copy()
    keys['old_any']=keys.postId.map(feature_by_post)
    assert keys.old_any.notna().all()
    nohit=keys.loc[~keys.old_any.astype(bool), 'sample_id'].tolist()
    def states(sids):
        recs=[records[s] for s in sids]
        return {
          'n':len(recs),
          'readable':sum(r['observation_state']=='readable' for r in recs),
          'content_specified':sum(r['domain_state']=='specified' for r in recs),
          'content_unspecified':sum(r['domain_state']=='unspecified' for r in recs),
          'content_uncertain':sum(r['domain_state']=='uncertain' for r in recs),
          'content_unavailable':sum(r['domain_state']=='unavailable' for r in recs),
          'any_domain':sum(bool(r['domains']) for r in recs),
          'any_function':sum(bool(r['functions']) for r in recs),
          'any_domain_or_function':sum(bool(r['domains'] or r['functions']) for r in recs),
          'two_or_more_domains':sum(len(r['domains'])>=2 for r in recs),
          'two_or_more_functions':sum(len(r['functions'])>=2 for r in recs),
        }
    return {'n':len(records),'categories':results,
            'sample_states':states(list(records)),
            'old_no_hit_subset':states(nohit)}


def main():
    f=pd.read_csv(ROOT/'results/post_features.csv',dtype={'postId':str})
    assert len(f)==9532 and f.postId.is_unique
    cols=['self_discipline','social_address','positive_expression','question']
    assert all(f[c].isin([0,1]).all() for c in cols)
    hit=f.set_index('postId')[cols].sum(axis=1).gt(0).to_dict()
    pop=pd.read_csv(PRIVATE/'body_population.csv',dtype={'postId':str,'author':str},keep_default_na=False)
    assert len(pop)==len(f) and pop.postId.is_unique
    book=json.loads((ROOT/'code/classification_codebook_v1.json').read_text())
    protocol=json.loads((ROOT/'results/classification_rebuild_protocol.json').read_text())
    stages={'development':'development_coding.json','calibration':'calibration_coding.json',
            'holdout_A':'holdout_coder_a.json','holdout_B':'holdout_coder_b.json'}
    outputs={}; keys_all={}
    for stage,filename in stages.items():
        role=stage.split('_')[0]
        k=pd.read_csv(PRIVATE/(role+'_keys.csv'),dtype={'postId':str,'author':str},keep_default_na=False)
        assert k.postId.is_unique and k.sample_id.is_unique
        keys_all[role]=k
        d=load_coding(filename)
        outputs[stage]=count_scope(d,k,hit,book)
        outputs[stage]['sample_authors']=k.author.nunique()
        outputs[stage]['median_length']=float(k.clean_text.str.len().median())
        outputs[stage]['role_population_nonempty']=int(((pop.role==role)&(pop.length>0)).sum())
    assert len(set(keys_all['development'].postId)&set(keys_all['calibration'].postId))==0
    assert len(set(keys_all['development'].postId)&set(keys_all['holdout'].postId))==0
    assert len(set(keys_all['calibration'].postId)&set(keys_all['holdout'].postId))==0
    a=load_coding('holdout_coder_a.json'); b=load_coding('holdout_coder_b.json')
    shared=sorted(a)
    assert set(a)==set(b)
    comparison={'n':len(shared), 'both_any_domain':sum(bool(a[x]['domains']) and bool(b[x]['domains']) for x in shared),
                'both_any_function':sum(bool(a[x]['functions']) and bool(b[x]['functions']) for x in shared),
                'both_any_domain_or_function':sum(bool(a[x]['domains'] or a[x]['functions']) and bool(b[x]['domains'] or b[x]['functions']) for x in shared)}
    old0=keys_all['holdout'].loc[~keys_all['holdout'].postId.map(hit), 'sample_id'].tolist()
    comparison['old_no_hit_n']=len(old0)
    comparison['old_no_hit_both_any_domain_or_function']=sum(bool(a[x]['domains'] or a[x]['functions']) and bool(b[x]['domains'] or b[x]['functions']) for x in old0)
    sources=[ROOT/'results/post_features.csv', ROOT/'code/classification_codebook_v1.json', ROOT/'results/classification_rebuild_protocol.json']
    sources += [PRIVATE/(s+'_keys.csv') for s in ['development','calibration','holdout']]
    sources += [PRIVATE/x for x in stages.values()]
    res={'status':'exploratory_previous_ai_codings_only_no_new_labels','stage_protocol':protocol['sampling_scope'],
         'interpretation':'同基座AI编码，非人工或真值；多标签可共现；开发/校准有设计性偏差；留出仅为其作者与去模板抽样框，不能推断全部帖子。',
         'stages':outputs,'holdout_A_B_comparison':comparison,
         'source_sha256':{str(p.relative_to(ROOT)):digest(p) for p in sources}}
    OUT.write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
    h=outputs['holdout_A']; hb=outputs['holdout_B']; hs=h['sample_states']; hbs=hb['sample_states']; no=h['old_no_hit_subset']; nob=hb['old_no_hit_subset']
    cats={x['code']:x for x in h['categories']}; catsb={x['code']:x for x in hb['categories']}
    lines=['# 既有AI正文编码的描述性分析（探索性样本）','','这份记录汇总此前已完成的400条AI编码，不是新一轮全样本语义分类，也没有把旧分类器预测当成真实标签。编码以清理后的正文为单位，内容对象与表达行为分别允许多标签；没有读取图片、视频语音或标签来补出正文含义。','','开发160条刻意兼顾作者与正文长度，校准80条及留出160条来自不同的作者角色；校准与留出排除早先角色及历史检查中的相同模板。开发、校准用于形成和调整编码手册，并非总体代表性样本；留出从其作者角色的881条符合条件不同正文中抽取，只能描述这批抽样范围，不能直接推及5,414条非空正文或全部帖子。160条留出由同一模型基座、不同上下文独立编码两次，下列分别报告A和B，不将两者合成为人工真值。','','| 已编码样本 | 条数 | 作者数 | 正文长度中位数（字符） | 同角色非空正文数 |','| --- | ---: | ---: | ---: | ---: |']
    for stage,label in [('development','开发'),('calibration','校准'),('holdout_A','留出')]:
        x=outputs[stage]; lines.append(f"| {label} | {x['n']} | {x['sample_authors']} | {x['median_length']:g} | {x['role_population_nonempty']} |")
    lines+=['','留出样本中，根据A／B各自编码，内容对象明确的分别为'+f"{hs['content_specified']}／{hbs['content_specified']}条，领域未指明分别为{hs['content_unspecified']}／{hbs['content_unspecified']}条。"+'可读不代表内容对象一定能确定；领域未指明、无法判断和信息不足保留各自状态。','','| 留出内容对象 | A编码帖数 | B编码帖数 |','| --- | ---: | ---: |']
    for code in ('d_exercise','d_body','d_food','d_life','d_tools','d_other'):
        lines.append(f"| {cats[code]['label']} | {cats[code]['positive']} | {catsb[code]['positive']} |")
    lines+=['','| 留出表达行为 | A编码帖数 | B编码帖数 |','| --- | ---: | ---: |']
    functions=[x for x in h['categories'] if x['axis']=='functions']
    for x in functions:
        lines.append(f"| {x['label']} | {x['positive']} | {catsb[x['code']]['positive']} |")
    lines+=['','每列分母都是160条留出正文；上表各类可以共现，因此各类数量不能相加成160，也不能当成全样本主题占比。标签边界及A/B不确定项的具体处理，应参考原编码手册与[原始验证报告](分类测量重建_实证依据与验证报告.md)。','',f"在160条留出正文里，原四项字面规则均未命中的有{no['n']}条。对这部分，编码A／B分别在{no['any_domain_or_function']}／{nob['any_domain_or_function']}条中记录了至少一个内容对象或表达行为；双方都记录至少一项的有{comparison['old_no_hit_both_any_domain_or_function']}条。这表明部分旧规则未覆盖的正文仍能被阅读出其他内容或表达，但不意味着任何一方的每个标签均经人工证实。",'', '以上是同基座模型的既有编码记录。它能展示可观察的分类对象、重叠与边界，不能证明最优分类、全样本覆盖率或类别与点赞的关系。此前字符识别器出现过度检出，尤其无法妥善保留领域未指明状态；本分析没有把它的全量输出作为结果，也没有新增类别回归。', '', '旧字面回归仍回答固定词项与问号的条件关联；旧NMF回归仅为探索性词语成分关联；评论及网络结果使用另一份已采集评论记录。这些结果可以与本文并列，但不能把本样本的AI类别直接套到全量帖子或据此解释旧回归系数。', '', '可审计汇总见 `results/existing_ai_coding_descriptive.json`，生成脚本为 `code/analyze_existing_ai_coding_descriptive.py`。逐条正文、作者、原始ID和编码证据仅保留在本地私有目录。','']
    REPORT.write_text('\n'.join(lines))
    print(json.dumps({'saved':[str(OUT),str(REPORT)],'holdout_comparison':comparison,'holdout_no_old_A':no,'holdout_no_old_B':nob},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
