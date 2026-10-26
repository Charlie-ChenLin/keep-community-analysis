"""Render a standalone, source-backed oral-defense checklist to A4 PDF."""
import asyncio
from collections import Counter
import hashlib
from html import escape
import json
from pathlib import Path
import re
import unicodedata

import pymupdf as fitz
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'validation/defense_qa'
STEM = 'Keep社区内容表达与互动反馈_答疑清单'
SOURCES = [
 ('S1', 'statsmodels：普通最小二乘 OLS', 'https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLS.html', 'OLS定义与实现。'),
 ('S2', 'statsmodels：作者等单向聚类协方差', 'https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_cluster.html', '聚类协方差及小样本修正。'),
 ('S3', 'statsmodels：BH多重检验调整', 'https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html', 'fdr_bh及调整后p值；项目将该列记为BH q。'),
 ('S4', 'Santos Silva与Tenreyro：The Log of Gravity（2006）作者说明', 'https://personal.lse.ac.uk/tenreyro/LGW.html', 'PPML用于非负结果的原理与相关研究；原论文DOI：10.1162/rest.88.4.641。'),
 ('S5', 'statsmodels：Poisson族与GLM拟合', 'https://www.statsmodels.org/stable/generated/statsmodels.genmod.families.family.Poisson.html', 'Poisson族默认log链接；GLM.fit支持协方差与推断选项。'),
 ('S6', 'scikit-learn：文本特征与TF-IDF', 'https://scikit-learn.org/stable/modules/feature_extraction.html#tfidf-term-weighting', '词频、逆文档频率及文本特征。'),
 ('S7', 'scikit-learn：非负矩阵分解 NMF', 'https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.NMF.html', 'X≈WH的非负分解及主题提取。'),
 ('S8', 'NetworkX：有向网络密度', 'https://networkx.org/documentation/stable/reference/generated/networkx.classes.function.density.html', '有向密度m/[n(n−1)]；本项目先排除自我互动。'),
 ('S9', 'NetworkX：弱连通分量', 'https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.weakly_connected_components.html', '有向网络中的弱连通分量。'),
 ('S10', 'NIST：置信区间的重复抽样解释', 'https://itl.nist.gov/div898/handbook/prc/section1/prc14.htm', '95%覆盖率的含义。'),
]

STYLE = r'''
@page{size:A4;margin:0}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:#fff;color:#20332f}
body{font-family:"Arial Unicode MS","PingFang SC","Microsoft YaHei",sans-serif;font-size:10.5pt;line-height:1.46}
.sheet{width:210mm;height:297mm;position:relative;padding:13mm 17mm 16mm;break-after:page;overflow:hidden;background:#fff}
.sheet:last-child{break-after:auto}
.eyebrow{font-size:9pt;color:#65756f;margin-bottom:2.5mm}
h1{font-size:25pt;line-height:1.22;color:#245c4f;margin:0 0 3.5mm}
h2{font-size:17pt;line-height:1.3;color:#245c4f;margin:0 0 2mm}
.lead{font-size:10.5pt;margin:0 0 4mm}
h3{font-size:12pt;color:#245c4f;margin:4mm 0 2mm}
p{margin:0 0 2.2mm}
a{color:#245c4f;text-decoration:none}
.meta{font-size:8.5pt;color:#65756f;margin:1.1mm 0 2.2mm}
.footer{position:absolute;left:17mm;right:17mm;bottom:7.5mm;display:flex;justify-content:space-between;font-size:8.5pt;color:#65756f}
.questions{margin-top:4mm}
.question{margin:0 0 5mm;break-inside:avoid}
.question:last-child{margin-bottom:0}
.qtitle{font-size:12.2pt;line-height:1.32;font-weight:bold;color:#20332f;margin:0}
.qid{color:#b97339;margin-right:2mm}
.short{background:#edf4f0;padding:2.3mm 3.2mm;margin:0 0 2mm;font-size:10.5pt}
.label{font-weight:bold;color:#245c4f}
.follow{font-size:10.15pt;line-height:1.47}
.avoid{font-size:9.4pt;color:#775a42;margin-top:1.8mm;line-height:1.42}
.index{display:grid;grid-template-columns:1fr 1fr;gap:1.8mm 4mm;font-size:10pt;margin:1mm 0 3mm}
.index a{display:block;background:#f6f8f7;padding:1.9mm 2.5mm}
table{width:100%;border-collapse:collapse;font-size:9.5pt;line-height:1.35;margin:2mm 0 3.3mm}
th,td{padding:2mm 2.6mm;text-align:left;vertical-align:top;border-bottom:1px solid #e1e8e3}
th{background:#edf4f0;color:#245c4f;font-weight:bold}
.small{font-size:9.1pt;color:#65756f;line-height:1.4}
.role{font-size:10pt;background:#f6f8f7;padding:2.7mm 3.5mm;margin:3mm 0}
.ref{font-size:10pt;line-height:1.37;margin-bottom:3.2mm}
.ref strong{color:#245c4f}
.local{background:#f6f8f7;padding:3mm 4mm;font-size:9.4pt;line-height:1.4;margin-top:3mm}
'''


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s).replace('−', '-').replace('–', '-'))


