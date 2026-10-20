"""Create the requested local academic report, PowerPoint and executed notebook.

The assignment explicitly requires PDF/PPT; this is a file-only academic package.
All text and tables are generated from reviewed local results, not demo values.
"""
from pathlib import Path
import argparse
import html
import json
import os
import textwrap
import pandas as pd
import numpy as np
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement
from docx import Document
from docx.shared import Cm, Pt as DPt
from docx.oxml import OxmlElement as DOxmlElement
from docx.oxml.ns import qn
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]
S=json.loads((ROOT/'results/summary.json').read_text())
CFG=json.loads((ROOT/'code/project_config.json').read_text())
C=pd.read_csv(ROOT/'results/regression_coefficients.csv')
F=pd.read_csv(ROOT/'results/model_fit.csv')
T=pd.read_csv(ROOT/'results/text_features_summary.csv')
D=pd.read_csv(ROOT/'results/descriptive_statistics.csv').set_index('variable')
N=S['network']
MAIN=C.loc[C.model.eq('M3_作者与日期固定效应')].set_index('term')
FOCAL=['log_length','self_discipline','social_address','positive_expression','question']
TITLE=CFG['title']
SUBTITLE=CFG['subtitle']
BLUE='#356D9A'; DARK='#213444'; GOLD='#B88425'


def esc(x):return html.escape(str(x))
def num(x,d=3):return f'{x:.{d}f}'
def pct(x,d=1):return f'{100*x:.{d}f}%'
def pval(x):return '<0.001' if x<.001 else f'{x:.3f}'
def para(s):return '<p>'+s+'</p>'
def ul(items):return '<ul>'+''.join('<li>'+x+'</li>' for x in items)+'</ul>'
def box(title,s):return f'<div class="callout"><strong>{title}</strong><p>{s}</p></div>'
def table(headers,rows,widths=None):
    col=''
    if widths:col='<colgroup>'+''.join(f'<col style="width:{w}%">' for w in widths)+'</colgroup>'
    return '<table>'+col+'<thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in rows)+'</tbody></table>'
def fig(name,caption):return f'<figure><img src="figures/{name}.png"><figcaption>{caption}</figcaption></figure>'
def note(s):return '<p class="note">'+s+'</p>'
def formula(s):return '<div class="formula">'+s+'</div>'


