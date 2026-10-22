"""Recover visible PDF content by coordinates; change presentation only."""
from pathlib import Path
from collections import Counter
import bisect, hashlib, json, re
import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
VAL = Path(__file__).resolve().parent
SOURCE = ROOT/'分析报告_Phase2_中文新版_insight_v2_修改版.pdf'
STEM = '分析报告_Phase2_中文新版_insight_v2_修改版_排版优化'
NORM = lambda s: re.sub(r'\s+', '', s)

def join(a,b):
    if not a:return b
    if not b:return a
    sep=' ' if re.search(r'[A-Za-z0-9.,;:!?\]\)]$',a) and re.match(r'[A-Za-z]',b) else ''
    return a+sep+b

def records_text(records):
    return ''.join(c['c'] for c in sorted(records,key=lambda c:(round(c['y']/2.7),c['x'])))

def make_lines(records):
    groups=[]
    for c in sorted(records,key=lambda c:(c['y'],c['x'])):
        if not groups or abs(c['y']-groups[-1]['y'])>2.7:
            groups.append({'y':c['y'],'chars':[c]})
        else:groups[-1]['chars'].append(c)
    for g in groups:
        g['chars'].sort(key=lambda c:c['x'])
        g['text']=''.join(c['c'] for c in g['chars']).strip()
        g['x']=min(c['x'] for c in g['chars'])
        g['top']=min(c['box'][1] for c in g['chars'])
        g['bottom']=max(c['box'][3] for c in g['chars'])
    return groups

def plain(records):
    result=''
    for line in make_lines(records):result=join(result,line['text'])
    return result

# Page number, top/header/body/bottom rules, column anchors. Split tables share a key.
SPECS=[
('rq',1,656.3,676.3,767.6,[65.2,182.9,300.6,418.3]),
('sources',2,277.2,297.2,359.9,[65.2,222.2,379.1]),
('cleaning',2,408.8,428.8,577.0,[65.2,222.2,379.1]),
('variables',2,701.9,721.9,780,[65.2,222.2,379.1]),
('variables',3,65.5,85.5,176.8,[65.2,222.2,379.1]),
('features',5,721.0,741.0,780,[181.3,244.6,279.2,328.1]),
('features',6,65.5,85.5,119.8,[181.3,244.6,279.2,328.1]),
('topic_weights',8,502.9,522.9,600.0,[202.2,258.3,321.5]),
('language',10,256.5,276.5,339.2,[65.2,159.4,253.5,347.7,441.9]),
('direct_replies',10,520.6,550.9,585.1,[65.2,159.4,253.5,347.7,441.9]),
('networks',11,291.3,311.3,416.7,[65.2,182.9,300.6,418.3]),
('accounts',12,623.9,643.8,735.1,[65.2,159.4,253.5,347.7,441.9]),
('windows',13,512.9,532.9,567.2,[65.2,143.7,222.2,300.7,379.2,457.7]),
('suggestions',15,164.3,184.3,332.5,[65.2,182.9,300.6,418.3]),
('coefficients',16,266.7,286.7,363.7,[148.6,224.4,253.6,295.4,365.2,401.6]),
('sensitivity',16,525.6,545.6,608.3,[187.7,250.8,278.2,307.4,377.2]),
('topic_model',17,107.3,137.6,214.6,[65.2,132.5,199.8,267.0,334.3,401.6,468.9]),
('media',17,728.7,748.6,780,[214.1,248.7,276.2,310.8,345.4]),
('media',18,65.5,85.5,119.8,[214.1,248.7,276.2,310.8,345.4]),
('members',18,175.2,195.2,258.0,[189.8,259.5,361.6])]