def question_html(q):
    refs = ' '.join(f'<a href="#ref-{r}">[{r}]</a>' for r in q['source_refs'])
    pages = '、'.join(map(str, q['slide_pages']))
    return f'''<article class="question" id="{q['id']}">
    <p class="qtitle"><span class="qid">{q['id']}</span>{escape(q['title'])}</p>
    <div class="meta">建议主答：{escape(q['owner'])}　｜　对应PPT：第{pages}页　{refs}</div>
    <div class="short"><span class="label">现场短答：</span>{escape(q['short_answer'])}</div>
    <p class="follow"><span class="label">如果被追问：</span>{escape(q['follow_up'])}</p>
    <p class="avoid"><strong>易混淆：</strong>{escape(q['avoid'])}</p></article>'''


def cover(questions, locations):
    index = [('M10','PPML是什么、为什么能保留零'), ('M11','方差大于均值还能否用PPML'),
             ('M12','PPML与对数OLS不能混用什么'), ('M07','p显著、BH q不显著怎么解释'),
             ('M03','作者和日期固定效应调整什么'), ('T06','主题权重与10个百分点的含义'),
             ('N04','54%、57%、89%、82.2%的分母'), ('N07','2.05小时遗漏了哪些留言')]
    links=''.join(f'<a href="#{qid}">{qid}　{escape(t)}<br><span class="small">见本清单第{locations[qid]}页</span></a>' for qid,t in index)
    return f'''<div class="eyebrow">Keep社区内容表达与互动反馈分析 · 独立备查材料</div>
    <h1>答疑清单</h1><p class="lead">28个常见问题：先用绿色框里的短答回应，再按追问展开。PPT页码对应含Credit的25页最终汇报版；研究内容仍在第1—24页。</p>
    <div class="role"><strong>答疑分工建议</strong><br>陈霖先答：问题提出、数据清洗、RQ1内容与分布。<br>董依心（dyx）先答：RQ2建模与推断、RQ3评论和网络；对方可补充相关背景。</div>
    <h3>先熟悉这8个问题</h3><div class="index">{links}</div>
    <h3>现场最容易混用的数字</h3>
    <table><thead><tr><th style="width:31%">口径</th><th>本研究应怎样说</th></tr></thead><tbody>
    <tr><td>M3积极表达</td><td>β=−0.086；原始p=0.016，BH q=0.079。五项文字联合p=0.130。</td></tr>
    <tr><td>PPML积极表达</td><td>β=−0.135，95%区间[−0.299, 0.028]，p=0.103；拟合原始点赞条件均值。</td></tr>
    <tr><td>主题回归</td><td>2,470帖、86作者；用连续权重，训练交流为参照，主题联合p=0.166。</td></tr>
    <tr><td>根评论回复</td><td>54.0%：根评论后7天内直接回复；57.0%：留言串参与、不限7天。分母均6,609。</td></tr>
    <tr><td>回复方向与评论时间</td><td>89.0%的分母是4,902次明确回复；82.2%的分母是11,595条评论，从发帖起算。</td></tr>
    </tbody></table>
    <p class="small">本材料解释已经做过的分析。遇到没有拟合过的模型、没有采集的字段或没有做的检验，说明本次范围即可，不临场补造结果。</p>'''


def references():
    out='<div class="eyebrow">核查依据</div><h2>术语来源与本研究结果口径</h2><p class="lead">技术定义参考官方文档与作者原始研究；样本量、系数、比例和分工按本项目现有结果及已确认信息核对。</p>'
    for key,title,url,why in SOURCES:
        extra=' · <a href="https://www.statsmodels.org/stable/generated/statsmodels.genmod.generalized_linear_model.GLM.fit.html">GLM.fit参数</a>' if key=='S5' else ''
        out+=f'<div class="ref" id="ref-{key}"><strong>[{key}] <a href="{escape(url,quote=True)}">{escape(title)}</a>{extra}</strong><br>{escape(why)}</div>'
    out+='''<div class="local"><strong>项目内的核查入口</strong><br>
    主模型、敏感性与拟合：results/regression_coefficients.csv、model_fit.csv、summary.json；实现见code/analyze.py。<br>
    主题与作者权重：extension_topics.csv、extension_topic_regression.csv、supplemental_topic_author_weighting.csv；实现见code/extend_analysis.py。<br>
    评论口径：comment_text_features.csv、supplemental_direct_reply_language.csv、network_nodes.csv、extension_summary.json、supplemental_summary.json。<br>
    版本记录：statsmodels 0.14.2、scikit-learn 1.5.1、NetworkX 3.3；本材料未新增统计拟合。</div>'''
    return out


