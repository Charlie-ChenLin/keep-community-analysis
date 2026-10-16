"""Create the requested local academic report, PowerPoint and executed notebook.

The assignment explicitly requires PDF/PPT; this is a file-only academic package.
All text and tables are generated from reviewed local results, not demo values.
"""
from pathlib import Path
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
        '<div class="cover-meta">课程：社交媒体与网络分析<br>资料范围：课程提供的 Keep 社区帖子及评论<br>帖子发布时间：2020-11—2020-12（UTC）<br>分析完成日期：2026-10-16</div>'
        '<h2>摘要</h2>'+para(f'本研究分析100位作者的9,532条帖子，将正文转换为长度、自律/目标词、社交称呼/互助词、积极表达词和问号等变量，以 ln(1+点赞数) 为因变量建立回归；另将去重后的11,595条评论构造成互动网络。')+
        para(f'主模型控制作者、发帖日期、内容形式及其他特征后，五项核心文本特征的联合检验 p={S["models"]["joint_focal_p"]:.3f}，新增解释度为{100*S["models"]["incremental_r2_text"]:.3f}个百分点；没有充分证据认定某类词汇稳定伴随更多点赞。积极表达词的负系数在原始检验中显著，但BH校正 q={MAIN.loc["positive_expression","q_bh_focal"]:.3f}，且PPML计数模型区间包含零，应视为探索性信号。')+
        para(f'观察到的评论互动集中于少数账号，前10位接收{pct(N["top10_received_share"])}的事件。建议将词汇优化视为待检验方案，结合用户层面的对照实验评估互动质量。点赞不是运动效果，观察到的评论网络也不是整个平台的社交图谱。')+
        note('关键词：Keep；内容分析；固定效应；聚类标准误；评论网络。组号和成员信息尚待填写；文中分工均为建议。'))
    add('01 · 研究背景与意义','从健身记录到社区反馈',
        para('健身社区把运动记录、情绪表达和同伴交流放在同一场景中。点赞可以反映平台内一种可观察的反馈，但它还受到作者既有受众、媒体形式和曝光机会影响。因此，不能只比较某类帖子平均点赞就判断内容表达是否有效。')+
        para('Richardson 等（2010）的随机试验发现，增加在线社区功能与较低的项目流失相关，但未发现组间步数增幅存在显著差异。[1] 这提示我们区分社区参与和行为改变。本项目仅研究平台内反馈，不测量运动坚持、健康或体重变化。')+
        '<h2>研究问题</h2>'+table(['编号','可检验问题','分析路径'],[
            ['RQ1','样本帖子、表达方式及点赞如何分布？','描述统计、正文分词与词汇命中统计'],
            ['RQ2','同一作者不同帖子的文本特征与点赞是否相关？','作者与日期固定效应回归；稳健性比较'],
            ['RQ3','采集到的评论如何连接用户？互动集中在哪里？','有向加权网络、互惠率、接收集中度']], [10,56,34])+
        '<h2>研究预期与解释边界</h2>'+ul(['自律/目标词可能使运动记录更易理解；社交称呼和互助词可能邀请反馈。这些是待检验解释，不是已成立的因果机制。',
            '积极表达和问号的方向不预设；正文长度是表达规模的控制与比较维度。四类二元特征和长度共同构成五项核心检验。',
            '报告完整呈现正、负及不显著结果。词典在本次拟合前固定，但没有事前注册；研究仍属探索性分析。'])+
        note('课程对应：《内容分析与自然语言处理》第10、14、18页提供“描述—解释—决策”和文本预处理框架；本研究将其落实为可复查的编码与建模步骤。[3]'))
    add('02 · 数据来源与清洗','先确定样本与字段含义',
        table(['文件','粒度与规模','用途'],[
            ['sample_post_2022.csv','每行1帖；9,532帖；100位作者','全部描述统计与回归'],
            ['sample_comment_2022.csv','原始13,511行；去重后11,595条评论','仅用于评论覆盖说明与网络'],
            ['KeepData_dictionary.pdf','课程提供的字段解释','确定ID、点赞、父评论与直接回复对象']], [33,34,33])+
        '<h2>实际清洗流程</h2>'+table(['步骤','发现及处理'],[
            ['主键与重复','帖子ID全部唯一。评论ID有1,916行重复；逐字段验证没有冲突，按cmtId保留1条。'],
            ['表关联','所有去重评论均能关联到帖子；1323帖有采集到的评论，其余8209帖的评论覆盖未知，不赋值为0。'],
            ['时间','原字段以Z结尾，按UTC解析；发帖日期、时段统一转换为Asia/Shanghai。北京时间末尾跨至2021-01-01。'],
            ['正文','3984帖content为空；保留帖子，文本计数置0，并另设has_text控制“无可用正文”状态。'],
            ['口径异常','8286帖likes大于viewCount（86.9%）。无法确认两个计数字段可比分母关系，因此不计算点赞率或将浏览数设为offset。'],
            ['极端值','保留全部真实观测进入主模型。仅在稳健性规格中剔除点赞最高1%，不把极端值预先认定为错误。']], [17,83])+
        box('文件名不能当作观测年份','帖子UTC发布时间为2020-11-01至2020-12-31；评论最晚到北京时间2021-08-26。2022和2026均不是本项目观测年份。采集时点未提供，点赞的累计观察时长未知。')+
        note('可复核证据：results/summary.json保存原文件SHA-256；results/post_features.csv保存匿名作者和建模特征。评论缺失覆盖与重复处理分别核查，不将删重视作“删异常用户”。'))
    statsrows=[]
    for name,label in [('likes','点赞数'),('viewCount','记录浏览数'),('favoriteCount','收藏数'),('length','清理后正文字符数')]:
        r=D.loc[name];statsrows.append([label,num(r['mean'],2),num(r['50%'],0),num(r['95%'],1),num(r['max'],0)])
    add('03 · 描述统计','点赞分布长尾明显，均值高于中位数',
        fig('01_sample_and_likes','图1　全部9,532帖的点赞分布与北京时间逐日发帖数。首末本地日期为不完整日，末端下降不能解释为活跃度骤降。')+
        table(['变量','均值','中位数','95分位数','最大值'],statsrows,[33,17,17,17,16])+
        para(f'平均点赞为{S["likes_mean"]:.2f}，中位数为25，最大值为5126，零点赞占{pct(S["likes_zero_share"])}。点赞方差约为均值的{S["likes_variance_mean"]:.1f}倍。主模型用ln(1+点赞数)缓和长尾影响；同时用聚类稳健推断和计数模型检查结论。')+
        para('作者发帖数很不均衡：中位作者发布66帖，发帖最多者发布783帖。单纯把帖子看成独立随机样本会低估同一作者帖子的相关性，因此标准误按作者聚类；另用作者等权规格检查高产作者的影响。')+
        note('字符数为去URL、成对课程后缀、方括号表情及空白后的字符数；并非纯汉字数。上述分位数基于所有帖子，含无可用正文者。'))
    m=pd.read_csv(ROOT/'results/media_summary.csv')
    mrows=[[{'img':'图片','none':'无媒体','video':'视频','txt':'纯文字'}[r.contentTypeStr],f'{r.n:,}',pct(r.share),num(r.mean_likes,2),num(r.median_likes,0)] for r in m.itertuples()]
    add('04 · 描述统计','内容形式之间存在明显的原始差异',
        fig('02_media_summary','图2　内容形式及其点赞均值、中位数。类别是原始contentTypeStr，不等同于是否有正文。')+
        table(['形式','帖子数','占比','平均点赞','点赞中位数'],mrows)+
        para('图片和视频帖的原始点赞明显高于无媒体及纯文字帖，但这同时混合了作者构成、帖子业务类型和内容差异。不能据此断言“发布图片会提高点赞”，也不把此差异当作文本词汇的作用。')+
        para('帖子业务类型包括normal、hiking、run、yoga、cycling、direct与share；这些原始类别进入回归。发帖时段分为00—05、06—11、12—17、18—23点。日期固定效应控制同一天样本共有的变化，无法解决每帖真实累计曝光时长不明的问题。')+
        note('输出文件：media_summary.csv、post_type_summary.csv、monthly_summary.csv。北京时间2021年1月仅包含UTC年底跨日的少量帖子，不能与完整月份比较活跃趋势。'))
    add('05 · 文本结构化','把可见正文转换为可重复的变量',
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
        para('正文中的话题元数据不拼接进词典匹配，以免将平台话题名当成用户表达。成对“Ⓚ…Ⓚ”视为可观察的课程分享后缀；非成对标记不强行删除。方括号表情不参加核心词匹配，另计数量。')+
        box('词汇代理的含义','命中=检测到字面表达；未命中=规则未检测到，不等于没有该主题或没有情绪。has_text=0也不意味着用户没有表达意图，可能是图片表达或字段未采集。')+
        note('课程依据：[3]第14、18、24—28页；全部规则见code/analyze.py与text_dictionary.json。文本分析与回归通过同一postId关联，未使用点赞反向定义词典。'))
    dic=json.loads((ROOT/'code/text_dictionary.json').read_text())
    add('06 · 编码规则与可解释性','先固定规则，再检查其语义边界',
        table(['维度','完整规则'],[
            ['自律/目标词','、'.join(dic['self_discipline'][:-1])+'；第[数字或汉字数词]天'],
            ['社交称呼/互助词','、'.join(dic['social_address'])],
            ['积极表达词','、'.join(dic['positive_expression'])],
            ['问号','? 或 ？；不推断是否真正提问']], [23,77])+
        '<h2>怎样从一句话产生一行数据</h2>'+table(['匿名正文节选','生成的结构化信息'],[
            ['“夜跑打卡”','self_discipline=1；其余三类二元特征=0'],
            ['“谢谢你们！……一起开启……”','social_address=1；其他维度按各自规则独立判断'],
            ['“用心感受清晨的美好”','positive_expression=1'],
            ['“今天 你笑了么？”','question=1；问号本身不等同于互动请求']], [48,52])+
        para('词典采用子串匹配，每个维度命中任一项记1，不累计同一词反复出现次数；维度之间允许重叠。自律词中的“加油”属于激励表达，积极词维度则聚焦愉悦或赞许词。它们不是互斥的主题标签，也不是正负情感评分。')+
        para('另使用jieba精准分词、停用词过滤和逐帖去重，计算词的文档频数。高频词用于描述“大家在说什么”，不据此生成新的显著性检验。停用词沿用课程数据内BaiduStopwords.txt并增加少量口语停用词；便携副本保存在code/stopwords.txt。')+
        note('未拟合LDA：此任务要求至少一种文本或网络分析，本项目采用可解释内容分析并额外完成网络分析。词云不是回归变量，也不作为结论依据。'))
    tr=[[r.label,f'{r.n_hit:,}',pct(r.share_all),pct(r.share_visible),str(r.authors_with_within_variation)] for r in T.itertuples()]
    add('07 · 文本描述结果','“打卡”和日常表达占据主要位置',
        fig('03_text_features','图3　文本特征命中数及高频词。各特征可重叠；正文分词仅分析清理后的可见文本。')+
        table(['特征','命中帖数','全部帖子占比','可见正文占比','有作者内变动的作者数'],tr,[27,15,18,19,21])+
        para('自律/目标词在全部帖子中占9.2%，在有可见正文的5548帖中占15.8%；不能混用两个分母。社交称呼/互助词和问号较少，分别仅有42和32位作者提供作者内部的0/1变化，其系数不确定性相对较大。')+
        para('高频“打卡”“运动”“加油”等与健身记录语境相符，但不意味着平台上的全部内容以此为主。当前样本只覆盖100位作者，且41.8%的帖子没有可用正文；图片文字和视频语音未识别。')+
        note('高频词为“含该词的帖子数”，每帖至多计1次；不是总词频。特征分母和作者内变动计数见text_features_summary.csv。'))
    rawrows=[[r.label,num(r.raw_mean_likes_hit,2),num(r.raw_mean_likes_nohit,2)] for r in T.itertuples()]
    add('08 · 从描述到回归','原始均值差异不能直接解释为内容作用',
        table(['特征','命中帖平均点赞','未命中帖平均点赞'],rawrows,[44,28,28])+
        para('所有二元特征的命中帖在原始均值上都更受欢迎。例如社交称呼/互助词命中帖的平均点赞约90，未命中帖约36。这个比较同时包含作者受众规模差异、媒体形式差异及极端高赞帖，尚不能回答“同一作者采用这种表达是否更受欢迎”。')+
        '<h2>逐步控制什么</h2>'+table(['模型','控制项','比较含义'],[
            ['M1 基础关联','文本特征、内容形式、业务类型、时段、性别、keepValue、kgLevel、会员','不同作者和帖子混合后的条件关联'],
            ['M2 作者固定效应','M1的帖子层面控制 + 作者虚拟变量；去掉作者内不变属性','同一作者不同帖子的条件比较'],
            ['M3 主模型','M2 + 北京时间发帖日期固定效应','进一步扣除同一天的共同变化']], [20,46,34])+
        para('100位作者的gender、keepValue、kgLevel和memberStatus在样本内均不变化；作者固定效应已吸收这些属性，所以M2/M3不再重复加入。没有粉丝数、推荐曝光、视觉内容质量、社交关系或统一采集时间，不能将固定效应解释为消除了全部混杂。')+
        box('为什么不用“评论数”作为另一种全样本结果变量','仅1323帖存在采集到的评论记录，无法知道其余帖子是真的零评论还是未采集。网络使用已有记录；回归不以这些记录推算完整评论效果。'))
    add('09 · 模型与统计推断','主模型比较同一作者的不同帖子',
        formula('ln(1 + likes<sub>it</sub>) = α<sub>i</sub> + δ<sub>d</sub> + β<sub>1</sub> ln(1 + length<sub>it</sub>)<br>+ β<sub>2</sub> discipline<sub>it</sub> + β<sub>3</sub> social<sub>it</sub> + β<sub>4</sub> positive<sub>it</sub><br>+ β<sub>5</sub> question<sub>it</sub> + γ′Z<sub>it</sub> + ε<sub>it</sub>')+
        para('i表示作者，t表示帖子；α是作者固定效应，δ是北京时间发帖日期固定效应。Z包括可见正文、话题标记、表情标记、课程分享标记、内容形式、业务类型和时段。日期按实际本地时间跨到2021-01-01，不人为截断。')+
        table(['项目','实施方式'],[
            ['估计','普通最小二乘；9532条观测，182个参数，设计矩阵满秩。'],
            ['标准误','按100位作者聚类；CR1小样本系数修正；t分布自由度99计算p值和95%区间。[2]'],
            ['多重检验','对五项核心文本系数进行Benjamini–Hochberg FDR校正；控制变量不加入该检验家族。'],
            ['联合检验','五项文本系数同时为零的聚类稳健Wald F检验。'],
            ['效应解释','二元变量的exp(β)−1表示“1+点赞数”条件几何均值的相对差异；不是算术平均点赞的变化，更不是因果提升。']], [20,80])+
        para('长度使用自然对数：若1+正文长度翻倍，模型预期的1+点赞数几何均值乘以2<sup>β1</sup>。不把长度系数解释成“每多一个字增加多少点赞”。')+
        note('这些规格在本次首次拟合前写入代码；没有事前注册。聚类稳健标准误允许同一作者误差相关及异方差，但不自动解决遗漏变量、抽样选择和反向因果。'))
    mainrows=[]
    for term in FOCAL:
        r=MAIN.loc[term];mainrows.append([esc(r.label),num(r.coef),num(r.se_cluster),f'[{r.ci_low:.3f}, {r.ci_high:.3f}]',pval(r.p),num(r.q_bh_focal)])
    fitrows=[[r.model,f'{r.n:,}',num(r.r_squared),num(r.adj_r_squared)] for r in F.head(3).itertuples()]
    add('10 · 回归结果','没有充分证据表明核心词汇伴随更多点赞',
        table(['核心变量','系数','聚类SE','95%区间','p','BH q'],mainrows,[28,12,13,25,11,11])+
        note('因变量：ln(1+点赞数)。M3控制作者、日期、内容形式、业务类型、时段及其余文本标记；N=9532，作者聚类数=100。原始p值未使用星号，以免掩盖多重检验结果。')+
        para(f'自律/目标词、社交称呼/互助词和问号的区间均包含零；这些结果不能支持“只需增加相关词就能获得更多点赞”。积极表达词系数为{MAIN.loc["positive_expression","coef"]:.3f}，原始p={MAIN.loc["positive_expression","p"]:.3f}，但五项检验校正后q={MAIN.loc["positive_expression","q_bh_focal"]:.3f}，未达到0.05。')+
        table(['模型','样本量','R²','调整R²'],fitrows,[48,18,17,17])+
        para(f'主模型R²={F.iloc[2].r_squared:.3f}，但五项核心文本特征相对“相同控制、去掉五项特征”的模型仅增加{100*S["models"]["incremental_r2_text"]:.3f}个百分点解释度。五项系数联合检验F(5,99)={S["models"]["joint_focal_F"]:.3f}，p={S["models"]["joint_focal_p"]:.3f}。整体R²的大部分不能归因于这些词汇。')+
        box('不显著结果的正确读法','现有样本与测量下，没有足够证据拒绝零关联；这不等于证明所有表达方式都没有作用。低频特征、粗糙词典和缺失视觉信息都可能降低辨识能力。'))
    add('11 · 系数及效应含义','负系数也需要检验其稳定性',
        fig('04_main_coefficients','图4　M3五项核心文本系数和按作者聚类的95%置信区间。此处区间未进行多重检验调整；q值见表。')+
        para(f'积极表达词的点估计对应“1+点赞数”的条件几何均值低约{abs(MAIN.loc["positive_expression","pct_on_likes_plus1"]):.1f}%，其原始95%区间为[{MAIN.loc["positive_expression","pct_ci_low"]:.1f}%, {MAIN.loc["positive_expression","pct_ci_high"]:.1f}%]。这一变换仅说明模型尺度，不能据此建议减少积极表达。')+
        para('原始均值为正、控制后的系数为负，说明发出这些表达的作者及帖子的其他特征与点赞有关。控制模型可改变比较对象，但并不证明积极表达造成点赞下降；词语可能出现在不同内容场景，仍有不可观测混杂。')+
        '<h2>长度的量级</h2>'+para(f'1+正文长度翻倍时，主模型的1+点赞数几何均值点估计约变化{100*np.expm1(MAIN.loc["log_length","coef"]*np.log(2)):.1f}%；长度系数区间包含零。这不支持“文案越长越好”，也不能据此确定最佳字数。')+
        note('全部系数、控制标记系数及变换区间保存在regression_coefficients.csv；词汇之间可能相关，见within_author_feature_correlations.csv。'))
    robustness=[]
    for model,label in [('M3_作者与日期固定效应','主模型'),('R1_仅可见正文','仅可见正文'),('R2_去除最高1%点赞','去除最高1%'),('R3_作者等权','作者等权'),('R4_PPML计数模型','PPML计数')]:
        rr=C.loc[(C.model==model)&(C.term=='positive_expression')].iloc[0];ff=F.loc[F.model.eq(model)].iloc[0]
        robustness.append([label,f'{ff.n:,}',num(rr.coef),f'[{rr.ci_low:.3f}, {rr.ci_high:.3f}]',pval(rr.p)])
    add('12 · 稳健性检验','换用计数模型后，积极表达的区间包含零',
        fig('05_robustness','图5　三类词汇在不同规格下的系数与原始95%聚类置信区间。OLS刻画ln(1+点赞数)；PPML刻画算术条件期望点赞数的对数，系数不能直接视作同一估计量。')+
        table(['积极表达词规格','N','系数','95%区间','原始p'],robustness,[26,14,16,29,15])+
        para(f'仅正文规格保留5548帖/95位作者；去除最高1%时，保留likes≤{S["models"]["trim_threshold_likes_p99"]:.2f}的9436帖。作者等权使每位作者总权重相同，减少高产作者主导。PPML以原始点赞计数为因变量，采用相同控制项与聚类稳健推断，已收敛。')+
        para('OLS中积极表达词的负关联在若干规格下仍存在，但PPML区间包含零，而且主模型BH校正后不显著。因此不能将它描述为稳定、确定的负面效果。其他词汇的证据同样不足，稳健性检验也不能消除选择偏差。')+
        note('稳健性规格仅用于方向和敏感性检查，表内p值为各规格原始p值，不构成新的“挑显著”检验家族。完整五项结果见regression_coefficients.csv。'))
    add('13 · 文本测量核查','字面规则与真实语义之间仍有距离',
        para('对四类二元特征分别抽取5条命中及5条未命中的可见正文，共40个“帖子—特征”检查单元，可能含重复帖子。抽查样本未展示点赞数；由Codex辅助进行语义核查，未采用独立人工双编码，规则命中状态可见。它用于展示测量边界，不能据此宣称整体准确率或编码一致性。')+
        table(['例子与现象','规则结果','对解释的影响'],[
            ['“完成”的对象是身体部位配合或画作进度','自律词命中','通用词会产生健身自律语义的误报。'],
            ['“一起”叙述线下和朋友跑步','社交词命中','不能据此推断面向线上受众的互动邀请。'],
            ['“OK啦”表示满意','积极词未命中','口语表达可能被词典漏掉。'],
            ['“我不要面子的吗？”等反问','问号命中','问号不是实际求助或信息需求。']], [42,21,37])+
        '<h2>保留哪些结论，放弃哪些推断</h2>'+ul(['保留“含哪些字面词汇”及其统计关联，因为定义与代码可以复现。',
            '不把词命中称为心理状态、真实社会支持、情绪强度或用户自律程度；不生成未经验证的情感总分。',
            '不因结果不显著而回头修改词典；抽查发现用于限定结论，并为后续人工标注设计提供依据。',
            '后续可从全部可见正文随机抽样，隐藏模型预测与互动指标，由两人按预先定义的语义标准独立编码，再报告一致性与分类误差。'])+
        note('完整40条记录及具体判断：results/text_coding_review.csv；固定抽样种子与过程：code/analyze.py、code/annotate_review.py。该抽查不是对独立测试集的效度验证。'))
    add('14 · 评论网络构建','一条边表示一次可观察的评论指向',
        formula('根评论：评论者 → 帖子作者<br>明确回复：回复者 → replyUserId<br>同一用户对多次互动：合并为一条有向边，边权 = 事件数')+
        para('先按cmtId去重，再用postId查找帖子作者。回复优先使用显式replyUserId；缺失时仅可用已观测的直接回复评论ID确定对象。不得把所有子评论都指向帖主。自我互动不进入网络，删除的84个事件单独记录。')+
        table(['转换阶段','规模'],[
            ['去重评论','11595条'],['时间早于所属帖的评论','0条'],['无法确定指向对象','0条'],['自我互动移除','84条'],
            ['可用互动事件','11511次 = 6609次根评论 + 4902次明确回复'],['用户对合并后','4069条有向边；2932个有边节点'],
            ['仅明确回复子网络','1074节点；1271边']], [35,65])+
        para('网络只保留至少参与一条非自环边的节点；100位样本作者中有77位出现在该网络。其余不自动视作平台孤立用户。节点编号为稳定匿名标识，图和导出边表不显示原始用户ID。')+
        box('网络指标不是发帖前的控制变量','评论在发帖后产生，最晚延续到2021年8月。因此PageRank、入度或评论接收量只用于补充描述，不能作为“发帖前影响力”回归控制，也不能反推传播因果。')+
        note('课程依据：《社交网络分析简介》第32—37页及《Social Network Influencial》第30、35页。[4][5] 网络是评论关系而非关注、好友或实际信息扩散路径。'))
    add('15 · 网络结构','少数账号连接了大部分已采集互动',
        fig('06_comment_network','图6　全部2932个有边节点、4069条有向边。为可读性省略箭头；金色为样本帖子作者，蓝色为其他参与者；节点大小按接收事件数的对数缩放。仅标注前5位接收者。')+
        table(['指标','结果','含义'],[
            ['弱连通分量',str(N['weak_components']),'忽略方向后彼此连通的子图数'],
            ['最大弱连通分量',f'{N["largest_weak_component"]}节点（{pct(N["largest_weak_component_share"])}）','有边节点大部分落在同一弱连通分量'],
            ['密度',f'{N["density"]:.6f}','4069 / (2932×2931)；稀疏程度受节点抽样影响'],
            ['互惠率',pct(N['reciprocity']),'具有反向边的有向边占比，不按事件权重计算'],
            ['仅明确回复互惠率',pct(N['reply_only_reciprocity']),'改变建边范围后互惠率下降']], [29,29,42])+
        para('最大弱连通分量占比高，说明这些采集互动存在跨作者的连接；它不证明单次内容能够触达全部节点。整体互惠率49.6%，仅明确回复网络为29.9%，显示根评论建边规则会影响结构指标。两个网络的节点集合不同，差异不宜解释为同一群体的行为变化。')+
        note('布局使用固定种子的弹簧算法，节点的图面距离不是社交距离的统计估计。未计算网络总体的抽样置信区间，结果仅描述这一观测网络。'))
    add('16 · 互动集中度','前10位接收者获得54.0%的互动事件',
        fig('07_network_concentration','图7　接收事件前10位与累计接收分布。排序和占比均按边权，分母为11511次非自我互动事件；同一用户可重复产生事件。')+
        para(f'前10位账号共接收{pct(N["top10_received_share"])}的互动事件，第一位接收{pct(N["top1_received_share"])}。{pct(N["to_sample_author_share"])}的事件指向样本帖子作者。这里的“接收量”是评论和回复事件数，不是独立用户数、点赞数或平台粉丝数。')+
        para('样本从100位作者的帖子出发采集评论，天然偏向这些作者及其活跃互动对象。根评论均指向帖主，结构上就会产生中心节点。集中度可用于说明样本内互动分配，但不能用来挑选Keep全平台“最有影响力用户”。')+
        '<h2>与文本结果共同说明什么</h2>'+para('文本中的少量词汇不能稳定解释点赞差异，而已采集的评论在用户之间分配不均。这支持后续同时观察内容、受众及关系背景；它没有证明关系比内容更重要，也没有量化两者因果贡献。')+
        note('入度表示不同发送者数量；加权入度表示接收事件数；PageRank为补充节点指标。三者在network_nodes.csv中分开保存，报告不将它们互换。'))
    add('17 · 解释与建议','优先验证表达与互动机制，避免词汇处方',
        table(['证据','可支持的建议','需要进一步验证'],[
            ['五项核心词汇联合检验p=0.130；词典代理粗糙','不要将固定词汇加入运营模板并承诺提升点赞。提供可选的真实运动经历、感受与问题填写提示。','内容质量、图片/视频和曝光机会是否改变结果。'],
            ['原始均值与控制后系数不一致','评估内容方案时按作者或用户分组，记录曝光分母和统一观察窗口。','在可比作者、相近内容下做前瞻随机对照。'],
            ['互动接收集中，且受抽样影响','对新用户和低反馈用户提供自愿互助场景；先监测是否有人被长期忽略。','用随机用户样本验证集中度；同时衡量回复质量。']], [31,37,32])+
        '<h2>后续研究设计（尚未执行）</h2>'+para('若有平台实验权限，可将愿意参与的作者按用户随机分配至“运动过程记录提示”“面向伙伴的问题提示”和常规发布组，防止同一作者跨组污染。固定7天观察窗，记录真实曝光及独立互动用户数；把用户是否继续发布和高质量回复作为额外结果。样本量需用试点方差和最小有意义差异另行计算，本项目不虚设实验效果或样本数。')+
        '<h2>关键局限</h2>'+ul(['100位作者的课程样本与不明抽样机制，不能外推到Keep总体。',
            '正文缺失、图片文字和视频语音缺失，词典未经过独立人工效度验证。',
            '统一采集时间、有效曝光分母和粉丝信息缺失；作者/日期固定效应不能完全处理帖子观察时长及时间变化的受众差异。',
            '观察性回归不能识别因果；评论覆盖不完整，网络边界与根评论建边规则影响结构指标。'])+
        box('回答研究题目','当前数据没有支持一种可复制的“高赞用词公式”。更可靠的产出是清楚的测量、可复查的条件关联，以及下一步能验证的研究设计。'))
    add('18 · 参考资料与复现','结论可以追溯到数据、代码和原始材料',
        '<div class="references">'+para('[1] Richardson CR, Buis LR, Janney AW, et al. (2010). An Online Community Improves Adherence in an Internet-Mediated Walking Program. Part 1: Results of a Randomized Controlled Trial. <i>Journal of Medical Internet Research</i>, 12(4), e71. <a href="https://doi.org/10.2196/jmir.1338">doi:10.2196/jmir.1338</a>。用于研究动机，不把该试验效果套用到Keep。')+
        para('[2] statsmodels 官方文档：RegressionResults.get_robustcov_results，cluster参数、小样本修正与t分布推断。<a href="https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_robustcov_results.html">官方链接</a>。访问：2026-10-16；实际使用statsmodels 0.14.2，数值复核采用独立矩阵算法。')+
        para('[3] 课程材料《内容分析与自然语言处理.pdf》：第10页内容分析的三层问题，第14页预处理，第18页停用词，第24—28页中文分词。作者与年份未在文件中确认，故不补造。')+
        para('[4] 课程材料《社交网络分析简介.pdf》：第32—37页网络度分布、点度与中介中心性。')+
        para('[5] 课程材料《Social Network Influencial.pdf》：第30页入度/出度，第35页中心性与影响力的解释限制。')+
        para('[6] 课程数据《KeepData_dictionary.pdf》与两份原始CSV；字段字典和数据原样保留在提交包。')+'</div>'+
        '<h2>复现顺序</h2>'+formula('python -m pip install -r requirements.txt<br>python code/analyze.py<br>python code/annotate_review.py<br>python code/validate.py<br>python code/build_deliverables.py<br>python code/render_outputs.py<br>python code/package_submission.py')+
        para('分析过程.ipynb为已执行的伴随Notebook，保存表格和图像输出。数值核查用另一套矩阵计算独立复算主模型五项系数、聚类标准误、p值和区间，并核对去重、网络边权及互惠率。图表、回归表和正文均读取同一results目录。')+
        note('所有产出均位于projects/group内。PDF由同一份分析报告.html打印生成；演示文稿复用同一批审阅过的PNG图与数值。没有发布到外部站点。'))
    add('19 · 课程汇报与交付','填写身份信息后即可整理提交',
        table(['作业要求','对应成果'],[
            ['小组成员、题目与意义','封面、研究背景；成员留待真实填写'],
            ['完整过程与描述统计','报告02—07及代码、Notebook'],
            ['非结构化数据转结构化后回归','报告05—13；post_features.csv与回归结果'],
            ['至少一种文本或网络分析','已完成词典内容分析、分词统计及评论网络'],
            ['解释和建议','报告10—17；明确不显著结果及局限'],
            ['Presentation全员参与','16页PPTX、逐页讲稿及建议分工表'],
            ['PDF、PPT及必要文件打包','提交包ZIP含报告、演示稿、代码、数据、结果与复现说明']], [35,65])+
        '<h2>可调整的汇报分工</h2>'+table(['成员占位','建议负责内容','PPT页码'],[[r['member'],r['work'],r['slides']] for r in CFG['roles']],[25,55,20])+
        note(CFG['role_note'])+
        para('课程PDF注明：以“第几组-社交媒体分析报告.zip”为文件名，课程截止后两周（11月10日23:59）提交，11月15日前各自提交互评。原文件未明确年份，本项目只转述原要求，不推断当前学期是否沿用该日期，请以课程平台通知为准。')+
        box('提交前需要真实补齐','填写组号、成员及学号；按实际人数和贡献修订分工；检查每位成员均有汇报部分；依组号重命名ZIP。互评模板不是已完成的个人互评，不能代替真实贡献记录。'))
    return pages


