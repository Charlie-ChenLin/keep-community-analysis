"""Compose the report around text–likes associations and comment interactions."""
import copy
import html
import json
from pathlib import Path
import re

import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
CHAPTERS=['研究题目','研究问题的意义','描述性统计分析','非结构化数据的结构化与回归分析',
          '文本与网络分析','结果与解释','建议']
CHINESE_NUMBERS='一二三四五六七'
RQ1='样本帖子、表达方式及点赞如何分布？'
RQ2='不同文本特征与点赞是否相关？'
RQ3='采集到的评论主要表达什么、如何连接用户？互动集中在哪里？'


def organize_report(pages,ui,title):
    para,table,note,box,fig=[ui[key] for key in ('para','table','note','box','fig')]
    sources={page['title']:copy.deepcopy(page) for page in pages[1:]};used=set()
    def take(source):
        assert source not in used,source
        used.add(source);return sources[source]['body']
    def elements(body):return list(BeautifulSoup(body,'html.parser').find_all(recursive=False))
    c=json.loads((ROOT/'results/comment_text_summary.json').read_text())
    rules=json.loads((ROOT/'code/comment_text_config.json').read_text())['features']
    cf=pd.read_csv(ROOT/'results/comment_text_features.csv')
    words=pd.read_csv(ROOT/'results/comment_text_terms.csv').set_index('term')
    hits=lambda role,key:cf.loc[cf.role.eq(role)&cf.feature.eq(key)].iloc[0]

    cover=copy.deepcopy(pages[0]);soup=BeautifulSoup(cover['body'],'html.parser')
    abstract=[p for p in soup.find_all('p',recursive=False) if not p.get('class')]
    abstract[0].string='本研究以Keep社区100位作者的9,532条帖子及11,595条去重评论为材料，从帖子内容与评论互动两个层面考察社区反馈。帖子分析将正文转换为词典特征，估计作者与日期固定效应模型，并以TF-IDF和NMF识别内容主题、检验主题权重的条件关联；评论分析结合词语统计、字面表达编码与有向加权网络，描述评论内容、回应角色和互动分布。'
    abstract[1].string='在控制作者及发帖情境后，五项核心文本特征的联合检验不显著（p=0.130），新增解释度为0.065个百分点。积极表达词的负系数经BH校正后q=0.079，且PPML区间包含零。主题回归在2,470条有效正文中进行，联合检验p=0.166。上述结果适用于各自样本与测量范围，尚不足以支持稳定的高赞表达规则。'
    abstract[2].string=f'评论中，其他用户发言的鼓励或赞许词命中率为{hits("其他用户发言","encouragement").share:.1%}，帖主发言的感谢词命中率为{hits("帖主发言","thanks").share:.1%}。网络中89.0%的明确回复由帖主发出，前10位账号接收54.0%的互动事件，呈现围绕帖主展开且接收较集中的结构。内容与关系分析共同描述已采集的社区反馈，未识别文本经由关系结构影响点赞的因果机制。'
    cover['body']=str(soup)

    topic=para(f'本研究题目为《{html.escape(title)}》，以课程提供的Keep帖子与评论为材料，'
        '研究社区反馈在内容和关系两个层面的表现。点赞描述帖子获得的累计反馈，评论文本呈现用户的字面回应，'
        '评论网络则描述回应在用户之间的指向与分配。三者共同构成研究对象，各自的统计单位和解释范围分别界定。')
    topic+=table(['研究要素','范围与界定'],[
        ['数据范围','100位作者的9,532条帖子；关联的11,595条去重评论，仅覆盖1,323条帖子。'],
        ['帖子时间','2020年11—12月（UTC），本地日期末尾跨至2021年1月1日；点赞的统一采集时点未知。'],
        ['评论时间','沿用已采集记录，最晚延续至2021年8月；另比较发帖后7天内的网络。'],
        ['分析单位','帖子用于点赞回归；评论用于内容描述；用户与有向互动事件用于网络分析。'],
    ],[23,77])
    topic+='<h2>两条分析线</h2>'+para('第一条分析线研究文本与点赞的条件关联：先描述帖子差异，'
        '再将字面表达和内容主题分别结构化，控制作者及发帖情境后进行回归。第二条分析线研究已采集评论的内容与关系：'
        '先统计评论表达，再分析用户连接、互动集中度和回应角色。两条线在共同的社区反馈问题下并列展开，'
        '不将发帖后形成的评论网络作为发帖前的解释变量。')
    topic+=note('数据仅来自2026Data/Keep Data的两份课程CSV；文件名中的“2022”不作为实际观测年份。')

    background=elements(take('健身社区中的内容表达与互动反馈'))
    rationale=''.join(str(el) for el in background[:2])
    rationale+='<h2>从内容反馈到回应关系</h2>'+para('社区反馈既包括一条帖子获得多少点赞，也包括评论中表达了什么、'
        '哪些用户彼此回应。前者适合在帖子层面比较内容与反馈，后者需要同时观察评论语言和互动指向。'
        '分别研究这两个层面，有助于避免仅凭累计次数推断交流质量，或仅凭常见词语概括用户关系。')
    rationale+=para('研究的解释重点是：原始文本组间差异在控制作者与情境后是否仍然存在，以及评论互动是否广泛分散在参与者之间。'
        '据此，回归分析用于考察条件关联，评论文本与网络分析用于描述已观测的回应内容和结构。'
        '这两类证据可以相互补充，但不能据此比较内容与关系对点赞的因果贡献。')
    questions=table(['编号','研究问题','对应分析'],[
        ['RQ1',RQ1,'第3章描述统计；第4.3节编码后特征分布。'],
        ['RQ2',RQ2,'第4章词典主回归与敏感性检验；第5.1—5.3节主题分析及回归。'],
        ['RQ3',RQ3,'第5.4—5.5节评论文本；第5.6—5.10节评论网络。'],
    ],[10,49,41])
    questions+='<h2>研究概念与可观测变量</h2>'+para('RQ2区分字面表达与内容模式。正文长度用于描述表达规模；'
        '自律与目标词对应健身记录中的目标、过程线索；社交称呼与互助词对应显式称呼或共同参与的线索；'
        '积极表达词和问号分别描述部分赞许、愉悦用语与标点。它们均为字面代理，不能直接测量自律程度、情绪强度或真实互动意图。'
        '主题模型则从词项共现中概括正文主要谈论的内容，为RQ2提供另一层文本表示。')
    questions+=para('RQ3同时考察评论内容与关系结构。字面表达命中率描述可见回应的语言特征，网络指标描述事件如何分配到用户。'
        '二者分别统计，不预设“某类评论带来更高互惠率”或“关系结构解释点赞差异”。')
    questions+=note('研究定位为探索性分析，未事前注册。原五项词典检验完整保留；主题、作者剔除及评论内容分析分别报告，未依据点赞结果调整编码规则。')

    topic_parts=elements(take('主题分布及其作者集中度'))
    assert [el.name for el in topic_parts]==['figure','p','table','p','p']
    stability,coef_note=topic_parts[-1].get_text().split('表内系数',1)
    topic_description=''.join(str(el) for el in topic_parts[:2])
    topic_description+='<h2>主题与作者的关系</h2>'+para('主题描述主要内容模式，也可能包含作者反复使用的记录模板。'
        '因此，主题占比不能直接解释为互动效果；下一节在有效正文子样本中检验其与点赞的条件关联。')+note(stability)
    topic_regression=para('为检验内容主题是否在既有词典特征与控制项之外提供关联信息，'
        '在同一有效正文子样本中加入四项主题权重，保留作者、日期及帖子控制项。')
    topic_regression+=''.join(str(el) for el in topic_parts[2:4])+note('表内系数'+coef_note)
    topic_regression+='<h2>与主回归的关系</h2>'+para('本节以2,470条有效正文为条件，主回归则使用全部9,532条帖子。'
        '两者的样本范围与文本表示均有差别，不能把两个不显著结果视为同一检验的重复验证，也不直接比较模型R²。'
        '在当前子样本中，主题权重尚未提供明确的额外关联证据；这一判断不能外推到缺少有效正文的帖子。')
    topic_method=para('本章继续回答RQ2，并在第5.4节转向RQ3。词典特征检验预先界定的字面表达，'
        '主题分析概括正文主要谈论的内容。通过这一补充，可以考察内容模式与点赞的条件关联，'
        '同时保留两类文本表示各自的测量范围。')+take('TF-IDF与非负矩阵分解的主题分析')

    comment_words=para('本节开始回答RQ3，先描述评论内容，再分析关系结构。文本统计使用全部11,595条去重评论，'
        '保留不同评论ID下的重复短句及84次自我互动；后续网络另行排除自我事件。')
    comment_words+=table(['环节','处理与口径'],[
        ['文本清理','统一全半角与空白，移除URL和方括号标记；没有汉字、字母或数字的记录另列为仅标记或符号。'],
        ['词语统计','jieba分词、停用词过滤；每条评论内词项去重后计算文档频数，另报告去重发言用户数。'],
        ['覆盖边界','仅描述已采集评论；同一用户的重复发言保留，不将评论次数视为独立参与人数。'],
    ],[22,78])
    comment_words+=fig('14_comment_words','图0　常见词的评论文档频数占比；分母为11,595条评论。词语至少覆盖5位发言用户，各词可在同一评论中共现。')
    comment_words+=para(f'清理后评论字符数中位数为{c["median_clean_length"]:.0f}，其中{c["markers_or_symbols_only"]:,}条（{c["markers_or_symbols_only_share"]:.1%}）仅有标记或符号。'
        f'“加油”出现于{int(words.loc["加油","comments"]):,}条评论、覆盖{int(words.loc["加油","senders"]):,}位用户；'
        f'“谢谢”出现于{int(words.loc["谢谢","comments"]):,}条、覆盖{int(words.loc["谢谢","senders"]):,}位用户。频数与用户覆盖反映不同侧面，常见短句不一定意味着广泛参与。')
    comment_words+=note('分词、编码规则及校验值见comment_text_config.json与comment_text_summary.json；常见词仅描述可见语言，不作为完整情感或支持类型分类。')
    feature_rows=[]
    for key,rule in rules.items():
        item=c['features'][key]
        feature_rows.append([rule['label'],'、'.join(rule['terms']),f'{item["hits"]:,}（{item["share"]:.1%}）',str(item['senders_hit'])])
    comment_expressions=table(['字面特征','完整规则：含任一项记1','评论数与占比','覆盖用户'],feature_rows,[19,43,23,15])
    comment_expressions+=fig('15_comment_expressions','图0　按发言者是否为所属帖子的作者分组，比较四项字面特征；分母分别为该角色的全部已采集评论，各项可重叠。')
    comment_expressions+=para(f'其他用户发言中，鼓励或赞许词命中率为{hits("其他用户发言","encouragement").share:.1%}，'
        f'帖主发言中为{hits("帖主发言","encouragement").share:.1%}；感谢词则分别为{hits("其他用户发言","thanks").share:.1%}和{hits("帖主发言","thanks").share:.1%}。'
        '在所选规则下，两类角色的常见回应存在差异。后续网络分析进一步描述回应指向和接收分布，未逐线程检验“鼓励—感谢”的固定回应链条。')
    comment_expressions+=note('规则于本轮首次统计前固定，不使用点赞指标。未作人工语义效度验证，未命中不等于没有相应含义；问号也不等于真实提问。角色按每条评论界定，同一用户在不同帖子中可处于不同角色，用户覆盖不可相加。')

    network_rules=para('以下将分析单位由评论文本转换为用户间的有向互动。内容统计描述“说了什么”，'
        '网络描述“谁回应谁”；两者均来自已采集评论，但统计分母和指标含义分别定义。')+take('评论关系的识别与建图规则')
    concentration=BeautifulSoup(take('前10位接收者获得54.0%的互动事件'),'html.parser')
    for heading in concentration.find_all('h2'):
        if heading.get_text()=='点赞与评论反映不同的互动侧面':
            heading.find_next_sibling('p').decompose();heading.decompose()

    conclusion=elements(take('研究结论、实践启示与后续设计'))
    discussion=table(['问题','综合回答'],[
        ['RQ1：样本分布','点赞存在长尾，作者发帖量和内容形式差异明显；正文覆盖不均，低频特征的作者内变动有限。'],
        ['RQ2：文本与点赞','主回归及主题子样本回归均缺少明确的关联证据，分别受到字面测量和有效正文筛选的限制。'],
        ['RQ3：评论内容与结构','鼓励、赞许、感谢等字面表达具有可见分布；帖主与其他用户的发言特征不同，评论网络呈现围绕帖主的回应与较集中的接收结构。'],
    ],[28,72])
    discussion+='<h2>原始差异与条件关联为何需要区分</h2>'+para('积极表达词命中帖的原始平均点赞较高，控制作者与情境后的系数却为负，'
        '说明原始组间差异与作者内比较并不一致。该负系数的证据又受到BH校正和PPML比较限制。'
        '由此能够支持的判断是：仅凭高赞帖中的常见表达推导内容策略并不充分；当前结果尚不能确定差异由哪些具体机制形成。')
    discussion+='<h2>评论内容与关系结构如何互补</h2>'+para('评论文本显示，所选鼓励或赞许词更多出现在其他用户发言中，感谢词更多出现在帖主发言中；'
        '网络显示，多数明确回复由帖主发出。这两个侧面共同描绘了围绕帖主展开的交流，但尚未检验具体词语与回应方向的逐条对应，'
        '也未证明这种结构提升了点赞、运动坚持或交流质量。')
    discussion+=box('总体解释','文本回归与评论分析分别刻画帖子反馈和回应关系。前者提供条件关联证据，后者提供内容与结构描述；'
        '本研究未识别“文本—评论关系—点赞”的因果路径，也未比较内容与关系对点赞的影响大小。')
    limitations=table(['分析范围','能够支持的判断'],[
        ['全样本帖子：9,532条、100位作者','词典回归的条件关联；无可用正文者通过指示变量保留，无法恢复其图片或视频中的表达。'],
        ['主题子样本：2,470条、86位作者','满足文本条件的正文中的主题分布和条件关联；不能代表全部帖子。'],
        ['已采集评论与网络','评论文本覆盖2,910位发言者；网络含2,932个有边节点，包含接收者。仅适用于采集到的关系与评论窗口。'],
    ],[36,64])
    limitations+='<h2>主要限制</h2>'+str(conclusion[6])
    limitations+=para('评论字面规则未经过独立人工语义验证，频数较高或角色命中率不同，不能直接解释为情感强度或社会支持水平。'
        '评论与帖子均存在观察边界；首周截点可减少晚期评论的影响，却无法补回未采集记录。')
    limitations+=para('不显著结果表示当前数据与测量下的证据有限，并非证明表达没有作用。主题回归与主回归的范围不同，'
        '两类结果应分别解释；作者固定效应和聚类推断也不能消除全部遗漏变量或识别因果。')

    recommendations=para('建议首先围绕现有证据改进内容评价与互动统计，再考虑需要验证的服务方案。')
    recommendations+=table(['研究依据','可直接落实的改进'],[
        ['词典与主题关联证据有限','减少依据单一词语、简易情感标签或原始平均点赞评价内容；记录内容情境、曝光和统一反馈窗口后再比较。'],
        ['常见短句的次数与用户覆盖不同','同时报告评论事件数、去重参与人数与重复短句情况，区分发言频繁和参与广泛。'],
        ['网络指标受指向规则、窗口和样本边界影响','评价互动时注明根评论与明确回复、自我事件处理及评论时间范围；补充采集覆盖后再讨论总体关系结构。'],
    ],[35,65])
    recommendations+='<h2>后续研究的优先事项</h2>'+para('优先补充真实曝光、统一观察窗口和更完整的评论记录，并用独立双人编码核查文本规则，'
        '再扩展图片文字和视频语音等内容。若进一步评估表达提示或同伴互助方案，应以作者为单位预先设置对照，'
        '明确点赞、独立互动人数和回复质量等评价口径。上述干预尚未实施，现有结果未估计其效果。')

    groups=[
        [('研究题目与两条分析线',topic)],
        [('研究背景与研究意义',rationale),('研究问题与分析目标',questions)],
        [('数据来源、样本范围与清洗',take('数据来源、样本范围与清洗')),
         ('正文覆盖与缺失分布',take('正文缺失与内容形式、作者均有关联')),
         ('点赞分布与作者发帖差异',take('点赞分布长尾明显，均值高于中位数')),
         ('内容形式与点赞表现',take('不同内容形式的点赞表现存在差异'))],
        [('正文预处理与变量构建',take('正文预处理与变量构建')),
         ('词典编码规则与解释范围',take('词典编码规则及其解释范围')),
         ('文本特征的分布与作者覆盖',take('文本特征的分布与作者覆盖')),
         ('语义测量局限与抽查',take('词典编码的语义局限与抽查')),
         ('从组间差异到作者内比较',take('从组间差异到作者内比较')),
         ('固定效应模型与统计推断',take('固定效应模型与统计推断')),
         ('主回归结果',take('核心文本特征的关联证据有限')),
         ('回归系数的量级与解释',take('回归系数的量级与解释')),
         ('样本与模型设定的稳健性',take('积极表达的负关联对模型设定敏感')),
         ('逐作者剔除的敏感性',take('逐作者剔除后的系数敏感性'))],
        [('文本主题分析的目的与方法',topic_method),('主题分布及其作者集中度',topic_description),
         ('主题权重与点赞的条件关联',topic_regression),('评论文本的范围与常见词语',comment_words),
         ('评论字面表达与发言角色',comment_expressions),('评论关系识别与建图规则',network_rules),
         ('网络连通性与互惠性',take('评论互动网络的连通性与互惠性')),
         ('互动接收的集中度',str(concentration)),('评论时序与回应角色',take('多数明确回复由帖主发出')),
         ('评论观察窗口的敏感性',take('首周网络的互惠性更高，集中度略低'))],
        [('内容关联与互动结构的综合解释',discussion),('证据边界与研究局限',limitations)],
        [('基于现有证据的建议',recommendations)],
    ]
    output=[cover];figures=0
    for chapter,sections in enumerate(groups,1):
        chapter_name=f'第{CHINESE_NUMBERS[chapter-1]}章 {CHAPTERS[chapter-1]}'
        for index,(heading,body) in enumerate(sections,1):
            section=f'{chapter}.{index}'
            body=body.replace('文本测量核查部分','第4.4节').replace('第13节','第4.4节')
            if section=='4.10':
                body+=para('本章完成了字面表达的测量、作者内比较与敏感性检验。下一章先从内容主题补充回答RQ2，'
                           '随后转向评论文本和用户关系，回答RQ3。')
            soup=BeautifulSoup(body,'html.parser')
            for h in soup.find_all('h2'):h.name='h3'
            for caption in soup.find_all('figcaption'):
                figures+=1;caption.string=re.sub(r'^图\d+',f'图{figures}',caption.get_text())
            output.append({'chapter':chapter,'chapter_name':chapter_name,'chapter_start':index==1,
                           'section':section,'anchor':f'section-{chapter}-{index}','kicker':chapter_name,
                           'title':heading,'body':str(soup)})
    reference=take('参考文献与复现说明')
    appendix=take('课程要求与小组分工')
    appendix=appendix.replace('封面、研究背景；成员留待真实填写','第1—2章及封面；成员待据实填写')
    appendix=appendix.replace('数据、描述统计与文本分析部分；代码及Notebook','第3章及第4.3节；代码与已执行Notebook')
    appendix=appendix.replace('文本编码、主题与回归部分；特征表及模型结果','第4章与第5.1—5.3节；特征表及模型结果')
    appendix=appendix.replace('已完成词典内容分析、分词统计及评论网络','第5章；帖子主题、评论文本与评论网络')
    appendix=appendix.replace('回归及网络结果的解释与讨论','第6章综合解释与第7章建议')
    for heading,anchor,body in [('参考文献与复现说明','references',reference),('附录：课程要求与小组分工','appendix',appendix)]:
        output.append({'kicker':'参考资料' if anchor=='references' else '附录','title':heading,'anchor':anchor,'body':body})
    assert used==set(sources),set(sources)-used
    assert figures==13,figures
    return add_contents(output)


