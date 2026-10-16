"""Export saved notebook outputs as a portable static HTML without remote scripts."""
from pathlib import Path
import nbformat
from nbconvert import HTMLExporter
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]

def main():
    nb=nbformat.read(ROOT/'分析过程.ipynb',4)
    exporter=HTMLExporter(template_name='lab')
    body,_=exporter.from_notebook_node(nb)
    soup=BeautifulSoup(body,'html.parser')
    # No widgets, TeX or JS-driven charts are used. All figure outputs are embedded PNGs.
    for script in soup.find_all('script'):script.decompose()
    style=soup.new_tag('style')
    style.string='pre {white-space:pre-wrap!important;overflow-wrap:anywhere!important} .jp-InputArea-editor {overflow-x:auto} body {font-family:"PingFang SC","Microsoft YaHei",sans-serif}'
    soup.head.append(style)
    (ROOT/'分析过程.html').write_text(str(soup),encoding='utf-8')
    print('Exported static notebook HTML with embedded images and no remote scripts.')

if __name__=='__main__':main()