def write_html(pages):
    css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e9edf0;color:#243746;font-family:"PingFang SC","Microsoft YaHei","Arial Unicode MS",sans-serif;font-size:10.2pt;line-height:1.72}.page{position:relative;width:210mm;height:297mm;padding:15mm 18mm 18mm;background:white;margin:8mm auto;break-after:page;overflow:visible}.page:last-child{break-after:auto}.kicker{color:#356D9A;font-size:9pt;letter-spacing:.8px;margin:0 0 3mm}h1{font-size:22pt;font-weight:650;line-height:1.4;margin:0 0 6mm;color:#213444}h2{font-size:12.5pt;color:#356D9A;margin:5mm 0 2mm}p{margin:0 0 3mm}ul{padding-left:5mm;margin:2mm 0 4mm}li{margin-bottom:2mm}table{width:100%;border-collapse:collapse;table-layout:fixed;font-size:9pt;line-height:1.55;margin:3mm 0 4mm}th{background:#eaf0f5;color:#254c68;text-align:left;font-weight:600}td,th{padding:2mm 2.1mm;border-bottom:.2mm solid #dce4e9;vertical-align:top;overflow-wrap:anywhere}.note,figcaption{font-size:8.5pt;color:#627581;line-height:1.6}.callout{border-left:1mm solid #B88425;background:#f7f5ee;padding:3mm 4mm;margin:4mm 0}.callout p{margin:1mm 0 0}.formula,.pipeline{padding:4mm;background:#f3f6f8;font-size:10pt;line-height:1.8;margin:4mm 0;overflow-wrap:anywhere}figure{margin:4mm 0}figure img{display:block;width:100%;height:auto;max-height:122mm;object-fit:contain}figcaption{margin-top:2mm}footer{position:absolute;bottom:9mm;left:18mm;right:18mm;border-top:.2mm solid #dce4e9;padding-top:2mm;display:flex;justify-content:space-between;font-size:8pt;color:#71818b}.subtitle{font-size:15pt;color:#356D9A;margin:3mm 0 6mm}.coverline{width:24mm;height:1.5mm;background:#B88425;margin:8mm 0}.byline{font-size:13pt;line-height:1.8}.cover-meta{font-size:10pt;color:#627581;margin:6mm 0 7mm}.references{font-size:9pt;line-height:1.65}a{color:#356D9A;text-decoration:none}@media print{body{background:white}.page{margin:0;box-shadow:none}}'''
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+esc(TITLE)+'</title><style>'+css+'</style><body>']
    for i,p in enumerate(pages,1):
        parts.append(f'<section class="page" id="page-{i}"><main><div class="kicker">{p["kicker"]}</div><h1>{p["title"]}</h1>{p["body"]}</main><footer><span>Keep 社区文本与互动网络分析 · {esc(CFG["group"])}</span><span>{i:02d} / {len(pages):02d}</span></footer></section>')
    parts.append('</body></html>');(ROOT/'分析报告.html').write_text(''.join(parts),encoding='utf-8')


