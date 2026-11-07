"""Check actual PPTX geometry and create clearly labelled approximate previews.

No source-deck screenshots or old PDF crops are used. Charts are independently
drawn from the new package's actual series, and all shapes come from the new
PPTX. This is a QA aid, not a PowerPoint render or a presentation PDF export.
"""
from io import BytesIO
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import re
import subprocess
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import pymupdf as fitz
from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.enum.chart import XL_CHART_TYPE
from pptx.enum.text import PP_ALIGN

QA=Path(__file__).resolve().parent
ROOT=QA.parents[1]
DECK=ROOT/'Keep社区帖子特征与互动反馈_正式修订版.pptx'
SOURCE=ROOT/'Keep社区内容表达与互动反馈_老师意见修订版.pptx'
FONT_PATH=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
FONT=FontProperties(fname=str(FONT_PATH))
EMU=914400
spec=importlib.util.spec_from_file_location('geometry_helpers',ROOT/'validation/revision_delivery/check_slide_layout.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)


def pt(x):return float(x)*72/EMU


def rgba(fill,default=None):
    try:
        value=fill.fore_color.rgb
        return tuple(x/255 for x in value)
    except (AttributeError,TypeError):return default


def text_color(frame):
    for p in frame.paragraphs:
        for r in p.runs:
            try:return tuple(x/255 for x in r.font.color.rgb)
            except (AttributeError,TypeError):pass
    return (.12,.20,.18)


def xvalues(series):
    return [float(e.text)for e in series._element.xpath('./c:xVal//c:pt/c:v')]


def draw_text(page,unit,color):
    ox,oy=unit['draw_origin_pt'];aw=unit['available_width_pt']
    for p in unit['draw_lines']:
        for i,(line,width)in enumerate(zip(p['lines'],p['widths'])):
            x=ox
            if p['alignment']=='CENTER (2)':x+=max(0,(aw-width)/2)
            elif p['alignment']=='RIGHT (3)':x+=max(0,aw-width)
            page.insert_text((x,oy+p['offset_y']+p['size']+i*p['advance']),line,
                             fontname='audit_unicode',fontfile=str(FONT_PATH),fontsize=p['size'],color=color)


def chart_image(chart,w,h):
    """Render new-deck series as an approximation, with no screenshot reuse."""
    fig,ax=plt.subplots(figsize=(w/72,h/72),dpi=125)
    colors=['#245C4F','#AFBCB5','#B97339','#7DA095','#20332F']
    if chart.chart_type==XL_CHART_TYPE.XY_SCATTER:
        for i,series in enumerate(chart.series):
            ax.plot(xvalues(series),list(series.values),marker='o',markersize=3,
                    linewidth=.8,color=colors[i%len(colors)])
        ax.axvline(0,color='#AAB8B0',linewidth=.6)
    else:
        cats=[c.label for c in chart.plots[0].categories]
        n=len(cats);k=len(chart.series);width=.72/max(k,1)
        horizontal=chart.chart_type==XL_CHART_TYPE.BAR_CLUSTERED
        for i,series in enumerate(chart.series):
            loc=[j+(i-(k-1)/2)*width for j in range(n)]
            if horizontal:
                bars=ax.barh(loc,list(series.values),height=width,color=colors[i%len(colors)])
            else:bars=ax.bar(loc,list(series.values),width=width,color=colors[i%len(colors)])
            for b,v in zip(bars,series.values):
                label=f'{v:.1f}' if abs(v-round(v))>1e-6 else f'{v:,.0f}'
                if horizontal:ax.text(v,b.get_y()+b.get_height()/2,label,ha='left',va='center',fontsize=7)
                else:ax.text(b.get_x()+b.get_width()/2,v,label,ha='center',va='bottom',fontsize=7)
        if horizontal:
            ax.set_yticks(range(n),cats,fontproperties=FONT,fontsize=8);ax.invert_yaxis()
            ax.margins(x=.20)
        else:
            ax.set_xticks(range(n),cats,fontproperties=FONT,fontsize=7.5)
            ax.margins(y=.22)
        if k>1:
            ax.legend([s.name for s in chart.series],prop=FontProperties(fname=str(FONT_PATH),size=7),frameon=False,loc='upper right')
    ax.spines[['top','right','left']].set_visible(False)
    ax.spines['bottom'].set_color('#DFE6E2');ax.grid(axis='x'if chart.chart_type==XL_CHART_TYPE.BAR_CLUSTERED else 'y',alpha=.15)
    ax.set_axisbelow(True);ax.tick_params(length=0,labelsize=7,colors='#65756F')
    fig.tight_layout(pad=.8)
    buf=BytesIO();fig.savefig(buf,format='png',facecolor='white');plt.close(fig)
    return buf.getvalue()


def compare_series(source,new,mapping):
    result=[]
    for row in mapping:
        old=source.slides[row['source_teacher_page']-1];newslide=new.slides[row['new_page']-1]
        aa=[s.chart for s in old.shapes if s.has_chart];bb=[s.chart for s in newslide.shapes if s.has_chart]
        # The new measurement-boundary slide intentionally removes its old chart.
        if row['source_teacher_page']==6:continue
        assert len(aa)==len(bb),(row,len(aa),len(bb))
        for a,b in zip(aa,bb):
            assert len(a.series)==len(b.series)
            for x,y in zip(a.series,b.series):
                assert list(x.values)==list(y.values)
                if a.chart_type==XL_CHART_TYPE.XY_SCATTER:assert xvalues(x)==xvalues(y)
            result.append({'page':row['new_page'],'series_values_unchanged':True,'series':len(b.series)})
    return result


def main():
    pres=Presentation(DECK);source=Presentation(SOURCE)
    sw,sh=pt(pres.slide_width),pt(pres.slide_height)
    records=[];issues=[];overlaps=[];bounds=[];preview=fitz.open();native_count=0
    for no,slide in enumerate(pres.slides,1):
        pg=preview.new_page(width=sw,height=sh)
        bg=rgba(slide.background.fill,(1,1,1));pg.draw_rect(pg.rect,fill=bg,color=None)
        units=[]
        for shape in slide.shapes:
            x,y,w,h=map(pt,[shape.left,shape.top,shape.width,shape.height]);box=fitz.Rect(x,y,x+w,y+h)
            if x<-.1 or y<-.1 or x+w>sw+.1 or y+h>sh+.1:bounds.append({'page':no,'shape':shape.name,'bounds_pt':[x,y,w,h]})
            if shape.has_chart:
                native_count+=1
                pg.insert_image(box,stream=chart_image(shape.chart,w,h),keep_proportion=False)
            elif shape.shape_type==13:
                pg.insert_image(box,stream=shape.image.blob,keep_proportion=False)
            elif shape.has_table:
                cy=y
                for ri,row in enumerate(shape.table.rows):
                    cx=x
                    for ci,cell in enumerate(row.cells):
                        cw=pt(shape.table.columns[ci].width);rh=pt(row.height)
                        pg.draw_rect(fitz.Rect(cx,cy,cx+cw,cy+rh),fill=rgba(cell.fill,(1,1,1)),color=(1,1,1),width=.6)
                        if cell.text:
                            unit=helper.text_fit(cell.text_frame,[cx,cy,cw,rh],f'table:{shape.shape_id}/r{ri+1}c{ci+1}',True,cell)
                            unit['color']=text_color(cell.text_frame);units.append(unit)
                        cx+=cw
                    cy+=pt(row.height)
            else:
                color=rgba(shape.fill,None)if hasattr(shape,'fill')else None
                if color and w>0 and h>0:pg.draw_rect(box,fill=color,color=None)
            if shape.has_text_frame and shape.text:
                unit=helper.text_fit(shape.text_frame,[x,y,w,h],f'shape:{shape.shape_id}',True)
                unit['color']=text_color(shape.text_frame);units.append(unit)
        for unit in units:
            if unit['assessment']!='fits_estimate':issues.append({'page':no,**{k:v for k,v in unit.items()if k not in ['draw_lines','color']}})
            draw_text(pg,unit,unit['color'])
        for i,a in enumerate(units):
            for b in units[i+1:]:
                iw,ih=helper.intersect(a['ink_bounds_pt'],b['ink_bounds_pt'])
                if iw>2 and ih>2:overlaps.append({'page':no,'a':a['unit'],'b':b['unit'],'intersection_pt':[iw,ih],'a_text':a['text'],'b_text':b['text']})
        pg.insert_text((7,8),f'APPROXIMATE SHAPE/DATA PREVIEW - NOT OFFICE RENDER - PAGE {no:02d}',fontsize=5.5,color=(.75,.28,.12))
        pg.get_pixmap(matrix=fitz.Matrix(1.25,1.25),alpha=False).save(QA/f'approximate-slide-{no:02d}.png')
        records.append({'page':no,'text_units':[{k:v for k,v in u.items()if k not in ['draw_lines','color']}for u in units]})
    preview.save(QA/'approximate-shape-preview.pdf',garbage=4,deflate=True)
    ims=[]
    for n in range(1,len(pres.slides)+1):
        im=Image.open(QA/f'approximate-slide-{n:02d}.png');im.thumbnail((400,225));ims.append(im.copy())
    for start in range(0,len(ims),12):
        chunk=ims[start:start+12];contact=Image.new('RGB',(3*420,math.ceil(len(chunk)/3)*253),'#DDE5E0');draw=ImageDraw.Draw(contact)
        for i,im in enumerate(chunk):
            x=(i%3)*420+10;y=(i//3)*253+21;contact.paste(im,(x,y));draw.text((x,y-15),f'Page {start+i+1} (approximate)',fill='#173F36')
        contact.save(QA/f'approximate-contact-{start//12+1}.png')
    mapping=json.loads((QA/'page_mapping.json').read_text());series=compare_series(source,pres,mapping)
    manifest=json.loads((QA/'slides_manifest.json').read_text())
    text_dump='\n\n'.join(f'PAGE {m["page"]}｜{m["title"]}\n'+'\n'.join(x['text']for x in m['text'])+'\n'+'\n'.join(' | '.join(r)for t in m['tables']for r in t)for m in manifest)
    (QA/'actual_deck_text.txt').write_text(text_dump)
    forbidden=['自律 / 目标','社交 / 互助','积极表达','积极BH q','积极β']
    package_checks=[]
    with zipfile.ZipFile(DECK)as z:
        for name in z.namelist():
            if name.startswith('ppt/charts/')and name.endswith('.xml'):
                xml=z.read(name).decode();assert not any(x in xml for x in forbidden),(name,'stale cache')
                package_checks.append(name)
            if name.startswith('ppt/embeddings/')and name.endswith('.xlsx'):
                with zipfile.ZipFile(BytesIO(z.read(name)))as book:
                    for item in book.namelist():
                        if item.endswith('.xml'):assert not any(x in book.read(item).decode()for x in forbidden),(name,item,'stale workbook')
            if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',name):
                assert '本轮未进行人工语义复核'in z.read(name).decode()
    assert len(pres.slides)==28 and native_count==13
    assert all(s.has_notes_slide for s in pres.slides)
    assert not any(x in text_dump for x in ['TODO','lorem','00 / 00'])
    result={'deck':str(DECK),'deck_sha256':hashlib.sha256(DECK.read_bytes()).hexdigest(),
            'method':'New PPTX actual shape/text/table geometry and series values; approximate chart drawing. No old screenshots or source PDF crops.',
            'limitations':['Not a native Office render.','CJK wrapping, paragraph heights and chart layout are approximate.','All text units are measured, including inherited baseline.'],
            'slides':len(pres.slides),'native_charts':native_count,'chart_series_numerically_unchanged':series,
            'chart_caches_without_legacy_feature_labels':len(package_checks),'xlsx_labels_checked':True,'all_notes_present':True,
            'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            'shape_bounds_violations':bounds,'text_fit_candidates':issues,'ink_overlap_candidates':overlaps,'page_records':records}
    (QA/'layout_and_content_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k not in ['page_records','chart_series_numerically_unchanged']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