def report_pages():
    pages=[]
    def add(kicker,title,body):pages.append({'kicker':kicker,'title':title,'body':body})
    add('SOCIAL MEDIA DATA ANALYSIS · 小组项目',TITLE,
        f'<div class="subtitle">{SUBTITLE}</div><div class="coverline"></div>'
        f'<p class="byline">{CFG["group"]}<br>{CFG["members"]}</p>'
        f'<div class="cover-meta">课程：社交媒体与网络分析<br>资料范围：课程提供的 Keep 社区帖子及评论<br>帖子发布时间：2020-11—2020-12（UTC）<br>分析更新日期：{CFG.get("analysis_date", "2026-10-16")}</div>'
        '<h2>摘要</h2>'+para(f'本研究以Keep社区100位作者的9,532条帖子为样本，考察文本表达与点赞表现的关系。通过词典编码，将正文转换为长度、自律/目标词、社交称呼/互助词、积极表达词及问号等变量，并以ln(1+点赞数)为因变量建立作者与日期固定效应模型。在此基础上，利用去重后的11,595条评论构建有向加权互动网络，分析用户间的互动分布。')+
        para(f'回归结果表明，在控制作者、发帖日期、内容形式等因素后，五项核心文本特征的联合检验未达到统计显著水平（p={S["models"]["joint_focal_p"]:.3f}），对模型解释度的增量为{100*S["models"]["incremental_r2_text"]:.3f}个百分点。积极表达词呈负向关联，但经BH多重检验校正后q={MAIN.loc["positive_expression","q_bh_focal"]:.3f}，且PPML计数模型的置信区间包含零，说明这一关联的证据仍不充分。')+
        para(f'评论网络呈现较高的互动接收集中度，前10位账号接收了{pct(N["top10_received_share"])}的事件。这一结果受到样本选取与建边规则影响，适用于描述已采集的互动关系。总体而言，现有数据尚不足以支持通过特定词汇稳定提高点赞的策略；后续研究可结合曝光记录和用户层面的对照实验，进一步检验表达方式与互动质量的关系。')+
        note('关键词：健身社区；文本表达；点赞；固定效应模型；互动网络。'))
    add('01 · 研究背景与意义','健身社区中的内容表达与互动反馈',
        para('健身社区既是用户记录运动的空间，也是分享感受、交流经验和获得同伴反馈的场所。点赞作为一种可观察的互动行为，为研究内容表达与社区反馈的关系提供了切入点。不过，点赞还受到作者既有受众、媒体形式及曝光机会等因素影响。因此，有必要在控制相关因素后，考察文本特征与点赞数之间的关系。')+
        para('Richardson等（2010）的随机试验发现，增加在线社区功能有助于降低项目流失，但组间步数增幅未呈现显著差异。[1] 这说明社区参与和运动行为变化需要分别衡量。据此，本研究将分析范围限定为平台内的互动反馈，研究结论不延伸至运动坚持、健康或体重变化。')+
        '<h2>研究问题</h2>'+table(['编号','可检验问题','分析路径'],[
            ['RQ1','样本帖子、表达方式及点赞如何分布？','描述统计、正文分词与词汇命中统计'],
            ['RQ2','同一作者不同帖子的文本特征与点赞是否相关？','作者与日期固定效应回归；稳健性比较'],
            ['RQ3','采集到的评论如何连接用户？互动集中在哪里？','有向加权网络、互惠率、接收集中度']], [10,56,34])+
        '<h2>研究预期与分析定位</h2>'+ul(['自律与目标相关词汇可能使运动经历更易理解，社交称呼和互助表达可能为读者提供参与交流的线索。本研究将这些解释作为待检验的研究预期。',
            '积极表达与问号的关联方向不作预设；正文长度用于衡量表达规模。上述四类二元特征与长度共同构成五项核心检验。',
            '词典与模型设定在本次首次拟合前确定，并完整报告各项结果。由于未进行事前注册，研究定位为探索性分析。'])+
        note('方法参考：《内容分析与自然语言处理》第10、14、18页关于内容分析与文本预处理的讨论。[3]'))
    add('02 · 数据来源与清洗','数据来源、样本范围与清洗',
        table(['文件','粒度与规模','用途'],[
            ['sample_post_2022.csv','每行1帖；9,532帖；100位作者','全部描述统计与回归'],
            ['sample_comment_2022.csv','原始13,511行；去重后11,595条评论','仅用于评论覆盖说明与网络'],
            ['KeepData_dictionary.pdf','课程提供的字段解释','确定ID、点赞、父评论与直接回复对象']], [33,34,33])+
        '<h2>数据核查与处理</h2>'+table(['步骤','发现及处理'],[
            ['主键与重复','帖子ID全部唯一。评论ID有1,916行重复；逐字段验证没有冲突，按cmtId保留1条。'],
            ['表关联','去重后的评论均能关联到帖子。1,323帖有采集到的评论；其余8,209帖的评论覆盖情况未知，保留为缺失。'],
            ['时间','原字段以Z结尾，按UTC解析；发帖日期、时段统一转换为Asia/Shanghai。北京时间末尾跨至2021-01-01。'],
            ['正文','3,984帖的content为空。保留这些帖子，将文本计数设为0，并以has_text标记是否有可用正文。'],
            ['口径异常','8,286帖的likes大于viewCount（86.9%），两个字段的统计口径与对应关系不明。因此不计算点赞率，也不以浏览数作为计数模型的曝光量偏置项（offset）。'],
            ['极端值','主模型保留全部观测；在稳健性检验中单独剔除点赞最高1%的帖子，检验极端值对结果的影响。']], [17,83])+
        box('观测时间与文件命名','帖子实际发表于2020-11-01至2020-12-31（UTC），评论最晚延续至北京时间2021-08-26。分析以实际时间字段为准。由于数据未提供统一采集时点，各帖点赞的累计观察时长无法确定。')+
        note('数据来源与原文件SHA-256保存在results/summary.json；匿名作者编号及建模特征保存在results/post_features.csv。'))
    statsrows=[]
    for name,label in [('likes','点赞数'),('viewCount','记录浏览数'),('favoriteCount','收藏数'),('length','清理后正文字符数')]:
        r=D.loc[name];statsrows.append([label,num(r['mean'],2),num(r['50%'],0),num(r['95%'],1),num(r['max'],0)])
    add('03 · 描述统计','点赞分布长尾明显，均值高于中位数',
        fig('01_sample_and_likes','图1　全部9,532帖的点赞分布与北京时间逐日发帖数。首末本地日期为不完整日，末端下降不能解释为活跃度骤降。')+
        table(['变量','均值','中位数','95分位数','最大值'],statsrows,[33,17,17,17,16])+
        para(f'样本帖子的平均点赞数为{S["likes_mean"]:.2f}，中位数为25，最大值为5,126，零点赞帖子占{pct(S["likes_zero_share"])}。点赞方差约为均值的{S["likes_variance_mean"]:.1f}倍，反映出明显的离散性和长尾分布。主模型采用ln(1+点赞数)缓和极端值的影响，并通过聚类稳健推断与计数模型检验结果。')+
        para('作者之间的发帖量差异较大：发帖数中位数为66，最多者发布783帖。考虑到同一作者的帖子可能具有相关的未观测特征，回归标准误按作者聚类；同时采用作者等权的设定，检查发帖较多的作者对估计结果的影响。')+
        note('字符数为去URL、成对课程后缀、方括号表情及空白后的字符数；并非纯汉字数。上述分位数基于所有帖子，含无可用正文者。'))
    m=pd.read_csv(ROOT/'results/media_summary.csv')
    mrows=[[{'img':'图片','none':'无媒体','video':'视频','txt':'纯文字'}[r.contentTypeStr],f'{r.n:,}',pct(r.share),num(r.mean_likes,2),num(r.median_likes,0)] for r in m.itertuples()]
    add('04 · 描述统计','不同内容形式的点赞表现存在差异',
        fig('02_media_summary','图2　内容形式及其点赞均值、中位数。类别是原始contentTypeStr，不等同于是否有正文。')+
        table(['形式','帖子数','占比','平均点赞','点赞中位数'],mrows)+
        para('图片和视频帖的原始点赞数明显高于无媒体及纯文字帖。由于不同形式还可能对应不同作者、业务类型和内容，这一差异只能作为描述性结果。后续回归将内容形式纳入控制，以减少其对文本特征比较的干扰。')+
        para('回归保留normal、hiking、run、yoga、cycling、direct与share等原始业务类别，并将发帖时段划分为00—05、06—11、12—17、18—23点。日期固定效应用于控制同一天样本共有的变化；各帖累计观察时长不明的问题仍需在解释结果时予以考虑。')+
        note('输出文件：media_summary.csv、post_type_summary.csv、monthly_summary.csv。北京时间2021年1月仅包含UTC年底跨日的少量帖子，不能与完整月份比较活跃趋势。'))
    add('05 · 文本结构化','正文预处理与变量构建',
        '<div class="pipeline">原始content → 还原换行 → 去URL、课程后缀及表情标记 → 正文字符数与规则匹配 → jieba分词/词频 → 回归特征表</div>'+
        table(['变量','定义与编码','用途'],[
            ['log_length','ln(1+清理后非空白字符数)','核心检验1；控制表达规模'],
            ['self_discipline','含坚持、自律、目标等任一词或明确“第N天”模式=1','核心检验2；自律/目标词命中'],
            ['social_address','含大家、小伙伴、谢谢、一起等任一词=1','核心检验3；社交称呼/互助词命中'],
            ['positive_expression','含开心、快乐、喜欢、哈哈等任一词=1','核心检验4；积极表达词命中'],
            ['question','出现半角?或全角？=1','核心检验5；标点特征'],
            ['has_text','原content经去空白后非空=1','区分无可用正文与可用正文'],
            ['has_tag','hashTags不等于[]记1','话题元数据；不混入正文词典'],
            ['emoji_count','ln(1+方括号表情标记数)','控制标记表达；不代表全部Unicode表情'],
            ['course_ref','原文出现Ⓚ记1','控制课程分享痕迹']], [24,48,28])+
        para('话题标签作为独立元数据编码，不拼接到正文中参与词典匹配。成对的“Ⓚ…Ⓚ”按课程分享后缀处理，未成对的标记予以保留。方括号表情单独计数，不参与核心词汇匹配。上述处理使正文表达与平台附加标记在变量构建中保持区分。')+
        box('变量的解释范围','词典命中表示规则检测到了相应的字面表达，未命中则表示未被该规则识别。无可用正文的帖子仍可能通过图片等方式表达，因此has_text=0仅描述正文数据的可用状态。')+
        note('方法参考：[3]第14、18、24—28页。具体规则见code/analyze.py与text_dictionary.json；文本特征通过postId与帖子数据关联。'))
    dic=json.loads((ROOT/'code/text_dictionary.json').read_text())
    add('06 · 编码规则与可解释性','词典编码规则及其解释范围',
        table(['维度','完整规则'],[
            ['自律/目标词','、'.join(dic['self_discipline'][:-1])+'；第[数字或汉字数词]天'],
            ['社交称呼/互助词','、'.join(dic['social_address'])],
            ['积极表达词','、'.join(dic['positive_expression'])],
            ['问号','? 或 ？；不推断是否真正提问']], [23,77])+
        '<h2>文本结构化示例</h2>'+table(['匿名正文节选','生成的结构化信息'],[
            ['“夜跑打卡”','self_discipline=1；其余三类二元特征=0'],
            ['“谢谢你们！……一起开启……”','social_address=1；其他维度按各自规则独立判断'],
            ['“用心感受清晨的美好”','positive_expression=1'],
            ['“今天 你笑了么？”','question=1；问号本身不等同于互动请求']], [48,52])+
        para('词典采用子串匹配：每个维度命中任一项记为1，同一词重复出现不累加，维度之间允许重叠。“加油”归入自律/目标词，以表示激励性表达；积极表达词主要覆盖愉悦或赞许用语。这些变量用于识别特定字面特征，不构成互斥主题分类或完整的情感评分。')+
        para('此外，采用jieba精准分词，经停用词过滤和帖内词项去重后计算文档频数，以描述语料的主要表达内容。停用词使用课程数据中的BaiduStopwords.txt，并补充少量口语词；本地复现副本位于code/stopwords.txt。高频词统计仅用于描述，不作为额外的假设检验。')+
        note('本研究采用词典内容分析，使编码规则与回归变量之间保持明确对应。其语义测量局限在第13节进一步讨论。'))
    tr=[[r.label,f'{r.n_hit:,}',pct(r.share_all),pct(r.share_visible),str(r.authors_with_within_variation)] for r in T.itertuples()]
    add('07 · 文本描述结果','文本特征的分布与作者覆盖',
        fig('03_text_features','图3　文本特征命中数及高频词。各特征可重叠；正文分词仅分析清理后的可见文本。')+
        table(['特征','命中帖数','全部帖子占比','可见正文占比','有作者内变动的作者数'],tr,[27,15,18,19,21])+
        para('自律/目标词在全部帖子中的命中率为9.2%；以5,548条可见正文为分母时，命中率为15.8%。社交称呼/互助词和问号出现较少，分别只有42和32位作者在其帖子之间呈现0/1取值变化，能够为作者内比较提供的信息相对有限。')+
        para('“打卡”“运动”“加油”等高频词与健身记录的语境一致。不过，该描述仅覆盖100位作者的可用文本：41.8%的帖子缺少正文，图片中的文字和视频语音也未进入分析，因而无法据此概括平台整体内容。')+
        note('高频词为“含该词的帖子数”，每帖至多计1次；不是总词频。特征分母和作者内变动计数见text_features_summary.csv。'))
    rawrows=[[r.label,num(r.raw_mean_likes_hit,2),num(r.raw_mean_likes_nohit,2)] for r in T.itertuples()]
    add('08 · 从描述到回归','从组间差异到作者内比较',
        table(['特征','命中帖平均点赞','未命中帖平均点赞'],rawrows,[44,28,28])+
        para('四类二元特征的命中帖子均具有更高的原始平均点赞数。例如，社交称呼/互助词命中帖的平均点赞约为90，未命中帖约为36。由于这一比较混合了作者受众规模、媒体形式及极端高赞帖等差异，后续通过逐步加入控制项，将分析重点转向同一作者不同帖子之间的条件关联。')+
        '<h2>逐步建模的比较思路</h2>'+table(['模型','控制项','比较含义'],[
            ['M1 基础关联','文本特征、内容形式、业务类型、时段、性别、keepValue、kgLevel、会员','不同作者和帖子混合后的条件关联'],
            ['M2 作者固定效应','M1的帖子层面控制 + 作者虚拟变量；去掉作者内不变属性','同一作者不同帖子的条件比较'],
            ['M3 主模型','M2 + 北京时间发帖日期固定效应','进一步扣除同一天的共同变化']], [20,46,34])+
        para('100位作者的gender、keepValue、kgLevel和memberStatus在样本内均保持不变，已由作者固定效应吸收，因此M2和M3不再重复纳入。作者固定效应有助于控制稳定的作者差异，但粉丝变化、推荐曝光、视觉内容质量及累计观察时长等因素仍无法充分控制。')+
        box('结果变量的选择','只有1,323帖存在采集到的评论记录，其余帖子的评论覆盖情况未知。因此，帖子层面的回归以点赞数为结果变量；评论数据用于描述已观测的互动网络。'))
    add('09 · 模型与统计推断','固定效应模型与统计推断',
        formula('ln(1 + likes<sub>it</sub>) = α<sub>i</sub> + δ<sub>d</sub> + β<sub>1</sub> ln(1 + length<sub>it</sub>)<br>+ β<sub>2</sub> discipline<sub>it</sub> + β<sub>3</sub> social<sub>it</sub> + β<sub>4</sub> positive<sub>it</sub><br>+ β<sub>5</sub> question<sub>it</sub> + γ′Z<sub>it</sub> + ε<sub>it</sub>')+
        para('i表示作者，t表示帖子；α为作者固定效应，δ为北京时间发帖日期固定效应。Z包含正文可用状态、话题标记、表情标记、课程分享标记、内容形式、业务类型和发帖时段。日期依据实际本地时间划分，范围延伸至2021-01-01。')+
        table(['项目','实施方式'],[
            ['估计','普通最小二乘；9532条观测，182个参数，设计矩阵满秩。'],
            ['标准误','按100位作者聚类；CR1小样本系数修正；t分布自由度99计算p值和95%区间。[2]'],
            ['多重检验','对五项核心文本系数进行Benjamini–Hochberg FDR校正；控制变量不加入该检验家族。'],
            ['联合检验','五项文本系数同时为零的聚类稳健Wald F检验。'],
            ['系数解释','二元变量的exp(β)−1对应“1+点赞数”条件几何均值的相对差异，反映给定控制项后的统计关联。']], [20,80])+
        para('正文长度采用自然对数形式。当1+正文长度翻倍时，模型对应的1+点赞数几何均值乘以2<sup>β1</sup>。这一解释针对对数模型的尺度，不能换算为每增加一个字所带来的固定点赞变化。')+
        note('模型设定在本次首次拟合前确定，未进行事前注册。聚类稳健推断考虑作者内误差相关和异方差；遗漏变量、抽样选择及因果识别仍属于研究局限。'))
    mainrows=[]
    for term in FOCAL:
        r=MAIN.loc[term];mainrows.append([esc(r.label),num(r.coef),num(r.se_cluster),f'[{r.ci_low:.3f}, {r.ci_high:.3f}]',pval(r.p),num(r.q_bh_focal)])
    fitrows=[[r.model,f'{r.n:,}',num(r.r_squared),num(r.adj_r_squared)] for r in F.head(3).itertuples()]
    add('10 · 回归结果','核心文本特征的关联证据有限',
        table(['核心变量','系数','聚类SE','95%区间','p','BH q'],mainrows,[28,12,13,25,11,11])+
        note('因变量为ln(1+点赞数)。M3控制作者、日期、内容形式、业务类型、时段及辅助文本标记；N=9,532，作者聚类数为100。表中同时报告原始p值与BH校正后的q值。')+
        para(f'自律/目标词、社交称呼/互助词和问号的系数均未达到统计显著水平，其95%置信区间包含零。积极表达词的系数为{MAIN.loc["positive_expression","coef"]:.3f}，原始p={MAIN.loc["positive_expression","p"]:.3f}；经五项核心检验的BH校正后，q={MAIN.loc["positive_expression","q_bh_focal"]:.3f}，在5%显著性水平下不再显著。')+
        table(['模型','样本量','R²','调整R²'],fitrows,[48,18,17,17])+
        para(f'主模型R²为{F.iloc[2].r_squared:.3f}。相对于保留相同控制项、但不含五项核心文本特征的模型，R²仅增加{100*S["models"]["incremental_r2_text"]:.3f}个百分点，表明这些特征提供的额外解释较少。五项系数的联合检验结果为F(5,99)={S["models"]["joint_focal_F"]:.3f}，p={S["models"]["joint_focal_p"]:.3f}，与单项检验反映的有限证据相一致。')+
        box('结果解释','在现有样本与变量定义下，回归结果尚不足以支持核心文本特征与点赞数存在明确关联。低频特征、词典测量误差及未观测的视觉内容均可能影响估计精度，因此不显著结果也不能证明所有表达方式均无影响。'))
    add('11 · 系数及效应含义','回归系数的量级与解释',
        fig('04_main_coefficients','图4　M3五项核心文本系数和按作者聚类的95%置信区间。此处区间未进行多重检验调整；q值见表。')+
        para(f'将积极表达词的系数转换到相对差异尺度，其点估计对应“1+点赞数”的条件几何均值低约{abs(MAIN.loc["positive_expression","pct_on_likes_plus1"]):.1f}%，原始95%置信区间为[{MAIN.loc["positive_expression","pct_ci_low"]:.1f}%, {MAIN.loc["positive_expression","pct_ci_high"]:.1f}%]。这一量级应结合多重检验结果及后续模型比较共同理解，而不宜直接转化为调整表达方式的建议。')+
        para('积极表达词命中帖的原始平均点赞更高，但回归系数为负，说明未调整的组间比较与控制后的作者内比较并不一致。作者构成和帖子情境可能参与形成这种差异；当前设计无法进一步区分具体机制，也无法将负系数解释为积极表达导致点赞下降。')+
        '<h2>正文长度的关联量级</h2>'+para(f'当1+正文长度翻倍时，主模型中1+点赞数的条件几何均值点估计约增加{100*np.expm1(MAIN.loc["log_length","coef"]*np.log(2)):.1f}%。由于长度系数的置信区间包含零，现有结果不足以确定正文长度的明确关联，更无法推导出最优字数。')+
        note('完整系数及变换后的区间见regression_coefficients.csv；作者内特征相关性见within_author_feature_correlations.csv。'))
    robustness=[]
    for model,label in [('M3_作者与日期固定效应','主模型'),('R1_仅可见正文','仅可见正文'),('R2_去除最高1%点赞','去除最高1%'),('R3_作者等权','作者等权'),('R4_PPML计数模型','PPML计数')]:
        rr=C.loc[(C.model==model)&(C.term=='positive_expression')].iloc[0];ff=F.loc[F.model.eq(model)].iloc[0]
        robustness.append([label,f'{ff.n:,}',num(rr.coef),f'[{rr.ci_low:.3f}, {rr.ci_high:.3f}]',pval(rr.p)])
    add('12 · 稳健性检验','积极表达的负关联对模型设定敏感',
        fig('05_robustness','图5　三类词汇在不同规格下的系数与原始95%聚类置信区间。OLS刻画ln(1+点赞数)；PPML刻画算术条件期望点赞数的对数，系数不能直接视作同一估计量。')+
        table(['积极表达词规格','N','系数','95%区间','原始p'],robustness,[26,14,16,29,15])+
        para(f'为检验结果对样本与估计方式的敏感性，分别采用四种补充设定：仅保留可见正文的5,548帖、95位作者；剔除点赞最高1%的帖子，保留likes≤{S["models"]["trim_threshold_likes_p99"]:.2f}的9,436帖；使每位作者的总权重相同；以原始点赞数估计PPML计数模型。PPML保留相同控制项并采用聚类稳健推断，模型已收敛。')+
        para('积极表达词的负系数在若干OLS设定下仍然存在，但在PPML中未达到统计显著水平，置信区间包含零。结合主模型的BH校正结果，这一负关联仍应视为有待验证的探索性发现。其余词汇的结果也未提供明确的正向关联证据。')+
        note('表内p值均为各设定的原始p值，稳健性比较用于评估结果的敏感性。完整五项结果见regression_coefficients.csv。'))
    add('13 · 文本测量核查','词典编码的语义局限与抽查',
        para('为检查字面匹配与语义解释的一致程度，对四类二元特征分别抽取5条命中和5条未命中的可见正文，共形成40个“帖子—特征”检查单元，其中可能包含重复帖子。抽查由Codex辅助完成，未展示点赞数，但规则命中状态可见。由于未采用独立人工双编码，该检查仅用于识别典型误差，不据此估计总体准确率或编码一致性。')+
        table(['例子与现象','规则结果','对解释的影响'],[
            ['“完成”的对象是身体部位配合或画作进度','自律词命中','通用词会产生健身自律语义的误报。'],
            ['“一起”叙述线下和朋友跑步','社交词命中','不能据此推断面向线上受众的互动邀请。'],
            ['“OK啦”表示满意','积极词未命中','口语表达可能被词典漏掉。'],
            ['“我不要面子的吗？”等反问','问号命中','问号不是实际求助或信息需求。']], [42,21,37])+
        '<h2>对测量与后续研究的启示</h2>'+para('抽查显示，同一词语在不同语境中未必具有相同含义，字面匹配的可复现性也不等于语义测量的有效性。因此，本研究将词典变量解释为字面表达的代理，不据此推断用户自律程度、情绪强度或实际获得的社会支持。抽查发现用于限定结果的解释范围，未据此重新调整词典。')+
        para('后续可从全部可见正文中随机抽样，在隐藏互动指标的条件下，由两位编码者依据预先确定的语义标准独立标注，并评估编码一致性与分类误差。这样可以进一步判断回归中的有限证据在多大程度上与文本测量有关。')+
        note('40条检查记录见results/text_coding_review.csv；抽样与记录过程见code/analyze.py和code/annotate_review.py。'))
    add('14 · 评论网络构建','评论关系的识别与建图规则',
        formula('根评论：评论者 → 帖子作者<br>明确回复：回复者 → replyUserId<br>同一用户对多次互动：合并为一条有向边，边权 = 事件数')+
        para('评论按cmtId去重后，通过postId关联帖子作者。根评论的接收对象为帖主；回复评论优先依据显式replyUserId确定对象，缺失时再利用已观测的直接回复评论ID识别。84次自我互动单独记录并从网络中排除，同一发送者与接收者之间的多次事件合并为一条加权有向边。')+
        table(['转换阶段','规模'],[
            ['去重评论','11595条'],['时间早于所属帖的评论','0条'],['无法确定指向对象','0条'],['自我互动移除','84条'],
            ['可用互动事件','11511次 = 6609次根评论 + 4902次明确回复'],['用户对合并后','4069条有向边；2932个有边节点'],
            ['仅明确回复子网络','1074节点；1271边']], [35,65])+
        para('网络包含至少参与一条非自环边的用户，100位样本作者中有77位出现在该网络中。其余作者未出现在本次采集的有效互动关系中，并不意味着其在平台上没有社交联系。图表及导出边表均使用稳定的匿名用户编号。')+
        box('网络分析与回归的关系','评论在发帖后形成，最晚延续至2021年8月。为避免将结果发生后的信息作为发帖前特征，PageRank、入度及互动接收量仅用于描述网络结构，不纳入帖子点赞回归。')+
        note('方法参考：《社交网络分析简介》第32—37页及《Social Network Influencial》第30、35页。[4][5] 本网络表示已观测的评论指向关系。'))
    add('15 · 网络结构','评论互动网络的连通性与互惠性',
        fig('06_comment_network','图6　全部2932个有边节点、4069条有向边。为可读性省略箭头；金色为样本帖子作者，蓝色为其他参与者；节点大小按接收事件数的对数缩放。仅标注前5位接收者。')+
        table(['指标','结果','含义'],[
            ['弱连通分量',str(N['weak_components']),'忽略方向后彼此连通的子图数'],
            ['最大弱连通分量',f'{N["largest_weak_component"]}节点（{pct(N["largest_weak_component_share"])}）','有边节点大部分落在同一弱连通分量'],
            ['密度',f'{N["density"]:.6f}','4069 / (2932×2931)；稀疏程度受节点抽样影响'],
            ['互惠率',pct(N['reciprocity']),'具有反向边的有向边占比，不按事件权重计算'],
            ['仅明确回复互惠率',pct(N['reply_only_reciprocity']),'改变建边范围后互惠率下降']], [29,29,42])+
        para('最大弱连通分量包含94.4%的有边节点，表明采集到的互动在忽略方向后形成了较大的连通结构。整体互惠率为49.6%；仅保留明确回复时，互惠率为29.9%。这一差异反映出建边范围对网络指标的影响。由于两个网络的节点集合不同，该比较不对应同一群体在两个时期的行为变化。')+
        note('网络图采用固定随机种子的弹簧布局，图面距离仅用于展示连接结构。各指标描述本次观测网络，未估计平台总体网络的抽样置信区间。'))
    add('16 · 互动集中度','前10位接收者获得54.0%的互动事件',
        fig('07_network_concentration','图7　接收事件前10位与累计接收分布。排序和占比均按边权，分母为11511次非自我互动事件；同一用户可重复产生事件。')+
        para(f'按接收事件数排序，前10位账号接收了全部非自我互动的{pct(N["top10_received_share"])}，排名第一的账号接收{pct(N["top1_received_share"])}。共有{pct(N["to_sample_author_share"])}的事件指向样本帖子作者。接收量按评论和回复次数累计，同一用户的重复互动分别计数，因此不同于独立互动用户数。')+
        para('这一集中度需要结合样本边界理解。评论从100位作者的帖子出发采集，根评论又直接指向帖主，因此这些作者及其活跃互动对象更容易成为网络中心。由此得到的接收量排名适用于描述样本内互动分配，不宜外推为Keep全平台的影响力排名。')+
        '<h2>点赞与评论反映不同的互动侧面</h2>'+para('回归分析未发现核心文本特征与点赞数存在充分、稳定的关联证据；网络分析则显示，已采集评论的接收分布较为集中。两部分分别描述帖子层面的反馈和用户间的互动结构。后续研究若进一步收集受众与关系数据，可以检验内容表达在不同关系背景下是否呈现不同关联。')+
        note('入度为不同发送者数量，加权入度为接收事件数，PageRank为补充节点指标；完整结果见network_nodes.csv。'))
    add('17 · 解释与建议','研究结论、实践启示与后续设计',
        table(['证据','可支持的建议','需要进一步验证'],[
            ['五项核心文本特征的联合检验p=0.130，词典测量仍有局限','将内容提示设计为可供选择的表达辅助，鼓励用户描述运动经历、感受或具体问题；其互动效果需另行检验。','内容质量、图片/视频及曝光机会是否改变结果。'],
            ['原始均值与控制后系数不一致','评估内容方案时按作者或用户分组，记录曝光分母和统一观察窗口。','在可比作者、相近内容下做前瞻随机对照。'],
            ['互动接收集中，且受抽样影响','对新用户和低反馈用户提供自愿互助场景；先监测是否有人被长期忽略。','用随机用户样本验证集中度；同时衡量回复质量。']], [31,37,32])+
        '<h2>后续研究设计</h2>'+para('后续可在获得平台实验权限后，以作者为单位随机分组，比较“运动过程记录提示”“面向伙伴的问题提示”与常规发布三种情形。以用户为分组单位有助于减少同一作者跨组带来的干扰。建议设置统一的7天观察窗口，记录实际曝光、独立互动用户数、后续发布行为及回复质量，并根据试点方差和最小有意义差异估算所需样本量。该方案尚未实施。')+
        '<h2>关键局限</h2>'+ul(['100位作者的课程样本与不明抽样机制，不能外推到Keep总体。',
            '正文缺失、图片文字和视频语音缺失，词典未经过独立人工效度验证。',
            '统一采集时间、有效曝光分母和粉丝信息缺失；作者/日期固定效应不能完全处理帖子观察时长及时间变化的受众差异。',
            '观察性回归不能识别因果；评论覆盖不完整，网络边界与根评论建边规则影响结构指标。'])+
        box('研究结论','本研究将帖子文本转换为可复现的结构化特征，并结合固定效应回归与评论网络分析，考察健身社区中的表达与互动。现有证据尚不足以支持特定词汇能够稳定伴随更多点赞；理解互动差异，仍需更完整的内容、曝光及关系数据。'))
    add('18 · 参考资料与复现','参考文献与复现说明',
        '<div class="references">'+para('[1] Richardson CR, Buis LR, Janney AW, et al. (2010). An Online Community Improves Adherence in an Internet-Mediated Walking Program. Part 1: Results of a Randomized Controlled Trial. <i>Journal of Medical Internet Research</i>, 12(4), e71. <a href="https://doi.org/10.2196/jmir.1338">doi:10.2196/jmir.1338</a>。')+
        para('[2] statsmodels 官方文档：RegressionResults.get_robustcov_results，cluster参数、小样本修正与t分布推断。<a href="https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html">官方链接</a>。访问：2026-10-16；实际使用statsmodels 0.14.2，数值复核采用独立矩阵算法。')+
        para('[3] 课程材料《内容分析与自然语言处理.pdf》：第10页内容分析的三层问题，第14页预处理，第18页停用词，第24—28页中文分词。作者及年份信息不详。')+
        para('[4] 课程材料《社交网络分析简介.pdf》：第32—37页网络度分布、点度与中介中心性。')+
        para('[5] 课程材料《Social Network Influencial.pdf》：第30页入度/出度，第35页中心性与影响力的解释限制。')+
        para('[6] 课程数据《KeepData_dictionary.pdf》与两份原始CSV；字段字典和数据原样保留在提交包。')+'</div>'+
        '<h2>复现与数值核查</h2>'+para('项目保存原始输入的校验值、文本编码规则、统计结果和已执行Notebook。独立数值核查采用矩阵算法，重新计算主模型五项系数、聚类标准误、p值及置信区间，并核对评论去重、网络边权和互惠率。报告正文、表格与图形均基于同一results目录生成。')+
        para('公开仓库提供项目目录与数据放置说明。读者可先查看汇总结果；完成原始数据配置后，按README中的命令运行完整分析。正式PDF由分析报告.html导出，可编辑DOCX由相同的文字与表格生成。')+
        note('项目地址：https://github.com/Charlie-ChenLin/keep-community-analysis。公开文件范围和输入要求见README.md与DATA.md。'))
    add('19 · 附录','课程要求与小组分工',
        table(['作业要求','对应成果'],[
            ['小组成员、题目与意义','封面、研究背景；成员留待真实填写'],
            ['完整过程与描述统计','报告02—07及代码、Notebook'],
            ['非结构化数据转结构化后回归','报告05—13；post_features.csv与回归结果'],
            ['至少一种文本或网络分析','已完成词典内容分析、分词统计及评论网络'],
            ['解释和建议','报告10—17；明确不显著结果及局限'],
            ['Presentation全员参与',f'{len(slide_specs())}页PPTX、逐页讲稿及建议分工表'],
            ['PDF、PPT及必要文件打包','提交包ZIP含报告、演示稿、代码、数据、结果与复现说明']], [35,65])+
        '<h2>汇报分工建议</h2>'+table(['成员占位','建议负责内容','PPT页码'],[[r['member'],r['work'],r['slides']] for r in CFG['roles']],[25,55,20])+
        note(CFG['role_note'])+
        para('课程作业要求提交报告PDF、演示PPT及必要附件，压缩包命名为“第几组-社交媒体分析报告.zip”。原文件注明11月10日23:59提交、11月15日前完成个人互评，但未标明年份，具体时间以课程平台通知为准。')+
        note('本附录保留组号、成员和学号占位。分工表为待调整建议，须依据实际人数与贡献填写；每位成员应参与汇报，并独立完成个人互评。'))
    from report_extensions import extend_report
    pages=extend_report(pages,{'para':para,'table':table,'fig':fig,'note':note,'box':box,'ul':ul})
    from report_structure import organize_report
    return organize_report(pages,{'para':para,'table':table,'note':note,'box':box,'fig':fig},TITLE)


