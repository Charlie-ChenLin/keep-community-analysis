"""Organize the reviewed report into seven chapters and a linked two-level TOC."""
import copy
import html
import re

from bs4 import BeautifulSoup


CHAPTERS = [
    '研究题目', '研究问题的意义', '描述性统计分析',
    '非结构化数据的结构化与回归分析', '文本与网络分析', '结果与解释', '建议',
]
CHINESE_NUMBERS = '一二三四五六七'


def organize_report(pages, ui, title):
    para, table, note, box = [ui[key] for key in ('para', 'table', 'note', 'box')]
    sources = {page['title']: copy.deepcopy(page) for page in pages[1:]}
    used = set()

    def take(source):
        assert source not in used, f'Duplicate report section: {source}'
        used.add(source)
        return sources[source]['body']

    def elements(body):
        return list(BeautifulSoup(body, 'html.parser').find_all(recursive=False))

    # Separate the rationale from the questions, retaining the original evidence.
    background = elements(take('健身社区中的内容表达与互动反馈'))
    rationale = ''.join(str(el) for el in background[:2])
    rationale += '<h2>研究意义</h2>' + para(
        '在研究层面，本项目将健身分享中的字面表达与可观察的互动反馈联系起来，'
        '考察日常语言特征是否在作者与帖子情境之外提供额外信息。将原始组间比较与作者内比较并置，'
        '有助于识别哪些表面差异可能来自作者构成，避免把高赞帖中常见的词语直接解释为有效的表达策略。')
    rationale += para(
        '在方法层面，正文缺失、评论采集范围和累计点赞观察时长共同决定了分析能够回答的问题。'
        '本研究据此结合可复现的词典编码、固定效应回归与主题建模，'
        '考察不同层次的文本表示与点赞的条件关联，并用评论网络补充描述用户之间的回应关系。')
    rationale += para(
        '在实践层面，研究为内容提示和社区互动方案提供评估依据。若某些表达的关联并不稳定，'
        '就不宜仅凭词频或单一模型的显著性推广固定文案；若互动主要围绕帖主展开，'
        '则需要进一步考察回应质量及低反馈用户的参与机会。上述用途均以样本范围和测量条件为边界。')
    questions = ''.join(str(el) for el in background[2:])

    # Topic descriptions belong in chapter 5; the regression belongs in chapter 6.
    topic_parts = elements(take('主题分布及其作者集中度'))
    assert [el.name for el in topic_parts] == ['figure', 'p', 'table', 'p', 'p']
    topic_note = topic_parts[-1].get_text()
    stability, coefficient_note = topic_note.split('表内系数', 1)
    topic_description = ''.join(str(el) for el in topic_parts[:2])
    topic_description += '<h2>主题与作者的关系</h2>' + para(
        '主题占比刻画的是满足纳入条件的正文中，各类表达模式的分布；它并不对应全部帖子的内容构成。'
        '记录模板高度集中于少数作者，也说明主题与作者身份可能同时变化。'
        '因此，某一主题的原始点赞均值即使较高，也不能单独说明该主题更容易获得反馈。'
        '主题权重与点赞的条件关联将在第6.5节检验。') + note(stability)
    topic_regression = para(
        '第5.2节显示，主题分布与作者的记录习惯相互交织。为考察主题是否在既有词典特征之外提供额外解释，'
        '本节在主题模型子样本内加入四项主题权重，保留原有作者、日期和帖子控制项。'
        '这一分析与全样本的五项核心词典检验分别报告。')
    topic_regression += ''.join(str(el) for el in topic_parts[2:4])
    topic_regression += para(
        '“生活感悟与问候”的原始p值虽低于0.05，但BH校正后未达到5%显著性水平；'
        '其余主题也未形成明确证据。该结果表明，在当前子样本及设定下，将表达概括为潜在主题，'
        '仍不足以识别稳定的点赞差异。它不意味着主题内容没有价值，也不能外推至缺少有效正文的帖子。')
    topic_regression += note('表内系数' + coefficient_note)

    # Distribute the former combined conclusion across discussion and recommendations.
    conclusion = elements(take('研究结论、实践启示与后续设计'))
    assert [el.name for el in conclusion] == ['table', 'h2', 'p', 'h2', 'p', 'h2', 'ul', 'div']
    discussion = table(['研究问题', '主要结果与解释'], [
        ['RQ1：内容与反馈如何分布？', '点赞明显长尾，内容形式之间存在原始差异；正文覆盖不均，低频文本特征的作者内变动有限。'],
        ['RQ2：文本与点赞是否相关？', '五项核心特征联合检验p=0.130，新增解释度为0.065个百分点。积极表达词的负系数经BH校正后证据不足，且PPML区间包含零。'],
        ['RQ3：评论如何连接用户？', '前10位账号接收54.0%的互动事件，89.0%的明确回复由帖主发出；结构指标受到建边范围与评论窗口影响。'],
    ], [34, 66])
    discussion += str(conclusion[2])
    discussion += '<h2>研究局限</h2>' + str(conclusion[6]) + str(conclusion[7])
    recommendations = para(
        '本研究的实践建议侧重于如何改进内容支持与评估方式。现有结果未给出稳定的高赞用词依据，'
        '而网络集中度也受样本边界影响，因此不宜直接据此制定词汇奖励或账号影响力排名。'
        '更合适的做法是将内容提示与互助方案作为待评估的服务设计，并以统一口径记录实际反馈。')
    recommendations += str(conclusion[0])
    recommendations += '<h2>内容表达与互动支持</h2>' + para(
        '面向发帖者，可以提供自愿使用的表达提示，帮助其交代运动情境、过程和具体问题，'
        '同时保留个人化表达。这一建议旨在提高信息完整性和交流便利性；是否增加点赞，需要通过后续实验检验。')
    recommendations += para(
        '面向社区运营，可以先在更完整的用户样本中观察新用户、低反馈用户及普通参与者之间的回应分布，'
        '再试点同伴互助或回应提示。评价时同时关注独立互动人数、回复内容和持续参与，'
        '避免仅用评论次数衡量交流质量，或将少数活跃帖主的高回应量视为普遍现象。')
    recommendations += note('本节建议由样本发现引出，尚未作为干预方案实施，也未估计其效果。')
    future_design = str(conclusion[4])
    future_design += '<h2>实验方案与评价口径</h2>' + table(['环节', '建议设计'], [
        ['随机分组', '以作者为单位分配至过程记录提示、面向伙伴的问题提示和常规发布三组；同一作者保持同组，预先记录可能的跨组互动。'],
        ['主要指标', '预先指定7天内独立互动用户数作为主要评价指标；累计点赞、有效回复及后续发布行为作为补充指标，并同步记录曝光。'],
        ['比较方法', '按最初随机分组比较，保留未采用提示的用户；根据作者层面的分配与重复发帖结构确定推断方式，预先约定多重检验处理。'],
        ['样本与周期', '先通过试点估计作者层面的结果波动，再结合最小有意义差异和统计功效计算样本量；不由当前观察性系数反推实验效果。'],
    ], [22, 78])
    future_design += '<h2>数据与测量的优先改进</h2>' + para(
        '开展实验前，应首先补充统一观察窗口、真实曝光、作者属性历史时戳及更完整的评论记录。'
        '文本测量可采用隐藏互动指标的双人独立编码，并将图片文字和视频语音纳入内容表示。'
        '这些改进分别对应当前研究中的结果口径、时间可比性和语义测量局限，'
        '有助于区分表达本身、内容情境与曝光机会对反馈差异的影响。')
    future_design += box('实施与报告原则',
        '在数据口径和实验条件明确后，预先固定指标、分组与分析方案，完整报告各组结果及不确定性。'
        '若效果区间仍不足以支持有意义的改善，应保留这一结果，并据此调整方案。')

    topic = para(f'本研究题目为《{html.escape(title)}》。研究以课程提供的Keep社区帖子和评论为材料，'
                 '围绕“内容如何表达、反馈如何形成、用户如何互动”展开分析。'
                 '题目中的“更容易获得点赞”对应待检验的问题，不预设存在可直接推广的高赞表达方式。')
    topic += table(['研究要素', '范围与界定'], [
        ['研究对象', '100位作者发布的9,532条帖子，以及关联的11,595条去重评论。'],
        ['观测时间', '帖子发表于2020年11—12月（UTC），本地日期末尾跨至2021年1月1日；评论最晚延续至2021年8月。'],
        ['分析单位', '描述统计和回归以帖子为单位；网络以用户为节点、非自我评论或回复为有向互动事件。'],
        ['核心解释对象', '帖子文本与累计点赞的条件关联，以及已采集评论中的关系结构；不推断运动成效或健康变化。'],
    ], [24, 76])
    topic += '<h2>研究路径</h2>' + para(
        '研究先描述样本与反馈分布，再将非结构化正文转换为可检验的变量，'
        '通过作者与日期固定效应回归考察条件关联。主题建模用于补充识别内容模式，'
        '主题权重进一步进入回归以检验其条件关联，评论网络则用于描述回应关系。'
        '最后综合各类证据，讨论结论的适用范围并提出后续建议。')
    topic += note('数据使用范围为2026Data/Keep Data内的两份课程CSV；文件名中的“2022”不作为实际观测年份。')

    # A subsection is a reading unit; existing analytical tables and figures stay intact.
    groups = [
        [('研究题目与分析范围', topic)],
        [('研究背景与研究意义', rationale), ('研究问题与分析目标', questions)],
        [
            ('数据来源、样本范围与清洗', take('数据来源、样本范围与清洗')),
            ('正文覆盖与缺失分布', take('正文缺失与内容形式、作者均有关联')),
            ('点赞分布与作者发帖差异', take('点赞分布长尾明显，均值高于中位数')),
            ('内容形式与点赞表现', take('不同内容形式的点赞表现存在差异')),
            ('文本特征的分布与作者覆盖', take('文本特征的分布与作者覆盖')),
        ],
        [
            ('正文预处理与变量构建', take('正文预处理与变量构建')),
            ('词典编码规则与解释范围', take('词典编码规则及其解释范围')),
            ('语义测量局限与抽查', take('词典编码的语义局限与抽查')),
            ('从组间差异到作者内比较', take('从组间差异到作者内比较')),
            ('固定效应模型与统计推断', take('固定效应模型与统计推断')),
        ],
        [
            ('TF-IDF表示与NMF主题建模', take('TF-IDF与非负矩阵分解的主题分析')),
            ('主题分布及其作者集中度', topic_description),
            ('评论关系识别与建图规则', take('评论关系的识别与建图规则')),
            ('网络连通性与互惠性', take('评论互动网络的连通性与互惠性')),
            ('互动接收的集中度', take('前10位接收者获得54.0%的互动事件')),
            ('评论时序与互动角色', take('多数明确回复由帖主发出')),
            ('评论观察窗口的敏感性', take('首周网络的互惠性更高，集中度略低')),
        ],
        [
            ('主回归结果', take('核心文本特征的关联证据有限')),
            ('回归系数的量级与解释', take('回归系数的量级与解释')),
            ('样本与模型设定的稳健性', take('积极表达的负关联对模型设定敏感')),
            ('逐作者剔除的敏感性', take('逐作者剔除后的系数敏感性')),
            ('主题权重的回归检验', topic_regression),
            ('综合讨论与研究局限', discussion),
        ],
        [('内容表达与社区互动建议', recommendations), ('后续研究与对照实验方案', future_design)],
    ]
    output = [copy.deepcopy(pages[0])]
    figures = 0
    for chapter, sections in enumerate(groups, 1):
        chapter_name = f'第{CHINESE_NUMBERS[chapter-1]}章 {CHAPTERS[chapter-1]}'
        for index, (heading, body) in enumerate(sections, 1):
            section = f'{chapter}.{index}'
            body = body.replace('文本测量核查部分', '第4.3节').replace('第13节', '第4.3节')
            if section == '3.5':
                body += note('本节先描述特征的样本分布，具体预处理和编码规则见第4.1—4.2节。')
            soup = BeautifulSoup(body, 'html.parser')
            # Chapter, subsection and within-page headings have distinct levels.
            for heading_el in soup.find_all('h2'):
                heading_el.name = 'h3'
            for caption in soup.find_all('figcaption'):
                figures += 1
                caption.string = re.sub(r'^图\d+', f'图{figures}', caption.get_text())
            output.append({'chapter': chapter, 'chapter_name': chapter_name,
                           'chapter_start': index == 1, 'section': section,
                           'anchor': f'section-{chapter}-{index}', 'kicker': chapter_name,
                           'title': heading, 'body': str(soup)})

    reference = take('参考文献与复现说明')
    appendix = take('课程要求与小组分工')
    appendix = appendix.replace('封面、研究背景；成员留待真实填写', '第1—2章及封面；成员待据实填写')
    appendix = appendix.replace('数据、描述统计与文本分析部分；代码及Notebook', '第3章；清洗代码及已执行Notebook')
    appendix = appendix.replace('文本编码、主题与回归部分；特征表及模型结果', '第4章与第6章；特征表及模型结果')
    appendix = appendix.replace('已完成词典内容分析、分词统计及评论网络', '第5章；主题建模与有向加权评论网络')
    appendix = appendix.replace('回归及网络结果的解释与讨论', '第6章结果解释与第7章建议')
    for heading, anchor, body in [('参考文献与复现说明', 'references', reference),
                                  ('附录：课程要求与小组分工', 'appendix', appendix)]:
        output.append({'kicker': '参考资料' if anchor == 'references' else '附录',
                       'title': heading, 'anchor': anchor, 'body': body})
    assert used == set(sources), f'Unplaced report sections: {set(sources)-used}'
    assert figures == 11, figures
    return add_contents(output)


