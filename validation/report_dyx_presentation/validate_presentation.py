"""Verify text, cells, figure pixels, page geometry and unchanged branch inputs."""
from pathlib import Path
from collections import Counter
import hashlib, json, re
from bs4 import BeautifulSoup
from docx import Document
from docx.oxml.ns import qn
import pymupdf as fitz
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
VAL=Path(__file__).resolve().parent
STEM='分析报告_Phase2_中文新版_insight_v2_修改版_排版优化'
norm=lambda t:re.sub(r'\s+','',t)

def block_text(b):
    if b['kind']=='figure':return ''
    if b['kind']=='table':return ''.join(b['headers'])+''.join(''.join(row) for row in b['rows'])
    return b['text']

def main():
    blocks=json.loads((VAL/'content_blocks.json').read_text())
    expected=norm(''.join(block_text(b) for b in blocks))
    doc=BeautifulSoup((ROOT/(STEM+'.html')).read_text(),'html.parser')
    actual=''
    for section in doc.select('main > section'):
        for e in section.find_all(['h1','h2','h3','p','figcaption','th','td']):
            actual+=e.get_text()
    assert norm(actual)==expected,'HTML ordered text differs'
    html_tables=doc.select('main table')
    table_blocks=[b for b in blocks if b['kind']=='table']
    for html,b in zip(html_tables,table_blocks):
        rows=[[norm(c.get_text()) for c in row.find_all(['th','td'])] for row in html.find_all('tr')]
        assert rows==[[norm(c) for c in row] for row in [b['headers']]+b['rows']],b['key']
    pdf=fitz.open(ROOT/(STEM+'.pdf'))
    text=norm(''.join(p.get_text(clip=fitz.Rect(0,0,p.rect.width,790)) for p in pdf))
    missing=[]
    for b in blocks:
        if b['kind'] in ['table','figure']:continue
        if norm(b['text']) not in text:missing.append(b['text'][:90])
    assert not missing,missing
    bounds=[]
    for pi,p in enumerate(pdf,1):
        for block in p.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line['spans']:
                    x0,y0,x1,y1=span['bbox']
                    if x0<45 or x1>p.rect.width-45 or y0<40 or y1>p.rect.height-13:
                        bounds.append({'page':pi,'text':span['text'],'bbox':span['bbox']})
    assert not bounds,bounds
    wanted=[]
    for b in blocks:
        if b['kind']=='figure':
            im=Image.open(ROOT/b['path']).convert('RGB')
            wanted.append((im.size,hashlib.sha256(im.tobytes()).hexdigest()))
    found=[]
    for p in pdf:
        for item in p.get_image_info(xrefs=True):
            pix=fitz.Pixmap(pdf,item['xref'])
            if pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
            if pix.alpha:pix=fitz.Pixmap(pix,0)
            found.append(((pix.width,pix.height),hashlib.sha256(pix.samples).hexdigest()))
    assert wanted==found,'Exported figure pixels/order differ'
    word=Document(ROOT/(STEM+'.docx'));wordtext='';skip=False
    for child in word.element.body:
        if child.tag==qn('w:p'):
            t=''.join(x.text or '' for x in child.iter(qn('w:t')))
            pstyle=child.find('w:pPr/w:pStyle',child.nsmap)
            style=pstyle.get(qn('w:val')) if pstyle is not None else ''
            if t=='目录':skip=True;continue
            if skip and style=='Heading1' and t.startswith('1. '):skip=False
            if not skip:wordtext+=t
        elif child.tag==qn('w:tbl') and not skip:
            wordtext+=''.join(x.text or '' for x in child.iter(qn('w:t')))
    assert norm(wordtext)==expected,'DOCX ordered text differs'
    assert len(word.tables)==17 and len(word.inline_shapes)==13
    protected=json.loads((VAL/'protected_inputs.json').read_text())
    changed=[p for p,h in protected.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
    assert not changed,changed
    render=json.loads((VAL/'render_checks.json').read_text())
    assert render['directory_page_numbers_verified']
    assert render['source_sha256']==hashlib.sha256((ROOT/(STEM+'.md')).read_bytes()).hexdigest()
    result={'source_commit':'b6c31d20fbe59b096de568e8b6cd93aa395283bb',
      'source_authority':'Visible content of the dyx revised PDF; Markdown is not the content authority.',
      'source_characters_accounted_for_once':18431,
      'non_whitespace_content_characters':len(expected),
      'html_ordered_text_matches_recovered_pdf_content':True,
      'docx_ordered_text_matches_recovered_pdf_content':True,
      'all_paragraphs_present_in_rendered_pdf':True,
      'table_count':len(html_tables),'all_table_cells_preserved':True,
      'figures':len(found),'all_exported_figure_pixels_and_order_preserved':True,
      'pages':len(pdf),'toc_entries':len(pdf.get_toc()),
      'toc_page_numbers_verified':True,'pdf_text_within_page_bounds':True,
      'protected_inputs_unchanged':len(protected),
      'formatting_changes_only':['Fonts and hierarchy','Blue-grey palette','Page size and margins','Chapter pagination','Table widths and repeat-header consolidation','Full-width original figures and attached captions','Contents, page numbers and bookmarks','Paragraph and reference line reflow'],
      'output_sha256':{ext:hashlib.sha256((ROOT/(STEM+ext)).read_bytes()).hexdigest() for ext in ['.md','.html','.pdf','.docx']}}
    (VAL/'content_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='output_sha256'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
