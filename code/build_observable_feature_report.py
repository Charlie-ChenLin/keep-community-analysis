"""Build the observable-feature report from frozen, previously computed results.

No statistical model, dictionary, threshold or semantic recognizer is refitted.
Legacy variable identifiers remain internal keys of the frozen input files.
"""
from pathlib import Path
import hashlib
import html
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'validation/observable_feature_report'
STEM = '分析报告_字面特征与互动结构版'
SOURCE = ROOT / '分析报告_老师意见修订版.md'
FONT_FILE = Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
os.environ.setdefault('MPLCONFIGDIR', str(QA / 'mplconfig'))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pandas as pd
import pymupdf as fitz
from PIL import Image, ImageDraw
from docx import Document
from docx.oxml.ns import qn
from bs4 import BeautifulSoup
import build_phase2_report as office

SCOPE = json.loads((ROOT / 'code/observable_feature_scope.json').read_text())
LABELS = SCOPE['feature_labels']
SHORT = SCOPE['feature_short_labels']
FEATURES = list(LABELS)
FONT = FontProperties(fname=str(FONT_FILE))
plt.rcParams.update({'font.family': FONT.get_name(), 'axes.unicode_minus': False,
                     'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
COMMENT_LABELS = ['加油等词项（评论组1）', '谢谢等词项（评论组2）',
                  '早安等词项（评论组3）', '问号（评论组4）']


def read(name):
    return json.loads((ROOT / 'results' / name).read_text())


def table(headers, rows):
    def cell(value):
        return str(value).replace('|', '／').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(map(cell, headers)) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(map(cell, row)) + ' |' for row in rows]) + '\n'


def f(value):
    return f'{float(value):.3f}'.replace('-', '−')


def ci(row):
    return '[' + f(row['ci_low']) + ', ' + f(row['ci_high']) + ']'


def section(text, start, end):
    return text[text.index(start):text.index(end)].strip()


def neutralize(text):
    replacements = [
        ('自律／目标词命中', LABELS[FEATURES[1]]), ('社交称呼／互助词命中', LABELS[FEATURES[2]]),
        ('积极表达词命中', LABELS[FEATURES[3]]), ('自律／目标词', SHORT[FEATURES[1]]),
        ('社交／互助词', SHORT[FEATURES[2]]), ('社交称呼或互助词', SHORT[FEATURES[2]]),
        ('社交称呼／互助词', SHORT[FEATURES[2]]), ('积极表达词', SHORT[FEATURES[3]]),
        ('积极表达', SHORT[FEATURES[3]]), ('积极词', SHORT[FEATURES[3]]),
        ('自律词', SHORT[FEATURES[1]]), ('社交词', SHORT[FEATURES[2]]),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    text = text.replace('问号出现', LABELS[FEATURES[4]])
    return text


def save(fig, name):
    fig.tight_layout()
    path = ROOT / 'figures' / ('observable_' + name + '.png')
    fig.savefig(path, dpi=190, bbox_inches='tight')
    plt.close(fig)
    return path


def redraw_figures():
    """Read result tables only; the revised figures change labels and arrangement."""
    fig, ax = plt.subplots(figsize=(10.6, 3.1))
    labels = ['原始正文不可见', '原始可见、清理后为空', '清理后正文非空']
    values = [3984, 134, 5414]
    ax.barh(labels, values, color=['#849c94', '#b58b44', '#245c4f'])
    ax.invert_yaxis()
    for i, value in enumerate(values):
        ax.text(value + 80, i, f'{value:,}（{value / 9532:.1%}）', va='center')
    ax.set(xlim=(0, 6700), xlabel='帖子数；三类互斥，合计9,532帖', title='正文的可观察范围')
    save(fig, 'body_coverage')

    hits = pd.read_csv(ROOT / 'results/text_features_summary.csv')
    words = pd.read_csv(ROOT / 'results/word_document_frequency.csv').head(10)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.1), gridspec_kw={'width_ratios': [1.2, 1]})
    axes[0].barh([SHORT[x] for x in hits.feature], hits.n_hit, color='#245c4f')
    axes[0].invert_yaxis(); axes[0].set(xlim=(0, 1080), xlabel='命中帖子数', title='A. 四条固定字面规则（可重叠）')
    for i, value in enumerate(hits.n_hit): axes[0].text(value + 15, i, str(value), va='center')
    axes[1].barh(words.term, words.document_frequency, color='#356c92')
    axes[1].invert_yaxis(); axes[1].set(xlabel='含该词的帖子数', title='B. 清理正文的高频词')
    save(fig, 'text_features')

    cm = read('teacher_complete_body_model.json')['models']
    fig, ax = plt.subplots(figsize=(10.8, 4.8))
    colors = ['#839991', '#356c92', '#245c4f']
    for j, model in enumerate(cm):
        items = {x['term']: x for x in model['terms']}
        y = [i + (j - 1) * .22 for i in range(5)]
        rows = [items[x] for x in FEATURES]
        ax.errorbar([x['coef'] for x in rows], y,
                    xerr=[[x['coef'] - x['ci_low'] for x in rows],
                          [x['ci_high'] - x['coef'] for x in rows]],
                    fmt='o', capsize=3, color=colors[j],
                    label=['全样本＋正文可见标记', '原始正文可见', '清理后正文非空'][j])
    ax.set_yticks(range(5), [SHORT[x] for x in FEATURES]); ax.invert_yaxis()
    ax.axvline(0, color='#8c9893', linestyle='--', linewidth=1)
    ax.set(xlabel='ln(1+点赞数)的系数及原始95%作者聚类区间', title='三种既有正文口径并列展示')
    ax.legend(fontsize=9, loc='upper center', bbox_to_anchor=(.5, -.21), ncol=3)
    save(fig, 'three_body_coefficients')

    coefs = pd.read_csv(ROOT / 'results/regression_coefficients.csv')
    models = list(coefs.model.unique())
    selected = [x for x in models if x.startswith(('M3', 'R1', 'R2', 'R3'))]
    if len(selected) < 4:
        selected = [x for x in models if x.startswith('M3') or '可见' in x or '1%' in x or '等权' in x]
    selected = selected[:4]
    assert len(selected) == 4, models
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
    for i, feature in enumerate(FEATURES[1:4]):
        data = coefs.loc[coefs.term.eq(feature) & coefs.model.isin(selected)].set_index('model').loc[selected]
        axes[i].errorbar(data.coef, range(4), xerr=[data.coef - data.ci_low, data.ci_high - data.coef], fmt='o', capsize=3, color='#245c4f')
        axes[i].axvline(0, color='#8c9893', linestyle='--', linewidth=1)
        axes[i].set(title=SHORT[feature], xlabel='系数及原始95%区间')
    axes[0].set_yticks(range(4), ['原全样本M3', '原始正文可见', '去最高1%点赞', '作者等权']); axes[0].invert_yaxis()
    save(fig, 'robustness')

    data = pd.read_csv(ROOT / 'results/extension_author_influence.csv')
    fig, ax = plt.subplots(figsize=(10.7, 3.7))
    vals = [data.loc[data.term.eq(feature), 'coefficient'].to_numpy() for feature in FEATURES]
    ax.boxplot(vals, vert=False, tick_labels=[SHORT[x] for x in FEATURES], showfliers=True)
    ax.axvline(0, color='#8c9893', linestyle='--', linewidth=1)
    ax.set(xlabel='每次剔除一位作者后的系数；每项100次', title='单个作者影响：保持原全样本模型口径')
    ax.invert_yaxis(); save(fig, 'author_influence')

    data = pd.read_csv(ROOT / 'results/comment_text_features.csv')
    comment_keys = list(json.loads((ROOT / 'code/comment_text_config.json').read_text())['features'])
    fig, ax = plt.subplots(figsize=(10.8, 3.7))
    for j, role in enumerate(['其他用户发言', '帖主发言']):
        part = data.loc[data.role.eq(role)].set_index('feature').loc[comment_keys]
        ax.barh([i + (j - .5) * .31 for i in range(4)], part.share * 100, height=.3,
                color=['#356c92', '#b58b44'][j], label=role)
    ax.set_yticks(range(4), COMMENT_LABELS); ax.invert_yaxis()
    ax.set(xlabel='占相应角色全部已采集评论的比例（%）', title='评论中的固定词项命中与问号')
    ax.legend(loc='lower right', fontsize=10); save(fig, 'comment_features')

    topic = read('teacher_topic_summary.json')
    order = [2, 4, 3, 0, 1]
    names = ['成分2：运动／时间／训练词群', '成分4：人生／生活／早安词群',
             '成分3：打卡／夜跑词群', '成分0：靠墙／膝盖词群', '成分1：公里／骑行词群']
    values = [topic['original_dominant_counts'][i] / topic['documents'] * 100 for i in order]
    fig, ax = plt.subplots(figsize=(10.8, 3.8)); ax.barh(names, values, color='#245c4f'); ax.invert_yaxis()
    for i, value in enumerate(values): ax.text(value + .6, i, f'{value:.1f}%', va='center')
    ax.set(xlim=(0, 64), xlabel='最高权重成分的数值份额（分母：2,470帖）', title='探索性附录：冻结NMF词共现成分')
    save(fig, 'component_shares')


