"""Render the dyx PDF's verbatim recovered content in the approved insight style."""
from pathlib import Path
import importlib.util
import sys
import json

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('report_renderer',ROOT/'code/build_phase2_report.py')
renderer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
renderer.CSS += """
h1 { font-size: 26pt; }
table { break-inside: avoid; }
.toc a { padding: 0.2mm 0; line-height: 1.3; font-size: 9pt; }
.toc .level-1 { margin-top: 1mm; font-size: 9.5pt; }
.toc .level-2 { font-size: 9pt; }
.chapter.dense-synthesis p { margin-bottom: 3mm; line-height: 1.75; }
.chapter.dense-synthesis h3 { margin-top: 5mm; }
.table-intro { break-after: avoid; }
.chapter .table-note { font-size: 8.7pt; color: #5e7281; line-height: 1.6; }
.chapter .table-rq td:last-child { white-space: nowrap; }
.cover > p { color: #263746; }
.cover > p:first-of-type { margin-top: 8mm; font-size: 13.5pt; }
.references p { text-align: left; }
@media print {
 .toc a { padding: 0.2mm 0; }
 .references { break-before: auto; margin-top: 9mm; }
 .chapter:has(> #heading-01) p { margin-bottom: 3mm; }
 .chapter:has(> #heading-01) h3 { margin-top: 6mm; margin-bottom: 3mm; }
}
"""
original_write_html=renderer.write_html
def write_html(soup,headings):
    doc=original_write_html(soup,headings)
    for h in doc.find_all('h2'):
        if h.get_text()=='参考文献':h.parent['class']=['chapter','references']
        elif h.get_text().startswith('8. '):h.parent['class']=['chapter','dense-synthesis']
    blocks=json.loads((ROOT/'validation/report_dyx_presentation/content_blocks.json').read_text())
    tables=[b for b in blocks if b['kind']=='table']
    widths={'rq':[9,40,36,15], 'cleaning':[18,39,43], 'sources':[18,38,44],
            'variables':[21,49,30], 'suggestions':[18,30,26,26], 'members':[28,47,25]}
    for table,block in zip(doc.select('main table'),tables):
        key=block['key'];table['class']=['table-'+key]
        if key in widths:
            cols=doc.new_tag('colgroup')
            for width in widths[key]:
                col=doc.new_tag('col');col['style']=f'width:{width}%';cols.append(col)
            table.insert(0,cols)
            table['style']='table-layout:fixed'
        if key=='variables':
            intro=table.find_previous_sibling('p')
            intro['class']=['table-intro']
        following=table.find_next_sibling('p')
        if following and following.get_text().startswith(('作者内比较','使用同一批','其他用户发言','直接回复比例','三类网络','接收事件数','互惠按边','标准误按','本表保留','描述按每帖','上表为建议')):
            following['class']=['table-note']
    for paragraph in doc.select('main p'):
        if paragraph.get_text().startswith('•'):
            following=paragraph.find_next_sibling('p')
            if following and following.get_text().startswith('•'):
                paragraph['style']='break-after:avoid'
    (ROOT/(renderer.STEM+'.html')).write_text(str(doc))
    return doc
renderer.write_html=write_html
sys.argv=[str(ROOT/'code/build_phase2_report.py'),'--stem',
          '分析报告_Phase2_中文新版_insight_v2_修改版_排版优化',
          '--validation-dir','validation/report_dyx_presentation']
renderer.main()