def main():
    doc=fitz.open(SOURCE); pages=[]; allchars=[]; removed=[]
    for pi,p in enumerate(doc):
        chars=[]
        for bi,b in enumerate(p.get_text('rawdict')['blocks']):
            if b['type']!=0:continue
            for li,l in enumerate(b['lines']):
                for si,s in enumerate(l['spans']):
                    for ci,c in enumerate(s['chars']):
                        x,y=c['origin']
                        item={'id':f'{pi+1}:{bi}:{li}:{si}:{ci}','c':c['c'],'x':x,'y':y,'box':list(c['bbox'])}
                        if c['bbox'][1]>=790:removed.append(item)
                        else:chars.append(item);allchars.append(item)
        pages.append(chars)
    used=set(); blocks=[]; tables={}; duplicate_headers=[]
    for key,pn,top,mid,bottom,cols in SPECS:
        candidates=[c for c in pages[pn-1] if top<c['box'][1]<bottom and cols[0]-6<c['x']<535]
        header=[c for c in candidates if c['box'][1]<mid]
        data=[c for c in candidates if c['box'][1]>=mid]
        edges=[x-2 for x in cols[1:]]
        headers=[plain([c for c in header if bisect.bisect_right(edges,c['x']+0.1)==i]) for i in range(len(cols))]
        starts=[]
        for line in make_lines([c for c in data if c['x']<cols[1]-2]):
            if abs(line['x']-cols[0])<7:starts.append(line['top'])
        if not starts:raise RuntimeError(('No rows',key,pn))
        rows=[]; cells=[]
        for ri,start in enumerate(starts):
            end=starts[ri+1]-2 if ri+1<len(starts) else bottom
            chunk=[c for c in data if start-2<=c['box'][1]<end]
            row=[]
            for i in range(len(cols)):
                cc=[c for c in chunk if bisect.bisect_right(edges,c['x']+0.1)==i]
                row.append(plain(cc));cells.append({'row':ri,'col':i,'ids':[c['id'] for c in cc]})
            rows.append(row)
        for c in candidates:
            if c['id'] in used:raise RuntimeError(('Double used',key,c['id']))
            used.add(c['id'])
        if key not in tables:
            table={'kind':'table','key':key,'page':pn,'y':top,'headers':headers,'rows':rows,'ids':[c['id'] for c in candidates],'fragments':[pn], 'cell_sources':cells, 'header_sources':[[c['id'] for c in header if bisect.bisect_right(edges,c['x']+0.1)==i] for i in range(len(cols))]}
            tables[key]=table;blocks.append(table)
        else:
            table=tables[key]
            if [NORM(x) for x in table['headers']] != [NORM(x) for x in headers]:raise RuntimeError(('Repeated header mismatch',key,headers))
            offset=len(table['rows'])
            for cell in cells:cell['row']+=offset
            table['cell_sources']+=cells
            table['rows']+=rows;table['ids'] +=[c['id'] for c in data];table['fragments'].append(pn)
            duplicate_headers +=header
    # Original figure pixels match the repository PNGs; reuse the matched originals.
    known={}
    for p in (ROOT/'figures').glob('*.png'):
        im=Image.open(p).convert('RGB');known[(im.size,hashlib.sha256(im.tobytes()).hexdigest())]=str(p.relative_to(ROOT))
    figure_number=0
    for pn,p in enumerate(doc,1):
        for im in p.get_image_info(xrefs=True):
            pix=fitz.Pixmap(doc,im['xref'])
            if pix.colorspace.n!=3:pix=fitz.Pixmap(fitz.csRGB,pix)
            if pix.alpha:pix=fitz.Pixmap(pix,0)
            match=known[((pix.width,pix.height),hashlib.sha256(pix.samples).hexdigest())]
            figure_number+=1
            blocks.append({'kind':'figure','page':pn,'y':im['bbox'][1],'path':match,'number':figure_number,'ids':[]})
        for line in make_lines([c for c in pages[pn-1] if c['id'] not in used]):
            blocks.append({'kind':'line','page':pn,'y':line['top'],'bottom':line['bottom'],'text':line['text'],'ids':[c['id'] for c in line['chars']]})
    blocks.sort(key=lambda b:(b['page'],b['y']))
    # Rejoin paragraph lines in visual reading order. Paragraph breaks are presentation only.
    out=[]
    in_references=False
    for b in blocks:
        if b['kind']!='line':out.append(b);continue
        text=b['text']
        if not text:continue
        if text.startswith('Keep') and not out:kind='title'
        elif re.match(r'^(?:\d+\.\s|附录[A-Z]|参考文献$)',text):kind='chapter'
        elif re.match(r'^(?:\d+\.\d+(?:\s|(?=[\u4e00-\u9fff]))|A\.\d+\s)',text):kind='section'
        elif text=='【摘要】':kind='abstract_label'
        else:kind='paragraph'
        b['kind']=kind
        if kind=='chapter' and text=='参考文献':in_references=True
        can_join=False
        if kind=='paragraph' and out and out[-1]['kind']=='paragraph':
            prev=out[-1];samepage=prev['page']==b['page']
            gap=b['y']-prev['bottom'] if samepage else 0
            starts_bullet=text.startswith('•');prev_bullet=prev['text'].startswith('•')
            if not starts_bullet:
                can_join=(samepage and gap<10) or not re.search(r'[。！？：；.!?]$',prev['text'])
                if in_references and re.match(r'^\[\d+\]',text):can_join=False
        if can_join:
            prev=out[-1];prev['text']=join(prev['text'],text);prev['ids']+=b['ids'];prev['bottom']=b['bottom'];prev['page']=b['page']
        else:out.append(b)
    # Caption text remains adjacent to its original image; table fragmentation is layout only.
    md=[]
    references=False
    byid={c['id']:c for c in allchars}
    for b in out:
        if b.get('text')=='参考文献':references=True
        k=b['kind']
        if k=='table':
            esc=lambda t:t.replace('|','\\|')
            md.append('| '+' | '.join(esc(t) for t in b['headers'])+' |\n| '+' | '.join('---' for _ in b['headers'])+' |\n'+'\n'.join('| '+' | '.join(esc(t) for t in row)+' |' for row in b['rows']))
        elif k=='figure':md.append(f'![图{b["number"]}]({b["path"]})')
        else:
            prefix={'title':'# ','chapter':'## ','section':'### ','abstract_label':''}.get(k,'')
            text=b['text']
            if k=='section':text=re.sub(r'^(\d+\.\d+)(?=[\u4e00-\u9fff])',r'\1 ',text)
            if references and k=='paragraph':
                source_lines=make_lines([byid[i] for i in b['ids']])
                text='<br>\n'.join(line['text'] for line in source_lines)
            if k=='abstract_label':text='**'+text+'**'
            md.append(prefix+text)
    output=ROOT/(STEM+'.md');output.write_text('\n\n'.join(md)+'\n')
    source_chars=Counter(NORM(''.join(c['c'] for c in allchars)))
    expected=source_chars-Counter(NORM(''.join(c['c'] for c in duplicate_headers)))
    actual=Counter()
    for b in out:
        if b['kind']=='table':actual.update(NORM(''.join(b['headers'])+''.join(''.join(row) for row in b['rows'])))
        elif b['kind']!='figure':actual.update(NORM(b['text']))
    flat_ids=[]
    for b in out:
        if b['kind']=='table':
            selected=[i for cell in b['header_sources'] for i in cell]+[i for cell in b['cell_sources'] for i in cell['ids']]
            if set(selected)!=set(b['ids']) or len(selected)!=len(set(selected)):
                raise RuntimeError(('Cell source coverage',b['key']))
            flat_ids+=selected
        else:flat_ids+=b['ids']
    expected_ids={c['id'] for c in allchars}-{c['id'] for c in duplicate_headers}
    if set(flat_ids)!=expected_ids or len(flat_ids)!=len(set(flat_ids)):
        raise RuntimeError('Source character IDs are not covered exactly once')
    coverage={'source_character_ids_covered_once':len(flat_ids),'source_pdf':SOURCE.name,'source_pdf_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'source_commit':'b6c31d20fbe59b096de568e8b6cd93aa395283bb','output_markdown':output.name,'body_characters':sum(expected.values()),'duplicate_table_header_characters':sum(Counter(NORM(''.join(c['c'] for c in duplicate_headers))).values()),'missing_characters':dict(expected-actual),'extra_characters':dict(actual-expected),'figures':figure_number,'tables':len(tables),'excluded_layout':'Original running page numbers and repeated table headers; whitespace reflow.'}
    (VAL/'extraction_checks.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    (VAL/'content_blocks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(coverage,ensure_ascii=False,indent=2))
    print('TABLES:')
    for key,t in tables.items():print(key, t['headers'],t['rows'])
    if expected!=actual:raise RuntimeError('Character coverage differs; inspect extraction_checks.json')
if __name__=='__main__':main()
