#!/usr/bin/env python3
"""Create a separate report for v3 AI-assisted expression definitions.

Requires validated full-corpus coding and computed aggregated diagnostics. No
classifier/model is run by this builder; older reports are never overwritten.
"""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'分析报告_表达变量重建版_可编辑.md'
OUT=ROOT/'分析报告_表达细分与共线性版_可编辑.md'
R=ROOT/'results'

def extract(text,start,end):
    if text.count(start)!=1 or text.count(end)!=1:raise ValueError('Non-unique section markers: '+start+' / '+end)
    return text[text.index(start):text.index(end)].strip()+'\n\n'

def f(x):return f'{x:.3f}' if x is not None else '—'

def main():
    src=SOURCE.read_text()
    expr=json.loads((R/'v3_expression_analysis.json').read_text())
    agreement=json.loads((R/'v3_independent_ai_agreement.json').read_text())
    col=json.loads((R/'v3_collinearity_audit.json').read_text())
    oldcol=json.loads((R/'five_expression_collinearity_audit.json').read_text())
    content=json.loads((R/'v2_primary_classification_summary.json').read_text())
    low_support={x['code'] for x in agreement['variables'] if x['low_positive_support']}
    nonempty=expr['coverage']['n_nonempty']; available=expr['coverage']['at_least_one_positive']
    aux=expr['prior_auxiliary_comparison']
    codes=list(expr['variables']);mainmodels=expr['models']['main']
    estimable=[(k,mainmodels[k]) for k in codes if mainmodels[k]['status']=='estimated_exploratory']
    significant=[(k,x) for k,x in estimable if x['q_bh_within_v3_family']<.05]
    if significant:
        finding=(f'九项表达中有{len(significant)}项在本组BH校正后低于5%；'
                 '这些是回顾性探索中的条件关联，不能忽略标签误差或解释为因果。')
        if any(k in low_support for k,_ in significant):
            finding+='其中部分标签在120条双AI盲审中的阳性支持不足，语义可靠性尤其需要人工复核。'
    else:
        finding=('可估计的表达变量经本组BH校正后均未达到5%水平；'
                 '这不等于已证明不存在任何关联。')
    cover=f'''# Keep社区帖子特征与互动反馈

**正文表达细分、点赞关联与评论互动结构**

**摘要**

本研究使用课程提供的9,532条帖子和11,595条去重评论，考察可观察正文中的内容与表达，以及它们与累计点赞的关系，并描述已采集评论的互动结构。原四项词典变量与上一版五组合并变量作为历史对照保留；本版将正文表达进一步细分为行动记录、计划、目标、鼓励、个人体验、对象评价、问候、感谢和互动请求。

在5,414条清理后非空正文中，大模型按冻结手册分批重读4,156条不同正文并回填原帖；模型在{available:,}条中标出至少一项上述表达，不能仅凭该覆盖数判断标签准确。抽取{agreement['n_unique_texts']}条不同正文开展两份同基座AI独立上下文盲审，要求可读状态、阳性与不确定标签全部一致时为{agreement['strict_exact_agreement_including_state_and_unknown']}条。它衡量编码一致性，不是人工准确率。

对数据支持足够的表达变量分别估计探索性点赞回归，控制正文长度、媒体及作者、日期等因素；{finding}主题成分回归仍使用连续权重。评论分析中，4,902次明确回复中89.0%由帖主发给其他用户；互动次数和参与人数描述不同层面。

'''
    ch1=extract(src,'## 1. 研究背景、问题与范围','## 2. 数据来源、清洗与研究方法')
    ch1=ch1.replace('帖子内容对象、表达行为及探索性主题成分与点赞是否存在条件关联？','帖子内容对象、细分表达及探索性主题成分与点赞是否存在条件关联？')
    ch21=extract(src,'### 2.1 数据来源和清理口径','### 2.2 变量定义与研究方法')
    topicmethod=extract(src,'#### 2.2.3 主题分析与连续权重回归','#### 2.2.4 评论文本与互动网络分析')
    commentmethod=extract(src,'#### 2.2.4 评论文本与互动网络分析','## 3. 正文可观察范围、媒体、tag与点赞分布')
    methods=f'''## 2. 数据来源、清洗与研究方法

{ch21}### 2.2 变量定义与研究方法

#### 2.2.1 正文表达变量和模型辅助编码

内容对象沿用此前的运动、身体状态、饮食及具体生活等多标签框架。表达轴按语义进一步区分九项：行动或进度记录、未来行动安排、目标或个人期待、鼓励或行动提醒、自身感受或体验、对象或情境评价、问候或祝愿、感谢或致谢、向他人征询或邀请。同一帖子可同时具有多项，九项也不穷尽所有表达。对鼓励另记录明确指向自己、他人、双方或对象不明；不推断真实关系或人格。

在旧分类基础上重新定义边界：记录与未来计划分开，目标与鼓励分开，自身感受与对象评价分开，问候、感谢与互动请求分别记录。模型不能根据旧标签推导子类：按照冻结手册分84批重读4,156条完全不同的清理后正文，为每个阳性变量保留原文依据，再映射回5,414条非空原帖。没有正文、清理后为空及信息不足不记为语义阴性；仅对已读且能判断的标签区分阳性与阴性，未知单独保存。旧细分中的感悟、建议和题注保留为历史辅助变量，不冒称本轮九项重读结果。

在排除旧开发、试点、盲审及同文重复后，冻结手册再从{agreement['n_eligible_unique_texts']:,}条不同正文中随机抽取{agreement['n_unique_texts']}条，交给两个互不查看答案的AI上下文逐条编码。可读状态一致{agreement['observation_state_exact_agreement']}条；阳性标签集合一致{agreement['positive_label_set_exact_agreement']}条；若同时要求未知标签及状态完全相同，一致{agreement['strict_exact_agreement_including_state_and_unknown']}条。该样本按不同正文而非帖子等概率抽取，也未按作者隔离；这些正文曾在旧版模型分析中出现过。两次同基座AI编码的一致性不是人工信度或准确率，稀少标签的阳性支持尤其有限；独立人工复核尚未完成。

#### 2.2.2 点赞回归与共线性检查

因变量为ln(1+累计点赞数)。每个表达变量单独进入一个回顾性探索回归，比较该变量可判断为有和无的帖子；其余表达可并存但不同时作为该模型的额外控制。模型控制正文长度、有无原始tag、表情数量、课程分享标记、媒体及业务类型、发帖时段、作者和日期固定效应，标准误按作者聚类并作有限样本修正。旧四项词典变量不进入新主模型；它们作为附录B的历史对照。

每项模型只使用该项可判断记录；当阳性与阴性各至少40帖且至少10位作者内部存在变化时估计，未达门槛的类别只作描述。每个规格内对可估计的九项检验共同作BH校正；校正不覆盖此前其他变量设计和探索。另比较剔除各变量样本中最高1%点赞、仅保留至少10帖作者及作者等权三种设定。变量边界在看过此前探索之后确定，不能描述为事前注册，也不依据本次回归p值挑类。

为检查可能同时出现的表达变量是否在数值上重复，将九项均可判断的帖子用于单独的共线性诊断；在实际有支持的标签上，同时放入上述控制项、作者和日期固定效应，检查相关性、设计矩阵秩与VIF。此诊断是一个多变量设计，和正文中每项单独回归不同；低VIF不证明标签的语义有效性。

{topicmethod}{commentmethod}'''
    ch3=extract(src,'## 3. 正文可观察范围、媒体、tag与点赞分布','## 4. 正文内容、表达方式与点赞的关系（RQ2）')
    content_part=extract(src,'### 4.2 内容对象与点赞','### 4.3 表达方式与点赞')
    target=expr['exhortation_target_among_exhort_positive']
    part=f'''## 4. 正文内容、细分表达与点赞的关系（RQ2）

### 4.1 细分变量的覆盖与不确定性

对{nonempty:,}条清理后非空正文的模型重读中，{expr['observation_state_nonempty'].get('readable',0):,}条被判为可读，{expr['observation_state_nonempty'].get('insufficient',0):,}条被判信息不足。模型为{available:,}条标出九项中的至少一项，{expr['coverage']['at_least_two_positive']:,}条同时具有至少两项。{expr['coverage']['no_positive_all_known']:,}条九项均可判断且没有阳性，{expr['coverage']['no_positive_has_unknown']:,}条没有阳性且至少一项未知。无阳性不等于没有任何表达：一般观点、题注和其他可辨认表达并不全部属于这九项，因此九项与上一版五组的覆盖率也不应直接比较为准确性高低。

在没有九项阳性标签的帖子中，有{aux['n_without_v3_positive_but_with_prior_aux']:,}条在上一轮被标记为感悟、题注或建议等辅助表达：其中{aux['of_these_v3_readable']:,}条本轮判为可读，{aux['of_these_v3_insufficient']:,}条本轮判为信息不足。两轮对部分短文本的可读性判断不同；旧辅助标签仅作对照，不能将冲突或未知强行改成九项阳性。

内容对象轴仍使用上一轮模型编码：{content['coverage_comparison']['ai_at_least_one_content']:,}条正文被标出至少一个内容对象。两个轴描述不同方面，数量不能相加；所有数字都是模型赋标签结果，不能等同于分类准确率。

| 表达变量 | 阳性帖数 | 阴性帖数 | 非空正文中该项未知 | 有作者内变化的作者数 |
| --- | ---: | ---: | ---: | ---: |
'''
    for c in codes:
        r=expr['variables'][c]
        part+=f'| {r["label"]} | {r["n_positive"]:,} | {r["n_negative"]:,} | {r["n_unknown_nonempty"]:,} | {r["authors_within_variation"]} |\n'
    part+='\n鼓励阳性帖中的对象标签分布如下，未指明和无法判断保持独立，不强行归入自我或他人：\n\n| 鼓励对象 | 帖数 |\n| --- | ---: |\n'
    for key,label in [('self','明确自我'),('others','明确他人'),('both','明确双方'),('unspecified','未指明'),('uncertain','指向不确定')]:
        part+=f'| {label} | {target.get(key,0):,} |\n'
    part+='\n'+content_part
    part+='### 4.3 九项细分表达与点赞\n\n'
    part+='每项分别使用自身可判断的样本，控制已记录的帖子和作者、日期条件。阳性与阴性组之外的未知记录不进入该项比较；其他表达可以同时出现。各项均为独立模型而非互相调整的同一模型，BH只覆盖本规格中满足支持门槛的变量。变量名后有 * 表示该标签在120条双AI盲审的可比较样本中，双方至少一方标为阳性的正文不足10条；即使全量回归有足够支持，其语义稳定性仍待核实。\n\n'
    part+='| 表达变量 | 可判断帖数／作者 | 阳性帖数 | β | 原始95%区间 | 原始p | 组内BH q |\n| --- | ---: | ---: | ---: | --- | ---: | ---: |\n'
    for c in codes:
        r=mainmodels[c];label=expr['variables'][c]['label']+(' *' if c in low_support else '')
        if r['status']=='estimated_exploratory':
            part+=f'| {label} | {r["n"]:,}／{r["authors"]} | {r["n_positive"]:,} | {f(r["beta"])} | [{f(r["ci_low"])}, {f(r["ci_high"])}] | {f(r["p"])} | {f(r["q_bh_within_v3_family"])} |\n'
        else:part+=f'| {label} | {r["n"]:,}／{r["authors"]} | {r["n_positive"]:,} | — | 支持不足或设计矩阵不满秩 | — | — |\n'
    part+='\n'+finding+' 标签由AI辅助完成，且缺乏统一曝光与观察时长，不能将系数解释成表达导致点赞变化。\n\n'
    plan=mainmodels.get('V3_PLAN',{})
    if plan.get('status')=='estimated_exploratory' and plan['p']<.05 and plan['q_bh_within_v3_family']>=.05:
        plan_review=next(x for x in agreement['variables'] if x['code']=='V3_PLAN')
        part+=(f'例如，“未来行动安排”的点估计为{f(plan["beta"])}，原始p={f(plan["p"])}，'
               f'但组内BH q={f(plan["q_bh_within_v3_family"])}；盲审可比较样本中双方至少一方标阳性的只有'
               f'{plan_review["positive_union_support"]}条，因此不能将这一结果作为稳定发现。\n\n')
    part+='### 4.4 共线性与表达共现\n\n'
    part+=(f'为检查同一帖子同时包含多种表达时是否难以区分变量，我们在九项均可判断的{col["n_complete_all_nine"]:,}帖、'
           f'{col["n_authors"]}位作者中构建同时纳入非恒定且有作者内变化的标签的诊断模型；'
           f'其中{col["at_least_two_positive"]:,}帖被标记至少两项。'
           f'设计矩阵为{col["design_matrix"]["rows"]:,}×{col["design_matrix"]["columns"]}，'
           f'秩为{col["design_matrix"]["rank"]}。')
    if col['design_matrix']['full_rank']:
        v=[x['vif_full_design'] for x in col['variables'] if x['vif_full_design'] is not None]
        part+=f'受检变量在完整设计中的VIF范围为{min(v):.2f}—{max(v):.2f}。'
    else:part+='设计矩阵未满秩，无法为全部受检变量给出有限VIF。'
    part+='该检查同时考虑其他标签及作者、日期等控制项；若某标签没有正反例或作者内变化则不纳入诊断。低支持类别即使能计算VIF，也不能因此认为其回归有足够支持。\n\n| 表达变量 | 阳性帖数 | 作者内有变化人数 | 完整模型VIF |\n| --- | ---: | ---: | ---: |\n'
    for r in col['variables']:
        v=('未定义（矩阵不满秩）' if r['included'] else '未纳入（缺少变异）') if r['vif_full_design'] is None else f'{r["vif_full_design"]:.2f}'
        part+=f'| {r["label"]} | {r["positive_posts"]:,} | {r["authors_with_within_variation"]} | {v} |\n'
    part+=(f'\n历史五组合并变量在5,180条共同可判断帖子中的完整模型VIF为'
           f'{min(x["vif_full_design"] for x in oldcol["variables"]):.2f}—{max(x["vif_full_design"] for x in oldcol["variables"]):.2f}；'
           '其结果不能替代上述九项检查。共线性不等于语义重叠，低VIF也不能验证类别含义。\n\n')
    part+='### 4.5 表达回归的稳健性\n\n'
    part+='分别剔除该变量样本中点赞最高1%的帖子、只保留该样本至少10帖的作者、以及按作者等权重估计；各项模型的可用样本可能不同。表内为点估计，完整区间和逐规格BH结果见 `results/v3_expression_analysis.json`。\n\n'
    part+='| 表达变量 | 主模型 β | 剔除高赞 β | 保留至少10帖作者 β | 作者等权 β |\n| --- | ---: | ---: | ---: | ---: |\n'
    specs=['main','drop_top_1_percent_likes','authors_min_10_in_base_sample','author_equal_weight']
    for c in codes:
        values=[expr['models'][s][c] for s in specs]
        part+='| '+expr['variables'][c]['label']+' | '+' | '.join(f(x.get('beta')) for x in values)+' |\n'
    part+='\n这些对照不能修复分类误差或没有记录到的曝光；方向变化应结合原始区间及各规格BH结果理解，不能仅凭点估计判断稳定性。\n\n'
    part+='### 4.6 双AI盲审能说明什么\n\n'
    part+='下表按每个标签展示两次编码均可判断时的阳性一致情况；未知被单独排除。低阳性支持的比例很不稳定，同一模型基座还可能共同出错。\n\n| 表达变量 | 双方均阳性 | 仅一方阳性 | 排除未知 | 阳性一致率 |\n| --- | ---: | ---: | ---: | ---: |\n'
    for row in agreement['variables']:
        rate='—' if row['positive_agreement'] is None else f'{row["positive_agreement"]*100:.1f}%'
        part+=f'| {row["label"]} | {row["both_positive"]} | {row["a_positive_only"]+row["b_positive_only"]} | {row["n_excluded_unknown"]} | {rate} |\n'
    t=agreement['exhortation_target'];part+=(f'\n两份编码都认定为鼓励的{t["both_coders_identified_exhort"]}条中，'
        f'对象状态完全一致{t["target_exact_agreement"]}条。该检查包含“未指明”和“不确定”状态，不能称为对象判断准确率。'
        '具体例子和分歧应继续由独立人工盲审，不能将该样本再用于修改码本后宣称独立验证。\n\n')
    ch5=extract(src,'## 5. 帖子主题成分与点赞的关系（RQ2）','## 6. 评论内容与直接回复分析（RQ3）')
    ch6=extract(src,'## 6. 评论内容与直接回复分析（RQ3）','## 7. 评论互动网络分析（RQ3）')
    ch7=extract(src,'## 7. 评论互动网络分析（RQ3）','## 8. 研究结论')
    conclusion=f'''## 8. 研究结论

### 8.1 研究结论

RQ1：正文可观察范围随内容形式和作者变化，点赞呈长尾；缺少正文不等于原帖没有内容。

RQ2：模型对{nonempty:,}条非空正文完成细分编码，{available:,}条至少有一项九类表达标签。{finding}共线性诊断和双AI复核结果需与模型的语义误差、未知状态及作者支持一起理解；连续主题权重回归仍是探索性补充。

RQ3：已采集评论中的词项随角色分布不同，明确回复主要由帖主发给其他用户；互动事件数和不同发送者人数反映不同接收形态。

### 8.2 研究局限与展望

未观察的正文、图片、视频语音、曝光及累计观察时长限制了可比性，作者和日期固定效应不能消除所有随帖子变化的差异。九项细分标签由模型分批阅读产生，同基座AI一致性不是人工准确率；类别定义、作者选择和多重模型均属回顾性探索。应优先对随机一致样本、分歧、未知和稀少类别进行独立人工盲审，再检验变量是否可靠、是否需要调整。

'''
    appA=extract(src,'## 附录A　评论、网络与媒体口径','## 附录B　原四项字面变量的历史结果')
    appB=extract(src,'## 附录B　原四项字面变量的历史结果','## 参考文献')
    prior=extract(src,'### 4.3 表达方式与点赞','### 4.5 分类结果应怎样理解')
    prior=prior.replace('### 4.3 表达方式与点赞','### C.1 五组合并表达的历史模型',1).replace('### 4.4 表达变量的稳健性检验','### C.2 历史五组的稳健性检验',1)
    appC='## 附录C　上一版五组表达变量的历史对照\n\n这些模型使用上一轮合并标签，不是本轮九项细分变量；保留供比较，不将其稳健性结果套用到新变量。\n\n'+prior
    refs=src[src.index('## 参考文献'):].strip()+'\n'
    OUT.write_text(cover+ch1+methods+ch3+part+ch5+ch6+ch7+conclusion+appA+appB+appC+refs)
    print(OUT)

if __name__=='__main__':main()
