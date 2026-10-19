"""Integrate reviewed exploratory results into the academic report and slides."""
from pathlib import Path
import json
import re
import pandas as pd
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    r=ROOT/'results'
    s=json.loads((r/'extension_summary.json').read_text())
    labels=json.loads((ROOT/'code/topic_labels.json').read_text())['labels']
    load=lambda name:pd.read_csv(r/f'extension_{name}.csv')
    return s,labels,load


def extend_report(pages,ui):
    if not (ROOT/'results/extension_summary.json').exists():return pages
    s,labels,load=inputs();para,table,fig,note,box,ul=[ui[n] for n in ['para','table','fig','note','box','ul']]
    new={}
    def section(category,title,body):return {'kicker':category,'title':title,'body':body}
    coverage=load('coverage_media');c=s['coverage']
    rows=[]
    media={'img':'图片','none':'无媒体','video':'视频','txt':'纯文字'}
    for r in coverage.itertuples():rows.append([media[r.contentTypeStr],f'{r.posts:,}',f'{r.visible:,}',f'{r.visible_share:.1%}'])
    new['数据来源、样本范围与清洗']=[section('数据覆盖','正文缺失与内容形式、作者均有关联',
        fig('08_text_coverage','图8　不同内容形式的正文覆盖率，以及100位作者的发帖数与正文覆盖率。覆盖率按原始content是否存在可见字符计算。')+
        table(['内容形式','帖子数','有可用正文','正文覆盖率'],rows)+
        para('正文缺失并未均匀分布在不同形式的帖子中：“无媒体”帖的正文覆盖率仅为0.1%，图片帖为76.0%，视频帖为89.1%，纯文字帖则为100%。这些差异可能与记录生成方式或采集逻辑有关，现有字段不足以确认具体原因。')+
        para(f'作者之间也存在明显差异：{c["authors_without_visible_body"]}位作者的帖子均无可用正文，{c["authors_all_bodies_visible"]}位作者的帖子均有正文，作者正文覆盖率的中位数为{c["author_visible_share_median"]:.1%}。因此，正文缺失不能简单视为独立、随机发生的现象。原模型保留缺失指示变量和内容形式控制，并以“仅可见正文”设定进行比较；相关结果仍仅适用于当前可观测的数据。')+
        note('“有可用正文”包含仅有表情或平台标记的记录。清理后有非空正文的帖子为5,414条；后续主题模型进一步限制有效词数。'))]

    topics=load('topics');topic=s['topics'];reg=load('topic_regression')
    topic_index=topics.set_index('topic')
    rows=[]
    for r in topics.itertuples():
        rows.append([labels[str(r.topic)],'、'.join(r.keywords.split('、')[:6]),f'{r.dominant_documents:,}',f'{r.dominant_share:.1%}'])
    methodology=section('探索性主题分析','TF-IDF与非负矩阵分解的主题分析',
        para('原词典能够识别事先定义的字面特征，但覆盖范围较窄。为考察词典之外的内容差异，进一步将清理后的正文进行中文分词和停用词过滤，以TF-IDF构建文档—词项矩阵，再采用非负矩阵分解（NMF）提取五种潜在表达模式。[7] 主题数在本次扩展模型首次拟合前固定，不依据点赞结果选择。')+
        para('NMF将非负矩阵X近似分解为W与H的乘积：W描述每条文档的成分权重，H描述每个成分的词项权重。本研究将成分数设为5，作为便于描述的分析粒度，不将其视为语料唯一或最优的主题划分。')+
        table(['环节','设定'],[
            ['纳入标准','每帖至少含3个过滤后的有效词，并在最终词表中有非零表示。'],
            ['词项过滤','至少出现于5帖，最高文档比例0.9；词表上限4,000。'],
            ['模型与命名','NMF设为5个主题；依据关键词及不含点赞指标的正文抽查命名。'],
            ['权重解释','先校正NMF成分的任意尺度，再归一化文档权重。权重表示相对贡献，不是主题后验概率。'],
            ['稳定性','另用3个随机种子重复初始化，以成分余弦相似度匹配主题，比较前10关键词。']], [22,78])+
        para(f'以{topic["fitted_documents"]:,}条满足词项要求的正文拟合模型，其中{topic["near_zero_contribution_documents"]}条的成分贡献接近零，不作强制归类；其余{topic["documents"]:,}帖、{topic["authors"]}位作者进入主题描述和回归，词表含{topic["vocabulary"]:,}项。这一子样本覆盖全部帖子的{topic["documents"]/9532:.1%}，对较长、信息较充分的正文代表性更强。')+
        table(['主题名称','主要关键词','主导文档数','主导占比'],rows,[24,44,16,16])+
        note('主导主题为每帖权重最高的成分，五类主导文档互斥；一条正文的软权重仍可分布在多个主题中。'))
    topic_rows=[]
    for r in reg.itertuples():topic_rows.append([labels[str(r.topic)],f'{r.coef:.3f}',f'[{r.ci_low:.3f}, {r.ci_high:.3f}]',f'{r.p:.3f}',f'{r.q_bh:.3f}'])
    interpretation=section('探索性主题分析','主题分布及其作者集中度',
        fig('09_topics','图9　主题模型子样本中五类主导主题的占比。主题命名基于词项与正文内容，不使用点赞数。')+
        para(f'“运动与训练交流”和“生活感悟与问候”分别占主导文档的{topic_index.loc[2,"dominant_share"]:.1%}和{topic_index.loc[4,"dominant_share"]:.1%}。另有两个规模较小、形式较固定的记录主题：靠墙静蹲记录中，最大作者贡献91.8%的主导文档；骑行里程记录中，该比例为68.2%。因此，这些主题既反映内容差异，也反映特定作者反复使用的表达模板。')+
        table(['相对“运动与训练交流”','系数','95%聚类区间','原始p','BH q'],topic_rows,[34,14,26,13,13])+
        para(f'探索性回归在上述{topic["documents"]:,}帖中保留原模型控制项，并加入四个主题权重；基准主题按主导文档数确定。四项权重作为独立的探索性检验家族进行BH校正。联合检验p={topic["joint_topic_p"]:.3f}，各项校正后均未达到5%显著性水平，未提供足够证据支持主题权重在原有控制之外具有明确关联。')+
        note(f'三次初始化的前10关键词平均Jaccard为{topic["mean_top10_jaccard"]:.3f}，仅表明对初始化较稳定。表内系数对应主题权重变化1单位；10个百分点的变化对应0.1β。区间以主题特征为给定输入，未计入主题估计的不确定性。'))
    new['文本特征的分布与作者覆盖']=[methodology,interpretation]

    influence=load('author_influence_summary').set_index('term')
    positive=influence.loc['positive_expression'];social=influence.loc['social_address']
    influence_rows=[]
    label_map={'log_length':'正文长度','self_discipline':'自律/目标词','social_address':'社交称呼/互助词','positive_expression':'积极表达词','question':'问号'}
    for t,r in influence.iterrows():influence_rows.append([label_map[t],f'{r.min_coefficient:.3f}',f'{r.max_coefficient:.3f}',f'{int(r.positive_runs)}/{int(r.negative_runs)}'])
    influence_page=section('作者影响检验','逐作者剔除后的系数敏感性',
        para('作者固定效应可以控制稳定的作者差异，但个别作者仍可能为某些文本特征提供较多变化。为检验这种影响，依次剔除一位作者，重新估计原主模型，共进行100次计算；模型控制项与变量定义保持一致。该检验观察点估计的敏感性，不将100次结果作为额外的显著性检验。')+
        fig('12_author_influence','图12　逐次剔除一位作者后的五项核心系数分布。箱体表示中间50%，散点表示箱须之外的结果。')+
        table(['特征','最小系数','最大系数','正向/负向次数'],influence_rows,[38,20,20,22])+
        para(f'积极表达词在100次剔除中均为负，系数范围为[{positive.min_coefficient:.3f}, {positive.max_coefficient:.3f}]，说明其OLS负向点估计并非由单一作者决定。但符号稳定不能替代统计推断，原BH校正和PPML结果仍显示证据有限。社交称呼/互助词在{int(social.positive_runs)}次剔除后转为正值，与原系数接近零的结果一致。')+
        note('逐作者结果及以主模型聚类标准误为单位的系数变化见extension_author_influence.csv。'))

    new['积极表达的负关联对模型设定敏感']=[influence_page]

    comments=s['comments'];network=load('window_networks');reply_share=comments['reply_role_counts']['帖主回复其他用户']/comments['reply_events']
    comment_roles=section('评论时序与角色','多数明确回复由帖主发出',
        fig('13_comment_timing_roles','图13　已采集评论的发生时序，以及4,902次非自我明确回复的角色分布。时序分母为全部11,595条去重评论。')+
        para(f'在已采集评论中，{comments["within_24_hours_share"]:.1%}发生于发帖后24小时内，{comments["within_7_days_share"]:.1%}发生于7天内，间隔中位数为{comments["median_lag_hours"]:.1f}小时。这些比例描述记录的相对时间分布；由于各帖评论覆盖情况未知，不能将其视为完整的评论增长曲线。')+
        table(['明确回复的角色','事件数','占明确回复比例'],[
            ['帖主回复其他用户','4,361',f'{4361/4902:.1%}'],['其他用户回复帖主','444',f'{444/4902:.1%}'],['其他用户彼此回复','97',f'{97/4902:.1%}']], [54,22,24])+
        para(f'帖主发出的回复占{reply_share:.1%}，其他用户彼此回复仅占{97/4902:.1%}。这表明，当前样本的显式回复主要表现为围绕帖主展开的交流。结合根评论指向帖主的建边方式，原网络的互惠性应更多从这种回应结构理解，而非直接解释为用户间普遍存在的横向交流。')+
        note('有781条回复的直接被回复评论未被采集，但其replyUserId可用，且parentId均能关联到根评论；角色划分因此使用明确用户指向，线程分析使用parentId。'))
    network_rows=[[r.window,f'{r.events:,}',f'{r.nodes:,}',f'{r.edges:,}',f'{r.reciprocity:.1%}',f'{r.top10_share:.1%}'] for r in network.itertuples()]
    timing_window=section('观察窗口敏感性','首周网络的互惠性更高，集中度略低',
        table(['评论窗口','事件数','节点数','有向边','互惠率','前10接收占比'],network_rows,[25,15,15,15,15,15])+
        para('将每帖发出后的7天作为统一的相对时间截点，得到9,451次非自我互动、1,376个有边节点和2,278条边。相比使用全部已采集互动，首周网络的互惠率由49.6%提高至74.1%，前10位账号的接收占比由54.0%降至48.3%。这表明，晚期评论的纳入会改变网络的规模与结构描述。')+
        '<h2>根评论线程中的帖主参与</h2>'+para(f'共有{comments["incoming_root_threads"]:,}条外来根评论；其中{comments["threads_with_observed_author_reply"]:,}个线程内观察到帖主参与回复，占{comments["observed_author_reply_thread_share"]:.1%}。在这些有帖主回复的线程中，首次帖主回复距离根评论的中位间隔为{comments["conditional_author_reply_median_hours"]:.2f}小时。这里的参与比例是采集记录中的观测比例，未见回复的线程也可能存在未采集的回应。')+
        '<h2>对原网络结果的补充解释</h2>'+para('两种窗口的节点和边集合不同，指标差异不代表同一群体的互惠行为发生了时间趋势。首周截点减少了跨度极长的晚期评论，却无法补回未采集记录，也不能证明每个帖子都获得了完整的7天观察。网络结论因此应同时注明评论窗口、采集边界和角色构成。')+
        note('窗口指标见extension_window_networks.csv。回复时延仅在已观测到帖主参与的线程中计算，未将缺失回应当作无限等待或零时延。'))
    new['前10位接收者获得54.0%的互动事件']=[comment_roles,timing_window]

    # Update the reader-facing argument to cover the new experiments.
    cover=BeautifulSoup(pages[0]['body'],'html.parser');paragraphs=cover.find_all('p',recursive=False)
    abstract=[p for p in paragraphs if 'byline' not in p.get('class',[]) and 'note' not in p.get('class',[])]
    abstract[0].string='本研究以Keep社区100位作者的9,532条帖子及去重后的11,595条评论为样本，考察文本表达与互动反馈的关系。研究将正文转换为词典特征并估计作者与日期固定效应模型，通过调整样本范围、更换模型及逐作者剔除开展敏感性检验；进一步采用TF-IDF与NMF识别内容主题，并结合评论时序与回复角色分析互动网络。'
    abstract[1].string='五项核心文本特征的联合检验不显著（p=0.130），新增解释度为0.065个百分点。积极表达词呈负向关联，但BH校正后q=0.079，PPML区间也包含零。主题权重的联合检验p=0.166，各项经BH校正后均未达到5%显著性水平，现有结果尚不足以支持特定字面表达或内容主题与点赞存在明确、稳定的关联。'
    abstract[2].string=f'已采集的明确回复中，{reply_share:.1%}由帖主发给其他用户，表明交流主要围绕帖主展开。网络前10位账号接收54.0%的互动，但该比例和互惠率随评论窗口变化。总体而言，现有数据尚不足以支持固定的高赞表达策略；更完整的曝光、内容及关系记录有助于进一步检验这一问题。'
    pages[0]['body']=str(cover)
    pages[1]['body']+=note('主题建模、作者剔除及评论时序为2026-10-17追加的探索性分析，保留原五项核心检验作为主分析。主题数在本轮首次拟合前固定；主题名称和基准依据文本内容与频数确定。')
    conclusion=pages[-3]['body']
    conclusion=conclusion.replace('<h2>后续研究设计</h2>',
        '<h2>扩展分析的综合判断</h2>'+para('词典特征与潜在主题分别从字面表达和内容模式刻画正文，两类回归均未提供明确、稳定的点赞关联证据。逐作者剔除说明积极表达词的OLS负向点估计并非由单一作者决定，但这一发现仍需结合BH校正与PPML结果理解。评论角色和时间窗口分析则表明，网络互惠性与接收集中度的解释，需要考虑帖主回应及晚期评论的纳入范围。')+'<h2>后续研究设计</h2>')
    pages[-3]['body']=conclusion
    pages[-2]['body']=pages[-2]['body'].replace('</div>',
        para('[7] scikit-learn官方文档：NMF（1.5系列），用于非负矩阵分解与主题提取。<a href="https://scikit-learn.org/1.5/modules/generated/sklearn.decomposition.NMF.html">官方链接</a>。访问：2026-10-17。')+'</div>',1)
    pages[-1]['body']=pages[-1]['body'].replace('报告02—07及代码、Notebook','数据、描述统计与文本分析部分；代码及Notebook').replace('报告05—13；post_features.csv与回归结果','文本编码、主题与回归部分；特征表及模型结果').replace('报告10—17；明确不显著结果及局限','回归及网络结果的解释与讨论').replace('16页PPTX','21页PPTX')
    out=[]
    for p in pages:
        out.append(p);out.extend(new.get(p['title'],[]))
    number=0
    for i,p in enumerate(out):
        if i:p['kicker']=f'{i:02d} · '+p['kicker'].split(' · ')[-1]
        p['body']=p['body'].replace('第13节','文本测量核查部分')
        soup=BeautifulSoup(p['body'],'html.parser')
        for caption in soup.find_all('figcaption'):
            number+=1;caption.string=re.sub(r'^图\d+',f'图{number}',caption.get_text())
        p['body']=str(soup)
    return out


