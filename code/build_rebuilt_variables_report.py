#!/usr/bin/env python3
"""Build a separate report: rebuilt semantic variables are the RQ2 focus.

Reads existing frozen summaries and an existing manuscript. Does not reestimate
models or send post-level data anywhere. Historical dictionary results are kept
in Appendix B. All new semantic results remain AI-assisted and exploratory.
"""
from pathlib import Path
import json
import re
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '分析报告_正文双轴分类版_可编辑.md'
OUTPUT = ROOT / '分析报告_表达变量重建版_可编辑.md'
RESULTS = ROOT / 'results'


def section(text, start, end):
    if text.count(start) != 1 or text.count(end) != 1:
        raise ValueError(f'Expected one section marker: {start} / {end}')
    return text[text.index(start):text.index(end)].strip() + '\n\n'


def pretty(value):
    return f'{value:.3f}'


def main():
    src = SOURCE.read_text()
    primary = json.loads((RESULTS / 'v2_primary_classification_summary.json').read_text())
    expr = json.loads((RESULTS / 'rebuilt_expression_groups.json').read_text())
    topics = json.loads((RESULTS / 'topic_continuous_without_legacy.json').read_text())
    fresh = json.loads((RESULTS / 'v2_fresh_blind_agreement.json').read_text())
    assert not expr['legacy_four_used_as_model_controls']
    assert not topics['old_four_lexical_indicators_in_model']
    coverage = primary['coverage_comparison']
    states = primary['domain_state_nonempty']
    content_codes = ['C_EXERCISE', 'C_BODY', 'C_FOOD', 'C_LIFE']
    content = [r for r in primary['regression']['content']['coefficients'] if r['code'] in content_codes]
    assert len(content) == 4
    # Define the four main labels based on semantic review, not p values, after
    # prior exploratory analysis; this is retrospective, not preregistration.
    q4 = multipletests([r['p'] for r in content], method='fdr_bh')[1]
    content_q = dict(zip([r['code'] for r in content], q4))
    model_order = ['R_RECORD', 'R_EVALUATE', 'R_PLAN_ENCOURAGE', 'R_SOCIAL', 'R_REFLECT']
    expr_main = expr['models']['main']
    assert set(model_order) == set(expr_main)
    topic_models = topics['models']
    tmain = next(r for r in topic_models if r['minimum_topic_posts_per_author'] == 1)
    assert topics['n_posts'] == 2470 and topics['reference_topic'] == 2
    topic_by_id = {int(r['term'].split('_')[1]):r for r in tmain['coefficients']}
    assert set(topic_by_id) == {0, 1, 3, 4}

    cover = f'''# Keep社区帖子特征与互动反馈

**正文双轴分类、点赞关联与评论互动结构**

**摘要**

本研究使用课程提供的9,532条帖子和11,595条去重评论，考察帖子正文的内容对象、表达方式与累计点赞的关系，并描述已采集评论的互动结构。正文分类区分“谈什么”和“怎样表达”，同一帖子可以同时具有多个标签；原四项固定词项与问号变量作为历史对照保留在附录B。

5,414条帖子清理后有非空正文。按照冻结的编码手册，大模型分84批阅读4,156条去重正文，再将结果映射回原帖。模型为{coverage['ai_at_least_one_content']:,}条标出至少一个内容对象，为{coverage['ai_at_least_one_expression']:,}条标出至少一种表达行为；两者可以重叠。表达轴覆盖很广，也可能受到类别定义较宽或模型过度赋类影响，不能只凭覆盖率认定分类准确。

对主要内容对象及五组表达变量分别估计探索性点赞回归，控制正文长度、媒体形式、发帖时段、作者与日期等因素，不再把原四项词典变量作为主模型控制项。模型标签尚未经独立人工验证，结果反映条件关联，不能解释为内容导致点赞变化。主题成分回归使用连续权重，四项成分联合检验p={tmain['joint_topic_p']:.3f}，未提供明确的额外关联证据。

评论分析中，在4,902次明确回复中，89.0%由帖主发给其他用户；接收事件数相近的两个账号，其不同发送者人数分别为53和1,091。互动次数和参与人数描述不同层面，均不直接等同于真实社会支持或关系质量。

'''
    chapter1 = section(src, '## 1. 研究背景、问题与范围', '## 2. 数据来源、清洗与研究方法')
    chapter1 = chapter1.replace('本报告把解释限制在已记录的字面特征、点赞与互动结构。',
                                '本报告结合正文中的内容对象、表达行为、点赞和互动结构，讨论样本中可观察的关联。')
    chapter1 = chapter1.replace('正文表达线索及探索性主题成分与点赞是否存在条件关联？ | 词典回归、双轴分类与探索性主题回归',
                                '帖子内容对象、表达行为及探索性主题成分与点赞是否存在条件关联？ | 双轴分类、分项回归与探索性主题回归')
    ch2_1 = section(src, '### 2.1 数据来源和清理口径', '### 2.2 变量定义与研究方法')
    ch2_1 = ch2_1.replace('没有正文的全样本记录将字面特征设为0，并加入原始正文可见标记；该处理描述记录状态，不能恢复缺失内容或校正非随机缺失。',
                          '新分类只判断清理后非空正文；原始正文不可见或清理后为空单独记录，不能当作没有任何内容或表达。原全样本词典模型的缺失处理仅作为附录B中的历史对照。')
    comment_method = section(src, '#### 2.2.4 评论文本与互动网络分析', '#### 2.2.5 大模型辅助的正文双轴分类')
    methods = f'''## 2. 数据来源、清洗与研究方法

{ch2_1}### 2.2 变量定义与研究方法

#### 2.2.1 正文内容与表达变量

为更充分地利用未被清理掉的正文，本研究将正文分析分成“内容对象”和“表达行为”两个轴。内容轴的主要变量是运动与身体活动、身体状态或外形、饮食与营养、具体生活与关系话题；模型也记录工具与其他明确内容，但由于语境边界及样本支持问题，不将它们作为主要回归变量。不同内容可以同时出现。

表达轴将既有细标签按语义合并为五组：记录或呈现、体验或评价、计划期待或鼓励、问候感谢或邀请交流、感悟或观点。每组都允许与其他组同时出现。“信息解释或可执行建议”另作描述，不纳入主要回归；商品供给及其他开放槽因样本或定义限制也不作为主要回归变量。这五组在查看试点编码与边界后根据研究问题合并，不依据点赞结果或p值选择，属于回顾性探索。

模型依照冻结手册分84批阅读4,156条匿名、去重的清理正文，并为每个阳性标签记录原文依据；完全相同的正文只编码一次，再映射回5,414条非空原帖。模型未接收作者身份、点赞、原始tag或旧回归结果。任一子标签明确为阳性时合并组记为阳性；没有阳性但存在子标签不确定时记为未知，只有可判断且所有子标签均为阴性时才记为阴性。无正文、清理后为空与信息不足均不当作语义阴性。

在排除既有400条编码及前期规则抽查记录后，随机抽取90条不同正文，由独立上下文再次盲编码。两次阳性内容标签集合完全一致{fresh['positive_label_set_agreement']['content']}条、表达标签集合完全一致{fresh['positive_label_set_agreement']['expression']}条；进一步要求观察状态和不确定标签一致后，分别为{fresh['strict_agreement']['content']}条和{fresh['strict_agreement']['expression']}条。五组合并依据已查看的试点进行，不能将同基座AI的一致性当作独立人工信度或准确率；细分类和语境仍需人工复核。完整定义见《帖子内容与表达_双轴分类手册_v2》。

#### 2.2.2 点赞回归与适用样本

因变量为ln(1+累计点赞数)。每个主要内容或表达变量单独进入一个回归：比较该标签出现与未出现的合格帖子；其他内容或表达标签可能并存，未作为该模型的额外控制项。模型控制正文长度、有无原始tag、表情数量、课程分享标记、媒体形式、业务类型、北京时间发帖时段、作者固定效应与发帖日期固定效应；标准误按作者聚类，并作有限样本修正[5]。这些比较不能消除随帖子变化的曝光与观察时长差异。

内容回归限制在正文可读且领域明确、该维度没有不确定标签的3,302帖；每组表达回归使用该组标签可判断的帖子，因此样本量略有不同。按正负两组各至少40帖、至少10位作者内部存在该变量变化的规则检查支持情况。内容轴按四项主要变量的四个独立回归结果作Benjamini–Hochberg校正，工具类因语境一致性问题而未纳入主结果；表达轴按五个独立回归结果校正[6]。变量选择依据语义与一致性，不依据p值；选择发生在已有探索之后，并非事前注册。这些校正不覆盖全部模型与分析过程。未验证的AI语义标签及完整案例选择均限制结果解释。旧四项词典变量不进入这些主模型；其原有结果见附录B。

#### 2.2.3 主题分析与连续权重回归

对至少含3个有效词的正文构建TF-IDF矩阵，再用非负矩阵分解（NMF）提取五个词语成分。成分贡献经尺度调整并逐帖归一化，五项权重合计为1；一篇帖子可同时具有多个成分。分布图按每帖权重最高的成分概括，**主题回归仍使用连续权重**。带截距时省略成分2为参照，以避免权重和为1造成完全共线；系数描述在其他权重和控制项不变时，某一成分权重替代成分2权重的条件差异。重新估计的主题模型控制正文长度、元数据及作者和日期固定效应，不再纳入旧四项词典变量。主题权重是模型内部相对贡献，不是经过验证的语义类别概率。

{comment_method}'''
    chapter3 = section(src, '## 3. 正文可观察范围、媒体、tag与点赞分布', '## 4. 文本表达线索与点赞的关系（RQ2）')
    chapter3 = chapter3.replace('全样本回归以全部帖子为比较范围；原始正文可见和清理后非空口径同时列出。',
                                '新分类与回归主要使用实际可读的正文；原全样本词典模型及不同正文口径保留为历史对照。')

    ch4 = f'''## 4. 正文内容、表达方式与点赞的关系（RQ2）

### 4.1 正文分类的覆盖与边界

对5,414条清理后非空正文进行模型辅助编码后，5,228条被判为可读，186条信息不足。按内容轴，{states['specified']:,}条领域状态明确，{states['unspecified']:,}条可读但内容对象未指明，{states['uncertain']:,}条领域判断不确定，其余不可判断。部分领域状态不确定的帖子仍有其他明确对象标签，所以至少有一项内容标签的帖数（{coverage['ai_at_least_one_content']:,}）略高于领域状态明确的帖数。{coverage['ai_at_least_one_expression']:,}条有至少一种表达行为，内容与表达可以同时出现。

原四项规则未命中的{coverage['old_no_literal_match']:,}条非空正文中，模型为{coverage['old_missed_with_ai_expression']:,}条标出至少一种表达行为，其中{coverage['old_missed_with_ai_content']:,}条也有至少一个内容对象。这说明新框架可以描述旧词典未捕捉到的部分文字，但两个框架观察角度不同；模型有标签不等于语义判断已被证实正确。表达轴覆盖几乎全部可读文本，可能与分类范围宽或过度赋类有关。

| 内容对象 | 模型标记帖数 | 占5,414条非空正文 |
| --- | ---: | ---: |
'''
    for row in primary['descriptive']['content']:
        ch4 += f'| {row["label"]} | {row["post_count"]:,} | {row["post_count"]/5414*100:.1f}% |\n'
    ch4 += '\n| 表达变量 | 包含的原细标签 | 模型标记帖数 | 该变量在非空正文中未知数 |\n| --- | --- | ---: | ---: |\n'
    parts = {'R_RECORD':'行动、进度或事件记录；题注或景象描写',
             'R_EVALUATE':'体验或对象评价', 'R_PLAN_ENCOURAGE':'计划、目标或期待；动员或自我提醒',
             'R_SOCIAL':'问候、祝愿或感谢；联络邀请或向他人征询', 'R_REFLECT':'议论、格言或价值主张'}
    for code in model_order:
        row=expr['summary'][code]
        ch4 += f'| {row["label"]} | {parts[code]} | {row["n_positive"]:,} | {row["n_unknown_nonempty"]:,} |\n'
    ch4 += '''
同一帖子可以在每个轴上同时命中多个变量，表中数量不能相加。计划与鼓励合并后不等于作者具有自律人格；问候、感谢或邀请也不表示已经发生互助。信息解释与建议在149条正文中被标记，考虑到双模型复核中的支持量及一致性有限，暂不进入主要回归。

### 4.2 内容对象与点赞

为比较不同内容对象与点赞的关系，在领域明确且内容标签无不确定项的3,302帖、90位作者中，分别对四个主要内容变量估计回归。每次比较该标签出现与未出现的合格帖子；其他内容标签可以同时出现。控制正文长度、媒体形式、原始tag有无、表情数量、课程分享标记、业务类型、发帖时段以及作者和日期固定效应，标准误按作者聚类。以下q值对四个独立回归中的四项检验作BH校正；工具类因语境一致性问题不作为主结果展示。变量选择是回顾性的，校正不覆盖其他模型探索。

| 内容对象 | 标记帖数 | 系数 β | 原始95%区间 | 原始p | 四项BH q |
| --- | ---: | ---: | --- | ---: | ---: |
'''
    for row in content:
        ch4 += f'| {row["label"]} | {row["n_positive"]:,} | {pretty(row["beta"])} | [{pretty(row["ci_low"])}, {pretty(row["ci_high"])}] | {pretty(row["p"])} | {pretty(content_q[row["code"]])} |\n'
    ch4 += '''
这四项在各自模型中的原始区间均跨零，四项BH校正后也均未达到5%水平。当前数据未提供足够证据判断这些内容对象与点赞存在稳定关联，不能把不显著理解为已经证明完全没有差异。

### 4.3 表达方式与点赞

为观察正文怎样表达与点赞的关系，分别估计五个表达变量；每项只纳入该项可判断的帖子，故各模型样本数略有不同。每个变量分别回归，其他表达标签允许并存；控制项与内容模型一致。下表q值对五个独立回归中的五项检验共同进行BH校正。

| 表达变量 | 帖数／作者数 | 阳性帖数 | 系数 β | 原始95%区间 | 原始p | 五项BH q |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
'''
    for code in model_order:
        row=expr_main[code]; label=expr['group_definitions'][code]['label']
        ch4 += f'| {label} | {row["n"]:,}／{row["authors"]} | {row["n_positive"]:,} | {pretty(row["beta"])} | [{pretty(row["ci_low"])}, {pretty(row["ci_high"])}] | {pretty(row["p"])} | {pretty(row["q_bh_within_five_groups"])} |\n'
    ch4 += '''
五项表达变量的原始区间均跨零，五项BH校正后均未达到5%水平。这些结果说明模型没有提供明确的稳定关联证据；分类由AI辅助完成、曝光与累计观察时长未知，不能将结果理解为表达方式对点赞的因果效果。

### 4.4 表达变量的稳健性检验

为了检查结果是否受少数高赞帖子或高产作者影响，我们对每个表达变量分别比较原模型、剔除该变量合格样本中点赞最高1%的帖子、仅保留该样本内至少发10帖的作者，以及作者等权的回归。下表为各模型的点估计；高赞阈值和可用样本因变量而略有不同。

| 表达变量 | 原模型 β | 剔除高赞 β | 剔除少帖作者 β | 作者等权 β |
| --- | ---: | ---: | ---: | ---: |
'''
    names=['main','drop_top_1_percent_likes','authors_min_10_in_base_sample','author_equal_weight']
    for code in model_order:
        vals=[expr['models'][name][code] for name in names]
        ch4 += f'| {expr["group_definitions"][code]["label"]} | '+' | '.join(pretty(v['beta']) for v in vals)+' |\n'
    ch4 += '''
剔除高赞帖和少帖作者后，五项点估计方向与原模型相同；作者等权时，“感悟或观点”由负转正，其他四项方向保持一致，其中“计划、期待或鼓励”的估计更接近零。各设定内五项BH校正后均未达到5%水平；这些比较不消除模型标注误差，也不能替代对内容变量开展对应的稳健性分析。

### 4.5 分类结果应怎样理解

新变量让更多帖子能从内容或表达角度被描述，但类别是研究者与模型共同使用的操作化框架，不是帖子天然且唯一的类型。90条不同正文的第二次AI盲编码中，要求状态、不确定标签和阳性集合都一致时，内容轴一致62条、表达轴一致61条；问候邀请及部分工具、建议类的阳性样本较少，稳定性还需要独立人工核对。完整样本的高覆盖和可追溯证据不等于分类准确，短文本、反问、对象不明与重复模板尤其需要检查。

'''
    chapter5 = section(src, '## 5. 帖子主题成分与点赞的关系（RQ2）', '## 6. 评论内容与直接回复分析（RQ3）')
    ch5_start = section(chapter5, '## 5. 帖子主题成分与点赞的关系（RQ2）', '### 5.2 使用连续权重进行主题回归')
    ch5_start = ch5_start.replace('词典只能识别预先列出的用词。为了补充观察正文中反复出现的词语组合，',
                                  '为了从另一角度补充观察正文中反复出现的词语组合，')
    ch5 = ch5_start + f'''### 5.2 使用连续权重进行主题回归

为检验词语成分与点赞的关联，在2,470条有效正文中保留各成分的连续权重，并控制正文长度、媒体、发帖时段和作者、日期固定效应等；重新估计时不再控制旧四项词典变量。五项权重之和为1，带截距时省略成分2作为参照；每项系数表示该成分替代成分2同等权重的条件差异，10个百分点的替代对应系数的0.1倍。

| 成分（旧名称，仅供识别） | 连续权重 β | 原始95%区间 | 原始p | 四项BH q |
| --- | ---: | --- | ---: | ---: |
'''
    names_topic = {0:'靠墙静蹲',1:'骑行',2:'运动训练交流',3:'跑步打卡',4:'生活感悟与问候'}
    for i in range(5):
        if i == 2:
            ch5 += f'| 成分2（{names_topic[i]}） | 参照 | 不适用 | 不适用 | 不适用 |\n'
        else:
            r=topic_by_id[i]
            ch5 += f'| 成分{i}（{names_topic[i]}） | {pretty(r["coef"])} | [{pretty(r["ci_low"])}, {pretty(r["ci_high"])}] | {pretty(r["p"])} | {pretty(r["q_bh"])} |\n'
    ch5 += f'''
四项成分联合检验p={tmain['joint_topic_p']:.3f}，四项BH校正后均未达到5%水平，因此不能据此对真实内容类型的点赞表现排序。回归区间以既有成分为给定输入，没有纳入主题模型估计与语义命名的不确定性。

### 5.3 剔除少帖作者后的稳健性检验

为检查主题子样本中少帖作者的影响，按每位作者在主题子样本中的最低入模帖数重新估计连续权重模型。

| 每位作者至少入模帖数 | 保留帖数／作者数 | 成分联合检验p |
| --- | --- | ---: |
'''
    for r in topic_models:
        ch5 += f'| {r["minimum_topic_posts_per_author"]} | {r["n"]:,}／{r["authors"]} | {r["joint_topic_p"]:.3f} |\n'
    ch5 += '''
各门槛下联合检验仍未显示明确关联；但最高门槛只保留48位作者。该检查不能解决成分命名、覆盖和作者模板对主题结构的影响。

'''
    chapter6 = section(src, '## 6. 评论内容与直接回复分析（RQ3）', '## 7. 评论互动网络分析（RQ3）')
    chapter7 = section(src, '## 7. 评论互动网络分析（RQ3）', '## 8. 研究结论')
    conclusion = f'''## 8. 研究结论

### 8.1 研究结论

RQ1：可见正文随内容形式与作者变化，点赞呈长尾；不能把没有采到正文解释为帖子原本没有内容。

RQ2：模型辅助分类为{coverage['ai_at_least_one_content']:,}条非空正文标出至少一个内容对象、为{coverage['ai_at_least_one_expression']:,}条标出至少一种表达行为。四项主要内容变量与五组表达变量分别估计的条件关联在组内BH校正后均未达到5%水平；这不证明类别完全没有差异。主题连续权重模型的联合检验p={tmain['joint_topic_p']:.3f}，同样未给出明确的额外关联证据。上述结果尚受AI分类误差和不完整曝光信息限制。

RQ3：已采集评论中的词项随角色分布不同，明确回复主要由帖主发给其他用户；互动事件数和不同发送者人数反映不同的接收形态。网络互惠与线程参与也各自描述不同层面的连接。

### 8.2 研究局限与展望

正文缺失、未观察的图片与视频语音、抽样机制及累计观察时长未知限制了结果的适用范围；作者和日期固定效应不能解决随帖变化的曝光差异。双轴标签来自大模型分批阅读，同基座双次编码并非人工准确率验证；五组表达是看过试点后的回顾性合并，题注、短帖及含糊对象等边界仍需人工盲审。表达稳健性结果不能推及内容模型，探索性模型的多重比较也没有覆盖全部研究选择。

后续应优先让独立编码者复核有分歧、未知与模型一致的随机样本，检查各类标签边界及过度赋类；若获得统一观察窗口和曝光数据，再重新评估内容、表达与反馈的关系。

'''
    appendix_a = '## 附录A　评论、网络与媒体口径\n\n'
    appendix_a += section(src, '### A.3 评论配对、网络与时间口径', '### A.4 媒体分组的完整描述数值').replace('### A.3','### A.1',1)
    appendix_a += section(src, '### A.4 媒体分组的完整描述数值', '## 参考文献').replace('### A.4','### A.2',1)
    old_definition = section(src, '#### 2.2.1 正文文本分析', '#### 2.2.2 点赞回归与正文口径')
    old_definition = old_definition.replace('#### 2.2.1 正文文本分析', '### B.1 旧四项字面规则的定义', 1)
    old_definition = old_definition.replace('本研究不试图穷尽帖子的全部表达方式，而是结合研究问题，使用四项可从正文直接识别的语言线索：',
                                            '旧模型并未试图穷尽帖子全部表达，而是使用四项可从正文识别的语言线索：', 1)
    old_definition = old_definition.replace('我们把它们作为文本表达若干方面的操作化测量，而非完整的表达风格分类；',
                                            '旧模型将它们作为局部字面线索，而非完整的表达风格分类；', 1)
    old_definition = old_definition.replace('本版仅将它们沿用为固定、可复算的探索性操作指标；',
                                            '旧分析将它们沿用为固定、可复算的探索性操作指标；', 1)
    old = section(src, '### 4.1 原始均值有差异，但词典只能覆盖部分表达', '### 4.5 新分类：正文中可以观察到哪些内容与表达')
    for a,b in [('### 4.1','### B.2'),('### 4.2','### B.3'),('### 4.3','### B.4'),('### 4.4','### B.5')]:
        old=old.replace(a,b,1)
    old = old.replace('见下表及附录A。','见下表及附录B.6。')
    old = old.replace('RQ2的结论因而必须限定为这些规则的关联，不能概括全部内容的作用。',
                      '旧词典模型的结论因而必须限定为这些规则的关联，不能概括全部内容的作用。')
    old = old.replace('本轮正式问题聚焦可观察的固定字面特征，三种正文口径并列解释。', '历史词典分析中，三种正文口径并列解释。')
    oldA1 = section(src, '### A.1 三种既有正文口径的五项结果', '### A.2 稳健性分析补充结果').replace('### A.1','### B.6',1)
    oldA2 = section(src, '### A.2 稳健性分析补充结果', '### A.3 评论配对、网络与时间口径').replace('### A.2','### B.7',1)
    oldA2 = oldA2.replace('主分析的多重检验结果列于A.1。','历史词典模型的多重检验结果列于B.6。')
    appendix_b = ('## 附录B　原四项字面变量的历史结果\n\n'
                  '本附录保留原四项词典与问号变量的模型、图表和稳健性检查，'
                  '它们与正文中新分类模型使用不同变量与样本，不能将旧模型的结论直接套用到新变量。\n\n'
                  + old_definition + old + oldA1 + oldA2)
    refs = src[src.index('## 参考文献'):]
    doc = cover + chapter1 + methods + chapter3 + ch4 + ch5 + chapter6 + chapter7 + conclusion + appendix_a + appendix_b + refs
    # Original 5–8 move from the body to Appendix B; all references, captions
    # and alt text are changed in a single pass to avoid cascading substitutions.
    renumber = {1:1,2:2,3:3,4:4,9:5,10:6,11:7,12:8,13:9,14:10,5:11,6:12,7:13,8:14}
    doc = re.sub(r'图(\d+)', lambda m:'图'+str(renumber[int(m.group(1))]), doc)
    assert '主题回归仍使用连续权重' in doc
    assert len(re.findall(r'!\[图\d+\]\(',doc)) == 14
    assert 'self_discipline' not in doc
    OUTPUT.write_text(doc)
    print(OUTPUT)


if __name__ == '__main__':
    main()