def add_contents(pages):
    """Compute physical page numbers after placing both contents pages."""
    entries = []
    for physical, page in enumerate(pages[1:], 4):
        page['physical_page'] = physical
        anchor = page['anchor']
        if page.get('chapter_start'):
            entries.append({'level': 1, 'section': '', 'title': page['chapter_name'],
                            'anchor': f'chapter-{page["chapter"]}', 'page': physical,
                            'chapter': page['chapter']})
        entries.append({'level': 2 if page.get('section') else 1,
                        'section': page.get('section', ''), 'title': page['title'],
                        'anchor': anchor, 'page': physical, 'chapter': page.get('chapter', 8)})
    contents_pages = []
    for index, batch in enumerate(([e for e in entries if e['chapter'] <= 4],
                                    [e for e in entries if e['chapter'] >= 5]), 1):
        links = []
        for entry in batch:
            label = f'{entry["section"]}　{entry["title"]}' if entry['section'] else entry['title']
            links.append(f'<a class="toc-entry toc-level-{entry["level"]}" href="#{entry["anchor"]}">'
                         f'<span class="toc-title">{html.escape(label)}</span>'
                         '<span class="toc-leader" aria-hidden="true"></span>'
                         f'<span class="toc-page">{entry["page"]}</span></a>')
        contents_pages.append({'kicker': f'目录 · {index} / 2', 'title': '目录' if index == 1 else '目录（续）',
                               'body': '<nav class="toc" aria-label="报告目录">'+''.join(links)+'</nav>',
                               'toc_entries': batch})
    return [pages[0], *contents_pages, *pages[1:]]
