"""Build a concise, source-backed change note for the revised report and deck."""
from pathlib import Path
import hashlib
import json
import re

import markdown
import pymupdf as fitz

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / 'validation/revision_delivery'
STEM = '修订说明_新增分析与结论变化'


def load(name):
    return json.loads((ROOT/'results'/name).read_text())


def table(headers, rows):
    clean=lambda x:str(x).replace('|','／').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(map(clean,headers))+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(clean,row))+' |'for row in rows])


def main():
    QA.mkdir(parents=True,exist_ok=True)
    d=load('teacher_feedback_dictionary.json')
    body=load('teacher_complete_body_model.json')['models']
    a=load('teacher_author_tags_summary.json')
    t=load('teacher_topic_summary.json')
    coverage=load('teacher_label_coverage_summary.json')
    files=['分析报告_老师意见修订版.md','分析报告_老师意见修订版.pdf','分析报告_老师意见修订版.docx','Keep社区内容表达与互动反馈_老师意见修订版.pptx','Keep社区内容表达与互动反馈_老师意见修订版_逐页讲稿.txt']
    available=[x for x in files if (ROOT/x).is_file()]
    assert all((ROOT/x).is_file()for x in files[:4]), 'Build the revised report and slides first.'
    main_models={x['model']:x for x in a['model_fit']}
    md='''# 本次修订了什么，增加了哪些分析

基于老师反馈与2026年10月29日方法复核，已将结果落实到完整报告与汇报稿。旧版原件、数据和冻结模型保留，修订版另存。

## 一、结论和解释作了五项调整

'''
    md+=table(['原来的表达风险','修订后的处理'],[
        ['四类词典容易被当成四种内容类型','改为三类词汇规则＋问号标记；补分类理由、覆盖与语义边界，允许同帖多项命中。'],
        ['五个NMF名称容易被当成完整真实主题分类','改为探索性文本成分；原52.7%和35.8%仅保留为主导成分份额，不再据此推定真实内容分类占比。'],
        ['原M3不显著容易被概括为文字关联始终不显著','并列三种正文口径，明确证据对正文可观测范围敏感；旧M3是历史对照，修订分析限定于可观察正文，不按显著性挑模型。'],
        ['仅根据拟合度和系数方向解释原因','删去未经检验的“积极表达反转集中在生活问候”推断；不由R²/p值给作者、媒体和措辞做因果贡献排名。'],
        ['作者数、平台tag、主导主题与真实语义易混淆','主模型与主题子样本分别检查作者支持；区分原始tag、连续权重、argmax描述和探索性多标签。'],
    ])
    md+='''

## 二、纳入正式稿的七组新增分析

'''
    md+=table(['新增分析','关键结果及其作用'],[
        ['1. 词典覆盖、共现与共线性',f'完整M3四变量VIF为{d["summary"]["min_vif_full_main_model"]:.2f}—{d["summary"]["max_vif_full_main_model"]:.2f}；最大两两φ相关约0.119。非空正文中{coverage["dictionary_no_hit_nonempty"]:,}／{coverage["nonempty_clean_body"]:,}帖未命中任一规则，说明词典只覆盖部分表达，低VIF不能证明语义有效。'],
        ['2. 正文可观测口径对照','比较9,532帖全样本、5,548帖原始正文可见、5,414帖清理后非空；补联合检验、系数、区间和各模型内BH。缺失标记不被当作已恢复真实正文。'],
        ['3. 作者固定效应的支持范围','全样本2位单帖作者，主题子样本10位；补作者发帖分布、各变量作者内变化及作者门槛回归。主题样本保留至少10帖作者后为2,309帖／48人，不能仍称86人充分支持每项比较。'],
        ['4. 原始话题标签敏感性',f'原模型已经控制has_tag；新增9个频繁、跨作者tag身份控制（五项联合p={main_models["body_tag_identity_controls"]["joint_five_p"]:.3f}），以及正文＋tag重新编码（p={main_models["body_plus_tags_recoded"]["joint_five_p"]:.3f}）。拼接后自律命中877→3,342，显示测量范围改变。'],
        ['5. 非互斥0—1多标签诊断','保留冻结NMF连续权重，另按0.15／0.20／0.25阈值作探索性标记。0.20下1,088／2,470帖多标记；五项同入模满秩，联合p≈0.286。阈值标记不等于已经修复真实语义分类。'],
        ['6. 分类覆盖与语义反例筛查','对原主导成分各抽12帖，共60帖，另抽20条非空但未入模正文。单轮AI辅助筛查发现12条不支持指定名称、6条仅部分支持。此诊断不估计全样本错误率，也不能证明多数帖都在五类之外。'],
        ['7. 主题结构对拟合选择的依赖','比较K=3—8、完全重复正文删重与作者等权拟合目标。在冻结词表／IDF下，删重后原静蹲成分不再单列，出现包含早餐、咖啡等词的成分；说明模板和作者构成需要纳入诊断。'],
    ])
    md+='''

## 三、最需要记住的结论变化

'''
    rows=[]
    for label,x in zip(['全样本＋正文缺失标记','原始正文可见','清理后正文非空'],body):
        q=next(z['q_bh']for z in x['terms']if z['term']=='positive_expression')
        rows.append([label,f'{x["n"]:,}／{x["authors"]}',f'{x["joint_five_p"]:.3f}',f'{q:.3f}'])
    md+=table(['正文口径','帖数／作者','五项联合p','积极表达BH q'],rows)
    md+='''

现在的结论是：字面表达关联对正文可观察范围敏感，尚不足以推广为全体内容的稳定效果；五个NMF成分只作为探索性结构报告，暂不据此做真实主题的点赞排序。某一探索设定达到5%阈值，不构成因果发现或选择该模型的理由；本轮没有对所有探索模型统一多重校正。

## 四、哪些尚未完成

候选新框架把“谈什么内容”与“怎样表达”分开，保留其他可辨识内容、信息不足和无可用正文三种不同处理。它尚未经过独立人工编码验证，也未据此为全样本生成新标签。完成验证后，才应冻结新分类并重跑正式主题比较。

评论与网络的既有数据、图表和主要结果沿用；本轮未对它们进行新的全面审查。汇报稿扩展了方法与分析内容，不再标作原12分钟版本。

## 五、交付文件

'''
    for name in available:
        md+=f'- [{name}]({name})\n'
    manifest_path=ROOT/'validation/slides_teacher_feedback/slides_manifest.json'
    if manifest_path.is_file():
        manifest=json.loads(manifest_path.read_text())
        md+='\n汇报稿共'+str(len(manifest))+'页；新增页位置：\n\n'
        md+=table(['页码','新增内容'],[[x['page'],x['title']]for x in manifest if x.get('new_analysis')])
        md+='\n\n讲述预算约17分钟，须以排练校准。PPTX进行结构和几何检查；当前环境尚未完成Office原生渲染。\n'
    md+='\n复核依据仍保留在《方法复核与修订结论》中；完整可复现结果位于results/teacher_*。\n'
    (ROOT/(STEM+'.md')).write_text(md,encoding='utf-8')
    css='body{font-family:sans-serif;font-size:10.5pt;line-height:1.4;color:#20332f}h1{font-size:20pt;color:#173f36}h2{font-size:13pt;color:#245c4f;margin-top:16pt}table{width:100%;border-collapse:collapse;font-size:9pt;margin:8pt 0}td,th{padding:5pt;vertical-align:top;border:0}th{color:#245c4f;font-weight:bold}a{color:#245c4f}'
    paper=fitz.paper_rect('a4');box=paper+(43,40,-43,-43)
    writer=fitz.DocumentWriter(str(ROOT/(STEM+'.pdf')))
    # Keep the three-population comparison together at the top of page two.
    before,after=md.split('\n## 三、',1)
    for chunk in [before,'## 三、'+after]:
        doc='<html><head><meta charset="utf-8"><style>'+css+'</style></head><body>'+markdown.markdown(chunk,extensions=['tables'])+'</body></html>'
        story=fitz.Story(html=doc)
        more=1
        while more:
            device=writer.begin_page(paper);more,_=story.place(box);story.draw(device);writer.end_page()
    writer.close()
    pdf=fitz.open(ROOT/(STEM+'.pdf'))
    text=''.join(p.get_text()for p in pdf)
    assert all(x in re.sub(r'\s+','',text)for x in ['七组新增分析','0.040','0.048','尚未经过独立人工编码验证'])
    for i,p in enumerate(pdf,1):
        p.get_pixmap(matrix=fitz.Matrix(1,1),alpha=False).save(QA/f'changes-{i:02d}.png')
    result={'pages':len(pdf),'available_deliverables':available,'summary_sha256':hashlib.sha256((ROOT/(STEM+'.pdf')).read_bytes()).hexdigest(),'classification_status':'candidate; not validated full-sample semantic labels'}
    (QA/'revision_summary_checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