def write_docx(pages):
    from bs4 import BeautifulSoup, NavigableString
    doc=Document();sec=doc.sections[0];sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.8);sec.left_margin=Cm(2);sec.right_margin=Cm(2)
    style=doc.styles['Normal'];style.font.name='Microsoft YaHei';style.font.size=DPt(10)
    style.element.rPr.rFonts.set(qn('w:eastAsia'),'Microsoft YaHei')
    for i,page in enumerate(pages):
        if i:doc.add_page_break()
        doc.add_paragraph(page['kicker'],'Subtitle');doc.add_heading(page['title'],0 if i==0 else 1)
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
            elif el.name=='h2':doc.add_heading(el.get_text(),2)
            elif el.name=='ul':
                for li in el.find_all('li',recursive=False):doc.add_paragraph(li.get_text(' ',strip=True),'List Bullet')
            else:doc.add_paragraph(el.get_text('\n',strip=True))
    doc.save(ROOT/'分析报告_可编辑.docx')


def slide_specs():
    return [
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
    prs=Presentation();prs.slide_width=Inches(13.3333);prs.slide_height=Inches(7.5)
    specs=slide_specs();notes=[]
    for i,(title,bullets,img,speaker) in enumerate(specs,1):
        slide=prs.slides.add_slide(prs.slide_layouts[6]);slide.background.fill.solid();slide.background.fill.fore_color.rgb=RGBColor(255,255,255)
        textbox(slide,.55,.28,12,.3,f'KEEP COMMUNITY  /  小组项目  /  {i:02d}',size=11,color=BLUE)
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
        notes.append(f'第{i}页　{title}\n建议用时：'+('30秒' if i in [1,16] else '45—60秒')+'\n'+speaker+'\n')
    prs.save(ROOT/'演示文稿.pptx')
    (ROOT/'汇报讲稿.txt').write_text('建议总时长约12—15分钟，按课程时间限制调整。\n组号/成员待定，分工只是可修改建议。\n\n'+'\n'.join(notes),encoding='utf-8')


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
    pages=report_pages();write_html(pages);write_docx(pages);write_slides();notebook()
    (ROOT/'results/report_manifest.json').write_text(json.dumps({'pages':len(pages),'slides':len(slide_specs()),'report':'分析报告.html','pdf':'分析报告.pdf','pptx':'演示文稿.pptx'},ensure_ascii=False,indent=2))
    print('Built',len(pages),'report pages and',len(slide_specs()),'slides.')

if __name__=='__main__':main()
