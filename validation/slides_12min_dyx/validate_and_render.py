"""Inspect an actual PPTX export, render all pages, and check source integrity."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json
import re
import unicodedata
import zipfile

from lxml import etree
from PIL import Image, ImageDraw
import pymupdf as fitz
from pptx import Presentation

QA = Path(__file__).resolve().parent
ROOT = QA.parents[1]
STEM = 'Keep社区内容表达与互动反馈_12分钟合并版'


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s).replace('−', '-'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pages', help='Comma-separated pages to rasterize; default all')
    args = parser.parse_args()
    render_pages = set(map(int, args.pages.split(','))) if args.pages else set(range(1, 24))
    manifest = json.loads((QA / 'slides_manifest.json').read_text())
    protected = json.loads((QA / 'protected_before.json').read_text())
    changed = [p['file'] for p in protected if sha(ROOT / p['file']) != p['sha256']]
    assert not changed, changed
    pres = Presentation(ROOT / (STEM + '.pptx'))
    assert len(pres.slides) == len(manifest) == 23
    assert all(s.has_notes_slide for s in pres.slides)
    assert manifest[-1]['kind']=='credit'
    accepted=json.loads((ROOT/'validation/slides_12min/slides_manifest.json').read_text())
    mapping=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,None,19,20,21,22]
    assert [s['basePage'] for s in manifest]==mapping
    # Main estimates, topic coefficients, breadth examples and limitations stay intact.
    original=Presentation(ROOT/'Keep社区内容表达与互动反馈_12分钟版.pptx')
    for oldpage,newpage in [(10,10),(11,11),(13,13),(19,20),(21,22)]:
        def tables(slide):
            return [[[c.text for c in row.cells] for row in sh.table.rows] for sh in slide.shapes if sh.has_table]
        assert tables(original.slides[oldpage-1])==tables(pres.slides[newpage-1]), (oldpage,newpage)
    for oldpage,newpage in [(4,4),(5,5),(6,6),(15,15),(16,16),(18,18)]:
        assert [c['data'] for c in accepted[oldpage-1]['charts']]==[c['data'] for c in manifest[newpage-1]['charts']]
    assert accepted[8]['charts'][0]['data']==manifest[7]['charts'][0]['data']
    assert len(manifest[11]['sensitivityPanels'])==3
    assert '6,609条外来根评论' in ''.join(t['text'] for t in manifest[15]['text'])
    assert '137 / 513；195 / 3,055' in ''.join(t['text'] for t in manifest[15]['text'])
    timing=json.loads((QA/'timing_plan.json').read_text())
    assert timing['speech_seconds']==sum(x['seconds'] for x in manifest)==664
    assert timing['target_seconds']==694
    assert '陈霖' in ''.join(x['text'] for x in manifest[-1]['text'])
    assert '董依心（dyx）' in ''.join(x['text'] for x in manifest[-1]['text'])
    expected_blocks={'RQ1':[4,5,6,7], 'RQ2':[8,9,10,11,12,13,14], 'RQ3':[15,16,17,18,19,20,21]}
    for question,pages in expected_blocks.items():
        assert [s['page'] for s in manifest if s['question']==question]==pages
    assert all(manifest[i-1]['title'].startswith(q+'的回答') for q,i in [('RQ1',7),('RQ2',14),('RQ3',21)])
    bounds = []
    for i, s in enumerate(pres.slides, 1):
        for shape in s.shapes:
            if shape.left < -100 or shape.top < -100 or shape.left + shape.width > pres.slide_width + 100 or shape.top + shape.height > pres.slide_height + 100:
                bounds.append({'page': i, 'shape': shape.name})
    assert not bounds, bounds
    ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main', 'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
    with zipfile.ZipFile(ROOT / (STEM + '.pptx')) as z:
        for n in z.namelist():
            if n.endswith('.xml'):
                etree.fromstring(z.read(n))
        charts = [n for n in z.namelist() if re.fullmatch(r'ppt/charts/chart\d+\.xml', n)]
        assert len(charts) == 13
        all_text = ''.join(''.join(etree.fromstring(z.read(f'ppt/slides/slide{i}.xml')).xpath('//a:t/text()', namespaces=ns)) for i in range(1, 24))
        assert not re.search(r'\bTODO\b|lorem ipsum|\[insert|待填写|待补充|示例数据|答疑|备用页|64.5%|2.05小时|57.0%|互动时序|回得多快', all_text, re.I)
        assert all(slide._element.get('show', '1') != '0' for slide in pres.slides)

    pdf = fitz.open(ROOT / (STEM + '.pdf'))
    assert len(pdf) == 23
    missing = []
    overflow = []
    for i, (page, spec) in enumerate(zip(pdf, manifest), 1):
        expected = norm(''.join(t['text'] for t in spec['text']))
        actual = norm(page.get_text())
        count = Counter(expected) - Counter(actual)
        if sum(count.values()) > max(2, len(expected) * .005):
            missing.append({'page': i, 'missing': dict(count)})
        for block in page.get_text('dict')['blocks']:
            for ln in block.get('lines', []):
                for sp in ln['spans']:
                    x0, y0, x1, y1 = sp['bbox']
                    if x0 < -1 or y0 < -1 or x1 > page.rect.width + 1 or y1 > page.rect.height + 1:
                        overflow.append({'page': i, 'text': sp['text'], 'bbox': sp['bbox']})
        if i in render_pages:
            page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(QA / f'slide-{i:02d}.png')

    expected_chart_labels = {4: ['51.03', '48.05', '7.94', '3.91', '500+'],
                             5: ['52.7%', '35.8%', '4.6%', '3.4%'],
                             6: ['52.7%', '52.6%', '35.8%', '38.2%', '0.6%'],
                             8: ['63.7', '90.0', '57.3', '111.2'],
                             9: ['94.9%', '69.1%'],
                             15: ['16.9%', '4.5%', '7.9%', '0.6%'],
                             16: ['43.5%', '56.3%', '26.7%', '6.4%'],
                             18: ['89.0%', '9.1%', '2.0%'],
                             19: ['49.6%', '29.9%', '74.1%', '48.3%', '54.0%']}
    missing_labels = []
    for i, labels in expected_chart_labels.items():
        actual = norm(pdf[i-1].get_text())
        absent = [v for v in labels if norm(v) not in actual]
        if absent:
            missing_labels.append({'page': i, 'labels': absent})
    for batch, start in enumerate(range(0, 23, 9), 1):
        count = min(9, 23-start)
        sheet = Image.new('RGB', (1500, ((count+2)//3)*310), '#E2E8E4')
        draw = ImageDraw.Draw(sheet)
        for j in range(start, start+count):
            im = Image.open(QA / f'slide-{j+1:02d}.png')
            im.thumbnail((484, 273))
            x, y = (j-start)%3*500+8, (j-start)//3*310+28
            sheet.paste(im, (x, y))
            draw.text((x, y-20), str(j+1), fill='#173F36')
        sheet.save(QA / f'contact-{batch}.png')
    result = {'pptx_slides': 23, 'main_slides': 23, 'research_slides': 22, 'credit_slides': 1, 'appendix_slides': 0, 'hidden_slides': 0, 'native_charts': len(charts),
              'all_slides_have_notes': True, 'sources_unchanged': not changed, 'shapes_outside_slide': bounds,
              'missing_text': missing, 'missing_chart_labels': missing_labels, 'text_outside_pdf_page': overflow,
              'pptx_sha256': sha(ROOT / (STEM + '.pptx')), 'pdf_sha256': sha(ROOT / (STEM + '.pdf')),
              'renderer': 'LibreOffice headless, background-only PDF export', 'visual_review': 'pending'}
    (QA / 'render_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not missing, missing
    assert not missing_labels, missing_labels
    assert not overflow, overflow


if __name__ == '__main__':
    main()
