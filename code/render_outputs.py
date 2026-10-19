"""Render the canonical academic HTML to PDF and inspect its page geometry."""
from pathlib import Path
import asyncio
import json
import os
import shutil
import pymupdf as fitz
from PIL import Image, ImageDraw
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]

async def render():
    chrome=os.environ.get('CHROME_PATH') or shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome and Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome').is_file():
        chrome='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    async with async_playwright() as pw:
        launch_options={'headless':True}
        if chrome:launch_options['executable_path']=chrome
        browser=await pw.chromium.launch(**launch_options)
        page=await browser.new_page(viewport={'width':1100,'height':1200},device_scale_factor=1)
        await page.goto((ROOT/'分析报告.html').as_uri(),wait_until='networkidle')
        await page.evaluate('document.fonts.ready')
        geometry=await page.evaluate('''() => [...document.querySelectorAll('.page')].map(s=>({id:s.id,height:s.clientHeight,scrollHeight:s.scrollHeight,mainBottom:s.querySelector('main').getBoundingClientRect().bottom-s.getBoundingClientRect().top,footerTop:s.querySelector('footer').getBoundingClientRect().top-s.getBoundingClientRect().top}))''')
        bad=[r for r in geometry if r['mainBottom']>r['footerTop']-12 or r['scrollHeight']>r['height']+2]
        (ROOT/'validation/report_geometry.json').write_text(json.dumps({'pages':geometry,'overflow':bad},ensure_ascii=False,indent=2))
        if bad:raise ValueError('Report content overlaps footer: '+str(bad))
        await page.pdf(path=str(ROOT/'分析报告.pdf'),print_background=True,prefer_css_page_size=True)
        await page.locator('#page-1').screenshot(path=str(ROOT/'validation/report_cover.png'))
        manifest=json.loads((ROOT/'results/report_manifest.json').read_text())
        for index,physical in enumerate(manifest['toc_pages'],1):
            name='report_toc.png' if index==1 else f'report_toc_{index}.png'
            await page.locator(f'#page-{physical}').screenshot(path=str(ROOT/'validation'/name))
        for chapter in manifest['chapters']:
            await page.locator(f'#page-{chapter["page"]}').screenshot(
                path=str(ROOT/f'validation/report_chapter_{chapter["number"]}.png'))
        # A readable notebook HTML is for inspection and portable review, not a second report.
        await browser.close()
    doc=fitz.open(ROOT/'分析报告.pdf')
    expected=manifest['pages']
    assert len(doc)==expected,(len(doc),expected)
    entries=manifest['contents'];pdf_links=[]
    for physical in manifest['toc_pages']:pdf_links.extend(doc[physical-1].get_links())
    assert len(pdf_links)==len(entries),(len(pdf_links),len(entries))
    for entry,link in zip(entries,pdf_links):
        assert link['page']==entry['page']-1,(entry,link)
        assert link['nameddest']==entry['anchor'],(entry,link)
        target=''.join(doc[entry['page']-1].get_text().split())
        assert ''.join(entry['title'].split()) in target,entry
    doc.set_toc([[e['level'],f'{e["section"]} {e["title"]}'.strip(),e['page']] for e in entries])
    doc.saveIncr()
    (ROOT/'validation/report_toc_checks.json').write_text(json.dumps({
        'scope':'Seven-chapter structure, contents links and rendered report layout.',
        'report_pages':len(doc),'chapters':len(manifest['chapters']),
        'subsections':sum(len(c['subsections']) for c in manifest['chapters']),
        'toc_pages':manifest['toc_pages'],'toc_entries':len(entries),
        'pdf_link_targets_verified':len(pdf_links),'pdf_target_headings_verified':len(entries),
        'pdf_outline_entries':len(doc.get_toc()),'report_geometry_no_overflow':not bad,
    },ensure_ascii=False,indent=2)+'\n')
    previews=[]
    for i,p in enumerate(doc):
        assert p.get_text().strip(),'Empty PDF page'
        pix=p.get_pixmap(matrix=fitz.Matrix(.65,.65),alpha=False)
        im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
        im.thumbnail((310,440));previews.append(im)
    cols=4;cw=330;ch=470
    contact=Image.new('RGB',(cols*cw,((len(previews)+cols-1)//cols)*ch),'#dce3e8')
    draw=ImageDraw.Draw(contact)
    for i,im in enumerate(previews):
        x=(i%cols)*cw+10;y=(i//cols)*ch+22;contact.paste(im,(x,y));draw.text((x,y-16),f'Page {i+1}',fill='#243746')
    contact.save(ROOT/'validation/report_contact.png')
    print('Rendered and geometrically verified',len(doc),'report pages.')

if __name__=='__main__':asyncio.run(render())