def manuscript():
    old = SOURCE.read_text()
    dictionary = json.loads((ROOT / 'code/text_dictionary.json').read_text())
    comment_cfg = json.loads((ROOT / 'code/comment_text_config.json').read_text())
    cm = read('teacher_complete_body_model.json')['models']
    chunks = ['''# Keep社区帖子特征与互动反馈

**可观察字面特征、点赞关联与评论互动结构｜2026年10月29日**

**摘要**

本研究使用课程提供的9,532条帖子与11,595条去重评论，分析正文可观察范围、媒体形式和tag分布，比较固定词项、问号及正文长度与累计点赞的条件关联，并描述已采集评论的词项、直接回复和用户连接。主研究的测量对象是字面可观察特征，不再把固定词项或自动成分作为真实内容类别、人格、情绪或社会支持的测量。

正文清理后非空的帖子有5,414条；其中71.9%未命中四条固定规则。规则可以交叉命中，也不覆盖全部表达，未命中率不是分类错误率。三种既有正文口径并列报告：全样本、原始正文可见与清理后非空模型的五项联合p值分别为0.130、0.067与0.040。后者长度和开心等词项（C）的模型内BH q均约0.048，但这些口径是在原结果后补充比较的，不能据此追认为事前唯一主模型，或声称具有稳定增赞效果。

在4,902次明确回复中，89.0%由帖主发给其他用户；接收事件数相近的两个账号，发送者人数分别为53和1,091。评论次数、参与人数和直接回复覆盖提供不同的互动描述，均不直接等于真实社会支持或关系质量。

本轮未进行人工语义复核。候选内容框架、NMF成分、旧成分回归、多阈值及AI识别器均移入明确的探索性附录；400条文本的AI重建与留出预检验暴露了范围门控和过度检出问题，未形成可供正式类别效应分析的语义真值。主研究按当前可观察范围完成，人审手册及工具保留为有资源时的后续材料。

## 1. 研究背景、问题与范围

### 1.1 从运动社区中的发言与反馈出发

Keep的帖子同时含有正文、媒体和平台元数据。用户可能发布很短的记录，也可能在评论区与其他账号往来。只比较高赞帖常见用词，容易把作者、媒体和累计观察时间的差别一并归入文案。本研究因此分开描述样本覆盖、正文特征的条件关联，以及采集到的回复连接。

既有运动社区研究为讨论线上参与提供背景[1]，词项计数和文本矩阵方法提供可复核工具[2–4]。这些文献不能替本样本验证某个词组对应的心理构念。本报告把解释限制在已记录的字面特征、点赞与互动结构。

### 1.2 三个研究问题
''']
    chunks.append(table(['问题', '本轮问题', '证据与章节'], [
        [x['id'], x['text'], ['覆盖、媒体、tag与点赞描述；第3章',
                               '冻结模型、口径及控制项对照；第4章',
                               '评论词项、直接配对和有向网络；第5—6章'][i]]
        for i, x in enumerate(SCOPE['research_questions'])]))
    chunks.append('''### 1.3 本轮正式研究与探索材料的边界

主研究保留既有清理、固定词表、匹配方法、控制项与估计值，不重新选择统计结果，也不添加新的p值。所有正文模型并列披露；原M3是历史全样本设定，正文可见与非空口径是已有补充比较，均不因显著性被追认为事前唯一主模型。

本轮未进行人工语义复核，已完成的计算核查不称为语义效度验证。候选分类不进入正式RQ或主研究结论；旧NMF成分和分类重建仅在探索性附录记录其方法、结果与失败。未来若有资源，可使用现有手册与独立标注工具开展新的语义研究；这不是本作业本轮交付的先决步骤。

## 2. 数据、可观察特征与分析方法

### 2.1 数据来源和清理口径

研究使用课程提供的帖子表、评论表和字段说明。9,532帖来自100位作者，帖子发表于2020年11—12月（UTC）；北京时间末端跨至2021年1月1日。11,595条去重评论最晚延续至2021年8月26日。文件名中的“2022”不代表观测年份。

| 核查项 | 已有结果 | 本轮解释 |
| --- | --- | --- |
| 帖子与评论主键 | 帖子ID唯一；评论ID重复1,916行，无字段冲突 | 评论按ID去重，保留11,595条 |
| 原始正文 | 5,548帖有可见字符，3,984帖不可见 | 未记录正文不能视为原帖没有内容 |
| 清理正文 | 5,414帖非空；134帖原始可见但清理后为空 | 与全样本、原始可见口径并列 |
| 评论覆盖 | 去重评论均能关联帖子，分布在1,323帖下 | 其余帖子评论覆盖未知，不填成零评论 |
| 点赞与浏览 | 8,286帖点赞数高于记录浏览数 | 不计算点赞率，使用累计点赞 |
| 时间、媒体和长尾 | 累计观察时长未知，未读取图像或语音内容 | 不以正文补出媒体语义；保留极端值敏感性 |

正文清理还原转义换行，移除URL、成对的课程分享后缀和方括号表情，并统一空白；原始hashTags字段不拼入基本正文。没有正文的全样本记录将字面特征设为0，并加入原始正文可见标记；该处理描述记录状态，不能恢复缺失内容或校正非随机缺失。

### 2.2 正文的四条规则列全词项，不作为语义分类

正文长度为ln(1+清理后非空白字符数)。以下规则按固定子串或已冻结模式匹配，任一命中记1，重复出现不累加。A含下表末项正则模式，其余词项作字面子串匹配；B、C和D先对词项作正则转义再匹配，不是按分词频率编码。A、B、C、D可以交叉命中，既不互斥，也不完备。它们不直接测量人格、情绪、真实提问或社会支持。

A—C最初按词语的直观含义编制，缺少独立词表评审和语义验证。本版仅将它们沿用为固定、可复算的探索性操作指标；中性改名不补上理论或经验效度，也不表明三组词项是语料自然形成的分类。本轮未因显著性保留、增删词项，既有匹配规则不变。
''')
    chunks.append(table(['字面特征', '全部固定词项／模式', '操作与边界'], [
        [LABELS[feature], '、'.join(dictionary[feature]),
         ('末项为既有正则模式，其余按子串；不判断否定、反讽、意图或行为真实性。' if i == 0 else
          '任一子串命中记1；未处理否定、反讽或上下文含义。' if i < 3 else
          '任一问号出现记1；修辞问句会命中，无问号的提问可能漏掉。')]
        for i, feature in enumerate(FEATURES[1:])]))
    chunks.append('''同一条“加油”可能用于自我提醒或给别人留言；“谢谢”也不能证明已经发生互助。规则名称仅帮助读者辨认所列词项。数值共线性与语义含义是不同问题，低VIF不证明四项是独立心理维度。

辅助控制沿用原始正文可见状态、有无原始tag、表情数量、课程分享标记、媒体形式、业务类型和发帖时段。原始tag是用户选择的元数据，不能作为正文语义的标准答案。

### 2.3 点赞模型与三种正文口径并列

因变量为ln(1+点赞数)。原M3同时放入正文长度、A—D、已记录控制项、作者固定效应及北京时间发帖日期固定效应。作者固定效应调整不随帖子变化的作者间差别，日期固定效应调整同日共有差别；标准误按各模型实际包含的作者聚类，保留有限样本修正及t／F推断[5]。

原全样本9,532帖／100位作者、原始正文可见5,548帖／95位作者、清理后非空5,414帖／95位作者均报告。每个模型内的五项系数用Benjamini–Hochberg方法作BH校正，并列五项联合检验[6]。模型内BH不覆盖所有口径、控制项和探索分析，因此q=0.048不构成对整个研究探索过程的统一校正。

作者支持、少帖作者、tag身份与拼接、完整设计矩阵VIF、最高1%点赞剔除、作者等权、PPML和逐作者剔除沿用既有冻结结果。这些检查说明比较对处理方式如何变化，不能修复缺失曝光、累计时长或语义测量。

### 2.4 评论的字面规则、直接配对与网络

评论按ID去重，统一全半角与空白，移除URL和方括号标记。词项每条评论至多计一次，各组可交叉命中，分母为相应角色全部已采集评论。为使规则可复核，完整列出原评论词表；组名只指词项集合。
''')
    chunks.append(table(['评论字面规则', '全部固定词项'], [
        [COMMENT_LABELS[i], '、'.join(rule['terms'])]
        for i, rule in enumerate(comment_cfg['features'].values())]))
    chunks.append('''直接配对以其他用户发给帖主的根评论为起点，要求所属帖子、reply、replyUserId和parentId共同匹配，在根评论后168小时内取最早观测到的帖主直接回复。未采到直接回复不等于实际上没有回复。

有向网络以账号为节点、发送者指向接收者：根评论按所属帖子指向帖主，明确回复指向被回复账号。同向多次事件合并为边权，排除84次自我互动。全部事件、仅明确回复与发帖后7天三种范围分别描述。评论词项与网络均不度量真实支持、情感或关系质量，也不放入发帖前点赞模型。完整配对、窗口和互惠口径见附录A。
''')
    third = section(old, '## 3. 这批数据如何影响内容与评论的比较', '## 4. 字面表达的关联对正文可观测范围敏感')
    third = third.replace('## 3. 这批数据如何影响内容与评论的比较', '## 3. 正文可观察范围、媒体、tag与点赞分布')
    third = third.replace('本报告关心两个问题：文字表达与点赞差异怎样联系，评论中的交流具体如何发生。本章回应RQ1，说明这批数据的覆盖与分布，为第4—5 章的文字比较和第6—7章的评论分析确定比较范围。', '本章回应RQ1，说明可以观察哪些正文、媒体和元数据，以及点赞分布的范围，为第4章的关联比较和第5—6章的评论描述确定分母。')
    third = third.replace('原M3以全部帖子为历史比较范围，修订后的字面分析同时列出原始正文可见与清理后非空的样本。NMF最终只有2,470帖获得可用权重，占全样本25.9%、非空正文45.6%；另有2,944条非空正文未进入该主题表。未入模不等于没有主题，正文缺失也不等于图片和视频没有内容。图片文字和视频语音尚未观察，不能用现有文字类目补齐。', '原M3以全部帖子为历史比较范围；原始正文可见和清理后非空口径同时列出。3,984帖的原始正文不可见，另有134帖清理后为空。图片文字和视频语音尚未观察，不能用缺失标记或现有正文规则补齐。')
    third = third.replace('figures/teacher_text_coverage.png', 'figures/observable_body_coverage.png')
    third = third.replace('全样本按正文与原主题模型的覆盖状态划分，三类互斥，合计9,532帖。它显示分析能看到哪些记录，不是五类之外的语义比例。', '按原始正文可见与清理状态划分，三类互斥，合计9,532帖。图中表示记录可观察范围，不是语义类别。')
    third += '''\n\n### 3.3 原始tag覆盖一半以上帖子，与正文可见并不相同

5,209帖带有原始tag，占54.6%，共269种；其中1,517帖没有原始正文。5,207帖只有一个tag，仅2帖有两个。有tag、正文可见和某条规则命中分别描述不同字段，不能相互替代。tag的身份控制和拼接比较在第4章单独报告，避免把平台活动标题中的固定用词当作原正文的新增表达。
'''
    chunks.append(third)

    fourth = section(old, '## 4. 字面表达的关联对正文可观测范围敏感', '## 5. 五个用词成分不能直接当作完整内容分类')
    fourth = neutralize(fourth)
    for old_image, new_image in [('03_text_features', 'observable_text_features'), ('04_main_coefficients', 'observable_three_body_coefficients'), ('05_robustness', 'observable_robustness'), ('12_author_influence', 'observable_author_influence')]:
        fourth = fourth.replace('figures/' + old_image + '.png', 'figures/' + new_image + '.png')
    fourth = fourth.replace('原全样本M3的系数与原始95%作者聚类区间，N=9,532、100位作者；非空正文结果另列下表。', '三种既有正文口径的五项系数与原始95%作者聚类区间；样本数、作者数和模型内BH q见下表及附录A。')
    fourth = fourth.replace('修订后的问题明确聚焦“可观察的正文中的指定线索”。选择这个范围的理由是变量确实能够被测量，不是它的p值更小。原全样本模型作为历史对照保留。两者都缺少实际曝光、完整媒体内容和统一累计观察时长，不能识别词汇的因果作用。', '本轮正式问题聚焦可观察的固定字面特征，三种正文口径并列解释。非空正文口径的p=0.040和两项q=0.048不被追认为事前确定的唯一主模型；全样本p=0.130也不被概括为文字普遍没有关联。三者都缺少实际曝光、完整媒体内容和统一累计观察时长，不能识别词项的因果作用。')
    fourth = fourth.replace('更强自律或提出了问题', '不同的真实行为或提问意图')
    fourth = fourth.replace('该重分析是在原结果之后开展，且没有对所有探索性模型统一校正；结果靠近阈值，仍受到正文可观察范围的选择限制。', '该重分析是在原结果之后开展，且没有对所有探索性模型统一校正；结果靠近阈值，仍受到正文可观察范围的选择限制。三种p值的变化不是系数之间差异的显著性检验，也不能证明非随机正文缺失已被解决。')
    fourth = fourth.replace('原有的可见正文', '原有的原始正文可见')
    fourth = fourth.replace('本轮只依据频数与作者覆盖', '既有补充分析只依据频数与作者覆盖')
    fourth = fourth.replace('沿用原分析的三类词汇系数', '从冻结结果表重画的A、B、C系数')
    fourth = fourth.replace('1,523帖命中至少一项，3,891帖没有命中任何规则，占71.9%。', '1,523帖命中至少一项，3,891帖没有命中任何规则，占71.9%。71.9%是四条非完备规则的未命中比例，不是分类错误率。')
    chunks.append(fourth)

    chunks.append('''## 5. 评论词项与观测直接回复的分布

### 5.1 短评论与重复词项有不同的用户覆盖

清理后评论字符数中位数为6、75分位数为10；1,373条只留下标记或符号，占11.8%。这些记录只支持评论长度与字面形式的描述，不能据此判断发言者的态度强度。

![图](figures/14_comment_words.png)

图　以11,595条去重评论为分母展示常见词的出现占比。每条评论内同一词至多计一次，词项至少覆盖5位发言用户，各词可共同出现。

“加油”出现在612条评论中，涉及431位发言用户；“谢谢”出现在359条评论中，涉及53位用户。前者在更多用户之间出现，后者更集中于较少使用者。另有3,362条评论具有重复的标准化文本，按不同ID保留。评论次数和不同发言用户数应同时报告，不能把重复的短句直接当作更深的关系。

### 5.2 发言角色对应不同词项命中率

其他用户发言7,192条，帖主发言4,403条；同一用户可在不同帖子下切换角色。下表与图按每条评论的所属帖子定义角色，保留根评论、回复及84次自我互动。

![图](figures/observable_comment_features.png)

图　按发言者是否为所属帖子的作者分组，比较四组固定字面规则。分母为各角色全部已采集评论，各项可以重叠。

| 评论字面规则 | 全部命中数 | 全部占比 | 其他用户命中率 | 帖主命中率 |
| --- | --- | --- | --- | --- |
| 加油等词项（评论组1） | 1,413 | 12.2% | 16.9% | 4.5% |
| 谢谢等词项（评论组2） | 389 | 3.4% | 0.6% | 7.9% |
| 早安等词项（评论组3） | 551 | 4.8% | 4.4% | 5.4% |
| 问号（评论组4） | 427 | 3.7% | 4.1% | 2.9% |

评论组1在其他用户发言中的比例较高，评论组2在帖主发言中的比例较高。这是词项与角色的对应分布。评论组2包含“感谢”“多谢”等完整表中所列词项，因此命中数389大于“谢谢”单词项的359。它们不能直接证明已经发生真实支持，或将“感谢”解释为支持效果。

### 5.3 根评论的直接回复覆盖与回复词项应分开看

从6,609条其他用户发给帖主的根评论出发，按冻结规则查找根评论后7天内、明确指向该条评论及其作者的帖主回复。每条根评论只取最早符合条件的观测回复，共有3,568条根评论配到回复。

| 根评论的字面规则 | 根评论数 | 涉及帖主数 | 观测到7天内直接回复 | 已回复记录中，最早回复命中评论组2 |
| --- | --- | --- | --- | --- |
| 命中加油等词项（评论组1） | 1,180 | 54 | 513（43.5%） | 137（26.7%） |
| 未命中加油等词项（评论组1） | 5,429 | 77 | 3,055（56.3%） | 195（6.4%） |

直接回复比例以各组全部根评论为分母；最后一列仅以已观察到直接回复的根评论为分母，同一帖主可以进入两组。命中评论组1的根评论中，最早回复命中评论组2的比例在已回复记录中为26.7%，另一组为6.4%；换成全部根评论作分母则为11.6%和3.6%。

同一批记录中，评论组1命中组的观测直接回复覆盖为43.5%，低于未命中组的56.3%。这说明回复词项分布和直接回复覆盖可以走向不同。它不证明某组留言更容易被忽视或得到更高质量回应，因为帖主、具体情境与采集完整程度各不相同。本轮没有对此新选显著性检验，也不把未命中组视为语义上缺乏鼓励或未获得支持的对照组。
''')
    network = section(old, '## 7. 评论区围绕帖主往来，互动量与人数需分看', '## 8. 对表达与互动的整体理解')
    network = re.sub(r'(?m)^(##|###) 7\.', r'\1 6.', network)
    network = network.replace('第六章的直接回复比例', '第5章的直接回复比例')
    network = network.replace('### 6.4 双向往来体现留言与回话，首周关系较为互惠', '### 6.4 双向连接与首周窗口的结构差别')
    network += '\n\n上述网络图与数值沿用既有冻结结果，本轮重新核对描述范围与术语，未重估网络或全面重审评论采集过程。根评论指向帖主是构网规则的一部分；连通、互惠和中心性描述观测连接，不等于真实友谊、社区凝聚力或社会支持。\n'
    chunks.append(network)
    chunks.append('''## 7. 讨论、结论与后续资源

### 7.1 三个研究问题得到怎样的回答

RQ1显示，文字可观察范围随媒体与作者变化，累计点赞呈长尾，tag有无也不同于正文可见。正文、媒体和元数据应分别保留，不能因为没有记录到正文就补成没有内容。

RQ2显示，A—D与长度的关联取决于比较口径和已记录条件。开心等词项（C）的命中组原始平均点赞较高，而若干调整模型的点估计为负；原始算术均值和对数条件系数处在不同尺度，无法将差别归因于单一控制项。三种正文口径的联合p为0.130、0.067与0.040，应共同呈现；非空正文模型内q约0.048靠近惯用阈值，且不覆盖全部模型探索，不支持稳定增赞结论。

RQ3显示，评论中的固定词项随发言角色分布不同，明确回复以帖主发给其他用户为主，事件量与不同发送者人数反映不同接收形态。网络互惠和线程参与描述不同层面的连接，均不能直接作为真实支持或关系质量的测量。

### 7.2 当前结果可以怎样使用

本轮可交付的是明确分母、规则和模型条件的观察性报告。使用者可以据此检查某种比较是否混入了正文缺失、媒体构成或少数账号的重复发言；不能把高赞帖常用词当作推荐文案，也不能把负向系数改写成“减少开心用词能提高点赞”。

| 对象 | 目前可采用的做法 | 依据与条件 |
| --- | --- | --- |
| 研究小组 | 在报告中并列三种正文口径，公开全部词项及样本分母 | 字面关联会随观察范围改变，规则不穷尽表达 |
| 平台分析者 | 若获得新数据，统一发帖后7天曝光、反馈和不同参与者数 | 当前累计观察时长未知，次数与人数含义不同 |
| 后续研究者 | 有资源时使用候选手册与独立标注工具开展单独语义研究 | 本轮未进行人工语义复核；候选类别仅作探索 |
| 平台运营者 | 如评估表达或回复提示，以新设计的实验记录实际曝光和回应 | 当前观察性关联未识别干预收益 |

### 7.3 限制与交付边界

样本仅来自课程提供的100位作者，抽样机制和统一采集时点未知，不能代表Keep全平台。缺失正文、媒体内容未观察与评论采集缺口限制了可见范围。作者和日期固定效应不能消除随帖变化的曝光、粉丝变化、媒体内容与观察时长差别；点赞也不等于训练效果、自律程度或留存。

四条正文规则与四组评论规则是可交叉命中的字面规则，不是互斥、完备的语义分类，亦未完成本轮人工语义复核。低共线性和计算可复现均不建立语义效度。模型内BH只调整每个设定的五项检验，正文口径与其他补充分析未构成一个统一校正的检验家族。

本轮按可观察字面特征与互动关联的范围完成作业。探索性附录保留NMF、候选框架及失败的AI识别器，以说明为何没有正式报告真实主题占比或类别效应；其工具可供未来资源允许时使用。本轮不以补完人工分类作为结论或交付的前提。
''')

    chunks.append('''## 附录A　字面模型与互动口径的完整证据

### A.1 三种既有正文口径的五项结果

每个区间均为原始95%作者聚类区间；BH q分别在各模型内对五项校正。全样本／原始可见／清理非空三个口径分别包含9,532／5,548／5,414帖及100／95／95位作者。以下全部估计沿用冻结结果，未追认任何一个口径为事前唯一主模型。
''')
    rows = []
    for model, label in zip(cm, ['全样本', '原始可见', '清理非空']):
        for item in model['terms']:
            rows.append([label, LABELS[item['term']], f(item['coef']), f(item['se_cluster']), ci(item), f(item['p']), f(item['q_bh'])])
    chunks.append(table(['模型', '字面特征', 'β', '聚类SE', '原始95%区间', '原始p', 'BH q'], rows))
    app = section(old, '### A.2 原有敏感性分析的保留范围', '### A.3 原连续成分回归及二元多标记口径')
    app = app.replace('| 补充设定 | 样本量 | 系数 |', '| 补充设定 | 样本量 | 开心等词项（C）β |')
    chunks.append(neutralize(app))
    app = section(old, '### A.4 评论配对、网络与时间口径', '### A.6 本轮新增证据的可复现位置')
    app = app.replace('### A.4', '### A.3').replace('### A.5', '### A.4')
    app = app.replace('四类字面特征', '四组评论字面规则').replace('分析感谢词时', '分析评论组2时')
    chunks.append(app)

    chunks.append('''## 探索性附录B　旧NMF词共现成分与候选内容框架

本附录全部属于探索性材料，不回答主研究中的真实主题比例或类别效应。保留旧结果是为了公开测量限制；这些分析既没有被本轮升级为正式语义分类，也没有据其p值挑选新类数或阈值。
''')
    exploratory = section(old, '### 5.1 模型捕捉到反复出现的词群，覆盖边界仍然明显', '## 6. 鼓励与感谢有角色分工，回应覆盖另有差别')
    exploratory = re.sub(r'(?m)^### 5\.', '### B.', exploratory)
    exploratory = exploratory.replace('figures/revised_component_shares.png', 'figures/observable_component_shares.png')
    exploratory = exploratory.replace('下一步需两名同学独立标注覆盖作者、媒体、已入模和未入模帖的样本，讨论分歧后冻结边界，再用未参与修改的样本核查覆盖、各类一致性和“其他”占比。', '若未来开展独立语义研究，可由独立标注者使用覆盖作者、媒体、已入模和未入模帖的样本，讨论分歧、冻结边界并作留出核查；本轮没有开展人工语义复核，也不把该工作列为本次作业必须完成的步骤。')
    exploratory = exploratory.replace('本轮没有双人独立人工标注', '本轮未进行人工语义复核')
    exploratory = exploratory.replace('本轮固定随机种子', '此前核查固定随机种子')
    exploratory = exploratory.replace('### B.6 新的内容框架先统一分类轴，再做独立验证', '### B.6 早期候选建议：未采用为最终分类')
    exploratory = exploratory.replace('候选一级内容域只回答', '下表是较早修订阶段提出、未采用为最终分类的候选建议；它的层级与边界不是后续冻结规则。后续400条文本重建见探索性附录C及冻结码本，其中单独问候不自动赋内容领域。早期候选一级内容域只回答')
    chunks.append(neutralize(exploratory))
    reg = section(old, '### A.3 原连续成分回归及二元多标记口径', '### A.4 评论配对、网络与时间口径')
    reg = reg.replace('三个阈值均没有真实全零组', '三个阈值下均未观察到五标记全零组')
    chunks.append(neutralize(reg.replace('### A.3', '### B.7')))
    chunks.append('''## 探索性附录C　400条文本的AI重建与识别器失败

### C.1 重建流程和证据地位

此前的AI重建从400条正文出发，分为160条开发、80条校准及160条留出。候选框架分别归纳“谈什么”与“怎么表达”，形成17个内容叶和15个表达行为候选项，并在冻结手册中另设上层领域。原型训练只使用开发与校准的正文及AI编码，不使用点赞、评论、作者或旧分类来选择类别与阈值。该过程得到可复查的候选手册，未得到独立的人类语义真值。

留出160条由同一模型基座、分离上下文的两个AI代理编码；一致性只衡量两份AI记录之间的对应，不能称为人类一致性、准确率或构念效度。两名成员本轮未开展人工语义复核，人审表为空；候选手册与工具仅保留为后续资源。

### C.2 冻结后审计暴露了过度检出

| 留出诊断 | 冻结聚合结果 | 本轮判断 |
| --- | --- | --- |
| 两份AI均判断领域未指明 | 24条中22条通过原型门控，18条仍被赋至少一个领域 | 门控不能可靠保留未指明状态 |
| 体验自述候选项 | 原型检出150／160条；AI A、B分别标41和37条 | 明显的边际扩张，不能以150条作为真实占比 |
| 候选类训练支持 | 21个语义槽中14个达到开发5阳性／5阴性原型门槛，7个未支持 | 可拟合门槛不等于可靠检测 |
| 人工语义复核 | 完成编码者0人，未计算人类验证指标 | AI记录不合成为真值 |

这些诊断不是以某一AI代理为标准答案宣布错误率，而是说明冻结原型与候选规则的适用范围和输出边际存在冲突。因而没有用全体预测量改写正式主题占比，也没有新跑类别—点赞回归。原冻结codebook、recognizer和识别器实现均保留，不为本轮报告修补或调参。

完整聚合见results/classification_rebuild_scope_audit.json、classification_ai_agreement.json、classification_rebuild_training.json及classification_rebuild_recognition.json；候选手册与原始流程见《分类测量重建_实证依据与验证报告》及本地冻结记录。附录仅引用聚合，不导出原始帖ID或私有编码文本。

## 附录D　复现位置与成员分工

### D.1 证据位置与本轮文件保护

| 内容 | 冻结证据 |
| --- | --- |
| 正文词项、命中与原始均值 | code/text_dictionary.json；results/text_features_summary.csv |
| 三种正文口径 | results/teacher_complete_body_model.json |
| 数值共线性、作者内变化 | results/teacher_feedback_dictionary.json及VIF表 |
| 少帖作者、tag身份和拼接 | results/teacher_author_tags_summary.json |
| 评论词项与角色 | code/comment_text_config.json；results/comment_text_features.csv |
| 直接回复配对 | results/supplemental_direct_reply_language.csv及supplemental_summary.json |
| 网络与时间窗口 | results/extension_summary.json、network_nodes.csv与相关表 |
| 探索性成分和结构审计 | results/teacher_topic_summary.json、teacher_label_coverage_summary.json及teacher_topic_structure_summary.json |
| AI重建、冻结与候选手册 | results/classification_*.json；validation/classification_rebuild/freeze_record.json |
| 本版范围与生成 | code/observable_feature_scope.json；code/build_observable_feature_report.py |

本版生成器只读冻结证据，不重算统计。旧报告、结果、原图与冻结分类材料按SHA-256核对；图中含构念名称的旧图从结果表重画为observable_新图，原图保留。新报告、PDF页图与验证元数据位于validation/observable_feature_report对应记录。计算和文件核查只验证引用与交付一致性，不验证语义。

### D.2 成员分工

陈霖负责问题提出、数据清洗与RQ1；董依心负责RQ2与RQ3。上述为既有实际分工。本轮均未进行人工语义复核，未将AI编码计为成员已完成人审。
''')
    refs = old[old.index('## 参考文献'):]
    chunks.append(refs)
    md = '\n\n'.join(chunks).strip() + '\n'
    # Sequential figure labels keep the moved NMF figure explicitly in Appendix B.
    count = 0
    def replace_image(match):
        nonlocal count
        count += 1
        return f'![图{count}]({match.group(1)})'
    md = re.sub(r'!\[[^]]*\]\(([^)]+)\)', replace_image, md)
    md = re.sub(r'(!\[图(\d+)\]\([^)]+\)\n\n)图(?:S?\d+)?[ 　]+',
                lambda match: match.group(1) + '图' + match.group(2) + '　', md)
    # References to the moved figures must match their new positions.
    md = md.replace('图11 中的', '图11中的')
    return md


