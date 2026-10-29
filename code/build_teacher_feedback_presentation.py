"""Revise the accepted deck using checked teacher-feedback evidence.

Old slides/charts are retained, with supported interpretation repairs; seven
new evidence slides are inserted. No unvalidated replacement labels are fitted.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import uuid
import zipfile

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_DATA_LABEL_POSITION, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'validation/slides_teacher_feedback'
SOURCE = ROOT / 'Keep社区内容表达与互动反馈_12分钟合并版.pptx'
STEM = 'Keep社区内容表达与互动反馈_老师意见修订版'
FONT = 'Arial Unicode MS'
C = {'ink':'20332F','green':'245C4F','deep':'173F36','muted':'65756F','light':'EDF4F0','pale':'F6F8F7','line':'DFE6E2','orange':'B97339','white':'FFFFFF'}
CHAPTERS = ['研究背景、意义与研究问题','数据来源、清洗与分析方法','数据覆盖与描述统计','文字表达与点赞的关联','探索性文本成分与点赞','评论的主要内容','评论区的网络结构','研究结论与局限']


def load(name):
    return json.loads((ROOT/'results'/name).read_text())


def rgb(color):
    return RGBColor.from_string(color)


def new_text(slide, value, x, y, w, h, size=18, color='ink', bold=False, align=PP_ALIGN.LEFT):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h))
    tf=shape.text_frame
    tf.word_wrap=True
    tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
    tf.vertical_anchor=MSO_ANCHOR.TOP
    for i,line in enumerate(str(value).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.alignment=align
        p.space_before=p.space_after=Pt(0)
        p.line_spacing=1.15
        run=p.add_run();run.text=line
        run.font.name=FONT;run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=rgb(C.get(color,color))
    return shape


def rect(slide,x,y,w,h,color):
    shape=slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    shape.fill.solid();shape.fill.fore_color.rgb=rgb(C.get(color,color));shape.line.fill.background()
    return shape


def set_text(shape,value,size=None):
    tf=shape.text_frame
    old_run=next((r for p in tf.paragraphs for r in p.runs),None)
    props=deepcopy(old_run._r.rPr) if old_run is not None and old_run._r.rPr is not None else None
    first_p=deepcopy(tf.paragraphs[0]._p.pPr) if tf.paragraphs[0]._p.pPr is not None else None
    tf.text=str(value)
    for p in tf.paragraphs:
        if first_p is not None:
            if p._p.pPr is not None:p._p.remove(p._p.pPr)
            p._p.insert(0,deepcopy(first_p))
        for run in p.runs:
            if props is not None:
                if run._r.rPr is not None:run._r.remove(run._r.rPr)
                run._r.insert(0,deepcopy(props))
            if size is not None:run.font.size=Pt(size)


def change(slide, old, new, size=None):
    matches=[sh for sh in slide.shapes if sh.has_text_frame and sh.text==old]
    if len(matches)!=1:raise ValueError(f'Expected one shape: {old!r}; got {len(matches)}')
    set_text(matches[0],new,size)


def table(slide,headers,rows,x,y,w,widths,font=15,row_heights=None):
    height=sum(row_heights) if row_heights else .57*(len(rows)+1)
    shape=slide.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(w),Inches(height))
    t=shape.table
    for col,width in zip(t.columns,widths):col.width=Inches(width)
    for i,vals in enumerate([headers]+rows):
        if row_heights:t.rows[i].height=Inches(row_heights[i])
        for j,value in enumerate(vals):
            cell=t.cell(i,j);cell.text=str(value)
            cell.margin_left=cell.margin_right=Inches(.10)
            cell.margin_top=cell.margin_bottom=Inches(.07)
            cell.vertical_anchor=MSO_ANCHOR.MIDDLE
            cell.fill.solid();cell.fill.fore_color.rgb=rgb(C['light'] if i==0 else C['white'] if i%2 else C['pale'])
            for p in cell.text_frame.paragraphs:
                p.space_before=p.space_after=Pt(0)
                p.line_spacing=1.05
                for r in p.runs:
                    r.font.name=FONT;r.font.size=Pt(font);r.font.bold=i==0;r.font.color.rgb=rgb(C['green'] if i==0 else C['ink'])
            # Quiet white cell borders, instead of the source table style's blue.
            ns='http://schemas.openxmlformats.org/drawingml/2006/main'
            for side in ['lnL','lnR','lnT','lnB']:
                el=cell._tc.get_or_add_tcPr().find(f'{{{ns}}}{side}')
                if el is not None:cell._tc.get_or_add_tcPr().remove(el)
                el=etree.SubElement(cell._tc.get_or_add_tcPr(),f'{{{ns}}}{side}',w='6000')
                sf=etree.SubElement(el,f'{{{ns}}}solidFill');etree.SubElement(sf,f'{{{ns}}}srgbClr',val='FFFFFF')
    return shape


def bar(slide, labels, values, x,y,w,h, maxval, number='0.0', labelsize=12):
    data=CategoryChartData();data.categories=labels;data.add_series('复核结果',values)
    chart=slide.shapes.add_chart(XL_CHART_TYPE.BAR_CLUSTERED,Inches(x),Inches(y),Inches(w),Inches(h),data).chart
    chart.has_legend=False;chart.has_title=False
    plot=chart.plots[0];plot.gap_width=75;plot.has_data_labels=True
    plot.data_labels.position=XL_DATA_LABEL_POSITION.OUTSIDE_END
    plot.data_labels.number_format=number
    plot.data_labels.font.name=FONT;plot.data_labels.font.size=Pt(12);plot.data_labels.font.color.rgb=rgb(C['ink'])
    series=plot.series[0];series.format.fill.solid();series.format.fill.fore_color.rgb=rgb(C['green']);series.format.line.fill.background()
    chart.category_axis.reverse_order=True
    chart.category_axis.tick_labels.font.name=FONT;chart.category_axis.tick_labels.font.size=Pt(labelsize)
    chart.category_axis.tick_labels.font.color.rgb=rgb(C['ink'])
    chart.value_axis.minimum_scale=0;chart.value_axis.maximum_scale=maxval
    chart.value_axis.tick_labels.font.name=FONT;chart.value_axis.tick_labels.font.size=Pt(10)
    chart.value_axis.tick_labels.font.color.rgb=rgb(C['muted'])
    chart.value_axis.has_major_gridlines=True
    chart.value_axis.major_gridlines.format.line.color.rgb=rgb('E7ECE9')
    chart.value_axis.format.line.fill.background();chart.category_axis.format.line.fill.background()
    return chart


def main():
    QA.mkdir(parents=True,exist_ok=True)
    pres=Presentation(SOURCE)
    old_slides=list(pres.slides)
    old_meta=json.loads((ROOT/'validation/slides_12min_dyx/slides_manifest.json').read_text())
    d=load('teacher_feedback_dictionary.json');a=load('teacher_author_tags_summary.json')
    topics=load('teacher_topic_summary.json');body=load('teacher_complete_body_model.json')
    coverage=load('teacher_label_coverage_summary.json');ta=load('teacher_topic_author_support.json')
    am={x['model']:x for x in a['model_fit']}
    ac={(x['model'],x['term']):x for x in a['coefficients']}
    manifests={id(s):deepcopy(m) for s,m in zip(old_slides,old_meta)}
    new_specs={}
    total=30

    def fresh(key,title,chapter,foot,source,seconds,speech,focus):
        s=pres.slides.add_slide(pres.slide_layouts[0])
        s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(C['white'])
        question='RQ1' if chapter==3 else 'RQ2'
        headings={'RQ1':'内容与点赞的分布','RQ2':'文字、成分与点赞的关联'}
        new_text(s,f'{question}  {headings[question]}',.58,.30,8.8,.30,13,'green',True)
        new_text(s,CHAPTERS[chapter-1],9.12,.30,3.62,.30,11,'muted',align=PP_ALIGN.RIGHT)
        new_text(s,title,.58,.88,12.15,.72,27,'ink',True)
        new_text(s,foot,.58,7.09,11.36,.22,9,'muted')
        new_text(s,'00 / 30',11.99,7.07,.77,.25,10,'muted',align=PP_ALIGN.RIGHT)
        meta={'oldPage':None,'kind':'new_evidence','key':key,'title':title,'chapter':chapter,'chapterName':CHAPTERS[chapter-1],
              'subsection':CHAPTERS[chapter-1],'question':question,'rq':f'回答 {question} · 新增复核',
              'source':source,'foot':foot,'appendix':False,'speech':speech,'seconds':seconds,'focus':focus,'new_analysis':True}
        manifests[id(s)]=meta;new_specs[key]=s
        return s

    # Repair existing interpretations without changing accepted numeric charts.
    new_text(old_slides[0],'老师意见修订版 · 正文口径与测量效度复核',.80,5.18,11.5,.35,16,'BDD3C8')
    manifests[id(old_slides[0])].update(seconds=15,speech='这次保留内容、点赞和评论三个研究问题，重点补充老师提出的变量分类、主题重叠、作者固定效应与话题标签核查，并修正文中超出测量支持的解释。',focus='说明这是落实方法复核后的新版本。')
    change(old_slides[1],'RQ1  样本主要呈现什么内容，点赞怎样分布？','RQ1  样本覆盖、媒体与点赞怎样分布？',17)
    change(old_slides[1],'RQ2  文字表达与主题是否与点赞有关？','RQ2  可观测文字线索与成分是否与点赞相关？',16)
    change(old_slides[1],'自律、积极表达或提问可能对应较高点赞；\n调整作者与情境后，这些差异可能变化。','指定字面线索可能对应点赞差异；\n需检查测量、正文覆盖与作者内比较。',16)
    manifests[id(old_slides[1])]['speech']='我们保留三个问题：先描述样本覆盖、媒体和点赞，再看实际可观测文字线索与探索性成分的条件关联，最后描述评论回应与参与。内容标签、原始话题和模型成分不是同一对象，本次会把它们分开。'
    change(old_slides[2],'5,414帖清理后有非空正文；主题分析另筛选2,470帖、86位作者。\n正文覆盖随媒体和作者而不同，主题比例不能当作全部9,532帖的内容比例。','原始正文可见5,548帖；清理后非空5,414帖；NMF权重另有2,470帖、86位作者。\n三种口径回答不同范围的问题；缺失标记不能恢复未记录的文字。',15)
    change(old_slides[4],'帖子正文主题主要包括运动和生活','NMF成分占比：不等于真实内容分类',27)
    change(old_slides[4],'TF-IDF + 非负矩阵分解（NMF），固定提取5类主题；命名不参考点赞。','沿用原成分名称便于核对，尚未经语义效度验证；占比是主导成分份额。')
    change(old_slides[4],'用非负矩阵分解（NMF）提取主题','TF-IDF + NMF，固定提取5个成分',14)
    change(old_slides[4],'前两类合计88.5%。这批有效正文不仅讨论如何训练，也经常写感受、生活和问候，不能把健身社区里的文字都当成运动成绩记录。','前两个主导成分合计88.5%，只是旧模型的数值分配；不能据此认定88.5%的正文在语义上确实属于这两类。',18)
    change(old_slides[4],'占比按每帖权重最大的主题归类。同一作者可写多个主题，内容量大也可能是某些人写得多。','每帖取最高权重，仅用于这张描述图；原回归使用连续权重，同帖可有多个成分。',17)
    manifests[id(old_slides[4])].update(title='NMF成分占比：不等于真实内容分类',seconds=35,speech='旧模型将2,470条正文分解成五个成分，训练交流和生活问候只是沿用的解释名称。52.7%和35.8%是最高权重成分的份额，不能视为经过验证的真实内容比例。连续权重本来允许同一帖含多个成分；下一页进一步检查模型覆盖和语义错配。',focus='将模型成分与真实内容分类分开。')
    change(old_slides[5],'常见主题，也可能来自少数人的高频记录','成分份额也受到高产作者与重复记录影响',27)
    change(old_slides[5],'两组沿用同一主题分类；作者等权先计算每人的主题比例，再对86位作者平均。','两组沿用冻结成分；作者等权描述只改变汇总权重，不改变原NMF拟合。')
    change(old_slides[5],'85条主导文档中，78条来自同一作者。按帖看是在统计这种记录出现了多少次；作者等权后，才减少了高产作者的重复贡献。','85条主导文档中，78条来自同一作者。作者等权汇总减少了这类重复贡献，但没有修复拟合阶段的模板影响。',18)
    change(old_slides[5],'训练52.7% → 52.6%，生活35.8% → 38.2%。两条主要内容线仍在，变化集中在部分小主题。','原训练成分52.7% → 52.6%，生活成分35.8% → 38.2%。这些仍是成分份额，不能代替语义验证。',17.5)
    change(old_slides[5],'训练和生活是两条主要内容线；部分小主题的份额，则会被少数作者的持续记录放大。','作者等权调整的是成分描述份额，不修复拟合过程及名称的语义问题。',17)
    manifests[id(old_slides[5])].update(title='成分份额也受到高产作者与重复记录影响',seconds=30,speech='原静蹲成分的85帖里78帖来自一人，骑行85帖中58帖也来自同一作者。作者等权后的静蹲份额从3.4%降到0.6%，说明篇幅受高产作者影响。但旧做法先拟合再改汇总权重，没有重做NMF，因此不能据此证明分类结构已经稳健。',focus='区分拟合阶段与汇总阶段的作者影响。')
    change(old_slides[6],'范围：9,532帖；主题比例仅代表2,470条有效正文、86位作者。','范围：9,532帖；成分描述限于2,470帖；语义分类和覆盖不能由成分份额保证。')
    change(old_slides[6],'正文同时包含训练交流和生活分享，篇幅也受作者影响。','正文内容还不能用五个旧名称完整概括。',24)
    change(old_slides[6],'训练交流52.7%、生活问候35.8%，作者等权后仍是两条主线。静蹲却由3.4%降至0.6%，其中85帖有78帖来自一人：这种记录出现多，不等于很多作者都在写。','2,470帖进入NMF，只占非空正文45.6%。语义抽查和删重诊断提示错配与结构依赖；旧名称只能作为探索性成分索引。',19)
    change(old_slides[6],'RQ2接着问：把媒体、作者与日期一起纳入比较后，文字或主题与点赞还有多大关联？','RQ2接着问：在可观测正文范围内，指定文字线索与点赞的条件关联有多稳？',17)
    manifests[id(old_slides[6])].update(seconds=22,speech='RQ1可以确认媒体点赞不同、整体有长尾；但内容分布必须收窄解释。只有45.6%的非空正文进入NMF，成分名称有错配，份额还受重复与高产作者影响。下面的RQ2因此比较指定文字线索和探索性成分，不把它们当作全部内容。')
    change(old_slides[7],'除长度外，命中记1；一帖可同时命中多个词类。','三类词汇规则＋问号；除长度外，命中记1，可同时命中。',14.5)
    change(old_slides[9],'主分析为OLS；N=9,532、100位作者，标准误按作者聚类，五项核心系数采用BH校正。','历史M3：N=9,532、100位作者；作者聚类推断，五项核心系数BH校正；正文口径另行对照。')
    change(old_slides[9],'主模型 M3：ln(1 + 点赞数) = β′X + γ′C + α作者 + δ日期 + ε','历史基线 M3：ln(1 + 点赞数) = β′X + γ′C + α作者 + δ日期 + ε',22)
    change(old_slides[9],'X：文本长度（对数）、自律、社交、积极、问号。C：正文可用、话题、表情数、课程分享，以及媒体、业务类型、时段。','X：文本长度（对数）、自律、社交、积极、问号。C：原始正文可见、有无话题标签、表情、课程分享、媒体、业务类型与时段。',15)
    for shape in old_slides[9].shapes:
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    if cell.text=='M3 主模型':set_text(cell,'M3 历史基线',14.5)
    manifests[id(old_slides[9])]['speech']='保留M3作为历史基线，方程和原结果不变。作者固定效应利用同一作者内不同帖子的变化，日期效应调整公共发帖日差异。原模型已控制有无话题标签。缺失正文设零加标记不能恢复未记录的文字，所以后面并列比较实际可观测正文的两个范围，不按显著性挑模型。'
    change(old_slides[10],'M3没有保留原始用词优势','历史M3：全样本的指定字面线索关联',27)
    change(old_slides[10],'积极表达单项区间不跨0；\n但BH校正后，五项特征\n均未达到5%标准。','在这个全样本M3中，\n五项BH q均未到5%；\n不能概括其他正文口径。',17.5)
    change(old_slides[10],'还要核查：负向方向是否依赖缺失正文、极端高赞帖或某一位作者？','下一页并列三种正文口径；全样本不显著不等于所有设定都不显著。',12.5)
    manifests[id(old_slides[10])].update(title='历史M3：全样本的指定字面线索关联',speech='M3的原结果可以复算：积极表达系数负0.086、原始p为0.016，五项BH校正后q为0.079，联合p为0.130。这只对应9,532帖和原缺失处理。它不能推出积极用词降低点赞，也不能概括不同正文覆盖人群。下一页比较三种正文口径。')
    change(old_slides[12],'主题权重能否补充用词以外的点赞关联？','原NMF成分与点赞：仅作探索性核查',27)
    change(old_slides[12],'同一子样本N=2,470、86位作者；按作者聚类。回归使用连续主题权重，不是主导主题虚拟变量。','冻结成分子样本N=2,470、86位作者；作者聚类。连续权重回归不等于真实语义主题效应。')
    change(old_slides[12],'主题模型：M3原有线性项 + Σ θₖwₖ（省去“运动与训练交流”权重作为参照）','旧成分模型：M3原有线性项 + Σ θ_k w_k（五项和为1，省去一项权重作参照）',18)
    change(old_slides[12],'生活问候权重相对训练交流增加10个百分点时，“1+点赞”的条件几何均值点估计约低1.4%。','沿用旧命名，生活成分相对训练成分权重增加10个百分点，对应“1+点赞”点估计约低1.4%。',16)
    change(old_slides[12],'但其原始p = 0.035、BH q = 0.107；四项主题联合 p = 0.166，尚不能把点估计当成稳定的主题反馈排序。','原始p = 0.035、BH q = 0.107；成分联合p = 0.166。名称未经语义验证，不能据此做真实主题反馈排序。',16)
    for shape in old_slides[12].shapes:
        if shape.has_table and shape.table.cell(0,0).text=='相对训练交流的主题权重':
            set_text(shape.table.cell(0,0),'相对参照成分的权重')
    manifests[id(old_slides[12])].update(title='原NMF成分与点赞：仅作探索性核查',seconds=35,speech='原来的输入是连续权重，不是互斥虚拟变量。五项权重和为一，所以省去训练成分作参照；这是组成约束，不表示语义互斥。旧系数与联合p为0.166可以复算，但名称未经语义验证，也没有纳入主题估计不确定性，只能作成分数值关联的探索性核查。',focus='保留原计算，收窄语义解释。')
    change(old_slides[13],'RQ2的回答：用词和主题与点赞的关联有多稳','RQ2的回答：证据对正文范围和测量方式敏感',27)
    change(old_slides[13],'原始用词差异同时带着媒体与作者差异。','局部字面线索与点赞的证据依赖比较范围。',24)
    change(old_slides[13],'积极表达命中组的图片/视频占比94.9%，未命中组69.1%。M3调整后积极表达系数为−0.086、BH q=0.079；五项文字线索仅新增0.065个百分点R²，联合p=0.130。','历史全样本联合p=0.130；原始正文可见样本p=0.067；清理后非空正文p=0.040，长度与积极表达的模型内BH q约0.048。不能笼统称为“各种设定都不显著”。',18)
    change(old_slides[13],'换样本后的方向较一致，主题也没有补出稳定优势。','成分编码能复现，不代表内容分类已得到验证。',24)
    change(old_slides[13],'积极表达在多种处理下均为负，但PPML区间跨0；主题权重联合p=0.166。现有记录对这些用词和主题的额外点赞关联，仍缺少足够稳定的证据；这不等于证明文字内容普遍无效。','少帖作者与标签身份对照未改变全样本的主要判断，但不能修复缺失选择或语义测量。主题多标签仍继承旧成分问题，现阶段不作真实内容类型的稳定点赞排序。',18)
    manifests[id(old_slides[13])].update(title='RQ2的回答：证据对正文范围和测量方式敏感',seconds=35,speech='RQ2的结论需要修订。正文口径从全样本到非空正文，联合p由0.130变为0.040，不能笼统说全部设定都不显著；也不能因为这个模型更显著就换成确认性答案。字面规则只测局部表达，旧成分名称尚未验证，作者与tag检查不能修复这些问题。因此现在报告的是有限范围的观察性关联，暂不做真实内容主题的稳定排序。',focus='明确改正原结论的范围，不把新显著结果包装成因果。')
    manifests[id(old_slides[21])]['speech']='本次补充显示，样本覆盖、可观测文字和主题标签的语义都限制了判断。评论网络仍沿用原结果，本轮未重审其全部计算。下一步先由两名同学独立编码并验证内容边界，再冻结分类和重跑正式主题比较；曝光和统一观察窗口仍需额外数据。'
    for sh in old_slides[21].shapes:
        if sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    if cell.text=='词典与主题只是内容的部分表征':set_text(cell,'字面规则与成分名称尚未验证')
                    elif cell.text=='不能据用词判断情绪；主题区间未计入模型估计不确定性':set_text(cell,'不能据用词判定情绪；正文口径和标签边界限制结论')
                    elif cell.text=='语义复核、重复抽样与独立验证':set_text(cell,'独立人工编码、未见样本验证，再冻结分类')

    # New 1: coverage + semantic and fitting diagnostics.
    s=fresh('topic_coverage','分类覆盖与语义：五成分不能当作完整分类',3,
            '60条已分配帖的等额分层单轮AI筛查，不是独立人工金标准；不能推算全样本错误率。',
            'teacher_label_coverage_summary.json；teacher_topic_structure_summary.json；label_review_annotations.json',45,
            '2,470帖只占全部帖子的25.9%、非空正文的45.6%。剩下的有短文本、有未覆盖领域，也有信息不足，不能全部视为没有主题。每个成分抽12帖，共60帖，单轮AI筛查发现12条不支持被分配名称、6条仅部分支持、2条不足判断；这不能推算总体错误率。删掉104条重复正文后，静蹲不再单列，并出现早餐咖啡等词群。类别数和作者等权拟合也会改变结构，说明高权重和跨随机种子复现不等于语义有效。',
            '用覆盖、具体反例与拟合依赖说明分类问题。')
    new_text(s,'全样本中的三种记录状态',.75,1.85,6.2,.40,20,'green',True)
    bar(s,['无非空正文','非空但未入模型','进入NMF权重表'],[4118,2944,2470],.60,2.30,6.65,3.35,5500,'#,##0',12)
    new_text(s,'2,470 / 5,414 = 45.6%',.77,5.95,6.2,.40,22,'green',True)
    new_text(s,'未入模 ≠ 没有主题；无正文 ≠ 无图像／视频内容。',.77,6.52,11.8,.34,15,'muted')
    new_text(s,'语义与结构都需要复核',7.55,1.85,5.1,.40,20,'green',True)
    table(s,['60条筛查','帖数'],[['支持原名称','40'],['仅部分支持','6'],['不支持所分名称','12'],['信息不足','2']],7.48,2.48,5.15,[3.65,1.50],14.5,[.43,.43,.43,.43,.43])
    new_text(s,'静蹲类中有山河感悟、口罩提醒；\n跑步类中有绘画、出行和学期感受。',7.55,4.95,5.1,.67,15.5)
    new_text(s,'删重后静蹲不再单列，出现含\n早餐、咖啡等词的新成分；新成分同样待验证。',7.55,5.85,5.1,.71,14.5,'orange',True)

    # New 2: the four dictionary features are operational, not exhaustive classes.
    s=fresh('dictionary_definition','三类词汇＋问号：为什么区分，分别观察什么',4,
            '研究者制定的字面规则，允许重叠；不是四类穷尽性主题，也不是独立心理因子。',
            'teacher_feedback_dictionary.json definitions；teacher_label_coverage_summary.json',40,
            '这四项应称为三类词汇加一类问号。自律词观察目标行动，社交词观察面向他人的称呼或邀请，积极词观察感受赞许的表面用词，问号只是可观察的标点。它们角度不同，允许同帖同时出现；加油、谢谢等仍有跨维度语义。5,414条非空正文中有3,891条完全未命中，所以这套规则只能检验指定字面线索，不能代表帖子全部内容或真实心理状态。',
            '分类理由与测量边界一起说明。')
    table(s,['变量','分类依据／例词','不能据此推出'],[
        ['自律／目标词','目标和行动进度：坚持、目标、打卡、完成','真实自律人格或训练完成情况'],
        ['社交／互助词','面向他人：大家、一起、谢谢、请教','已经发生互助或关系更强'],
        ['积极表达词','积极感受或赞许：开心、喜欢、棒、哈哈','已经准确判断情绪；未处理反讽否定'],
        ['问号','正文出现 ? 或 ？：句式标点线索','确实在求助；反问也会命中']
    ],.68,1.98,12,[2.05,5.05,4.90],16,[.60,.73,.73,.73,.73])
    rect(s,.72,6.02,11.9,.68,'light')
    new_text(s,'3,891 / 5,414 = 71.9% 的非空正文未命中任何规则；词典只覆盖局部表达。',.92,6.20,11.5,.36,18,'green',True)

    # New 3: complete-model VIF rather than only marginal correlations.
    s=fresh('dictionary_vif','语义允许交叉，但现有变量未显示明显数值共线性',4,
            'VIF基于完整M3全部设计列；低VIF不能证明语义独立或词典有效。',
            'teacher_feedback_dictionary.json；teacher_feedback_dictionary_pairs.csv；teacher_feedback_dictionary_vif.csv',30,
            '共现不等于共线性。完整M3有182列且满秩，四项VIF约1.11到1.75，最大两两相关0.119，作者内最大相关0.085。182帖同时命中两项以上。现有数值不支持因为高度重复就机械合并变量；但低VIF不能证明它们测准了理论概念，仍需人工语义验证。',
            '区分数值冗余与测量效度。')
    defs=d['definitions']
    bar(s,['自律／目标','社交／互助','积极表达','问号'],[x['vif_full_main_model']for x in defs],.68,2.05,7.05,3.82,2.2,'0.000',14)
    new_text(s,'完整M3：182 / 182 满秩',8.12,2.12,4.52,.6,23,'green',True)
    new_text(s,'最大两两相关 0.119\n作者内最大相关 0.085',8.12,3.25,4.52,.90,19)
    new_text(s,'182帖同时命中≥2项\n共现可以保留，语义仍要验证。',8.12,4.75,4.52,.94,18)
    new_text(s,'目前不需要仅因“特征可能类似”就合并；更重要的是准确解释每个规则测到了什么。',.75,6.35,11.9,.55,18,'green',True)

    # New 4: report all defined body populations and within-model BH.
    s=fresh('body_scope','正文口径会改变统计判断：需要并列报告',4,
            '作者聚类t／F推断；BH仅在各模型内校正五项，不覆盖全部探索性设定。',
            'teacher_complete_body_model.json；analyze_complete_body.py',45,
            '缺失正文填零加has_text，不等于实际观察到没有相应用词。has_text表示原始正文可见，5,548帖；清理后真正非空只有5,414帖。全样本联合p为0.130，原始正文可见为0.067，非空正文为0.040；非空正文中长度和积极表达的模型内BH q约0.048。这个结果接近阈值，而且是探索性重分析，不能按显著性挑模型。修订后的文字问题应限定实际可观察正文，原M3保留作历史对照。',
            '解释不同人群、缺失选择与探索性，不只报告更显著模型。')
    rows=[]
    for label,m in zip(['历史全样本＋标记','原始正文可见','清理后正文非空'],body['models']):
        term={z['term']:z for z in m['terms']}
        rows.append([label,f"{m['n']:,}",str(m['authors']),f"{m['joint_five_p']:.3f}",f"{term['log_length']['q_bh']:.3f}",f"{term['positive_expression']['q_bh']:.3f}"])
    table(s,['正文范围','N','作者','五项联合p','长度BH q','积极BH q'],rows,.68,2.04,12,[3.15,1.55,1.15,2.05,2.05,2.05],16,[.65,.75,.75,.75])
    new_text(s,'“全部设定都不显著”不成立；“选更显著模型作答案”也不成立。',.78,5.30,11.8,.55,21,'orange',True)
    new_text(s,'修订分析对象：实际可观测的非空正文；旧M3保留历史对照。\n筛选改变了比较人群，仍不能恢复缺失文字或建立用词因果作用。',.78,6.10,11.8,.67,17)

    # New 5: estimate support must be counted separately in each sample.
    s=fresh('author_support','少帖作者：主回归与主题子样本分别检查',4,
            '作者次数指本课程样本内次数；共同斜率依赖作者内变化，单帖作者不提供该变化。',
            'teacher_author_tags_summary.json；teacher_topic_author_support.json',40,
            '全样本100位作者中只有两位单帖，中位66帖；但主题子样本86位作者中有10位单帖，中位14帖，不能用前者为后者作保证。分别保留至少5帖和10帖作者，主模型联合p基本不变；成分模型p由0.166到0.179和0.266，作者支持缩小到48人。自律、社交、积极和问号分别在76、42、64、32位作者内变化，所以稀少线索并没有100位有效变化来源。',
            '按实际模型样本计数；不把不显著当作已解决所有支持问题。')
    new_text(s,'主样本：100人，2名单帖，中位66帖。\n主题子样本：86人，10名单帖，中位14帖。',.78,1.85,11.9,.90,20,'green',True)
    tmods={x['minimum_topic_posts_per_author']:x for x in ta['models']}
    row=[]
    for k,key,label in [(1,'baseline_body','原样本'),(5,'authors_ge5','至少5帖'),(10,'authors_ge10','至少10帖')]:
        row.append([label,f"{am[key]['n']:,} / {am[key]['authors']}",f"{am[key]['joint_five_p']:.3f}",f"{tmods[k]['n']:,} / {tmods[k]['authors']}",f"{tmods[k]['joint_topic_p']:.3f}"])
    table(s,['作者门槛','主模型 N／作者','五项联合p','成分模型 N／作者','成分联合p'],row,.68,3.10,12,[1.75,2.85,1.80,3.15,2.55],15.5,[.60,.65,.65,.65])
    new_text(s,'主样本作者内变化人数：自律76、社交42、积极64、问号32。',.78,6.02,11.9,.50,17.5)
    new_text(s,'少帖剔除未改变主判断；它不能解决缺失选择、曝光差异或标签语义问题。',.78,6.55,11.9,.36,17,'green',True)

    # New 6: metadata controls versus changing the measured text.
    s=fresh('tags','原模型已有标签有无控制；tag内容另作对照',4,
            '9个标签按≥30帖且≥5位作者选择，不参考点赞；拼接tag是改变测量范围的补充分析。',
            'teacher_author_tags_summary.json；teacher_author_tags_tag_recoding_changes.csv',40,
            '5,209帖有原始tag，共269种，其中1,517帖缺正文。原M3已经控制has_tag，不是完全没考虑标签。本轮在原正文编码上增加9个频繁跨作者tag身份控制，联合p为0.102；把tag拼入正文后重编码，p为0.173。但拼接使自律命中877增至3,342、问号125增至354，很多来自统一话题措辞。原始tag不是正文语义金标准，拼接结果不能冒充原正文的同一效应。',
            '明确控制变量与重新定义文本的差别。')
    new_text(s,'5,209帖有tag · 269种 · 1,517帖缺正文但有tag',.78,1.87,11.9,.43,22,'green',True)
    rows=[]
    for key,label,note in [('baseline_body','历史M3','正文编码＋has_tag'),('body_tag_identity_controls','加9个tag身份','正文范围不变'),('body_plus_tags_recoded','正文＋tag重编码','被测文字范围改变')]:
        v=ac[(key,'positive_expression')]
        rows.append([label,f"{am[key]['joint_five_p']:.3f}",f"{v['coef']:.3f} / {v['q_bh_five']:.3f}",note])
    table(s,['模型设定','五项联合p','积极β／BH q','所回答的问题'],rows,.68,2.68,12,[3.05,2.05,2.90,4.00],16,[.60,.65,.65,.65])
    new_text(s,'拼接后：自律命中 877 → 3,342；问号 125 → 354。',.78,5.78,11.9,.48,21,'orange',True)
    new_text(s,'平台话题措辞不等于正文表达；tag身份是元数据，不是人工分类的标准答案。',.78,6.47,11.9,.40,17)

    # New 7: continuous, argmax and multilabel are distinct parameterizations.
    s=fresh('topic_multilabel','连续权重、主导归类与0–1多标签是三种对象',5,
            '阈值属本轮提出的探索性诊断；未验证旧成分语义，不能将其当作分类已修复。',
            'teacher_topic_summary.json；teacher_topic_models.csv；teacher_topic_regression.csv',35,
            '原来五个主题权重在零到一之间，但不是二元变量；互斥只发生在主导成分描述图。现在保留冻结权重，额外设置权重至少0.20时标一，1,088帖同时有两个以上标记，五项比例加总145.9%。五个二元标记可以一起入模，设计矩阵171列满秩，不需机械省一类。三个阈值下联合p都没有明确证据，但这些便捷阈值和原名称都未经语义验证，技术可估计不代表分类有效。',
            '允许同帖多成分，避免把参数化诊断包装为新内容标签。')
    table(s,['对象','定义','互斥／回归含义'],[
        ['原连续权重','每帖5项权重，合计1','语义可共存；带截距省一权重避免完全共线'],
        ['主导成分描述','argmax，最高权重归一类','仅描述图互斥，不能当真实分类精度'],
        ['补充0–1多标签','w_k ≥ 0.20记1；允许多个1','5项全入模满秩171／171；不是单一基准类比较']
    ],.68,1.95,12,[2.25,3.55,6.20],15,[.55,.70,.70,.70])
    tm=topics['threshold_results']
    table(s,['阈值','多标记帖／2,470','联合p','最小BH q'],[[f"{x['threshold']:.2f}",f"{x['multi_topic_documents']:,}",f"{x['joint_topic_p']:.3f}",f"{x['min_bh_q']:.3f}"]for x in tm],.68,5.00,8.15,[1.1,3.00,2.00,2.05],14,[.40,.40,.40,.40])
    new_text(s,'0.20阈值：\n1,088帖有≥2标记\n比例合计145.9%',9.10,5.12,3.52,1.15,17,'green',True)

    # Reorder existing slide registrations; no slide files are duplicated.
    insertions={5:['topic_coverage'],8:['dictionary_definition','dictionary_vif'],11:['body_scope'],12:['author_support','tags'],13:['topic_multilabel']}
    order=[]
    for old_page,s in enumerate(old_slides,1):
        manifests[id(s)]['oldPage']=old_page
        order.append(s)
        order.extend(new_specs[key]for key in insertions.get(old_page,[]))
    assert len(order)==total
    ids={rel.rId:rel for rel in pres.slides._sldIdLst}
    slide_elements={id(pres.part.related_slide(rel.rId)):rel for rel in pres.slides._sldIdLst}
    # related_slide() produces the same cached slide objects as Presentation.slides.
    for element in list(pres.slides._sldIdLst):pres.slides._sldIdLst.remove(element)
    for s in order:pres.slides._sldIdLst.append(slide_elements[id(s)])
    old_to_new={manifests[id(s)]['oldPage']:i for i,s in enumerate(order,1)if manifests[id(s)]['oldPage']}
    # Fix one explicit page reference that existed in the accepted deck.
    change(old_slides[8],'变量已在第8页定义；图示为各组图片或视频帖占比，尚未调整作者与发布情境。',f"变量已在第{old_to_new[8]}页定义；图示为各组图片或视频帖占比，尚未调整作者与发布情境。")
    final=[]
    elapsed=0
    for page,s in enumerate(order,1):
        m=manifests[id(s)]
        m.update(page=page,old_page=m.get('oldPage'),new_analysis=bool(m.get('new_analysis')),chapterName=CHAPTERS[m['chapter']-1]if m['chapter'] else m.get('chapterName','封面'))
        for sh in s.shapes:
            if sh.has_text_frame and re.fullmatch(r'\d{2} / \d{2}',sh.text):set_text(sh,f'{page:02d} / {total}')
        if m.get('oldPage')==13:m['focus']='旧连续成分回归是可复算的数值关联，不是真实主题效应。'
        m['start_seconds']=elapsed;elapsed+=m['seconds'];m['end_seconds']=elapsed
        s.notes_slide.notes_text_frame.text=f"老师意见修订版｜第{page}/{total}页｜本页讲述预算{m['seconds']}秒\n\n{m['speech']}\n\n讲述重点：{m.get('focus','')}\n\n来源：{m['source']}"
        m['text']=[{'text':sh.text,'x':round(sh.left/914400,4),'y':round(sh.top/914400,4),'w':round(sh.width/914400,4),'h':round(sh.height/914400,4)}for sh in s.shapes if sh.has_text_frame and sh.text]
        m['tables']=[[[c.text for c in row.cells]for row in sh.table.rows]for sh in s.shapes if sh.has_table]
        m['native_chart_count']=sum(sh.has_chart for sh in s.shapes)
        final.append(m)

    # Rebuild section membership, including new slides and a cover section.
    p14='http://schemas.microsoft.com/office/powerpoint/2010/main'
    section_list=pres._element.find(f'.//{{{p14}}}sectionLst')
    if section_list is not None:
        for node in list(section_list):section_list.remove(node)
        current=None;lst=None
        for s,m,sid in zip(order,final,list(pres.slides._sldIdLst)):
            key=('credit' if m.get('kind')=='credit' else m['chapter'])
            if key!=current:
                name='成员分工' if key=='credit' else f"{m['chapter']:02d} {m['chapterName']}"if m['chapter']else'封面'
                section=etree.SubElement(section_list,f'{{{p14}}}section',name=name,id='{'+str(uuid.uuid5(uuid.NAMESPACE_URL,STEM+name))+'}')
                lst=etree.SubElement(section,f'{{{p14}}}sldIdLst');current=key
            etree.SubElement(lst,f'{{{p14}}}sldId',id=str(sid.id))

    pres.core_properties.title='Keep社区内容表达与互动反馈｜老师意见修订版'
    pres.core_properties.subject='正文可观测范围、词典测量、作者支持及探索性成分的修订分析'
    out=ROOT/(STEM+'.pptx');pres.save(out)
    # Retain accepted chart XML and its workbook relationships byte-for-byte.
    # python-pptx otherwise rewrites only insignificant XML whitespace on load.
    with zipfile.ZipFile(SOURCE)as original,zipfile.ZipFile(out)as generated:
        keep={n:original.read(n)for n in original.namelist()if re.fullmatch(r'ppt/charts/chart\d+\.xml',n)or re.fullmatch(r'ppt/charts/_rels/chart\d+\.xml.rels',n)}
        packaged={n:generated.read(n)for n in generated.namelist()}
        packaged.update(keep)
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED)as target:
        for name,content in packaged.items():target.writestr(name,content)
    clock=lambda n:f'{n//60}:{n%60:02d}'
    mapping=[{'old_page':k,'new_page':v}for k,v in sorted(old_to_new.items())]
    timing={'slides':total,'new_slides':7,'research_slides':29,'credit_slides':1,'speech_seconds':elapsed,'transition_seconds':45,'target_seconds':elapsed+45,'note':'新增方法证据，不再标为12分钟版；时长为讲述预算，须排练校准。'}
    lines=[f'Keep社区内容表达与互动反馈｜老师意见修订版\n\n{total}页（新增7页，保留旧版）；讲述预算{clock(elapsed)}，另留45秒转场，目标{clock(elapsed+45)}。\n本次不再标为12分钟版。新语义分类尚未通过人工独立验证，不作为完成的新主题回归。\n\n新旧页码对照：']
    lines.extend(f'旧{k}页 → 新{v}页'for k,v in sorted(old_to_new.items()))
    lines.append('\n新增页：'+ '、'.join(f"第{m['page']}页 {m['title']}"for m in final if m.get('new_analysis')))
    lines.append('\n逐页讲稿\n')
    lines.extend(f"第{m['page']}页｜{m['title']}\n{clock(m['start_seconds'])}—{clock(m['end_seconds'])}；{m['seconds']}秒\n\n{m['speech']}\n\n重点：{m.get('focus','')}\n来源：{m['source']}\n"for m in final)
    (ROOT/(STEM+'_逐页讲稿.txt')).write_text('\n'.join(lines),encoding='utf-8')
    (QA/'slides_manifest.json').write_text(json.dumps(final,ensure_ascii=False,indent=2)+'\n')
    (QA/'timing_plan.json').write_text(json.dumps(timing,ensure_ascii=False,indent=2)+'\n')
    (QA/'page_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    # Verify the saved file, every slide boundary, notes, preserved charts/data.
    checked=Presentation(out);bounds=[]
    for i,s in enumerate(checked.slides,1):
        assert s.has_notes_slide
        for sh in s.shapes:
            if sh.left<0 or sh.top<0 or sh.left+sh.width>checked.slide_width+100 or sh.top+sh.height>checked.slide_height+100:bounds.append((i,sh.name))
    assert not bounds,bounds
    with zipfile.ZipFile(SOURCE)as z0,zipfile.ZipFile(out)as z1:
        oldcharts={n:z0.read(n)for n in z0.namelist()if re.fullmatch(r'ppt/charts/chart\d+\.xml',n)}
        # python-pptx preserves old chart parts without rewriting their contents.
        assert all(n in z1.namelist()and z1.read(n)==content for n,content in oldcharts.items())
        allcharts=[n for n in z1.namelist()if re.fullmatch(r'ppt/charts/chart\d+\.xml',n)]
        for n in z1.namelist():
            if n.endswith('.xml'):etree.fromstring(z1.read(n))
    # All comment/network slide content and tables are identical except page counters.
    for old_page in range(15,22):
        orig=old_slides[old_page-1];curr=checked.slides[old_to_new[old_page]-1]
        for ss in [orig,curr]:
            assert len(ss.shapes)>0
        atext=[sh.text for sh in orig.shapes if sh.has_text_frame and not re.fullmatch(r'\d{2} / \d{2}',sh.text)]
        btext=[sh.text for sh in curr.shapes if sh.has_text_frame and not re.fullmatch(r'\d{2} / \d{2}',sh.text)]
        assert atext==btext
    result={'pptx':str(out),'slides':len(checked.slides),'new_slides':7,'native_charts':len(allcharts),'preserved_old_native_charts':len(oldcharts),'original_chart_xml_unchanged':True,'all_notes_present':True,'shapes_outside_slide':bounds,'unvalidated_new_taxonomy_not_applied':True,'pptx_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'timing':timing,'office_render':'not performed: Office/QuickLook unavailable in this sandbox; no deck PDF is claimed','visual_review':'pending independent geometry/text-fit check'}
    (QA/'content_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