def add_contents(pages):
    entries=[]
    for physical,page in enumerate(pages[1:],4):
        page['physical_page']=physical
        if page.get('chapter_start'):
            entries.append({'level':1,'section':'','title':page['chapter_name'],'anchor':f'chapter-{page["chapter"]}',
                            'page':physical,'chapter':page['chapter']})
        entries.append({'level':2 if page.get('section') else 1,'section':page.get('section',''),
                        'title':page['title'],'anchor':page['anchor'],'page':physical,'chapter':page.get('chapter',8)})
    contents=[]
    for index,batch in enumerate(([e for e in entries if e['chapter']<=4],[e for e in entries if e['chapter']>=5]),1):
        links=[]
        for entry in batch:
            label=f'{entry["section"]}　{entry["title"]}' if entry['section'] else entry['title']
            links.append(f'<a class="toc-entry toc-level-{entry["level"]}" href="#{entry["anchor"]}"><span class="toc-title">{html.escape(label)}</span><span class="toc-leader" aria-hidden="true"></span><span class="toc-page">{entry["page"]}</span></a>')
        contents.append({'kicker':f'目录 · {index} / 2','title':'目录' if index==1 else '目录（续）',
                         'body':'<nav class="toc" aria-label="报告目录">'+''.join(links)+'</nav>','toc_entries':batch})
    return [pages[0],*contents,*pages[1:]]
