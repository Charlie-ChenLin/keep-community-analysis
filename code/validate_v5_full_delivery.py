#!/usr/bin/env python3
"""Verify editable delivery, references, headline counts and bounded privacy."""
from pathlib import Path
import hashlib, importlib.util, json, re, zipfile
from bs4 import BeautifulSoup
from docx import Document

ROOT=Path(__file__).resolve().parents[1]
STEM='分析报告_正文多维测量全量版_v5_可编辑'
RUN=ROOT/'validation/classification_rebuild/private/variable_scheme_v5_production'
PUBLIC_RESULTS=['v5_full_coding_summary.json','v5_full_analysis.json','v5_full_measurement_comparison.json',
 'v5_full_additional_ai_review.json','v5_full_independent_audit.json']
def js(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    md=(ROOT/f'{STEM}.md').read_text();html=(ROOT/f'{STEM}.html').read_text();soup=BeautifulSoup(html,'html.parser')
    doc=Document(ROOT/f'{STEM}.docx')
    body='\n'.join([p.text for p in doc.paragraphs]+[cell.text for t in doc.tables for row in t.rows for cell in row.cells])
    summary=js(ROOT/'results/v5_full_coding_summary.json');analysis=js(ROOT/'results/v5_full_analysis.json')
    expected=[summary['n_unique_texts'],summary['n_nonempty_posts'],analysis['main']['n'],summary['post_coverage']['axes']['expression']['any_positive']]
    for n in expected:
        if f'{n:,}' not in md or f'{n:,}' not in body:raise ValueError('Missing headline count in editable report')
    h2=soup.select('section.chapter > h2');images=soup.find_all('img');missing=[]
    for a in soup.find_all('a',href=True):
        href=a['href']
        if not href.startswith(('http://','https://','#','mailto:')) and not (ROOT/href).exists():missing.append(href)
    for img in images:
        if not (ROOT/img['src']).is_file():missing.append(img['src'])
    if missing:raise ValueError('Missing report target: '+str(missing))
    if len(h2)!=7 or len(images)!=3 or len(doc.inline_shapes)!=3 or len(doc.tables)<10:raise ValueError('Incomplete report structure')
    rows=sum(len(t.rows) for t in doc.tables)
    paragraphs='\n'.join(p.text for p in doc.paragraphs)
    if paragraphs.count('回归使用连续主题权重')!=1 or '独立人工语义复核为0' not in body:raise ValueError('Required measurement/method clarification absent')
    privacy_texts={f'{STEM}.md':md,f'{STEM}.html':soup.get_text(),f'{STEM}.docx':body}
    for name in PUBLIC_RESULTS:privacy_texts['results/'+name]=(ROOT/'results'/name).read_text()
    source=[]
    for p in (RUN/'inputs').glob('batch_*.jsonl'):
        source.extend(json.loads(x)['text'] for x in p.read_text().splitlines() if x.strip())
    leaks=[]
    for name,content in privacy_texts.items():
        if re.search(r'V5[PR]\d{4,6}',content):leaks.append({'file':name,'kind':'private_annotation_id'})
        # Bounded check: exact full original texts of >=12 characters only.
        # This cannot certify absence of all possible paraphrase/fragment leaks.
        matches=sum(bool(text and len(text)>=12 and text in content) for text in source)
        if matches:leaks.append({'file':name,'kind':'full_source_text_at_least_12_chars','count':matches})
    if leaks:raise ValueError('Privacy inspection required: '+str(leaks))
    result={'status':'passed_content_structure_links_and_bounded_privacy_checks','n_chapters':len(h2),'n_editable_word_tables':len(doc.tables),
      'n_editable_table_rows':rows,'n_figures':len(images),'n_word_embedded_figures':len(doc.inline_shapes),
      'headline_counts_match_aggregates':True,'relative_report_targets_exist':True,
      'private_annotation_ids_found':False,'full_source_texts_at_least_12_characters_found':False,
      'privacy_scope':'New report MD/HTML/extracted DOCX paragraphs+tables and five full-v5 public result JSONs. Exact full-text matches >=12 characters and annotation-ID pattern only; not a general privacy certification.',
      'native_word_pagination_rendered':False,'visual_validation':'PNG figures inspected separately. Native Word pagination not rendered in this environment.',
      'artifact_sha256':{f'{STEM}.{ext}':sha(ROOT/f'{STEM}.{ext}') for ext in ['md','html','docx']}}
    out=ROOT/'validation/variable_scheme_v5/full_run_delivery_checks.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
