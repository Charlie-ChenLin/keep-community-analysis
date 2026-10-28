"""Independently compare native point/interval caches and workbooks to source CSV."""
import csv
import io
import json
import posixpath
from pathlib import Path
import zipfile
from lxml import etree

ROOT=Path(__file__).resolve().parents[2]
QA=Path(__file__).resolve().parent
NS={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart','r':'http://schemas.openxmlformats.org/package/2006/relationships','x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
TERMS=[('self_discipline','自律 / 目标'),('social_address','社交 / 互助'),('positive_expression','积极表达')]
SPECS=[('M3_','主模型'),('R1_','仅可见正文'),('R2_','去最高1%'),('R3_','作者等权'),('R4_','PPML计数')]
rows=list(csv.DictReader((ROOT/'results/regression_coefficients.csv').open(encoding='utf-8-sig')))
checks=[]
with zipfile.ZipFile(ROOT/'Keep社区内容表达与互动反馈_12分钟合并版.pptx') as z:
    for name in z.namelist():
        if not name.startswith('ppt/charts/chart') or not name.endswith('.xml'):
            continue
        node=etree.fromstring(z.read(name))
        if node.find('.//c:scatterChart',NS) is None:
            continue
        series=node.findall('.//c:ser',NS)
        def tx(s): return ''.join(s.xpath('./c:tx//c:v/text()',namespaces=NS))
        match=next(((term,title) for term,title in TERMS if any(title+'（敏感性）' in tx(s) for s in series)),None)
        assert match,name
        term,title=match
        expected=[next(r for r in rows if r['model'].startswith(prefix) and r['term']==term) for prefix,_ in SPECS]
        point=next(s for s in series if title+'（敏感性）' in tx(s))
        def values(s,axis): return [float(x) for x in s.xpath('./c:'+axis+'//c:pt/c:v/text()',namespaces=NS)]
        assert all(abs(x-float(r['coef']))<1e-12 for x,r in zip(values(point,'xVal'),expected))
        assert values(point,'yVal')==[5,4,3,2,1]
        rel_name=name.replace('/charts/','/charts/_rels/')+'.rels'
        rel=etree.fromstring(z.read(rel_name))
        target=next(r.get('Target') for r in rel if r.get('Target','').endswith('.xlsx'))
        book_name=posixpath.normpath(posixpath.join(posixpath.dirname(name),target))
        with zipfile.ZipFile(io.BytesIO(z.read(book_name))) as book:
            sheet=etree.fromstring(book.read('xl/worksheets/sheet1.xml'))
            cells={c.get('r'):float(c.find('x:v',NS).text) for c in sheet.findall('.//x:c',NS) if c.find('x:v',NS) is not None and c.get('t')!='s'}
        for i,((prefix,label),row) in enumerate(zip(SPECS,expected)):
            interval=next(s for s in series if tx(s)==label+'95%区间')
            xv=values(interval,'xVal');yv=values(interval,'yVal')
            low,high=float(row['ci_low']),float(row['ci_high'])
            assert all(abs(a-b)<1e-12 for a,b in zip(xv,[low,low,low,high,high,high]))
            y=5-i
            assert all(abs(a-b)<1e-12 for a,b in zip(yv,[y-.08,y+.08,y,y,y-.08,y+.08]))
            for axis,cache in [('xVal',xv),('yVal',yv)]:
                formula=interval.find('c:'+axis+'/c:numRef/c:f',NS).text
                col=formula.split('!$')[1].split('$')[0]
                assert all(abs(cells[f'{col}{j+2}']-v)<1e-12 for j,v in enumerate(cache))
            checks.append({'term':term,'model':row['model'],'coef':float(row['coef']),'ci_low':low,'ci_high':high,'native_cache_and_workbook_match_source':True})
assert len(checks)==15
(QA/'sensitivity_numeric_checks.json').write_text(json.dumps({'checks':checks,'all_passed':True},ensure_ascii=False,indent=2))
print('15 coefficient points and 15 intervals match the original CSV and embedded worksheets.')
