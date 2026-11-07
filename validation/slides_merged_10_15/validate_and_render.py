"""Inspect an actual PPTX export, render all pages, and check source integrity."""
from collections import Counter
from pathlib import Path
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
STEM = 'Keep社区内容表达与互动反馈_10-15分钟合并版'


def norm(s):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', s).replace('−', '-'))


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    manifest = json.loads((QA / 'slides_manifest.json').read_text())
    protected = json.loads((QA / 'protected_inputs.json').read_text())
    changed = [p['file'] for p in protected if sha(p['file']) != p['sha256']]
    assert not changed, changed
    pres = Presentation(ROOT / (STEM + '.pptx'))
    assert len(pres.slides) == len(manifest) == 15
    assert all(s.has_notes_slide for s in pres.slides)
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
        assert len(charts) == 8
        all_text = ''.join(''.join(etree.fromstring(z.read(f'ppt/slides/slide{i}.xml')).xpath('//a:t/text()', namespaces=ns)) for i in range(1, 16))
        assert not re.search(r'\bTODO\b|lorem ipsum|\[insert|待填写|待补充|示例数据', all_text, re.I)

    pdf = fitz.open(ROOT / (STEM + '.pdf'))
    assert len(pdf) == 15
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
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(QA / f'slide-{i:02d}.png')

    expected_chart_labels = {3: ['51.03', '48.05', '7.94', '3.91'],
                             4: ['63.7', '90.0', '57.3', '111.2'],
                             6: ['52.7%', '52.6%', '35.8%', '38.2%', '0.6%'],
                             7: ['16.9%', '4.5%', '7.9%', '0.6%'],
                             8: ['43.5%', '56.3%', '26.7%', '6.4%'],
                             10: ['89.0%', '9.1%', '2.0%'],
                             12: ['64.5%', '82.2%']}
    missing_labels = []
    for i, labels in expected_chart_labels.items():
        actual = norm(pdf[i-1].get_text())
        absent = [v for v in labels if norm(v) not in actual]
        if absent:
            missing_labels.append({'page': i, 'labels': absent})
    for batch, start in enumerate(range(0, 15, 9), 1):
        count = min(9, 15-start)
        sheet = Image.new('RGB', (1500, ((count+2)//3)*310), '#E2E8E4')
        draw = ImageDraw.Draw(sheet)
        for j in range(start, start+count):
            im = Image.open(QA / f'slide-{j+1:02d}.png')
            im.thumbnail((484, 273))
            x, y = (j-start)%3*500+8, (j-start)//3*310+28
            sheet.paste(im, (x, y))
            draw.text((x, y-20), str(j+1), fill='#173F36')
        sheet.save(QA / f'contact-{batch}.png')
    pdf.select(list(range(13)))
    pdf.save(ROOT / (STEM + '_主讲阅读版.pdf'))
    result = {'pptx_slides': 15, 'main_slides': 13, 'appendix_slides': 2, 'native_charts': len(charts),
              'all_slides_have_notes': True, 'sources_unchanged': not changed, 'shapes_outside_slide': bounds,
              'missing_text': missing, 'missing_chart_labels': missing_labels, 'text_outside_pdf_page': overflow,
              'pptx_sha256': sha(ROOT / (STEM + '.pptx')), 'pdf_sha256': sha(ROOT / (STEM + '.pdf')),
              'renderer': 'LibreOffice headless, actual PPTX export', 'visual_review': 'pending'}
    (QA / 'render_checks.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    assert not missing, missing
    assert not missing_labels, missing_labels
    assert not overflow, overflow


if __name__ == '__main__':
    main()
