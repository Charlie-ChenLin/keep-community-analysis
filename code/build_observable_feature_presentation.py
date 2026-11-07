"""Build the observable-feature presentation from the protected teacher deck.

All estimates and matching rules are inherited. Only presentation scope,
terminology and package labels change; no model is selected or re-estimated.
"""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import hashlib
import json
import re
import uuid
import zipfile

from defusedxml import minidom
from lxml import etree
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from build_teacher_feedback_presentation import C, rgb, new_text, rect, set_text, table

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Keep社区内容表达与互动反馈_老师意见修订版.pptx'
STEM = 'Keep社区帖子特征与互动反馈_正式修订版'
QA = ROOT / 'validation/slides_observable_features'
SCOPE = json.loads((ROOT/'code/observable_feature_scope.json').read_text())
CHAPTERS = {'RQ1':'样本覆盖、媒体、tag与点赞', 'RQ2':'字面特征与点赞的条件关联', 'RQ3':'评论字面线索与连接结构'}

# The same replacements are applied to visible text, chart caches and xlsx cells.
# Longest matches first prevents partial changes of compound source labels.
LABELS = {
    '自律／目标词命中':'坚持等词项命中（A）',
    '社交称呼／互助词命中':'大家等词项命中（B）',
    '积极表达词命中':'开心等词项命中（C）',
    '自律 / 目标 D':'坚持等词项（A）',
    '社交 / 互助 S':'大家等词项（B）',
    '积极表达 P':'开心等词项（C）',
    '问号 Q':'问号（D）',
    '自律／目标词':'坚持等词项（A）',
    '社交／互助词':'大家等词项（B）',
    '积极表达词':'开心等词项（C）',
    '自律 / 目标':'坚持等词项（A）',
    '社交 / 互助':'大家等词项（B）',
    '自律／目标':'坚持等词项（A）',
    '社交／互助':'大家等词项（B）',
    '命中积极表达':'命中词项C',
    '积极表达':'开心等词项（C）',
    '积极BH q':'C的BH q',
    '积极β／BH q':'C的β／BH q',
    '鼓励 / 赞许':'鼓励或赞许词项',
    '鼓励性留言':'鼓励或赞许词项命中留言',
}


def replace_labels(text):
    for old,new in sorted(LABELS.items(), key=lambda x:-len(x[0])):
        text=text.replace(old,new)
    return text


def text_at(slide, index, value, size=None):
    set_text(slide.shapes[index],value,size)


def cells_at(slide, index, rows, size=15):
    t=slide.shapes[index].table
    assert len(rows)==len(t.rows)
    assert len(rows[0])==len(t.columns)
    for i,row in enumerate(rows):
        for j,value in enumerate(row):set_text(t.cell(i,j),value,size)


def clear(slide):
    for shape in list(slide.shapes):
        # Drop stale chart/image relations before deleting its shape.
        for el in shape._element.iter():
            for attr,value in list(el.attrib.items()):
                if attr.endswith('}embed') or attr.endswith('}id'):
                    if value in slide.part.rels:
                        try:slide.part.drop_rel(value)
                        except KeyError:pass
        slide.shapes._spTree.remove(shape._element)


def frame(slide,title,question,foot,dark=False):
    clear(slide)
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb=rgb(C['deep'] if dark else C['white'])
    new_text(slide,question,.58,.30,8.8,.30,13,'BDD3C8' if dark else 'green',True)
    new_text(slide,'可观察字面特征与互动关联',9.12,.30,3.62,.30,11,'BDD3C8' if dark else 'muted',align=PP_ALIGN.RIGHT)
    new_text(slide,title,.58,.88,12.15,.72,27,'white' if dark else 'ink',True)
    new_text(slide,foot,.58,7.09,11.36,.22,9,'BDD3C8' if dark else 'muted')
    new_text(slide,'00 / 00',11.99,7.07,.77,.25,10,'BDD3C8' if dark else 'muted',align=PP_ALIGN.RIGHT)


def card(slide,head,body,x,y,w,h,color='light',body_size=17):
    rect(slide,x,y,w,h,color)
    new_text(slide,head,x+.20,y+.17,w-.40,.42,20,'green',True)
    new_text(slide,body,x+.20,y+.80,w-.40,h-.94,body_size,'ink')


def patch_xml_strings(data):
    """Preserve OOXML prefixes while replacing only XML text nodes."""
    doc=minidom.parseString(data)
    changed=0
    is_post=any(x.encode('utf-8')in data for x in ['自律','社交 / 互助','积极表达','坚持等词项','大家等词项','开心等词项'])
    def walk(node):
        nonlocal changed
        for child in node.childNodes:
            if child.nodeType in (child.TEXT_NODE,child.CDATA_SECTION_NODE):
                revised=replace_labels(child.data)
                if is_post and revised=='问号':revised='问号（D）'
                if revised!=child.data:child.data=revised;changed+=1
            else:walk(child)
    walk(doc)
    return (doc.toxml(encoding='UTF-8') if changed else data),changed