PDF_CSS = '''@font-face{font-family:ArialUnicode;src:url("Arial Unicode.ttf");}
body{font-family:ArialUnicode,sans-serif;font-size:10.5pt;line-height:1.45;color:#20332f;}
h1{font-size:23pt;color:#173f36;}h2{font-size:17pt;color:#245c4f;margin-top:16pt;}
h3{font-size:12.5pt;color:#245c4f;margin-top:13pt;}p{margin:7pt 0;}
table{border-collapse:collapse;width:100%;font-size:8.5pt;margin:9pt 0;}
th,td{padding:4pt;border:0;vertical-align:top;}th{font-weight:bold;color:#245c4f;}
img{width:100%;}figure{margin:9pt 0;}figcaption{font-size:9pt;color:#536b61;}a{color:#245c4f;}'''


def export(md):
    (ROOT / f'{STEM}.md').write_text(md)
    office.STEM = STEM; office.VALIDATION = QA
    office.CSS = PDF_CSS + ' .document{max-width:940px;margin:25px auto;padding:35px;background:white;} .toc a{display:block;} .toc .level-2{margin-left:15px;} .chapter{margin-top:30px;}'
    _, soup, headings = office.read_manuscript()
    final = office.write_html(soup, headings)
    office.write_docx(final, headings)
    doc = Document(ROOT / f'{STEM}.docx')
    for style in doc.styles:
        if style.type == 1:
            style.font.name = 'Arial Unicode MS'
            style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), 'Arial Unicode MS')
    for paragraph in doc.sections[0].footer.paragraphs:
        for run in paragraph.runs:
            if 'Keep社区' in run.text:
                run.text = run.text.replace('Keep社区内容表达与互动反馈', 'Keep社区帖子特征与互动反馈')
    doc.save(ROOT / f'{STEM}.docx')
    sections = final.select('main > section')
    pieces = [sections[0], final.select_one('nav.toc')] + sections[1:]
    target = ROOT / f'{STEM}.pdf'
    paper = fitz.paper_rect('a4'); area = paper + (44, 42, -44, -44)
    archive = fitz.Archive([str(ROOT), str(FONT_FILE.parent)])
    def render_once(lookup=None):
        writer = fitz.DocumentWriter(str(target)); starts = []; pages = 0
        for node in pieces:
            if node is None: continue
            title = node.find(['h1', 'h2']).get_text() if node.find(['h1', 'h2']) else '目录'
            if node.name == 'nav':
                rows = []
                for node_section in sections[1:]:
                    heading = node_section.find('h2').get_text()
                    rows.append('<tr><td>' + html.escape(heading) + '</td><td>' + (str(lookup[heading]) if lookup else '—') + '</td></tr>')
                content = '<h2>目录</h2><table><tr><th>章节</th><th>页码</th></tr>' + ''.join(rows) + '</table><p>小节标题见正文；PDF书签可跳转章节。</p>'
            else:
                content = str(node)
            starts.append({'title': title, 'page': pages + 1})
            # MuPDF can shrink a late-page image to the remaining whitespace.
            # Start two selected subsections on new pages to retain readable
            # figures and the complete four-row comment rule table.
            split_at = ['4.2 ', '4.3 ', '4.5 '] if title.startswith('4.') else ['5.2 '] if title.startswith('5.') else []
            segments = [content]
            if split_at:
                parsed = BeautifulSoup(content, 'html.parser')
                segments, current = [], []
                for child in list(parsed.find(['section']).contents):
                    if getattr(child, 'name', None) == 'h3' and any(child.get_text().startswith(prefix) for prefix in split_at):
                        if current: segments.append(''.join(current))
                        current = []
                    current.append(str(child))
                if current: segments.append(''.join(current))
            for segment_content in segments:
                markup = '<html><head><style>' + PDF_CSS + '</style></head><body>' + segment_content + '</body></html>'
                story = fitz.Story(html=markup, archive=archive)
                more = 1
                while more:
                    device = writer.begin_page(paper)
                    more, _ = story.place(area); story.draw(device); writer.end_page(); pages += 1
                    assert pages < 85
        writer.close()
        return starts
    first = render_once()
    starts = render_once({x['title']: x['page'] for x in first})
    assert starts == first
    pdf = fitz.open(target)
    for i, page in enumerate(pdf, 1):
        page.insert_text((paper.width / 2 - 8, paper.height - 24), str(i), fontsize=9, color=(.35, .4, .37))
    pdf.set_toc([[1, x['title'], x['page']] for x in starts if x['title'] != '目录'])
    temp = QA / 'numbered_report.pdf'; pdf.save(temp, garbage=4, deflate=True); pdf.close(); os.replace(temp, target)
    return starts