def write_html(pages):
    css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e9edf0;color:#243746;font-family:"PingFang SC","Microsoft YaHei","Arial Unicode MS",sans-serif;font-size:10.2pt;line-height:1.72}.page{position:relative;width:210mm;height:297mm;padding:15mm 18mm 18mm;background:white;margin:8mm auto;break-after:page;overflow:visible}.page:last-child{break-after:auto}.kicker{color:#356D9A;font-size:9pt;letter-spacing:.8px;margin:0 0 3mm}h1{font-size:22pt;font-weight:650;line-height:1.4;margin:0 0 6mm;color:#213444}h2{font-size:12.5pt;color:#356D9A;margin:5mm 0 2mm}p{margin:0 0 3mm}ul{padding-left:5mm;margin:2mm 0 4mm}li{margin-bottom:2mm}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:9pt;line-height:1.55;margin:3mm 0 4mm}th{background:#eaf0f5;color:#254c68;text-align:left;font-weight:600}td,th{padding:2mm 2.1mm;border-bottom:.2mm solid #dce4e9;vertical-align:top;overflow-wrap:anywhere}.note,figcaption{font-size:8.5pt;color:#627581;line-height:1.6}.callout{border-left:1mm solid #B88425;background:#f7f5ee;padding:3mm 4mm;margin:4mm 0}.callout p{margin:1mm 0 0}.formula,.pipeline{padding:4mm;background:#f3f6f8;font-size:10pt;line-height:1.8;margin:4mm 0;overflow-wrap:anywhere}figure{margin:4mm 0}figure img{display:block;width:100%;height:auto;max-height:122mm;object-fit:contain}figcaption{margin-top:2mm}footer{position:absolute;bottom:9mm;left:18mm;right:18mm;border-top:.2mm solid #dce4e9;padding-top:2mm;display:flex;justify-content:space-between;font-size:8pt;color:#71818b}.subtitle{font-size:15pt;color:#356D9A;margin:3mm 0 6mm}.coverline{width:24mm;height:1.5mm;background:#B88425;margin:8mm 0}.byline{font-size:13pt;line-height:1.8}.cover-meta{font-size:10pt;color:#627581;margin:6mm 0 7mm}.references{font-size:9pt;line-height:1.65}a{color:#356D9A;text-decoration:none}@media print{body{background:white}.page{margin:0;box-shadow:none}}'''
    css+='''.chapter-title{font-size:20pt;margin-bottom:5mm;line-height:1.45}.section-title{font-size:20pt;font-weight:650;color:#213444;line-height:1.45;margin:0 0 6mm}.chapter-title+.section-title{font-size:14pt;color:#356D9A;margin-bottom:5mm}h3{font-size:12.5pt;color:#356D9A;margin:5mm 0 2mm}.toc{margin-top:2mm}.toc-entry{display:flex;align-items:baseline;gap:2mm;min-height:7.4mm;line-height:1.65;font-size:10pt;color:#243746}.toc-level-1{font-weight:650;color:#254c68;margin-top:3mm}.toc-level-1:first-child{margin-top:0}.toc-level-2{padding-left:5mm}.toc-title{flex:0 1 auto}.toc-leader{flex:1 1 5mm;border-bottom:.25mm dotted #becbd3;min-width:4mm;align-self:baseline}.toc-page{flex:0 0 7mm;text-align:right;font-variant-numeric:tabular-nums}.toc-entry:hover .toc-title{text-decoration:underline}'''
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+esc(TITLE)+'</title><style>'+css+'</style><body>']
    for i,p in enumerate(pages,1):
        if p.get('chapter'):
            kicker=p['chapter_name'].split(' ',1)[0] if p['chapter_start'] else p['chapter_name']
            heading=(f'<h1 class="chapter-title" id="chapter-{p["chapter"]}">{esc(p["chapter_name"].split(" ",1)[1])}</h1>'
                     if p['chapter_start'] else '')
            heading+=f'<h2 class="section-title" id="{p["anchor"]}">{p["section"]}　{esc(p["title"])}</h2>'
        else:
            kicker=p['kicker'];anchor=f' id="{p["anchor"]}"' if p.get('anchor') else ''
            heading=f'<h1{anchor}>{esc(p["title"])}</h1>'
        parts.append(f'<section class="page" id="page-{i}"><main><div class="kicker">{esc(kicker)}</div>{heading}{p["body"]}</main><footer><span>Keep 社区文本与互动网络分析 · {esc(CFG["group"])}</span><span>{i:02d} / {len(pages):02d}</span></footer></section>')
    parts.append('</body></html>');(ROOT/'分析报告.html').write_text(''.join(parts),encoding='utf-8')


