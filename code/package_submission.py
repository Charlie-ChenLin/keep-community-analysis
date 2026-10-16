"""Build the assignment ZIP from an explicit, portable allowlist."""
from pathlib import Path
import hashlib
import json
import zipfile
import nbformat
import pymupdf as fitz
from pptx import Presentation
from docx import Document

ROOT=Path(__file__).resolve().parents[1]

def evaluation_template():
    if (ROOT/'互评报告模板.docx').exists():return
    d=Document();d.add_heading('小组成员工作分工互评报告（空白模板）',0)
    d.add_paragraph('组号：【待填写】　评价人：【待填写姓名/学号】\n研究题目：什么样的健身分享更容易获得点赞？')
    d.add_paragraph('请各成员依据真实工作独立填写。本文件仅为模板，未完成任何实际评价；建议分工不等于实际贡献。')
    t=d.add_table(rows=1,cols=5);t.style='Light Shading Accent 1'
    for c,s in zip(t.rows[0].cells,['成员','实际完成内容','具体文件/工作证据','协作情况','总体评价（按课程标准）']):c.text=s
    for _ in range(4):
        for c in t.add_row().cells:c.text='【待填写】'
    d.add_heading('本人实际贡献',1);d.add_paragraph('【请据实填写负责的分析、资料、代码、修改、汇报等，以及相应文件和完成情况】')
    d.add_heading('协作与分工说明',1);d.add_paragraph('【说明讨论、整合、检查和修改情况。不要把建议分工直接当作已完成的分工。】')
    d.add_paragraph('日期：【待填写】')
    d.save(ROOT/'互评报告模板.docx')


def main():
    evaluation_template()
    nb=nbformat.read(ROOT/'分析过程.ipynb',4);nbformat.validate(nb)
    cells=[c for c in nb.cells if c.cell_type=='code']
    assert all(c.execution_count is not None for c in cells)
    assert not any(o.output_type=='error' for c in cells for o in c.outputs)
    assert len(fitz.open(ROOT/'分析报告.pdf'))==20
    assert len(Presentation(ROOT/'演示文稿.pptx').slides)==16
    checks=json.loads((ROOT/'validation/numerical_checks.json').read_text());assert all(c['passed'] for c in checks)
    geometry=json.loads((ROOT/'validation/report_geometry.json').read_text());assert not geometry['overflow']
    files=[]
    for name in ['README.md','requirements.txt','分析报告.pdf','分析报告.html','分析报告_可编辑.docx','演示文稿.pptx','汇报讲稿.txt','分析过程.ipynb','分析过程.html','互评报告模板.docx','小组项目作业.pdf']:
        p=ROOT/name;assert p.exists(),p;files.append((p,name))
    # Optional presentation PDF only if it matches the current slide count.
    p=ROOT/'演示文稿.pdf'
    if p.exists():
        assert len(fitz.open(p))==16
        assert p.stat().st_mtime >= (ROOT/'演示文稿.pptx').stat().st_mtime, 'Re-export the updated PPTX before packaging.'
        files.append((p,p.name))
    for folder,exts in [('code',{'.py','.json','.txt','.applescript'}),('results',{'.csv','.json','.log'}),('figures',{'.png'}),('validation',{'.json','.log','.png'})]:
        for p in sorted((ROOT/folder).iterdir()):
            if p.is_file() and p.suffix in exts and p.name!='submission_manifest.json':files.append((p,str(p.relative_to(ROOT))))
    for name in ['sample_post_2022.csv','sample_comment_2022.csv']:
        p=ROOT/'2026Data/Keep Data'/name;files.append((p,str(p.relative_to(ROOT))))
    p=ROOT/'2026Data/KeepData_dictionary.pdf';files.append((p,str(p.relative_to(ROOT))))
    for name in ['内容分析与自然语言处理.pdf','社交网络分析简介.pdf','Social Network Influencial.pdf']:
        candidates=[ROOT/'references'/name,ROOT.parents[1]/'materials'/name]
        p=next(p for p in candidates if p.exists());files.append((p,'references/'+name))
    manifest=[{'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p,name in files]
    (ROOT/'validation/submission_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    # Manifest is not self-hashed, avoiding a circular dependency.
    files=[(p,n) for p,n in files if n!='validation/submission_manifest.json']
    files.append((ROOT/'validation/submission_manifest.json','validation/submission_manifest.json'))
    target=ROOT/'第【待填写】组-社交媒体分析报告.zip'
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p,name in files:z.write(p,name)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(set(z.namelist()))
        assert all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist())
        print('ZIP:',target.name,'entries:',len(z.namelist()),'bytes:',target.stat().st_size)

if __name__=='__main__':main()