def write_html(questions, capacities):
    groups=[]
    for section in dict.fromkeys(q['section'] for q in questions):
        group=[q for q in questions if q['section']==section]
        cap=capacities.get(section,3)
        for start in range(0,len(group),cap):
            groups.append((section,group[start:start+cap]))
    locations={q['id']:i+2 for i,(_,items) in enumerate(groups) for q in items}
    pages=[('先看这页',cover(questions,locations))]
    for title,items in groups:
        body=f'<div class="eyebrow">独立答疑材料 · 每题先短答，再按追问展开</div><h2>{escape(title)}</h2><div class="questions">'+''.join(map(question_html,items))+'</div>'
        pages.append((title,body))
    pages.append(('参考来源',references()))
    total=len(pages)
    body=''.join(f'<section class="sheet" id="page-{i}"><main>{content}</main><footer class="footer"><span>Keep社区 · 答疑准备</span><span>{i} / {total}</span></footer></section>' for i,(_,content) in enumerate(pages,1))
    html=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Keep社区汇报答疑清单</title><style>{STYLE}</style><body>{body}</body></html>'
    (ROOT/(STEM+'.html')).write_text(html)
    return pages,locations


async def main():
    questions=json.loads((QA/'questions_final.json').read_text())
    assert len(questions)==28
    chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    capacities={}
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path=chrome)
        page=await browser.new_page(viewport={'width':1000,'height':1400},device_scale_factor=1)
        for attempt in range(3):
            pages,locations=write_html(questions,capacities)
            await page.goto((ROOT/(STEM+'.html')).as_uri(),wait_until='load')
            await page.evaluate('document.fonts.ready')
            geometry=await page.evaluate('''() => [...document.querySelectorAll('.sheet')].map((p,i)=>({page:i+1,mainBottom:p.querySelector('main').getBoundingClientRect().bottom-p.getBoundingClientRect().top,footerTop:p.querySelector('footer').getBoundingClientRect().top-p.getBoundingClientRect().top,clientHeight:p.clientHeight,scrollHeight:p.scrollHeight}))''')
            bad=[g for g in geometry if g['mainBottom']>g['footerTop']-13 or g['scrollHeight']>g['clientHeight']+2]
            if not bad:
                break
            changed=False
            for g in bad:
                title=pages[g['page']-1][0]
                if title not in ('先看这页','参考来源') and capacities.get(title,3)>2:
                    capacities[title]=2;changed=True
            if not changed:
                raise RuntimeError(f'PDF page overflow: {bad}')
        assert not bad,bad
        await page.pdf(path=str(ROOT/(STEM+'.pdf')),print_background=True,prefer_css_page_size=True)
        await browser.close()

    pdf=fitz.open(ROOT/(STEM+'.pdf'))
    index_links=[link for link in pdf[0].get_links() if link.get('nameddest') in locations and link.get('page',-1)>=0]
    assert len(index_links)==8
    assert all(link['page']+1==locations[link['nameddest']] for link in index_links)
    assert len(pdf)==len(pages)
    text=''.join(p.get_text() for p in pdf)
    missing=[]
    for q in questions:
        expected=norm(q['title']+q['short_answer']+q['follow_up']+q['avoid'])
        actual=norm(pdf[locations[q['id']]-1].get_text())
        diff=Counter(expected)-Counter(actual)
        if sum(diff.values())>2:
            missing.append({'question':q['id'],'chars':dict(diff)})
    assert not missing,missing
    toc=[[1,'先看这页',1]]
    last=None
    for q in questions:
        if q['section']!=last:
            toc.append([1,q['section'],locations[q['id']]]);last=q['section']
        toc.append([2,q['id']+' '+q['title'],locations[q['id']]])
    toc.append([1,'参考来源',len(pdf)])
    pdf.set_toc(toc)
    pdf.set_metadata({'title':'Keep社区内容表达与互动反馈分析｜答疑清单','author':'陈霖、董依心','subject':'28题现场短答、追问解释与易混淆口径'})
    tmp=QA/'qa_with_outline.pdf';pdf.save(tmp);pdf.close();tmp.replace(ROOT/(STEM+'.pdf'))
    pdf=fitz.open(ROOT/(STEM+'.pdf'))
    for i,p in enumerate(pdf,1):
        p.get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False).save(QA/f'qa-page-{i:02d}.png')
    for batch,start in enumerate(range(0,len(pdf),6),1):
        sheet=Image.new('RGB',(1260,2*610),'#DFE7E2');draw=ImageDraw.Draw(sheet)
        for j in range(start,min(start+6,len(pdf))):
            im=Image.open(QA/f'qa-page-{j+1:02d}.png');im.thumbnail((400,565))
            x=(j-start)%3*420+10;y=(j-start)//3*610+29;sheet.paste(im,(x,y));draw.text((x,y-20),str(j+1),fill='#245C4F')
        sheet.save(QA/f'qa-contact-{batch}.png')
    result={'pdf_pages':len(pdf),'questions':28,'question_pages':locations,'geometry':geometry,'overflow':bad,'missing_question_text':missing,'bookmark_entries':len(toc),'first_page_links_verified':len(index_links),'pdf_sha256':hashlib.sha256((ROOT/(STEM+'.pdf')).read_bytes()).hexdigest(),'visual_review':'pending'}
    (QA/'render_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='geometry'},ensure_ascii=False,indent=2))


if __name__=='__main__':
    asyncio.run(main())