def protected_inputs():
    current_delivery_prefixes = (STEM, '本轮修订说明_研究范围与结论边界',
                                 'Keep社区帖子特征与互动反馈_正式修订版')
    paths = [p for p in ROOT.glob('*') if p.is_file() and p.suffix.lower() in ['.md', '.html', '.docx', '.pdf', '.pptx', '.txt'] and not p.name.startswith(current_delivery_prefixes)]
    paths += [p for p in (ROOT / 'results').glob('*') if p.is_file()]
    paths += [p for p in (ROOT / 'figures').glob('*') if p.is_file() and not p.name.startswith('observable_')]
    paths += [p for p in (ROOT / 'code').glob('*') if p.is_file() and 'observable' not in p.name]
    freeze = ROOT / 'validation/classification_rebuild/freeze_record.json'
    if freeze.exists():
        paths.append(freeze)
        record = json.loads(freeze.read_text())
        def discover(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == 'path' and isinstance(value, str) and Path(value).is_file(): paths.append(Path(value))
                    elif isinstance(value, (dict, list)): discover(value)
            elif isinstance(node, list):
                for value in node: discover(value)
        discover(record)
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in set(paths)}


def validate(md, starts, protected):
    pdf = fitz.open(ROOT / f'{STEM}.pdf'); doc = Document(ROOT / f'{STEM}.docx')
    pdf_text = '\n'.join(page.get_text() for page in pdf)
    docx_text = '\n'.join(p.text for p in doc.paragraphs) + '\n'.join(c.text for t in doc.tables for r in t.rows for c in r.cells)
    required = ['71.9%', '0.130', '0.067', '0.040', '0.048', '89.0%', '1,091', '24条中22条', '18条', '150／160', '41和37', '未进行人工语义复核', '陈霖', '董依心']
    for kind, content in [('md', md), ('docx', docx_text), ('pdf', pdf_text)]:
        compact = re.sub(r'\s+', '', content)
        missing = [x for x in required if re.sub(r'\s+', '', x) not in compact]
        assert not missing, (kind, missing)
        (QA / f'{kind}_extract.txt').write_text(content)
    figures = re.findall(r'!\[[^]]*\]\(([^)]+)\)', md)
    assert len(figures) == 14, figures
    assert len(doc.inline_shapes) == len(figures)
    html_doc = BeautifulSoup((ROOT / f'{STEM}.html').read_text(), 'html.parser')
    assert len(doc.tables) == len(html_doc.find_all('table')) >= 15
    main = md[:md.index('## 附录A')]
    assert '## 7.' in main and '### 5.1' in main
    assert not re.search(r'自律／目标|社交／互助|积极表达词|鼓励性留言|真实支持水平|TODO|【待填写', md)
    for feature in FEATURES[1:]:
        assert all(term in md for term in json.loads((ROOT / 'code/text_dictionary.json').read_text())[feature])
    overflow = []; page_images = []; placed_images = []
    for i, page in enumerate(pdf, 1):
        assert page.get_text().strip(), i
        for placed in page.get_image_info():
            bbox = placed['bbox']
            placed_images.append({'page': i, 'width_points': bbox[2] - bbox[0], 'height_points': bbox[3] - bbox[1]})
            assert bbox[2] - bbox[0] > 450, ('Figure was shrunk into remaining whitespace', i, bbox)
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    x0, y0, x1, y1 = span['bbox']
                    if x0 < 20 or y0 < 10 or x1 > page.rect.width - 20 or y1 > page.rect.height - 10:
                        overflow.append({'page': i, 'text': span['text'], 'bbox': span['bbox']})
        path = QA / f'page-{i:02d}.png'; page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False).save(path); page_images.append(path)
    assert not overflow, overflow[:8]
    for batch, start in enumerate(range(0, len(pdf), 9), 1):
        count = min(9, len(pdf) - start)
        sheet = Image.new('RGB', (1500, ((count + 2) // 3) * 720), '#e3e9e5'); draw = ImageDraw.Draw(sheet)
        for j in range(count):
            im = Image.open(page_images[start + j]); im.thumbnail((480, 680))
            x = (j % 3) * 500 + 8; y = (j // 3) * 720 + 26
            sheet.paste(im, (x, y)); draw.text((x, y - 19), str(start + j + 1), fill='#173f36')
        sheet.save(QA / f'contact-{batch}.png')
    changed = [str(path.relative_to(ROOT)) for path, value in protected.items() if hashlib.sha256(path.read_bytes()).hexdigest() != value]
    assert not changed, changed
    manifest = {
        'scope': SCOPE['version'], 'source': SOURCE.name,
        'pdf_pages': len(pdf), 'main_chapters': 7, 'figures': len(figures),
        'main_figures': 13, 'exploratory_appendix_figures': 1,
        'docx_tables': len(doc.tables), 'docx_inline_images': len(doc.inline_shapes),
        'table_format': 'editable native Word tables', 'pdf_engine': 'PyMuPDF Story',
        'font_file': str(FONT_FILE), 'statistics_reestimated': False,
        'new_p_values_selected': False, 'human_semantic_review_conducted': False,
        'body_model_scopes_parallel': True, 'sources_unchanged': True,
        'text_outside_safe_page': overflow, 'chapter_starts': starts,
        'pdf_image_placements': placed_images,
        'visual_review': 'pending',
        'figure_audit': {'reused_after_visual_review': [x for x in figures if '/observable_' not in x],
                         'redrawn_from_frozen_results': [x for x in figures if '/observable_' in x]},
        'protected_input_count': len(protected),
        'protected_inputs': {str(path.relative_to(ROOT)): value for path, value in sorted(protected.items())},
        'output_sha256': {ext: hashlib.sha256((ROOT / f'{STEM}.{ext}').read_bytes()).hexdigest() for ext in ['md', 'html', 'docx', 'pdf']},
        'limitations': ['No human semantic review; lexical rules only.', 'Observational sample, incomplete text/media/exposure and comment collection.', 'BH is within each five-term model, not all model exploration.', 'NMF and AI categories are exploratory and are not semantic truth.'],
    }
    (QA / 'report_checks.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: value for key, value in manifest.items() if key not in ['protected_inputs', 'chapter_starts']}, ensure_ascii=False, indent=2))


def main():
    QA.mkdir(parents=True, exist_ok=True)
    protected = protected_inputs()
    redraw_figures()
    md = manuscript()
    starts = export(md)
    validate(md, starts, protected)


if __name__ == '__main__':
    main()