def write_docx(pages):
    from bs4 import BeautifulSoup, NavigableString
    from docx.enum.text import WD_TAB_ALIGNMENT, WD_TAB_LEADER, WD_LINE_SPACING
    doc=Document();sec=doc.sections[0];sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.8);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    style=doc.styles['Normal'];style.font.name='Microsoft YaHei';style.font.size=DPt(10)
    style.element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    for name,size in [('Heading 1',18),('Heading 2',15),('Heading 3',11.5)]:
        style=doc.styles[name];style.font.name='Microsoft YaHei';style.font.size=DPt(size)
        style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    update_fields=DOxmlElement('w:updateFields');update_fields.set(qn('w:val'),'true')
    doc.settings.element.append(update_fields)
    bookmark_id=0
    def bookmark(heading,anchor):
        nonlocal bookmark_id
        bookmark_id+=1
        start=DOxmlElement('w:bookmarkStart');start.set(qn('w:id'),str(bookmark_id));start.set(qn('w:name'),anchor.replace('-','_'))
        heading._p.insert(1 if heading._p.pPr is not None else 0,start)
        end=DOxmlElement('w:bookmarkEnd');end.set(qn('w:id'),str(bookmark_id));heading._p.append(end)
    for i,page in enumerate(pages):
        if i:doc.add_page_break()
        if page.get('chapter'):
            if page['chapter_start']:
                heading=doc.add_heading(page['chapter_name'],1);bookmark(heading,f'chapter-{page["chapter"]}')
            else:doc.add_paragraph(page['chapter_name'],'Subtitle')
            heading=doc.add_heading(f'{page["section"]}　{page["title"]}',2);bookmark(heading,page['anchor'])
        else:
            doc.add_paragraph(page['kicker'],'Subtitle')
            heading=doc.add_heading(page['title'],0 if i==0 or 'toc_entries' in page else 1)
            if page.get('anchor'):bookmark(heading,page['anchor'])
        if 'toc_entries' in page:
            for entry in page['toc_entries']:
                p=doc.add_paragraph();fmt=p.paragraph_format
                fmt.space_after=DPt(0);fmt.space_before=DPt(6 if entry['level']==1 else 0)
                fmt.line_spacing_rule=WD_LINE_SPACING.EXACTLY;fmt.line_spacing=DPt(20)
                if entry['level']==2:fmt.left_indent=Cm(.5)
                fmt.tab_stops.add_tab_stop(Cm(17),WD_TAB_ALIGNMENT.RIGHT,WD_TAB_LEADER.DOTS)
                anchor=entry['anchor'].replace('-','_')
                link=DOxmlElement('w:hyperlink');link.set(qn('w:anchor'),anchor)
                run=DOxmlElement('w:r');props=DOxmlElement('w:rPr')
                color=DOxmlElement('w:color');color.set(qn('w:val'),'243746');props.append(color)
                if entry['level']==1:props.append(DOxmlElement('w:b'))
                run.append(props);text=DOxmlElement('w:t')
                text.text=f'{entry["section"]}  {entry["title"]}' if entry['section'] else entry['title'];run.append(text)
                link.append(run);p._p.append(link);p.add_run('\t')
                field=DOxmlElement('w:fldSimple');field.set(qn('w:instr'),f'PAGEREF {anchor} \\h')
                field.set(qn('w:dirty'),'true')
                value=DOxmlElement('w:r');text=DOxmlElement('w:t');text.text=str(entry['page']);value.append(text)
                field.append(value);p._p.append(field)
            continue
        soup=BeautifulSoup(page['body'],'html.parser')
        for el in soup.children:
            if isinstance(el,NavigableString):continue
            if el.name=='figure':
                doc.add_picture(str(ROOT/el.img['src']),width=Cm(16.5));doc.add_paragraph(el.figcaption.get_text(),'Caption')
            elif el.name=='table':
                rows=el.find_all('tr');t=doc.add_table(rows=0,cols=len(rows[0].find_all(['td','th'])));t.style='Light Shading Accent 1'
                for r in rows:
                    cells=t.add_row().cells
                    for c,text in zip(cells,r.find_all(['td','th'])):c.text=text.get_text(' ',strip=True)
            elif el.name=='h2':
                if i==0:
                    run=doc.add_paragraph().add_run(el.get_text());run.bold=True;run.font.size=DPt(11.5)
                else:doc.add_heading(el.get_text(),2)
            elif el.name=='h3':doc.add_heading(el.get_text(),3)
            elif el.name=='ul':
                for li in el.find_all('li',recursive=False):doc.add_paragraph(li.get_text(' ',strip=True),'List Bullet')
            else:doc.add_paragraph(el.get_text('\n',strip=True))
    doc.save(ROOT/'分析报告_可编辑.docx')


