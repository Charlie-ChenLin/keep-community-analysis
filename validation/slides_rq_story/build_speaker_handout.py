"""Build a Word handout from the current 24-slide, question-led presentation."""
import hashlib
import json
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
OUT = ROOT / 'Keep社区内容表达与互动反馈_RQ分题讲述版_逐页讲稿与结构说明.docx'
FONT = 'Arial Unicode MS'
GREEN = '245C4F'
GRAY = '65756F'


def clock(seconds):
    return f'{seconds // 60}:{seconds % 60:02d}'


def set_font(run, size=11, bold=False, color=None):
    run.font.name = FONT
    run._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), FONT)
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


def para(doc, text, size=11, bold=False, color=None, after=6, keep=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.keep_with_next = keep
    set_font(p.add_run(text), size, bold, color)
    return p


def shade(cell, fill):
    node = OxmlElement('w:shd')
    node.set(qn('w:fill'), fill)
    cell._tc.get_or_add_tcPr().append(node)


def main():
    manifest_file = QA / 'slides_manifest.json'
    manifest = json.loads(manifest_file.read_text())
    timing = json.loads((QA / 'timing_plan.json').read_text())
    expected_blocks = {'RQ1': list(range(4, 9)), 'RQ2': list(range(9, 16)), 'RQ3': list(range(16, 24))}
    assert len(manifest) == 24
    assert all(not s['appendix'] for s in manifest)
    assert all(s['speech'].strip() and s['focus'].strip() for s in manifest)
    assert sum(s['seconds'] for s in manifest) == timing['speech_seconds']
    for question, pages in expected_blocks.items():
        assert [s['page'] for s in manifest if s['question'] == question] == pages

    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2)
    sec.left_margin = sec.right_margin = Cm(2.1)
    sec.header_distance = sec.footer_distance = Cm(.9)
    normal = doc.styles['Normal']
    normal.font.name = FONT
    normal._element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'), FONT)
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.15
    set_font(sec.header.paragraphs[0].add_run('Keep社区｜RQ分题讲述版'), 9, color=GRAY)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(footer.add_run('第 '), 9, color=GRAY)
    field = OxmlElement('w:fldSimple')
    field.set(qn('w:instr'), 'PAGE')
    footer._p.append(field)
    set_font(footer.add_run(' 页'), 9, color=GRAY)

    para(doc, 'Keep社区内容表达与互动反馈分析', 18, True, GREEN, 10)
    para(doc, 'RQ分题讲述版｜逐页讲稿与结构说明', 16, True, GREEN, 14)
    para(doc, f'24页全部为正文，无答疑页或隐藏页。标准排练预算{clock(timing["target_seconds"])}，包括讲述与指图{clock(timing["speech_seconds"])}、转场{timing["transition_seconds"]}秒；压缩预算{clock(timing["short_seconds"])}。', after=12)
    para(doc, '为什么按问题重排', 14, True, GREEN, 7)
    para(doc, '上一版虽然标了RQ，正文却仍按方法章节切换：分布还没讲完就进入回归，回归以后又回到主题构成。听众需要自己把同一问题的几段答案重新拼起来。这一版先完整回答RQ1，再进入RQ2和RQ3；每部分结尾立即收束本题，最后只交代共同局限。', after=10)

    rows = [
        ['共同开场', '1—3', '提出总问题、三个RQ与预期，再说明样本和记录范围。'],
        ['RQ1', '4—8', '正文覆盖 → 媒体与点赞分布 → 主题构成 → 作者贡献 → 第8页回答。'],
        ['RQ2', '9—15', '变量定义 → 原始差异与媒体构成 → 回归设定 → M3 → 敏感性 → 主题回归 → 第15页回答。'],
        ['RQ3', '16—23', '谁说什么 → 直接回复口径 → 哪些留言被回 → 网络结构 → 回复方向 → 参与人数 → 时序 → 第23页回答。'],
        ['共同局限', '24', '说明记录缺口与方法限制怎样影响判断，以及还需要补什么记录。'],
    ]
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    table.autofit = False
    widths = [Cm(2.0), Cm(1.7), Cm(12.1)]
    for column, width in zip(table.columns, widths):
        column.width = width
    for i, h in enumerate(['部分', 'PPT页码', '讲述顺序']):
        table.rows[0].cells[i].width = widths[i]
        table.rows[0].cells[i].text = h
        shade(table.rows[0].cells[i], 'EDF4F0')
    for values in rows:
        cells = table.add_row().cells
        for i, content in enumerate(values):
            cells[i].width = widths[i]
            cells[i].text = content
    for row_index, row in enumerate(table.rows):
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.space_after = Pt(4)
                p.paragraph_format.line_spacing = 1.1
                for run in p.runs:
                    set_font(run, 10.5, row_index == 0, GREEN if row_index == 0 else None)

    para(doc, '排练时怎么用', 14, True, GREEN, 7)
    para(doc, '每页以半分钟左右为基础，方程和主要推断页可稍长。表格保留给听众看与核对，口头抓住“讲述重点”，不要逐格念完全部数字。三个收束页分别完成本题的回答，再转入下一问；压缩时也保留这三处衔接。实际时长请按两人的语速、换人和指图情况排练校准。', after=6)

    elapsed = 0
    for start in range(0, len(manifest), 2):
        doc.add_page_break()
        for offset, slide in enumerate(manifest[start:start+2]):
            if offset:
                para(doc, '', after=10)
            para(doc, f'第{slide["page"]}页｜{slide["title"]}', 16, True, GREEN, 6, True)
            scope = slide['question'] or ('共同局限' if slide['page'] == 24 else '共同开场')
            subsection = slide.get('subsection') or slide['chapterName']
            para(doc, f'{scope}　｜　{subsection}', 10.5, color=GRAY, after=5, keep=True)
            para(doc, f'标准{slide["seconds"]}秒；累计{clock(elapsed)}—{clock(elapsed + slide["seconds"])}；压缩{slide["shortSeconds"]}秒', 10.5, color=GRAY, after=7, keep=True)
            para(doc, '讲述重点：' + slide['focus'], 11, True, after=8, keep=True)
            para(doc, slide['speech'], 11, after=10)
            para(doc, '来源：' + slide['source'], 9, color=GRAY, after=8)
            elapsed += slide['seconds']

    doc.core_properties.title = 'Keep社区内容表达与互动反馈分析｜RQ分题讲述版讲稿'
    doc.core_properties.author = '陈霖、董依心'
    doc.core_properties.subject = '24页正文；RQ1、RQ2、RQ3连续讲述与各自收束'
    doc.save(OUT)
    saved = Document(OUT)
    contents = '\n'.join(p.text for p in saved.paragraphs)
    assert all(s['speech'] in contents for s in manifest)
    assert all(f'第{s["page"]}页｜{s["title"]}' in contents for s in manifest)
    assert elapsed == timing['speech_seconds']
    assert not any(term in contents for term in ['22页全部', '13条反馈', 'RQ分析增强版'])
    checks = {
        'file': str(OUT),
        'manifest_sha256': hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
        'docx_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'slides': len(manifest),
        'all_speeches_match_manifest': True,
        'all_titles_match_manifest': True,
        'all_focuses_match_manifest': all(s['focus'] in contents for s in manifest),
        'question_blocks': expected_blocks,
        'target_seconds': timing['target_seconds'],
        'short_seconds': timing['short_seconds'],
    }
    (QA / 'handout_checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2))
    print(OUT)
    print('24 speaker scripts, titles and focus statements match the current manifest.')


if __name__ == '__main__':
    main()
