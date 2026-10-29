"""Publish the actual outcome-blind reconstruction, including failed detection.

Reads frozen evidence and aggregates only. It never chooses labels or thresholds.
"""
from pathlib import Path
import hashlib
import html
import json
import os
import re

ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'validation/classification_rebuild'
os.environ.setdefault('MPLCONFIGDIR',str(QA/'mplconfig'))
import markdown
import pymupdf as fitz
from bs4 import BeautifulSoup

STEM='分类测量重建_实证依据与验证报告'


def read(name):return json.loads((ROOT/'results'/name).read_text())
def number(x):return '—'if x is None else f'{x:.3f}'
def pct(x):return '—'if x is None else f'{100*x:.1f}%'
def table(headers,rows):
    def cell(v):return str(v).replace('|','／').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(map(cell,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(cell,r))+' |'for r in rows])+'\n'


def manuscript():
    plan=read('classification_rebuild_protocol.json')
    cal=read('classification_codebook_calibration.json')
    ai=read('classification_ai_agreement.json')
    audit=read('classification_rebuild_scope_audit.json')
    detection=read('classification_rebuild_recognition.json')
    human=read('classification_human_validation_status.json')
    assert human['status']=='pending','This v1 AI-only narrative must be revised when genuine human results arrive.'
    book=json.loads((ROOT/'code/classification_codebook_v1.json').read_text())
    model=json.loads((ROOT/'code/classification_recognizer_v1.json').read_text())
    frozen=json.loads((QA/'freeze_record.json').read_text())
    codes={x['code']:x['label']for axis in ['domains','functions']for x in book[axis]}
    comparisons=ai['rule_comparisons']['labels']
    unsupported=[codes[c]for c in audit['unsupported_codes']]
    matched={r['code']:r for r in ai['labels']}
    unknown=audit['domain_scope_diagnostics']['both_unspecified']
    out=['''# Keep正文分类测量重建：实证依据与验证结果

**2026年10月29日｜冻结版 v1｜AI开发与预验证，人工验证待完成**

此前最根本的问题是，研究把“词被命中”“模型中的词共现成分”与“真实内容或心理构念”混在了一起。补充低VIF、更多控制项或新的主题名字，都不能补上这条测量证据链。因此本轮重新做了语料取样、开放归纳、试编码、边界修订和留出检验；旧四规则与五个NMF成分保留为历史字面结果，不作为新类别设计的约束。

新结果支持建立一套可审查的候选编码手册，同时也发现：当前自动识别器不能可靠地把这套手册推广到全体正文。下文保留失败结果，不用全样本预测量冒充真实内容比例，也不据此重跑正式主题—点赞回归。

## 1. 原先的分类为什么不够成立

原四变量实际是三组词项和一个问号规则，层次并不一致。“打卡”可以记录行为、发布口号或仅指某种完成；“大家”可以称呼读者，却不证明发生互助；积极词不等于真实情绪；问号可能是反问、标题设问或自问自答。这些规则可以作为字面线索，尚不足以分别测量自律人格、社会支持、积极心理状态和真实求助。

五个NMF成分回答的是哪些词倾向共同出现。原分析固定K=5，依据少量高权重文档命名，近零权重排除后只覆盖2,470帖；删重和作者构成又会改变成分。连续权重本来可以并存，不能再解释成五个互斥、完备的真实内容类型。非空正文中71.9%未命中四规则，也不能直接称71.9%被错误分类，因为那四条规则从未构成穷尽式分类器。

本轮因此撤回“类别天然成立”的默认前提。低共线性只说明变量在样本中没有严重线性重合；它不说明名称准确，也不说明覆盖充分。作者固定效应和tag控制处理的是比较条件，不能替代正文语义验证。

## 2. 先固定观察对象，再重新抽样

只对清理后的正文作语义编码。原始tag、图片和视频不参与补全文意；需要研究这些信息时，应另建信息通道。9,532帖中5,414帖清理后非空，4,118帖没有可供本轮解释的正文；这不等于其原帖没有内容。

作者在不查看点赞等互动结果的情况下分为60／20／20人三个角色。开发样本刻意兼顾作者与长度，帮助发现类别；校准和留出在各自角色内随机抽取，并排除早先角色及历史已检查正文中的完全相同模板。该设计防止同一作者或相同文本直接跨阶段，但不能消除相似模板、共同平台语言及同基座AI的共享偏误。
''']
    out.append(table(['阶段','作者角色池／帖子','实际审读正文／作者','用途'],[
        ['开发','60人／6,446帖','160条／55人','开放归纳、形成定义'],
        ['校准','20人／1,591帖','80条／14人','严格试编码、补遗漏、固定边界'],
        ['留出','20人／1,495帖',f"160条／{audit['actual_packet_authors']['holdout']}人",'冻结后两份AI盲标、原型对照'],
        ['空正文控制','另抽12条','12条／10人','检验不把缺正文当所有语义阴性'],
    ]))
    out.append(f'''开发、校准与留出模板及作者角色均不重合，12条空正文控制均保持空正文状态。留出抽样框是881条符合条件的不同正文，实际抽到19位作者；不是“全Keep的代表样本”。新编码共涉及400条不同的非空正文，留出160条各编码两次。

编码输入只有匿名样本编号和正文；点赞、评论数、旧词典、旧NMF、作者身份、原始tag均不进入编码包。开发和校准仍是看过原研究后进行的探索性修复，不能改称事前注册研究。

## 3. 分类依据变成“概念区分＋本地语料＋反例”

本轮把两个问题分开：内容对象回答“谈论什么”，表达行为回答“这段文字在做什么”。一条“今晚跑了五公里，明天继续”的合成例句，同时包含运动对象、事件呈报和未来计划；没有必要只归一类。这是本项目的工作设计，并非某篇论文已经替Keep验证的标准分类。

运动社区研究可以为归纳、试编码和双人复核提供流程依据，例如Kalinowski等先阅读形成主题，再用试编码修订，并双人编码剩余材料；其八类及美国黑人女性社区比例不能直接移植。[Kalinowski等，2023](https://formative.jmir.org/2023/1/e43825)

主帖表达和回复支持也应分开：Wang等分别测量披露、提问、支持需要与支持提供；Stragier等的健身支持分类针对活动后的回复。本文据此要求行为证据，避免把称呼或感谢直接当作已发生互助，而不借用其社区效应。[Wang等，2015](https://www.jmir.org/2015/4/e99/)，[Stragier等，2018](https://journals.sagepub.com/doi/10.1177/1090198117703055)

词汇连贯与标签适配不是同一件事，Ying等提供了对原文和候选标签另行验证的思路；LIWC的方法文献也不能为未经独立评审的自编中文词表背书。这些文献支持验证任务，不证明当前Keep候选类别已经有效。[Ying等，2022](https://doi.org/10.1017/pan.2021.33)，[Tausczik与Pennebaker，2010](https://doi.org/10.1177/0261927X09351676)

### 3.1 内容对象：17个细分记录，按研究任务聚合展示

开发阅读形成15个内容细分，校准新增消费交易和居住装修，共17叶；为了展示而聚合成5个父组，并保留“其他明确内容”槽。父组的数量与合并方式是研究者的选择，不是统计模型证明的唯一自然分区。身体状态与体重外形、生活中的文化与关系仍保留叶级区别，不能因在同一父组就解释为同一心理构念。
''')
    grouped={x['code']:[]for x in book['domains']}
    for leaf in book['content_subdomains']:grouped[book['subdomain_to_parent'][leaf['code']]].append(leaf['label'])
    out.append(table(['父组','保留的细分','开发／校准阳性帖','开发阳性作者'],[
        [x['label'],'、'.join(grouped[x['code']])or'开放残余，须明确新对象',f"{x['development_posts']}／{x['calibration_posts']}",x['development_authors']]for x in book['domains']]))
    out.append('''这些计数证明对应对象在所读材料中确实出现，不能证明该聚合最优或推算全体比例。允许运动、身体、饮食与生活并存；“生活”要求具体生活、关系或社会文化对象，既不是“所有非运动”，也不吸收“早安”“加油”等无具体对象片段。本轮留出检验只评估父组，**17叶没有逐叶完成留出验证**。

### 3.2 表达行为：区分可观察话语，不推断人格

开发形成12个表达行为，校准发现明确感谢、商品供给和其他可辨识表达行为遗漏，增至15个。它们是候选行为码，不是要求每条都命中的15类人格。尤其将“记录行动”“未来意愿”“动员口号”分开，不合称自律；将体验自述、对象评价、感谢分开，不合称积极情绪。
''')
    out.append(table(['表达行为','开发160阳性','校准80阳性'],[[x['label'],x['development_posts'],x['calibration_posts']]for x in book['functions']]))
    out.append('''表达行为可以并存，但每个阳性都必须有正文逐字证据。礼貌称呼不能自动判为联络邀请；问号不能自动判为征询；一组动作数字不能自动判为指导。梦境、假设、转引可以含明确话题，却不能据此声称现实中的运动、疾病、关系或心理状态发生。

### 3.3 未知、缺失和其他分别保留

空正文是没有可用文字；信息不足是片段难以解读；领域未指明是能理解表达，却没有明确对象；领域不确定是可能指向某对象但证据不够；其他明确内容是确有对象而现有父组容不下。这些状态不都写成0，也不统一扔进“生活”。多标签中的0仅表示当前证据和口径下未编码该行为；原型的0则只表示未检出信号。

## 4. 校准实际改了什么

80条校准正文先按开发手册严格编码，随后保留原始版本并逐项修订。修改发生在留出包打开之前，留出出现的新缺口只记录，不再就地扩充v1。
''')
    out.append(table(['发现的问题','样本编号（匿名）','落实的修改'],[[x['issue'],'、'.join(x['evidence_ids']),x['decision']]for x in cal['changes']]))
    out.append(f'''三个新表达行为在回查160条开发正文时仍无明确阳性，因此保留为稀有候选，未为了训练而凑阳性。新增内容叶归到生活展示组也有条件：必须明确购物、交易、商业处境或住房装修本身，不能遇到品牌、家中训练、购买力比喻就一律加码。

完整纳入、排除、近邻边界及合成例句见《分类编码手册_v1》。定义、识别程序、模型和开发／校准输入均在{frozen['frozen_at_utc'][:19].replace('T',' ')} UTC记录SHA-256，随后才释放留出包。哈希能审计本地文件是否改动，不能把本次回顾性探索转成外部注册。

## 5. 冻结后检验：一致性与覆盖一起报告

两份留出编码来自相互隔离上下文的同基座AI，编码员只见冻结手册和正文。它们没有互看结果，但共享模型训练与概念偏误；以下是**AI预验证的一致性，不能称人工信度、准确率或构念效度**。正类一致率为2×双方阳性／双方阳性总数，避免只看大量共同阴性带来的高总一致率。
''')
    out.append(table(['编码','观察状态','领域状态'],[[name,'；'.join(f'{k} {v}'for k,v in ai['coverage'][key]['observation_states'].items()),'；'.join(f'{k} {v}'for k,v in ai['coverage'][key]['domain_states'].items())]for name,key in [('AI A','a'),('AI B','b')]]))
    out.append(table(['内容父组','A／B全部阳性','可比较n','正类一致率','κ'],[[x['label'],f"{x['a_positive_all']}／{x['b_positive_all']}",x['n'],pct(x['positive_agreement']),number(x['kappa'])]for x in ai['labels']if x['axis']=='domains']))
    out.append(table(['表达行为','A／B全部阳性','可比较n','正类一致率','κ'],[[x['label'],f"{x['a_positive_all']}／{x['b_positive_all']}",x['n'],pct(x['positive_agreement']),number(x['kappa'])]for x in ai['labels']if x['axis']=='functions']))
    out.append(f'''留出160条中，A／B分别有{audit['multi_label_counts']['AI_A']['domains']}／{audit['multi_label_counts']['AI_B']['domains']}条被赋多个内容域、{audit['multi_label_counts']['AI_A']['functions']}／{audit['multi_label_counts']['AI_B']['functions']}条被赋多个表达行为。当前多标签设计有实际共现证据；把它们强制互斥会丢掉同帖信息。两份编码又各有4条明确对象落入其他槽，动物和器物内容提示v1仍有覆盖缺口；这不是旧五成分的总体遗漏率。

领域比较只纳入双方均可读、均明确领域的正文，逐标签再排除不确定项；因此可比较n不能与160混用。函数比较允许领域未指明。完全没有正类时正类一致率可能无法定义；κ在期望一致率为1时留空，不能补为0或1。阳性少于5的类别证据稀薄，不能凭高总一致率宣布通过。

两份编码在{audit['different_record_n']}条记录的状态、标签或不确定项上存在差别，分歧原文和双方证据已保存为本地人工复核包；没有在计算前由AI强行裁决成一个“金标准”。本节的每类2×2计数、总一致率、排除原因和低支持标记均保留在汇总JSON／CSV。

## 6. 自动识别原型暴露了什么

为检验规则能否扩展，而非直接发放全样本新标签，本轮仅以160条AI开发编码训练字符2—4元TF-IDF＋逐标签逻辑回归，用80条校准选择预定候选阈值；词表只在开发集拟合，所有输入只用正文。该方案只是小样本基线，不能代表所有自动分类方法。

21个语义槽中只有14个达到开发至少5阳性、5阴性的训练门槛；另7个不输出自动0／1：{ '、'.join(unsupported) }。5／5是原型可拟合门槛，不是可靠性证明；校准阳性不足3的已训练类仍标记阈值未校准。
''')
    out.append(table(['表达行为','模型判阳性／160','AI A／B阳性','相对A：精确率／召回率','相对B：精确率／召回率'],[
        [codes[c],detection['holdout']['labels'][c]['states'].get('signal_detected',0),f"{matched[c]['a_positive_all']}／{matched[c]['b_positive_all']}"]+
        [f"{pct(next(x for x in comparisons if x['code']==c and x['reference']==r)['precision'])}／{pct(next(x for x in comparisons if x['code']==c and x['reference']==r)['recall'])}"for r in ['AI_A','AI_B']]
        for c in ['f_activity_update','f_experience_report','f_appraisal','f_explanation','f_practical_guidance']]))
    out.append('''上表的精确率和召回率仅以各份AI编码为参照，预测NA和语义不确定项按规则排除，是有输出条件下的指标，既非准确率，也非人类金标准性能。完整逐类TP／FP／FN／TN、F1、分母及Wilson区间见`results/classification_rule_vs_ai.csv`；逐类参照阳性中的NA数与把NA计作未检出的比例，另保存在覆盖审计中，不与条件召回率混用。区间按帖子二项模型计算，未处理同作者聚集、共享AI系统误差或类别设计不确定性。

### 6.1 不用过滤后的指标掩盖“无明确领域”
''')
    out.append(table(['AI参照／领域状态','正文数','原型适用门控通过','至少赋一个领域'],[[name+'／'+x['domain_state'],x['n'],x['gate_passed'],x['at_least_one_domain_assigned']]for name in ['AI_A','AI_B']for x in audit['domain_scope_diagnostics'][name]]))
    out.append(f'''双方都判断领域未指明的{unknown['n']}条中，原型仍给{unknown['at_least_one_domain_assigned']}条赋了至少一个领域。这个分歧不会进入“双方均有明确领域”的逐类条件比较，因此必须另列。留出正文中另有{audit['zero_development_vocabulary_overlap']['n']}条与开发词表没有任何字符n元重合，仍有{audit['zero_development_vocabulary_overlap']['at_least_one_domain_assigned']}条被赋领域；这时判定来自截距和阈值，不是成功理解了新正文。

当前原型同时出现过度检出、漏检与未指明领域误赋。不能仅因为它覆盖了多数正文，就把输出当作比旧五成分更好的真实分类。这次失败把正式应用的阻断点具体化了：需要足量且经人工核查的阳性／反例、适用范围识别和真正独立的语义验证，而不是继续调整阈值直到留出结果好看。

### 6.2 全语料运行只核查处理范围

9,532帖里，原型机械区分4,118条空正文、144条仅符号或数字正文、5,270条含文字正文。只有4,985条通过其领域门控；这只是程序状态，不是内容真实可识别率。全量`rebuilt_content_features.csv`保留分数、状态和NA，明确标为初筛，不进入正式回归，也不据其检出次数绘制“Keep主题占比”。

## 7. 正式研究应该采用哪些修订

四个旧词典变量继续可以报告为具体字面特征，但删除从词命中直接跳到自律、心理情绪、社会支持或真实求助的表述。旧五NMF成分继续可以报告为探索性词共现结构，不能作为已验证的全体真实分类。

新手册用于人工编码和后续测量验证。当前有语料与反例依据的，是“这些对象和行为在本地正文中出现、应加区分”；尚未证明的是“父组最优、类别齐全、普通人可稳定编码、原型能可靠推广、类别能解释点赞”。每一层结论都应单独取证。

多标签不要求互斥或合计100%，内容域和表达行为也不合并竞争。以后做回归时，独立0／1标签不因共同出现就必然完全共线；仍需在实际估计样本检查频数、作者内变化、秩和相关性。若重新使用归一化总和为1的主题权重，则仍须处理参照成分。验证未完成前不为新标签给出正式互动效应。

作者少帖和tag问题沿用前轮复核：全样本与主题子样本的作者支持须分别检查；tag保留为用户自选元数据，不能充当正文人工真值。它们可以用于日后冻结方案的情境控制或另一信息通道，不能挽救语义定义不成立的类别。

## 8. 已交付的人工验证工具与尚缺证据

已生成A／B两份各160条的盲审表，不含模型输出、旧类别、作者或互动结果；配有完整编码手册、冻结指纹、填写说明和校验程序。两人应先分别完成，再检查分歧并由未参与初始编码者裁决；若据此修改语义定义，须升级v2并另取新留出，不能回写本轮v1的检验结果。

人工应优先核对生活父组是否过宽、事件／体验／评价边界、短句领域未指明、其他槽与稀有类。对缺乏阳性的类另补有明确取样规则的针对性材料，可用于边界研究；该补样比例不能混入总体占比。17叶若要用于实质结论，还需逐叶验证。

当前人审状态为 **{human['status']}**：两份表均未填，程序未计算任何人类一致性或人类准确率。我们不能替研究者完成真实人类判断，现阶段最可靠的交付是可审查的重建记录、冻结手册、保留失败的预检验与可直接开始的人审材料。

## 9. 文件与复核入口

| 文件 | 用途 |
| --- | --- |
| 分类编码手册_v1.md／PDF | 逐类定义、纳入排除、近邻和合成例句 |
| code/classification_codebook_v1.json | 冻结机器可读定义与开发、校准证据 |
| results/classification_codebook_calibration.json | 校准修订轨迹与计数 |
| validation/classification_rebuild/freeze_record.json | 定义、程序、模型及输入哈希 |
| results/classification_ai_agreement.json／CSV | 每类AI一致性、2×2计数、分母与排除 |
| results/classification_rule_vs_ai.csv | 原型相对两份AI的完整条件指标 |
| results/classification_rebuild_scope_audit.json | 未指明领域、覆盖、词表零重合和划分复核 |
| validation/classification_rebuild/private/human_review_A.csv、B.csv | 本地全文盲审表，公开仓库忽略 |
| validation/classification_rebuild/private/holdout_disagreements_for_later_human_review.json | 未裁决的AI分歧证据，本地保留 |

在本地原始数据与已保存语义标注齐全时，运行`make classification-evaluate PYTHON=/path/to/python`重算评估，再运行`make classification-report`导出本报告与手册。语义标注本身不是可由正则重建的真值；公开代码和聚合结果不能代替缺失的人审。准备、拟合脚本在冻结后拒绝覆盖本版，后续重建须用新版本目录。
''')
    return '\n\n'.join(out)