def slide_specs():
    specs=[
      (TITLE,[SUBTITLE,CFG['group']+' · '+CFG['members'],'100位作者 · 9,532条帖子 · 11,595条去重评论'],None,
       '先介绍研究题目和成员。说明研究使用课程提供的Keep数据，帖子实际发表于2020年11—12月UTC，而不是文件名中的2022年。点赞是平台内反馈，不能代表运动效果。'),
      ('研究问题：表达方式与点赞有关吗？',['RQ1：帖子、表达方式与点赞如何分布？','RQ2：同一作者的文本特征与点赞是否相关？','RQ3：评论连接了谁，互动是否集中？'],None,
       '用三个问题串联描述、解释与建议。强调研究观察统计关联，不能回答改写文案是否会因果提高点赞。'),
      ('研究意义与计划',['在线社区可能有助于留存，社区互动与运动成效需要区分。[1]','计划：清洗 → 文本编码 → 固定效应回归 → 稳健性 → 网络 → 建议','以上分析均已完成；后续实验仅为研究方案。'],None,
       '引用Richardson等2010年的随机试验：社区功能降低流失，未发现组间步数增幅显著差异。我们不把该结果套用Keep，而是据此区分参与和行为结果。课程第七周汇报允许初步结果，本稿已有完整分析，可直接用于汇报。'),
      ('数据核查决定能回答什么',['评论13,511行 → 按cmtId去重后11,595条；1,916行完全重复。','正文缺失41.8%；仅1,323帖采集到评论，其余不记为零评论。','86.9%帖子点赞高于浏览数：不用该浏览字段计算点赞率。','北京时间逐日建模；末尾跨至2021-01-01。'],None,
       '逐项说明质量发现怎样改变设计：缺失正文保留并设指示变量；评论不完整所以不做评论数全样本回归；浏览字段口径存疑所以用点赞数。清洗没有删掉低赞或高赞用户。'),
      ('点赞分布存在长尾',['均值37.05，中位数25，最大5,126；零点赞占3.8%。','用ln(1+点赞数)；按作者聚类；另检查计数模型。','首末本地日期不完整，不解释末尾下降为活跃度骤降。'],'01_sample_and_likes',
       '先解释对数图横轴。作者发帖中位数66条，最多783条，同一作者帖子不独立，后续聚类标准误对应100位作者。'),
      ('如何把正文变成回归变量',['核心变量：长度、自律/目标词、社交称呼/互助词、积极表达词、问号。','清理URL、课程后缀、表情标记；话题标签单独编码。','词典命中可重叠；只表示字面表达，不是心理或情感量表。'],None,
       '用夜跑打卡生成self_discipline=1的例子说明非结构化到结构化过程。补充has_text、has_tag、表情和课程标记控制。词典拟合前固定，但没有事前注册。'),
      ('文本规模：注意分母和低频特征',['自律/目标词877帖：全部帖9.2%；可见正文15.8%。','社交词159帖；问号125帖，提供作者内变化的人数较少。','高频词是逐帖去重后的文档频数，不能当作效果证据。'],'03_text_features',
       '解释有正文的5548帖与所有9532帖两个分母。社交词和问号分别仅42和32位作者提供内部变化，区间会较宽。'),
      ('主模型：控制作者和日期',['因变量 ln(1+likes)；全部9,532帖，100位作者。','作者固定效应 + 日期固定效应 + 内容形式/类型/时段及文本标记。','作者聚类CR1标准误；t分布df=99；五项核心检验BH校正。','作者内不变的性别、会员、等级等由作者固定效应吸收。'],None,
       '解释同一作者发帖比较。没有曝光、粉丝与统一采集时间，固定效应没有消除全部混杂。若被问到公式，请对应报告第09节。'),
      ('主结果：没有明确的高赞用词公式',['五项核心特征联合检验p=0.130；新增R²仅0.065个百分点。','积极表达词β=-0.086；原始p=0.016，BH q=0.079。','不显著不是证明无作用；现有测量下证据不足。'],'04_main_coefficients',
       '图中误差线是原始95%聚类置信区间，未做多重检验调整。积极表达虽然区间未跨0，经过五项检验校正后证据不足。不要把模型总R²约0.688都归因于文本。'),
      ('稳健性：结论依赖尺度与规格',['检查仅可见正文、去最高1%点赞、作者等权、PPML计数模型。','积极表达词的PPML区间包含0，原始p=0.103。','OLS与PPML的估计量不同；不能以某个规格显著就宣称稳健。'],'05_robustness',
       '解释为什么不因长尾强行删除极端值：主模型保留，敏感性规格另行比较。PPML以原始点赞数的条件算术均值为目标，OLS刻画对数结果。'),
      ('词典测量也需要接受检查',['40个帖子—特征检查单元：按规则命中分层抽样，无点赞展示。','“完成”可能指绘画；“一起”可能描述线下朋友；问号可能是反问。','Codex辅助抽查，未做独立人工双编码；不宣称准确率。'],None,
       '这是方法上的边界检查。规则本身能复现不代表语义测量有效，未命中也不等于没有表达。没有使用结果来反复修改词典以获取显著系数。'),
      ('评论网络：明确每条边的指向',['根评论：评论者→帖主；明确回复：回复者→replyUserId。','去重后移除84次自我互动；11,511事件合并为4,069条边。','2,932个有边节点；箭头在图中省略，原数据保持有向。'],'06_comment_network',
       '不要把所有回复都连向帖主。评论最晚到2021年8月，所以网络指标不作为发帖前影响力加入回归。金色表示样本作者，蓝色表示其他参与者；节点大小按加权入度对数缩放。'),
      ('互动集中，但样本边界影响很大',['前10位接收者获得54.0%互动；第一位12.0%。','整体互惠率49.6%；仅明确回复子网络29.9%。','这是采集网络的接收事件数，不是平台影响力或独立粉丝数。'],'07_network_concentration',
       '样本从100位作者帖子出发，根评论天然指向帖主，会形成中心。互惠率按有反向边的有向边占比，不按权重；两个网络节点集合不同，不能解释为行为下降。'),
      ('建议：把表达方案交给对照实验',['不承诺“加某个词就会涨赞”；先保证真实、完整且易交流的内容。','固定观察窗口、记录真实曝光；按作者随机分组评估提示文案。','关注低反馈用户与回复质量，同时验证抽样是否造成集中。','未执行的实验是后续设计，不是已证实的增长方案。'],None,
       '提出用户层面随机分组，避免同作者跨组污染；三组可为过程记录提示、面向伙伴问题提示和常规发布，固定7天，样本量先做试点再计算。不宣称已发现提升方案。'),
      ('结论、局限与可复现性',['主结论：没有充分证据支持稳定的高赞词汇策略。','100位作者课程样本，抽样机制不明；正文/视觉缺失；曝光和统一采集时点未知。','代码、原始Keep数据、特征表、回归结果与已执行Notebook全部随附。','数值独立复核；填好组号、成员后按课程要求打包提交。'],None,
       '回到三个研究问题，分别给出描述、条件关联和网络结构答案。说明所有材料都可以本地复现。附参考资料：课程NLP与网络讲义；Richardson等2010；statsmodels官方文档。'),
      ('小组分工与讨论',['成员A【待填写】：研究问题与背景（1—3页）','成员B【待填写】：数据与文本（4—7页）','成员C【待填写】：模型与检验（8—11页）','成员D【待填写】：网络、建议与总结（12—16页）','此为建议分工，须按真实人数和贡献修订。'],None,
       '感谢听众并进入讨论。每名组员应汇报自己实际负责的内容。请在提交前替换姓名、组号与学号，并修改为真实贡献。互评需每人独立据实完成，模板不代表完成记录。')
    ]
    from report_extensions import extend_slides
    return extend_slides(specs)


