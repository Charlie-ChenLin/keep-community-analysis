#!/usr/bin/env python3
"""Create a new editable report from completed, validated direct-AI coding.

No classifier or statistical model is run here. Prior reports are not modified.
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '分析报告_表达特征核实版_可编辑.md'
OUT = ROOT / '分析报告_正文双轴分类版_可编辑.md'
RESULT = ROOT / 'results/v2_direct_classification_summary.json'
FRESH = ROOT / 'results/v2_fresh_blind_agreement.json'


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Expected a unique insertion point: ' + old)
    return text.replace(old, new, 1)


def main():
    result = json.loads(RESULT.read_text())
    fresh = json.loads(FRESH.read_text())
    source = SOURCE.read_text()
    n = result['n_nonempty']
    states = result['observation_state_nonempty']
    domains = result['domain_state_nonempty']
    coverage = result['coverage_comparison']
    abstract = (f'在保留原有字面特征、主题成分和评论分析的基础上，本研究增加正文双轴分类。'
                f'按照冻结手册，由大模型分批阅读去重后的正文并辅助编码，再映射回{n:,}条清理后非空帖子。'
                f'分类区分内容对象和表达行为，允许并存，也保留信息不足或内容未指明的记录。'
                f'这些是模型辅助编码结果，尚未经过独立人工验证。\n\n')
    marker = '## 1. 研究背景、问题与范围'
    source = replace_once(source, marker, abstract + marker)
    source = source.replace('词典回归、稳健性检验与主题回归；第4—5章',
                            '词典回归、双轴分类与探索性主题回归；第4—5章')
    methods = (
        '#### 2.2.5 大模型辅助的正文双轴分类\n\n'
        '为更充分地利用未被清理掉的正文，我们在保留既有结果的同时增加内容对象和表达行为两个分类轴。'
        '内容轴区分运动与身体活动、身体状态、饮食、具体生活、工具与其他明确内容；'
        '表达轴包括记录、体验与评价、计划、鼓励、建议、感悟、问候等。'
        '同一帖子可以有多个内容和表达标签；不能判断的内容单独保留未知。\n\n'
        '研究以清理后的完整正文为单位，完全相同的正文只编码一次。大模型依照冻结的编码手册，'
        '分84批阅读4,156条匿名正文，'
        '为每个阳性标签记录可在正文中找到的文字依据；随后按完全相同的正文映射回每条原帖。'
        '模型编码时不提供点赞、作者身份、原始话题标签或旧模型结果。程序检查编号完整、标签合法及证据确实出现在正文中；'
        '这些检查不能代替语义准确性检验。原始正文缺失和清理后为空单独保留，不能把它们记为各分类均不存在。\n\n'
        f'在排除既有400条编码及前期规则抽查记录后，抽取{fresh["n"]}条不同正文，'
        f'另由独立上下文重新盲编码；两次编码的阳性内容标签集合完全一致{fresh["positive_label_set_agreement"]["content"]}条，'
        f'阳性表达标签集合完全一致{fresh["positive_label_set_agreement"]["expression"]}条。'
        f'进一步要求观察状态和不确定标签也一致，内容轴为{fresh["strict_agreement"]["content"]}条，'
        f'表达轴为{fresh["strict_agreement"]["expression"]}条。'
        '该抽查按不同正文而非原帖等概率抽样。'
        '它显示一些类别边界仍有分歧；补充抽查还发现，有些身体状态或工具标签依赖的语境不足。'
        '两次均为AI编码，不能解释为独立人工信度或准确率。'
        '完整分类手册见《帖子内容与表达_双轴分类手册_v2》，'
        '逐帖原文与证据仅保留在本地私有目录。\n\n')
    source = replace_once(source, '## 3. 正文可观察范围、媒体、tag与点赞分布',
                          methods + '## 3. 正文可观察范围、媒体、tag与点赞分布')
    rows = []
    for fam, title in [('content', '内容对象'), ('expression', '表达行为')]:
        for item in result['descriptive'][fam]:
            rows.append(f'| {title} | {item["label"]} | {item["post_count"]:,} | '
                        f'{item["post_count"] / n * 100:.1f}% | {item["uncertain_count"]:,} |')
    classification = (
        '### 4.5 新分类：正文中可以观察到哪些内容与表达\n\n'
        f'对{n:,}条清理后非空正文进行模型辅助编码后，'
        f'{states.get("readable", 0):,}条被判为可读，{states.get("insufficient", 0):,}条信息不足。'
        f'按内容轴，{domains.get("specified", 0):,}条的领域状态为明确，'
        f'{domains.get("unspecified", 0):,}条可读但内容对象未指明，'
        f'{domains.get("uncertain", 0):,}条内容判断不确定；其余不可判断。'
        '内容对象未指明的帖子仍可能有可识别的表达行为。\n\n'
        f'按模型编码，{coverage["ai_at_least_one_content"]:,}条有至少一项明确的内容对象，'
        f'{coverage["ai_at_least_one_expression"]:,}条有至少一项表达行为；'
        f'分别有{coverage["ai_multiple_content"]:,}条和{coverage["ai_multiple_expression"]:,}条在对应轴上得到两项及以上标签。'
        '其中少数领域状态为不确定的帖子，仍可对正文中的其他明确对象赋予标签，因而该数与领域状态为明确的数量不同。'
        '两个轴可以同时有标签，不能将上述数量相加。表达轴几乎覆盖全部可读文本，'
        '可能与分类范围宽或过度赋类有关，不能仅凭覆盖率判断其准确。\n\n'
        f'旧四项规则未命中的{coverage["old_no_literal_match"]:,}条非空正文中，'
        f'模型为{coverage["old_missed_with_ai_any"]:,}条（{coverage["old_missed_with_ai_any"] / coverage["old_no_literal_match"] * 100:.1f}%）标出至少一个表达行为，'
        f'其中{coverage["old_missed_with_ai_content"]:,}条也标出至少一个内容对象；'
        f'另有{coverage["old_missed_without_ai_any"]:,}条未获阳性标签。'
        '这反映了两套工具捕捉线索的范围不同，不能把模型有标签的记录都当成正确分类。\n\n'
        '下表以全部清理后非空正文为统一分母，记录模型在正文中发现的线索；同一帖子可以有多个标签，'
        '各行不能相加。未确定的帖子另列，不能直接等同于该类不存在。\n\n'
        '可读文本中对某个标签显式标为不确定的数量在表中另列；186条信息不足的正文不计入该列，对各语义标签均无法判断。\n\n'
        '| 维度 | 分类 | 模型标记帖数 | 占非空正文 | 可读文本中该项显式不确定 |\n'
        '| --- | --- | ---: | ---: | ---: |\n' + '\n'.join(rows) + '\n\n')
    for fam, label in [('content', '内容对象'), ('expression', '表达行为')]:
        obj = result['regression'][fam]
        if obj['status'] != 'estimated_exploratory':
            classification += (f'{label}的探索性回归由于有效支持或模型秩不足，未作可解释的估计。\n\n')
            continue
        classification += (f'为观察{label}与点赞的条件关联，在可读且该维度没有不确定标签的完整案例中，'
                           f'沿用原有字面变量、作者与日期固定效应及其他控制项，'
                           f'估计探索性回归（{obj["n"]:,}帖、{obj["n_authors"]}位作者）。'
                           + ('内容轴另限制为具有明确内容对象的帖子。' if fam == 'content' else '')
                           + '纳入每组至少40条、且至少10位作者的帖子中该标签有变化的标签；其他明确内容等开放残余槽不进入回归。每个标签单独估计一个模型，'
                           '比较该标签出现与未出现的合格帖子；其他标签可能并存，也没有作为该组比较的额外控制项。'
                           '下表区间为作者聚类原始95%区间，'
                           'q值仅在本组标签内进行多重检验校正，不覆盖两个模型及其他研究检验的整体探索。\n\n'
                           '| 分类 | 标记帖数 | 系数 β | 原始95%区间 | 原始p | 组内BH q |\n'
                           '| --- | ---: | ---: | --- | ---: | ---: |\n')
        for row in obj['coefficients']:
            classification += (f'| {row["label"]} | {row["n_positive"]:,} | {row["beta"]:.3f} | '
                               f'[{row["ci_low"]:.3f}, {row["ci_high"]:.3f}] | '
                               f'{row["p"]:.3f} | {row["q_bh_within_family"]:.3f} |\n')
        classification += '\n'
    if all(all(row['q_bh_within_family'] >= .05 for row in obj['coefficients'])
           for obj in result['regression'].values() if obj['status'] == 'estimated_exploratory'):
        classification += ('两组分别进行多重检验校正后，单项标签均未达到5%水平；'
                           '这表示现有证据尚不足以作稳定关联判断，并不证明类别之间没有差异。\n\n')
    classification += ('这些类别与点赞的结果只描述已记录条件下的探索性关联。'
                       '模型标签可能有错判，样本排除了部分未知项，且没有曝光与统一观察时间；'
                       '因此不能据此解释为类别的因果效果，也不能将分类结果写成人工确认的真实比例。\n\n')
    marker = '## 5. 帖子主题成分与点赞的关系（RQ2）'
    source = replace_once(source, marker, classification + marker)
    conclusion = ('新增双轴分类在原始字面线索之外，提供了对正文内容与表达的补充描述；'
                  '这些标签由模型分批阅读正文得到，仍需独立人工复核，特别是短帖、未指明内容及表达边界。\n\n')
    source = replace_once(source, '### 8.2 结果的应用', conclusion + '### 8.2 结果的应用')
    OUT.write_text(source)
    print(OUT)


if __name__ == '__main__':
    main()