CSS='''body{font-family:sans-serif;font-size:10pt;line-height:1.5;color:#203028;}h1,h2,h3{page-break-after:avoid;}h1{font-size:23pt;color:#234d43;}h2{font-size:15pt;color:#234d43;margin-top:17pt;}h3{font-size:11.5pt;color:#304f46;margin-top:13pt;}p{margin:7pt 0;}table{width:100%;border-collapse:collapse;font-size:8.3pt;margin:8pt 0;}th,td{padding:4pt;text-align:left;vertical-align:top;}th{font-weight:bold;}a{color:#24604f;}code{font-size:8pt;}img{max-width:100%;}'''


def export_document(stem):
    source=ROOT/(stem+'.md')
    body=markdown.markdown(source.read_text(),extensions=['tables','fenced_code'])
    export_css=CSS+('body{line-height:1.40;}p{margin:6pt 0;}'if stem==STEM else'')
    markup='<html><head><meta charset="utf-8"><style>'+export_css+'</style></head><body>'+body+'</body></html>'
    (ROOT/(stem+'.html')).write_text(markup)
    target=ROOT/(stem+'.pdf')
    writer=fitz.DocumentWriter(str(target))
    story=fitz.Story(html=markup,archive=fitz.Archive(str(ROOT)))
    page=fitz.paper_rect('a4'); area=fitz.Rect(42,40,page.width-42,page.height-44)
    more=True;n=0
    while more:
        device=writer.begin_page(page);more,_=story.place(area);story.draw(device);writer.end_page();n+=1
        assert n<90
    writer.close()
    doc=fitz.open(target)
    for i,p in enumerate(doc,1):p.insert_text((page.width/2-8,page.height-22),str(i),fontsize=9,color=(.35,.4,.37))
    temp=QA/(stem+'_numbered.pdf');doc.save(temp,garbage=4,deflate=True);doc.close();os.replace(temp,target)
    # Reuse the repository's editable Word exporter on the same HTML content.
    import build_phase2_report as office
    office.STEM=stem
    soup=BeautifulSoup('<main><section>'+body+'</section></main>','html.parser')
    office.write_docx(soup,[])
    pdf=fitz.open(target)
    text=''.join(p.get_text()for p in pdf)
    checks={'page_count':len(pdf),'all_pages_nonempty':all(len(p.get_text().strip())>15 for p in pdf),
            'text_characters':len(text),'no_replacement_character':'\ufffd'not in text,
            'md_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'pdf_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
    # Save a compact visual proof; source text and private annotations stay out.
    from PIL import Image,ImageOps,ImageDraw
    thumbs=[]
    for i,p in enumerate(pdf):
        pix=p.get_pixmap(matrix=fitz.Matrix(.45,.45),alpha=False)
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        canvas=Image.new('RGB',(im.width+12,im.height+28),'#e7ece9');canvas.paste(im,(6,6))
        ImageDraw.Draw(canvas).text((8,im.height+8),str(i+1),fill='black');thumbs.append(canvas)
    cols=4;rows=(len(thumbs)+cols-1)//cols
    sheet=Image.new('RGB',(cols*thumbs[0].width,rows*thumbs[0].height),'#dce3df')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%cols)*im.width,(i//cols)*im.height))
    sheet.save(QA/(stem+'_contact.png'))
    pdf.close()
    assert checks['all_pages_nonempty']and checks['no_replacement_character']
    return checks


def main():
    md=manuscript()
    (ROOT/(STEM+'.md')).write_text(md)
    output={STEM:export_document(STEM)}
    if (ROOT/'分类编码手册_v1.md').is_file():output['分类编码手册_v1']=export_document('分类编码手册_v1')
    (QA/'delivery_checks.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