def set_run_font(run,size=20,color=DARK,bold=False):
    run.font.name='Microsoft YaHei';run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=RGBColor.from_string(color.lstrip('#'))
    rPr=run._r.get_or_add_rPr();ea=OxmlElement('a:ea');ea.set('typeface','Microsoft YaHei');rPr.append(ea)


def textbox(slide,x,y,w,h,text,size=20,color=DARK,bold=False):
    shape=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h));tf=shape.text_frame;tf.word_wrap=True
    tf.margin_left=0;tf.margin_right=0;tf.margin_top=0;tf.margin_bottom=0
    for i,line in enumerate(text.split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.space_after=Pt(9)
        set_run_font(p.add_run(),size,color,bold);p.runs[-1].text=line
    return shape


def write_slides():
    from PIL import Image
    from report_extensions import slide_section_label
    prs=Presentation();prs.slide_width=Inches(13.3333);prs.slide_height=Inches(7.5)
    specs=slide_specs();notes=[]
    for i,(title,bullets,img,speaker) in enumerate(specs,1):
        slide=prs.slides.add_slide(prs.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
        textbox(slide,.55,.28,12,.3,f'KEEP COMMUNITY  /  {slide_section_label(title)}  /  {i:02d}',size=11,color=BLUE)
        textbox(slide,.55,.82,12.2,.9,title,size=30 if i!=1 else 34,bold=True)
        if img:
            path=ROOT/'figures'/(img+'.png');w,h=Image.open(path).size
            maxw,maxh=8.15,4.4;cw=min(maxw,maxh*w/h);ch=cw*h/w
            slide.shapes.add_picture(str(path),Inches(.4+(8.4-cw)/2),Inches(2.0+(4.45-ch)/2),width=Inches(cw),height=Inches(ch))
            textbox(slide,9.0,2.0,3.7,4.7,'\n\n'.join(bullets),size=19)
        else:
            textbox(slide,.8,2.05,11.7,4.7,'\n\n'.join(bullets),size=24 if len(bullets)<=3 else 21)
        if i==3:
            textbox(slide,.8,6.25,11.7,.45,'[1] Richardson et al., Journal of Medical Internet Research, 2010;12(4):e71. doi:10.2196/jmir.1338',size=12,color=BLUE)
        textbox(slide,.55,7.02,11.8,.25,'Keep课程样本；观察性分析。全部数值与口径见分析报告及附带结果。',size=10,color='#71818B')
        textbox(slide,12.25,7.02,.6,.25,str(i),size=10,color=BLUE)
        slide.notes_slide.notes_text_frame.text=speaker
        notes.append(f'第{i}页　{title}\n建议用时：'+('30秒' if i in [1,len(specs)] else '45—60秒')+'\n'+speaker+'\n')
    prs.save(ROOT/'演示文稿.pptx')
    duration='18—22' if len(specs)>21 else '16—20' if len(specs)>16 else '12—15'
    (ROOT/'汇报讲稿.txt').write_text(f'完整版建议总时长约{duration}分钟，按课程时间限制选取内容。\n组号/成员待定，分工只是可修改建议。\n\n'+'\n'.join(notes),encoding='utf-8')


def notebook():
    nb=nbf.v4.new_notebook();md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
    nb.cells=[
      md('# Keep 社区：文本、点赞与评论网络\n\n## tl;dr\n分析课程提供的100位作者、9532条帖子和11595条去重评论。主模型五项文本特征联合检验 p=0.130；积极表达词原始 p=0.016，但BH q=0.079，PPML区间包含零。没有充分证据支持稳定的高赞词汇策略。网络前10位接收54.0%的事件，受样本边界影响。'),
      md('## Context & Methods\n这是报告的可复现伴随Notebook；代码参数及规则保存在code目录。\n\n### Key Assumptions\n- UTC发布时间转为Asia/Shanghai；帖子实际为2020年11—12月UTC。\n- 空正文保留并设指示变量；词汇仅代表字面代理。\n- 评论缺失覆盖不记零；评论ID精确去重。\n- 主模型控制作者和日期，标准误按作者聚类，df=99。\n- 观察性结果不支持因果或运动成效结论。\n\n### 1. 环境和来源'),
      code('from pathlib import Path\nimport sys, json\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT = Path.cwd()\nif not (ROOT / "code/analyze.py").exists():\n    ROOT = ROOT / "projects/group"\nassert (ROOT / "code/analyze.py").exists()\nsys.path.insert(0, str(ROOT / "code"))\nimport analyze\nprint("来源：2026Data/Keep Data/sample_post_2022.csv 与 sample_comment_2022.csv")\nprint("规则：code/text_dictionary.json；随机种子：", analyze.SEED)'),
      md('## Data\n### 2. 读取原始数据并按明示规则清洗'),
      code('posts, comments, audit = analyze.read_and_prepare()\ndisplay(pd.DataFrame([{"帖子数":len(posts),"作者数":posts.author.nunique(),"去重评论数":len(comments),"有评论覆盖的帖子":comments.postId.nunique(),"正文缺失数":int(posts.content.isna().sum())}]))\nassert posts.postId.is_unique and comments.cmtId.is_unique\nassert comments.postId.isin(posts.postId).all()\nprint("正文和点赞为不同粒度字段；不计算点赞/浏览率。")'),
      md('### 3. 描述统计与文本结构化\n字典特征在拟合前固定；词频只用于描述。'),
      code('analyze.describe(posts)\ndisplay(pd.read_csv(ROOT/"results/descriptive_statistics.csv").round(2))\ndisplay(pd.read_csv(ROOT/"results/text_features_summary.csv")[["label","n_hit","share_all","share_visible","authors_with_within_variation"]].round(4))'),
      md('## Results\n### 4. 拟合主模型及全部敏感性规格\n重新运行OLS和PPML，而非仅展示缓存结果。'),
      code('coefficients = analyze.models(posts, audit)\nmain = coefficients.loc[(coefficients.model == "M3_作者与日期固定效应") & coefficients.term.isin(analyze.FOCAL)]\ndisplay(main[["label","coef","se_cluster","ci_low","ci_high","p","q_bh_focal"]].round(4))\nprint("五项特征联合检验p =", round(audit["models"]["joint_focal_p"],4))'),
      md('### 5. 按明确指向构建网络并绘图\n根评论指向帖主；回复指向replyUserId；不将网络指标加入帖子回归。'),
      code('graph, node_table, pseudonyms = analyze.network(posts, comments, audit)\nanalyze.plot_all(posts, coefficients, graph, node_table, pseudonyms)\ndisplay(pd.DataFrame([{k:audit["network"][k] for k in ["nodes","edges","events","reciprocity","top10_received_share","reply_only_reciprocity"]}]).round(4))'),
      md('### 6. 分布和特征\n注意末尾本地日期不完整；命中率的分母为全部9532帖。'),
      code('display(Image(filename=str(ROOT/"figures/01_sample_and_likes.png"), width=950))\ndisplay(Image(filename=str(ROOT/"figures/03_text_features.png"), width=950))'),
      md('### 7. 系数与稳健性\n区间为原始95%聚类区间；BH校正值见表。PPML与OLS并非同一估计量。'),
      code('display(Image(filename=str(ROOT/"figures/04_main_coefficients.png"), width=900))\ndisplay(Image(filename=str(ROOT/"figures/05_robustness.png"), width=950))'),
      md('### 8. 网络与互动集中\n这些图仅描述已采集评论，不能外推为平台影响力。'),
      code('display(Image(filename=str(ROOT/"figures/06_comment_network.png"), width=900))\ndisplay(Image(filename=str(ROOT/"figures/07_network_concentration.png"), width=950))'),
      md('### 9. 独立数值验证\n另用NumPy最小二乘与按作者分组的sandwich矩阵重算五项系数、标准误、p值及95%区间。'),
      code('import validate\nvalidate.main()\nchecks = json.loads((ROOT/"validation/numerical_checks.json").read_text())\nassert all(row["passed"] for row in checks)\nprint("全部", len(checks), "项独立数值核查通过。")'),
      md('## Takeaways\n1. 不把词汇命中当作心理/情绪量表；40条Codex辅助语义抽查用于界定测量边界，没有声称准确率。\n2. 主模型中没有BH q<0.05的核心特征。原始正向均值差异不支持用词提升因果结论。\n3. 评论集中度受100位作者帖子抽样和根评论指向定义影响。\n4. 下一步可收集曝光与统一窗口，以用户为单位随机分组验证表达提示。\n\n来源和完整说明见《分析报告.html》《分析报告.pdf》与results/summary.json。')
    ]
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}}
    nbf.write(nb,ROOT/'分析过程.ipynb')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    outputs=parser.add_mutually_exclusive_group()
    outputs.add_argument('--report-only',action='store_true',help='Rebuild HTML/DOCX without changing the executed notebook or slides.')
    outputs.add_argument('--slides-only',action='store_true',help='Rebuild PPTX and speaker notes only.')
    args=parser.parse_args()
    if args.slides_only:
        write_slides()
        print('Built',len(slide_specs()),'slides and speaker notes.')
        return
    pages=report_pages();write_html(pages);write_docx(pages)
    if not args.report_only:
        write_slides();notebook()
    contents=[entry for page in pages for entry in page.get('toc_entries',[])]
    chapters=[{'number':page['chapter'],'title':page['chapter_name'].split(' ',1)[1],
               'page':page['physical_page'],
               'subsections':[p['section'] for p in pages if p.get('chapter')==page['chapter']]}
              for page in pages if page.get('chapter_start')]
    (ROOT/'results/report_manifest.json').write_text(json.dumps({
        'pages':len(pages),'slides':len(slide_specs()),'report':'分析报告.html',
        'pdf':'分析报告.pdf','pptx':'演示文稿.pptx','chapters':chapters,
        'toc_pages':[i for i,page in enumerate(pages,1) if 'toc_entries' in page],
        'contents':contents},ensure_ascii=False,indent=2))
    print('Built',len(pages),'report pages.' if args.report_only else 'report pages, slides and notebook template.')

if __name__=='__main__':main()