def patch_package(out):
    with zipfile.ZipFile(out) as z:parts={n:z.read(n)for n in z.namelist()}
    changes={'chart_text_nodes':0,'xlsx_text_nodes':0,'xlsx_files_changed':0}
    for name,data in list(parts.items()):
        if re.fullmatch(r'ppt/charts/chart\d+\.xml',name):
            parts[name],count=patch_xml_strings(data);changes['chart_text_nodes']+=count
        if name.startswith('ppt/embeddings/') and name.endswith('.xlsx'):
            with zipfile.ZipFile(BytesIO(data))as book:cells={n:book.read(n)for n in book.namelist()}
            count=0
            for cellname,xml in list(cells.items()):
                if cellname.endswith('.xml'):
                    cells[cellname],n=patch_xml_strings(xml);count+=n
            if count:
                buffer=BytesIO()
                with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED)as book:
                    for n,value in cells.items():book.writestr(n,value)
                parts[name]=buffer.getvalue()
                changes['xlsx_text_nodes']+=count;changes['xlsx_files_changed']+=1
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED)as z:
        for name,data in parts.items():z.writestr(name,data)
    return changes


def main():
    QA.mkdir(parents=True,exist_ok=True)
    source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    pres=Presentation(SOURCE);slides={i:s for i,s in enumerate(pres.slides,1)}
    old_manifest=json.loads((ROOT/'validation/slides_teacher_feedback/slides_manifest.json').read_text())
    meta={i:deepcopy(m)for i,m in enumerate(old_manifest,1)}

    def note(page,title,seconds,speech,question=None,source=None,appendix=False,focus=None):
        m=meta[page]
        m.update(title=title,seconds=seconds,speech=speech,appendix=appendix,
                 source=source or m['source'],focus=focus or title,question=question,
                 rq=question or ('探索附录，不计主讲' if appendix else '研究范围与说明'))
        m['chapterName']='探索性附录' if appendix else CHAPTERS.get(question,'研究设计与共同边界')

    # A visible, neutral label throughout the deck; caches/workbooks are patched later.
    for old_page,s in slides.items():
        for sh in s.shapes:
            if sh.has_text_frame:
                value=replace_labels(sh.text)
                if value!=sh.text:set_text(sh,value)
            if sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        value=replace_labels(cell.text)
                        if 9<=old_page<=18 and value=='问号':value='问号（D）'
                        if value!=cell.text:set_text(cell,value)

    # Cover and exact scope-wide research questions, with an explicit speaking path.
    s=slides[1]
    text_at(s,3,'帖子特征与\n互动反馈',40)
    text_at(s,4,SCOPE['subtitle'],24)
    text_at(s,6,'正式修订版 · 可观察特征与观察性关联',16)
    note(1,SCOPE['title'],20,'我们研究这批Keep帖子的可观察特征与互动反馈。正文部分使用固定词项、问号和长度，评论部分使用已记录的回复对象与账号连接。本轮没有进行人工语义复核，因此主结论不依赖内容分类。')

    s=slides[2]
    frame(s,'研究问题与汇报路径','三个问题，三种可核对的证据','主讲按RQ1→RQ2→RQ3展开；内容分类仅保留为探索附录。')
    qs=SCOPE['research_questions']
    paths=[('01  样本覆盖与描述','正文可见范围、媒体形式、原始tag、点赞分布'),('02  字面特征与点赞','固定规则、作者与日期控制、三种正文口径及复核'),('03  评论与连接','字面词项、直接回复、方向、窗口与参与人数')]
    for i,(q,path)in enumerate(zip(qs,paths)):
        y=1.90+i*1.53
        rect(s,.70,y,11.95,1.28,'light'if i%2==0 else 'pale')
        new_text(s,q['id'],.91,y+.20,.90,.35,21,'green',True)
        new_text(s,q['text'],1.92,y+.19,6.20,.83,16.5)
        new_text(s,path[0],8.60,y+.19,3.78,.35,18,'green',True)
        new_text(s,path[1],8.60,y+.63,3.78,.45,13.5,'muted')
    note(2,'研究问题与汇报路径',40,'我们分三步回答。第一步描述正文能观察到多少、媒体和tag怎样分布，以及点赞的长尾。第二步检验固定词项、问号和正文长度与点赞的条件关联，并列报告三种正文范围，不按显著性选模型。第三步描述已采集评论的字面线索、直接回复方向和用户连接。三部分分别回答分布、关联与结构；不把词项命中直接解释成人格、情绪或社会支持。')

    s=slides[3]
    text_at(s,12,'原始正文可见5,548帖；清理后非空5,414帖；5,209帖有原始tag。\n三种正文口径并列披露；缺失标记不能恢复未记录的文字。',15)
    note(3,'数据来源、清洗与可观察范围',40,'课程样本有9,532帖、100位作者，帖子发表于2020年十一月至十二月，按原始UTC时间；换成北京时间后，末端跨到2021年1月1日。评论按ID去重后有11,595条，但只有1,323帖采到评论，其余的覆盖情况未知。原始正文可见5,548帖，清理后5,414帖非空。累计点赞的统一采集时点和真实曝光缺失，所以不计算点赞率，也不能把记录较多视为内容完整。日期和时段统一按北京时间处理。')

    s=slides[4]
    text_at(s,0,'RQ1  样本覆盖、媒体、tag与点赞',13)
    text_at(s,11,'媒体与点赞显示反馈差异；正文缺失和tag则界定了接下来能比较哪些记录。',18)
    note(4,'媒体均值不同，点赞分布存在长尾',30,'图片和视频帖平均大约51赞和48赞，纯文字与无媒体约8赞和4赞。这是尚未调整的描述。整体点赞均值37.05，高于中位数25，最高为5,126，说明少量高赞帖拉高了均值；普通帖的情况不能只看平均数。','RQ1')

    s=slides[8]
    frame(s,'RQ1的回答：先交代记录范围，再看反馈分布','RQ1  样本覆盖、媒体、tag与点赞','分母为9,532帖；正文非空与tag有无是不同记录维度，不能相互替代。',dark=True)
    for y,num,head,body in [(1.90,'56.8%','清理后正文非空','5,414帖；其余4,118帖没有非空正文，不能据此判断图像或视频内容。'),(3.42,'54.6%','记录有原始tag','5,209帖、269种tag；其中1,517帖缺正文，tag有时补充记录，但不等于正文。'),(4.94,'25','点赞中位数','整体均值37.05；图片／视频帖原始均值更高，比较词项前需要考虑媒体与作者。')]:
        new_text(s,num,.85,y,2.15,.70,34,'white',True)
        new_text(s,head,3.10,y,9.10,.43,23,'white',True)
        new_text(s,body,3.12,y+.61,9.10,.67,17,'DFEAE3')
    note(8,'RQ1的回答：记录范围与反馈分布',25,'RQ1首先给出可观察范围：56.8%的帖子清理后正文非空，54.6%有原始tag，两种记录并不相同。点赞同时存在媒体均值差异和明显长尾。下面只分析已经记录到的字面特征，并明确不同样本口径。','RQ1',source='teacher_complete_body_model.json；teacher_author_tags_summary.json；summary.json')

    # Reuse the former semantic-diagnostics slot for the scope decision itself.
    s=slides[6]
    frame(s,'测量边界：本轮为什么不强制分类','主分析的测量范围','原型诊断来自AI预检验，不是人工准确率；本轮没有人工语义复核。')
    card(s,'本轮已完成的测量','固定词项命中、问号与正文长度；\n原始tag、媒体、点赞与明确回复记录。\n规则可重叠，也不穷尽帖子内容。',.72,1.95,5.78,2.44,body_size=17)
    card(s,'本轮未完成的验证','人工语义复核：0人。\n五个旧NMF名称及17内容叶／15行为候选\n框架均不作为正式内容类别。',6.80,1.95,5.78,2.44,body_size=17)
    rect(s,.72,4.74,11.86,1.12,'light')
    new_text(s,'24条领域未指明 → 原型仍给18条赋域',.94,4.94,11.42,.42,24,'orange',True)
    new_text(s,'这是两份AI记录均判“未指明”时的过度赋类线索；AI间一致也不能代替人工金标准。',.94,5.47,11.42,.30,15)
    new_text(s,'本轮交付不依赖填写人工编码A／B表；分类材料仅保留为后续探索资源。',.84,6.31,11.68,.47,18,'green',True)
    note(6,'测量边界：本轮为什么不强制分类',40,'这里说明本轮的范围选择。我们没有时间完成人工语义复核，因此人工复核人数是零。旧NMF五个名称，以及新提出的17个内容叶和15个表达行为，都只保留为探索材料。识别器原型在两份AI记录都判领域未指明的24条中，仍给18条赋了领域，提示强制归类会越过原文信息。这是AI预检验的诊断，不是人工准确率。当前交付直接使用可观察记录，不依赖再填写人工编码A、B表。',source='observable_feature_scope.json；classification_rebuild_scope_audit.json',focus='清楚说明已完成测量和未完成的语义验证，不以AI当人工。')

    s=slides[9]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,2,'固定字面规则与原始点赞均值',27)
    text_at(s,3,'全样本9,532帖；未命中组含缺失正文设0的帖子，不能视为完整正文中的纯未命中组。',9)
    cells_at(s,5,[['五项可观察变量','固定规则与例子'],['正文长度','ln(1+清理后字符数)'],['坚持等词项（A）','坚持、目标、打卡、完成等'],['大家等词项（B）','大家、小伙伴、谢谢、一起等'],['开心等词项（C）','开心、快乐、喜欢、哈哈等'],['问号（D）','正文出现 ? 或 ？即记1']],14)
    text_at(s,6,'四条规则的原始平均点赞',18)
    text_at(s,8,'四条规则允许交叉；命中记1，不构成内容分类。',14)
    text_at(s,10,'原始命中组均值较高；\n还要检查正文覆盖、媒体和作者构成。',17)
    note(9,'固定字面规则与原始点赞均值',30,'我们保持原来的词表和匹配方法，只把名称改为中性编号。A命中坚持等词项，B命中大家等词项，C命中开心等词项，D记录问号。四条规则可以交叉，正文长度另外计算。图中各命中组的原始点赞均值较高，但全样本未命中组还包括正文缺失后设零的帖子，不能据此说某种写法更有效。','RQ2')

    s=slides[10]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,2,'四条规则测到什么，以及解释到哪里',27)
    text_at(s,3,'A–C原词表按直观含义编制；改中性名不增加语义效度；仅沿用为固定、可复算的探索性指标。',9)
    cells_at(s,5,[['规则','固定字面匹配','解释边界'],['坚持等词项（A）','坚持、目标等；含“第…天”正则','不直接测自律人格或真实完成训练'],['大家等词项（B）','大家、一起、谢谢等；子串匹配','不直接测互助行为或关系强度'],['开心等词项（C）','开心、喜欢、棒等；子串匹配','不直接测情绪；未处理否定和反讽'],['问号（D）','正文出现 ? 或 ？','不直接测真实提问或求助意图']],15)
    text_at(s,7,'71.9%非空正文未命中规则，这是未命中率；词表未按显著性增删，不代表完整分类。',16.5)
    note(10,'四条规则的测量与解释边界',40,'A到C的原词表按直观含义编制，改成中性名称不会增加语义效度。本版只沿用为固定、可复算的探索性操作指标，没有按显著性增删词。A包含第几天的正则匹配，B和C使用子串字面匹配。坚持等词不直接代表自律人格，大家等词不直接代表互助，开心等词不能当情绪判断，问号也可能是反问。非空正文71.9%没有命中，说明规则局部、不穷尽，未命中率不能称为分类错误率。','RQ2')

    s=slides[11]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,2,'字面规则可交叉，数值上未见明显共线性',27)
    text_at(s,8,'182帖同时命中≥2项\n交叉命中可以保留。',18)
    text_at(s,9,'低VIF只说明与已纳入列的线性重复不强；不能证明四条规则具有语义独立性。',18)
    note(11,'交叉命中与完整设计矩阵VIF',30,'四条规则允许交叉，本样本有182帖同时命中至少两项。完整历史M3有182列并且满秩，四条规则的VIF约1.11到1.75，最大两两相关0.119。没有明显数值共线性，所以不必仅因可能共现就机械合并。低VIF只诊断设计矩阵，不能证明词项测准了某个心理或内容概念。','RQ2')

    s=slides[12]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,3,'全样本9,532帖；未命中组含缺正文设0者；图示为图片／视频帖比例，未作条件调整。',9)
    text_at(s,5,'词项C命中两组的图片／视频帖占比',18)
    note(12,'原始均值差异伴随媒体构成差异',25,'以开心等词项C为例，命中组图片或视频占比94.9%，未命中组69.1%，平均点赞分别为57.29和35.76。两组媒体构成和涉及作者不同，而且未命中组含缺失正文者。原始均值不能单独归给措辞，因此后面纳入媒体、作者和日期等条件。','RQ2')

    s=slides[13]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,7,'X：正文长度、A／B／C词项命中、问号D。C：原始正文可见、有无tag、表情、课程分享、媒体、业务类型与时段。',15)
    text_at(s,9,'作者固定效应利用同一作者的帖间变化；拟合度提高，不能据此认定消除了全部作者差异。',17)
    note(13,'既有模型：作者、日期与发布条件',40,'这里沿用历史M3，不重新挑模型。结果是累计点赞加一后的对数，解释变量是长度和四条字面规则，控制媒体、业务类型、时段、正文可见、tag有无等条件，并加入作者和日期固定效应。作者固定效应主要利用同一作者的帖间变化，标准误按作者聚类；五项检验在模型内做BH校正。它改善了比较，但不能控制每帖曝光等未记录差异，更不自动建立因果。','RQ2')

    s=slides[14]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,6,'词项C：β = −0.086',21)
    text_at(s,10,'原始均值差异未在调整比较中保留；不能据此推出“命中开心等词导致点赞下降”。',17)
    note(14,'历史M3：全样本条件关联',35,'历史全样本M3的五项联合p为0.130。开心等词项C的系数是负0.086，原始p为0.016，模型内五项BH校正后q为0.079。这个模型中五项q都没有达到5%的标准，新增解释度也只有0.065个百分点。这些数字保留原估计；负向条件关联不等于命中词项导致点赞降低，下一页还要看正文范围怎样改变结果。','RQ2')

    s=slides[15]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,6,'三种口径并列披露：不能说“全部设定都不显著”，也不能按p值追认唯一主模型。',20)
    text_at(s,7,'正文范围改变了比较人群；清理后非空正文p=0.040属于既有重分析结果，\n不追认为事前确定的唯一主分析。缺失文字和曝光仍无法恢复。',17)
    note(15,'三种正文口径并列报告',45,'三种范围回答的是不同人群。全样本有9,532帖，五项联合p为0.130；原始正文可见5,548帖，p为0.067；清理后正文非空5,414帖，p为0.040，长度和C的模型内BH q约0.048。不能笼统说全部设定都不显著，也不能因为第三个p更小就追认它为事前唯一主分析。BH只覆盖每个模型内这五项，不覆盖全部探索设定。我们并列披露，把差异解释为结论对记录范围敏感。','RQ2')

    s=slides[16]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,2,'既有敏感性分析：A、B、C的方向与区间',27)
    text_at(s,7,'历史M3',12)
    text_at(s,17,'词项C在这些设定中均为负，但PPML区间跨0；逐作者剔除范围[−0.100, −0.074]。',16.5)
    s.shapes[17].top=Inches(6.72);s.shapes[17].height=Inches(.30)
    for sh in s.shapes:
        if sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    if cell.text=='M3主模型':set_text(cell,'历史M3')
    note(16,'既有敏感性分析：方向与区间',25,'已有敏感性分析中，词项C的点估计方向较一致；去最高1%、作者等权和逐作者剔除后仍为负。但PPML的区间跨零，而且它拟合点赞均值，与对数模型的尺度不同。这说明方向检查不能替代区间、不确定性或正文口径比较，也不能据此给出增赞或降赞承诺。','RQ2')

    # Keep the author support evidence, remove topic effects from the main lecture.
    s=slides[17]
    frame(s,'作者支持：少帖作者与作者内变化','RQ2  字面特征与点赞的条件关联','作者次数指课程样本内次数；单帖作者不提供同一作者内的特征变化。')
    new_text(s,'100位作者 · 2名单帖 · 中位66帖',.80,1.91,11.82,.55,26,'green',True)
    table(s,['作者门槛','N／作者','五项联合p'],[['全部作者','9,532／100','0.130'],['至少5帖','9,524／95','0.131'],['至少10帖','9,462／87','0.130']],.74,2.83,7.10,[2.48,2.63,1.99],17,[.58,.65,.65,.65])
    new_text(s,'提供作者内变化的人数',8.35,2.91,4.10,.42,20,'green',True)
    new_text(s,'A  76人\nB  42人\nC  64人\nD  32人',8.36,3.63,4.10,1.80,20)
    new_text(s,'少帖作者剔除未改变全样本的联合检验判断；稀少特征的有效变化来源仍较少。',.80,6.18,11.82,.65,19,'green',True)
    note(17,'作者支持：少帖作者与作者内变化',30,'100位作者中有两名单帖作者，中位66帖。只保留至少5帖或10帖的作者后，历史M3五项联合p约为0.13，主要判断没有变化。但A、B、C、D分别只在76、42、64、32位作者内变化，稀少特征并没有100位作者都提供比较信息。这项检查不能修复曝光缺失或正文选择。','RQ2',source='teacher_author_tags_summary.json')

    s=slides[18]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,7,'拼接后：词项A命中 877 → 3,342；问号D 125 → 354。',21)
    text_at(s,8,'平台tag措辞改变了被测文字范围；tag是元数据，不能作为正文语义的标准答案。',17)
    note(18,'tag控制与正文加tag是两种比较',30,'原M3已经控制tag有无。进一步加上九个频繁且跨作者的tag身份，五项联合p为0.102；把tag拼进正文再重编码，p为0.173。后者使A命中从877变成3,342，问号从125变成354，说明平台话题措辞改变了被测文字范围。控制tag与把tag当正文不同，也都不等于验证了内容类别。','RQ2')

    s=slides[21]
    text_at(s,0,'RQ2  字面特征与点赞的条件关联',13)
    text_at(s,1,'字面特征与点赞的条件关联',11)
    text_at(s,3,'既有清理、规则、控制项与估计值保持不变；三种正文范围并列，不据显著性选择主模型。',9)
    text_at(s,5,'固定字面特征的条件关联随正文范围变化。',24)
    text_at(s,6,'五项联合p依次为0.130、0.067和0.040；非空正文模型的长度与C模型内BH q约0.048。解释范围应与各自样本一致，不能把局部证据概括为“文字无效”或“用词增赞”。',18)
    text_at(s,7,'作者、tag与VIF复核支持计算层面的可比性。',24)
    text_at(s,8,'少帖作者、tag和数值共线性检查没有消除正文缺失、曝光差异和观察性选择；本轮也未进行人工语义复核。主结论只涉及操作性字面特征。',18)
    text_at(s,10,'RQ3转向已采集评论：哪些词项出现、明确回复指向谁、由多少不同用户参与？',17)
    note(21,'RQ2的回答：条件关联与边界',25,'RQ2的回答是：指定字面特征与点赞存在一些局部关联，但统计判断随正文范围变化。作者、tag和VIF复核提供计算上的检查，不能消除正文选择或曝光差异，也不补上人工语义效度。我们报告条件关联，不给用词增赞建议，也不把它概括成文字内容普遍无效。','RQ2',source='既有M3、三种正文口径及作者／tag／VIF敏感性结果')

    # Repair semantic claims in the inherited comment results, preserving counts.
    s=slides[22]
    text_at(s,1,'评论的字面线索',11)
    text_at(s,3,'固定词表命中可交叉；分母为各角色全部发言。词项不直接测情绪、社会支持或语言功能。',9)
    text_at(s,9,'按帖子角色看：其他用户更多命中\n鼓励或赞许词项，帖主更多命中感谢词项。',17)
    text_at(s,10,'把外来根评论与帖主直接回复配对，分别观察已采集回复覆盖与最早回复的词项。',17)
    note(22,'评论长度、词项与帖子角色',30,'已采集评论的中位长度为六字符。加油出现在612条评论、431个账号中，谢谢出现在359条、53个账号中。前者的使用者更广，后者重复使用更集中。按所在帖子角色看，其他用户更多命中鼓励或赞许词项，帖主更多命中感谢词项。这里描述固定词项，不据此判断真实情绪、社会支持或语言功能。','RQ3')

    s=slides[23]
    text_at(s,1,'评论的字面线索与直接回复',11)
    text_at(s,2,'词项命中与已采集直接回复：覆盖和致谢要分开',26)
    text_at(s,3,'仅为已采集记录的描述；7天内未匹配直接回复，不等于真实未回复；未作因果检验。',9)
    text_at(s,6,'配对：6,609条外来根评论；从留言发出起7天，匹配明确指向该条留言的帖主直接回复。\n根评论未指定回复对象；匹配到多条直接回复时，只取最早一条。',14.5)
    text_at(s,7,'7天内匹配到已采集直接回复的比例',17)
    text_at(s,8,'已匹配记录中，最早回复含感谢词项比例',16.5)
    text_at(s,13,'鼓励或赞许词项命中组：回复覆盖低12.8个百分点；已匹配记录中感谢词项高20.3个百分点。',16.5)
    text_at(s,14,'已匹配回复中更常出现感谢词项，与更多留言得到回复是两件事；两组作者和情境也可能不同。',16.5)
    note(23,'直接配对：已采集回复覆盖与感谢词项',45,'以6,609条外来根评论为单位，从留言发出后七天内匹配已采集的帖主直接回复，只取最早一条。左图分母是各组全部根评论：鼓励或赞许词项命中组的覆盖为43.5%，未命中组为56.3%。右图分母只剩已经匹配到回复的记录，最早回复的感谢词项命中为26.7%和6.4%。所以，已回复记录中更常出现感谢词项，不代表更多留言获得回复。未匹配也不等于实际没有回复，因为这里只观察已采集记录。','RQ3')

    s=slides[24]
    text_at(s,3,'建边：根评论者→帖主是归属规则；明确回复者→已记录被回复用户；同向多次事件累加权重。',9)
    text_at(s,7,'排除84次自我互动后，11,511次事件形成有向边；根评论按帖子归属连向帖主。图中省略箭头，金色为样本帖作者。',16)
    note(24,'评论网络的建边规则与连通范围',30,'网络中根评论者连向帖主，这是根据帖子归属设定的建边规则；只有明确回复使用实际记录的被回复账号。同向多次事件累加权重，并排除自我互动。忽略方向后，94.4%的账号在最大连通部分，但有向密度只有0.0473%。广泛间接相连与稀疏直接连接可以同时出现；不能把共同面向帖主归属留言当作用户彼此对话。','RQ3')

    s=slides[25]
    text_at(s,7,'4,902次明确回复中，4,361次由帖主发给其他用户；其他用户彼此回复97次，占2.0%。',18)
    text_at(s,8,'已记录的直接回复方向主要围绕帖主；这描述回复事件构成，不等于所有留言的被回概率。',18)
    note(25,'明确回复方向主要围绕帖主',25,'单看4,902次非自我明确回复，89%由帖主发给其他用户，用户彼此回复只有97次、约2%。它描述的是已经记录的回复事件方向；89%的分母不是全部留言，所以不能当作被回复概率。','RQ3')

    s=slides[26]
    text_at(s,6,'根评论按归属连向帖主，帖主再明确回复同一用户，就会形成双向连接。\n去掉归属建边的根评论后互惠率降低，表明这一规则影响网络统计量。',17)
    note(26,'互惠率依赖建边规则和观察窗口',30,'全部互动有49.6%的有向边存在反向边，只看明确回复则降到29.9%。一部分双向连接来自根评论归属建边加上帖主回话，因此互惠率依赖建边规则。各帖发布后七天内的互惠率是74.1%，但账号和边的构成也变了，不能说同一批关系后来变淡。这里的七天从发帖起算，与上一页从留言起算的直接回复配对窗口不同。','RQ3')

    note(27,'互动次数与不同发送者人数',30,'U1528收到1,378次事件，来自53人；U0948收到1,275次，却来自1,091人。相近的次数可以由很不同的参与范围构成。U0112的180次仅来自四人。所以判断评论互动的集中程度，事件次数和不同发送者人数应该一起看，不能直接把次数当作广泛参与。','RQ3')

    # Final answer on one slide: no semantic content-category conclusion.
    s=slides[28]
    frame(s,'三个问题的回答：分布、关联与连接','本轮结论','结论限于课程样本和已采集记录；观察性关联不作因果或增赞承诺。',dark=True)
    rows=[('RQ1','正文非空覆盖56.8%，媒体均值不同，点赞有长尾。','tag与正文是不同记录维度，不能互相替代。'),('RQ2','固定字面特征的条件关联对正文范围敏感。','三口径联合p为0.130／0.067／0.040；不按阈值追认主模型。'),('RQ3','已记录回复主要围绕帖主，次数与参与人数不同。','89%是明确回复的事件构成；互惠率依赖建边与窗口。')]
    for i,(q,head,body)in enumerate(rows):
        y=1.94+i*1.52
        new_text(s,q,.83,y,1.35,.45,24,'BDD3C8',True)
        new_text(s,head,2.40,y,10.02,.52,22,'white',True)
        new_text(s,body,2.42,y+.68,10.00,.52,17,'DFEAE3')
    note(28,'三个问题的回答：分布、关联与连接',30,'三个问题各有清楚的回答。RQ1说明正文覆盖、媒体差异和点赞长尾；RQ2说明固定字面特征与点赞的条件关联对正文范围敏感，不能按p值选择唯一主模型；RQ3说明已记录明确回复主要围绕帖主，互动次数和参与人数要一起看。全篇没有把帖子强制分成真实内容类别，也没有据词项推断人格、情绪或社会支持。')

    s=slides[29]
    text_at(s,3,'后续优先补齐记录与统一观察窗口；语义分类若要转为正式研究，需另行独立人工验证。',9)
    cells_at(s,5,[['限制','对本轮结论的影响','相应改进'],['100位作者，抽样机制不明','分布和回复结构不能直接推广到全Keep','扩大并说明抽样框与作者覆盖'],['正文和评论覆盖不全','正文口径不同；未采到不等于未发生','补齐正文、媒体和直接回复记录'],['曝光与统一采集时点缺失','固定效应仍不能识别每帖措辞的因果作用','统一观察窗口，记录实际曝光'],['未进行人工语义复核','词项只作字面测量；候选分类仅作探索附录','本轮交付无需补人审表；未来另行验证']],14.5)
    text_at(s,6,'当前可交付的证据是字面分布、条件关联与记录连接；计算核查不能称作语义效度验证。',18)
    note(29,'共同局限与对应改进',35,'最后说明共同边界。样本只覆盖100位作者且抽样机制不明，正文和评论记录也不完整。缺少每帖曝光和统一采集时点，固定效应不能把关联变成因果。本轮未进行人工语义复核，所以正式结果只使用字面测量和已记录连接。当前交付不依赖补填人工编码表；如果未来要回答真实内容类别或表达行为问题，需要另行开展独立人工验证。')

    s=slides[30]
    text_at(s,6,'问题的提出\n数据清洗\nRQ1：样本覆盖与点赞的分布',20)
    text_at(s,8,'RQ2：字面特征与点赞的关联\nRQ3：评论线索与连接结构',20)
    note(30,'成员分工 / Credit',8,'陈霖负责问题提出、清洗和RQ1，董依心负责RQ2与RQ3。谢谢大家。')

    # Two compact exploratory slides, excluded from the main speaking budget.
    s=slides[5]
    text_at(s,0,'探索附录 A  旧NMF成分与结构诊断',13)
    text_at(s,1,'探索材料 · 不计入主讲',11)
    text_at(s,2,'旧NMF仅描述模型成分，不给出真实内容占比',27)
    text_at(s,3,'旧5成分、固定权重及数值份额保留供核对；名称未经人工语义复核。',9)
    text_at(s,7,'2,470帖仅占非空正文45.6%',16)
    text_at(s,8,'成分0—4沿用冻结模型ID；\n最高权重仅用于这张描述图。',16)
    text_at(s,9,'成分2和4的主导份额合计88.5%，不等于88.5%的帖子属于两个真实类别。静蹲旧成分85帖中78帖来自同一作者；删重后该成分不再单列。',17)
    text_at(s,10,'随机种子复现、改汇总权重或结构诊断都不能替代人工语义效度验证。',16)
    note(5,'探索附录A：旧NMF与结构诊断',0,'本页仅供答疑。图表保留旧NMF权重和份额，沿用冻结成分ID零至四。2,470帖只占非空正文45.6%；88.5%是成分2和4的主导份额合计，不是真实内容分类比例。旧静蹲成分85帖中78帖来自同一作者，删重后不再单列。它们说明模型结构依赖样本和重复记录，不证明语义正确。',appendix=True)
    # Chart source categories are now component indices; replace_data updates cache+xlsx together.
    from pptx.chart.data import CategoryChartData
    chart=next(sh.chart for sh in s.shapes if sh.has_chart)
    data=CategoryChartData();data.categories=['成分2','成分4','成分3','成分0','成分1']
    for ser in chart.series:data.add_series(ser.name,list(ser.values))
    chart.replace_data(data)

    s=slides[19]
    text_at(s,0,'探索附录 B  旧成分关联与候选分类',13)
    text_at(s,1,'探索材料 · 不计入主讲',11)
    text_at(s,2,'旧成分回归与候选分类均不进入主结论',27)
    text_at(s,3,'旧回归限于2,470帖、86位作者；连续成分权重不等于真实主题或表达行为效应。',9)
    text_at(s,6,'旧成分模型：既有M3线性项 + Σ θ_k w_k（省成分2，连续权重和为1）',18)
    t=s.shapes[7].table
    # Old rows map to source components in their fixed numerical order.
    for ri,label in enumerate(['相对成分2的连续权重','成分0（旧静蹲）','成分1（旧骑行）','成分3（旧跑步）','成分4（旧生活）']):set_text(t.cell(ri,0),label,14)
    text_at(s,8,'旧四项成分联合p=0.166；本表只保留数值核对，不作真实主题的反馈排序。',17)
    text_at(s,9,'17内容叶／15表达行为仍为候选框架；同基座AI编码预检验不是独立人工复核。\n未将候选类别替换进入本轮模型；识别器原型也不作为正式测量。',16)
    text_at(s,10,'本轮人工语义复核0人；AI间及模型相对AI的分歧均不能称为人工准确率。',15)
    s.shapes[10].top=Inches(6.72);s.shapes[10].height=Inches(.30)
    note(19,'探索附录B：成分回归与候选分类',0,'本页仅供答疑。原连续成分回归可以复算，联合p为0.166，但不等于真实主题效应。17个内容叶、15个表达行为和AI预检验均保留为候选材料。人工复核人数为零，AI间一致或模型相对AI的比较不能称为人工准确率。本轮没有把候选类别代入正式模型。',appendix=True)

    # Structure first: keep 26 main slides and 2 explicitly exploratory appendices.
    main_order=[1,2,3,4,8,6,9,10,11,12,13,14,15,16,17,18,21,22,23,24,25,26,27,29,28,30]
    appendix_order=[5,19]
    order=main_order+appendix_order
    by_slide={id(pres.part.related_slide(rel.rId)):rel for rel in pres.slides._sldIdLst}
    kept={id(slides[i])for i in order}
    for old,slide in slides.items():
        if id(slide)not in kept:pres.part.drop_rel(by_slide[id(slide)].rId)
    for el in list(pres.slides._sldIdLst):pres.slides._sldIdLst.remove(el)
    for i in order:pres.slides._sldIdLst.append(by_slide[id(slides[i])])

    total=len(order);final=[];elapsed=0
    for page,old in enumerate(order,1):
        s=slides[old];m=meta[old]
        m.update(page=page,source_teacher_page=old,main_lecture=old in main_order,appendix=old in appendix_order)
        m['start_seconds']=elapsed if m['main_lecture']else None
        if m['main_lecture']:elapsed+=m['seconds']
        m['end_seconds']=elapsed if m['main_lecture']else None
        for sh in s.shapes:
            if sh.has_text_frame:
                if re.fullmatch(r'\d{2} / \d{2}',sh.text):set_text(sh,f'{page:02d} / {total:02d}')
                if sh.text.startswith('RQ2  文字'):
                    set_text(sh,'RQ2  字面特征与点赞的条件关联')
        if old==12:
            m['foot']='全样本9,532帖；未命中组含缺正文设0者；原始媒体构成未作条件调整。'
        s.notes_slide.notes_text_frame.text=(
            f'正式修订版｜第{page}/{total}页｜'+('探索附录，不计主讲'if m['appendix']else f'讲述预算{m["seconds"]}秒，非实测')+
            f'\n\n{m["speech"]}\n\n范围：本轮未进行人工语义复核；当前交付不依赖填人工编码A／B。'+
            f'\n\n来源：{m["source"]}')
        m['text']=[{'text':sh.text,'x':round(sh.left/914400,4),'y':round(sh.top/914400,4),'w':round(sh.width/914400,4),'h':round(sh.height/914400,4)}for sh in s.shapes if sh.has_text_frame and sh.text]
        m['tables']=[[[c.text for c in row.cells]for row in sh.table.rows]for sh in s.shapes if sh.has_table]
        m['native_chart_count']=sum(sh.has_chart for sh in s.shapes)
        m['foot']=next((sh.text for sh in s.shapes if sh.has_text_frame and abs(sh.top/914400-7.09)<.005),m.get('foot',''))
        # Do not carry stale source chart metadata/category labels into new QA.
        m.pop('charts',None)
        final.append(m)

    p14='http://schemas.microsoft.com/office/powerpoint/2010/main'
    section_list=pres._element.find(f'.//{{{p14}}}sectionLst')
    if section_list is not None:
        for node in list(section_list):section_list.remove(node)
        current=None
        for old,sid in zip(order,list(pres.slides._sldIdLst)):
            name='探索性附录（不计主讲）'if old in appendix_order else meta[old]['chapterName']
            if name!=current:
                section=etree.SubElement(section_list,f'{{{p14}}}section',name=name,id='{'+str(uuid.uuid5(uuid.NAMESPACE_URL,STEM+name+str(old)))+'}')
                listing=etree.SubElement(section,f'{{{p14}}}sldIdLst');current=name
            etree.SubElement(listing,f'{{{p14}}}sldId',id=str(sid.id))

    pres.core_properties.title=SCOPE['title']+'｜正式修订版'
    pres.core_properties.subject=SCOPE['subtitle']
    pres.core_properties.comments='本轮未进行人工语义复核；主分析不依赖内容类别。'
    out=ROOT/(STEM+'.pptx');pres.save(out)
    patched=patch_package(out)
    timing={'slides':total,'main_lecture_slides':len(main_order),'appendix_slides':len(appendix_order),
            'speech_seconds':elapsed,'transition_seconds':35,'main_target_seconds':elapsed+35,
            'appendix_included_in_budget':False,'measured_by_rehearsal':False,
            'note':'仅为12—15分钟范围内的讲述预算，非排练或实测；附录仅供答疑，不计主讲。'}
    clock=lambda n:f'{n//60}:{n%60:02d}'
    lines=[SCOPE['title']+'｜正式修订版逐页讲稿',
           f'\n{len(main_order)}页主讲＋{len(appendix_order)}页探索附录。讲述预算{clock(elapsed)}，转场35秒，目标{clock(elapsed+35)}；预算非实测。',
           '附录不计主讲，只在答疑时使用。本轮未进行人工语义复核；当前交付不依赖填人工编码A／B。',
           '保持既有词项、匹配、样本、控制项及估计值；三种正文口径并列，不因p=0.040追认唯一主模型。\n']
    for m in final:
        label='探索附录，不计主讲'if m['appendix']else f'{clock(m["start_seconds"])}—{clock(m["end_seconds"])}；预算{m["seconds"]}秒，非实测'
        lines.append(f'第{m["page"]}页｜{m["title"]}\n{label}\n\n{m["speech"]}\n\n来源：{m["source"]}\n')
    (ROOT/(STEM+'_逐页讲稿.txt')).write_text('\n'.join(lines),encoding='utf-8')
    (QA/'slides_manifest.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n')
    (QA/'timing_plan.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2)+'\n')
    (QA/'page_mapping.json').write_text(json.dumps([{'source_teacher_page':old,'new_page':page,'appendix':old in appendix_order}for page,old in enumerate(order,1)],ensure_ascii=False,indent=2)+'\n')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_sha
    result={'pptx':str(out),'source':str(SOURCE),'source_sha256':source_sha,'source_unchanged':True,
            'pptx_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'slides':total,
            'main_lecture_slides':len(main_order),'appendix_slides':len(appendix_order),
            'native_charts':sum(m['native_chart_count']for m in final),'timing':timing,
            'label_package_changes':patched,'models_reestimated':False,
            'human_semantic_review_conducted':False,'requires_human_annotation_to_deliver':False}
    (QA/'build_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