def extend_slides(specs):
    if not (ROOT/'results/extension_summary.json').exists():return specs
    s,labels,load=inputs();new={};topic=s['topics'];frequencies=load('topics').set_index('topic')
    new['数据核查决定能回答什么']=[('正文覆盖取决于帖子形式与作者',[
        '无媒体帖正文覆盖率0.1%，图片76.0%，视频89.1%，纯文字100%。',
        '5位作者无可用正文；26位作者全部帖子有正文。',
        '保留缺失指示和形式控制；主题分析只使用信息较充分的正文。'],'08_text_coverage',
        '说明正文缺失不是均匀分布现象。记录生成方式和采集逻辑可能参与其中，无法凭这些字段认定缺失原因。')]
    new['文本规模：注意分母和低频特征']=[('NMF补充识别内容表达模式',[
        f'{topic["documents"]:,}帖、{topic["authors"]}位作者，{topic["vocabulary"]:,}词项；主题数固定为5。',
        f'运动与训练交流{frequencies.loc[2,"dominant_share"]:.1%}，生活感悟与问候{frequencies.loc[4,"dominant_share"]:.1%}。',
        '静蹲、骑行主题集中于少数作者，反映重复记录习惯。'],'09_topics',
        '主题根据不含点赞数的词项和例文命名。主导类别互斥，软权重可以混合。静蹲主题最大作者占91.8%，骑行主题68.2%。'),
        ('主题回归仍未提供明确的增量证据',[
            '以“运动与训练交流”为基准，加入4个主题权重。',
            f'联合检验p={topic["joint_topic_p"]:.3f}；4项BH校正后均未达到5%显著性水平。',
            '初始化关键词稳定，但不能代替抽样稳定性和测量效度。'],None,
            '主题模型纳入至少3个有效词的正文，并排除8条成分贡献近零的记录，占全部帖25.9%。回归控制原词典及作者、日期等因素，区间未包含主题估计误差。')]
    new['稳健性：结论依赖尺度与规格']=[('逐作者剔除：点估计与统计证据分开判断',[
        '逐次剔除1位作者，重复100次主模型估计。',
        '积极表达词始终为负，范围[-0.100,-0.074]。',
        '符号稳定不能替代BH校正和PPML结果；社交词在11次剔除后转正。'],'12_author_influence',
        '这一检查考察是否某一个作者决定结果，不新增100轮显著性判断。原始主检验和探索性检验保持分开。')]
    new['互动集中，但样本边界影响很大']=[('网络互惠主要体现围绕帖主的回应',[
        '已采集评论中64.5%在24小时内，82.2%在7天内。',
        '4,902次明确回复中，89.0%由帖主发出；用户彼此回复仅2.0%。',
        '首周互惠率74.1%，全部记录49.6%；窗口和采集边界影响结构。'],'13_comment_timing_roles',
        '比例都以已采集记录为条件。首次帖主回应的中位时延2.05小时仅在观测到回应的线程中计算，未见回应不等于没有回应。')]
    out=[]
    for s0 in specs:
        out.append(s0);out.extend(new.get(s0[0],[]))
    for i,(title,bullets,img,speaker) in enumerate(out):
        if title=='主结果：没有明确的高赞用词公式':title='主结果：核心文本特征的关联证据有限'
        speaker=speaker.replace('报告第09节','报告中的模型设定部分')
        if title=='小组分工与讨论':
            bullets=['成员A【待填写】：研究问题与背景（1—3页）','成员B【待填写】：数据、文本与主题（4—10页）',
                '成员C【待填写】：回归、检验与测量核查（11—15页）','成员D【待填写】：网络、建议与总结（16—21页）','建议分工须按真实人数和贡献修订。']
        if title=='结论、局限与可复现性':
            bullets[0]='词典特征与主题权重的回归均未提供明确、稳定的点赞关联证据。'
            speaker='回到三个研究问题，概括内容分布、条件关联和互动结构的结果。主题、作者剔除及评论时序属于探索性补充，完整参数及输出见附带Notebook与代码。'
        out[i]=(title,bullets,img,speaker)
    return out
