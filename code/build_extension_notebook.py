"""Build the runnable companion for the exploratory extension experiments."""
from pathlib import Path
import json
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]


def main():
    md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
    summary=json.loads((ROOT/'results/extension_summary.json').read_text())
    cells=[
        md(f'# Keep社区：扩展分析与计算实验\n\n## tl;dr\n正文覆盖与内容形式、作者有关。NMF识别的若干模板集中于少数作者；主题回归联合检验p={summary["topics"]["joint_topic_p"]:.3f}。时间留出和作者分组五折中，增加文本均未显示稳定的误差改善。89.0%的明确回复由帖主发出，首周与全部评论构成的网络指标也不同。\n\n原五项词典回归仍作为主分析，见《分析过程.ipynb》。本Notebook记录2026-10-17增加的探索性工作。'),
        md('## Context & Methods\n### Key Assumptions\n- 扩展配置见code/extension_config.json；不按测试结果调参。\n- NMF仅纳入至少3个有效词且具有非零TF-IDF表示的正文。\n- 所有预测编码、标准化与TF-IDF只拟合训练集；作者五折不允许作者重叠。\n- 留出目标仍是采集时点的累计点赞，缺少统一观察窗，不能视作实际部署评估。\n- 配对区间针对固定留出预测，不包含重新训练带来的变异。\n- 评论时序、回应比例均以已采集记录为条件。\n\n### 1. 环境与输入'),
        code('from pathlib import Path\nimport sys, json\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT = Path.cwd()\nif not (ROOT / "code/extend_analysis.py").exists():\n    ROOT = ROOT / "projects/group"\nsys.path.insert(0, str(ROOT / "code"))\nimport analyze\nimport extend_analysis as ext\nposts, comments, _ = analyze.read_and_prepare()\nsummary = json.loads((ROOT / "results/extension_summary.json").read_text())\nprint("帖子", len(posts), "作者", posts.author.nunique(), "去重评论", len(comments))'),
        md('## Data\n### 2. 正文覆盖与作者差异'),
        code('summary["coverage"] = ext.coverage(posts)\ndisplay(pd.read_csv(ROOT / "results/extension_coverage_media.csv").round(4))\nprint(summary["coverage"])'),
        md('## Results\n### 3. 重新拟合NMF与探索性主题回归\n主题名称来自关键词与不含点赞指标的例文；所有原始例文保留本地。'),
        code('summary["topics"] = ext.topic_model(posts)\nlabels = json.loads((ROOT / "code/topic_labels.json").read_text())["labels"]\ntopics = pd.read_csv(ROOT / "results/extension_topics.csv")\ntopics["名称"] = topics.topic.map(lambda i: labels[str(i)])\ndisplay(topics[["名称", "keywords", "dominant_documents", "dominant_share", "largest_author_share"]].round(4))\ndisplay(pd.read_csv(ROOT / "results/extension_topic_regression.csv").round(4))'),
        md('### 4. 重新执行时间留出和作者分组预测\n固定岭回归α=10；比较训练均值、结构化基线、词典特征及字符文本。所有变换在每个训练折内拟合。'),
        code('summary["prediction"] = ext.predictions(posts)\nmetrics = pd.read_csv(ROOT / "results/extension_prediction_metrics.csv")\ndisplay(metrics.loc[metrics.subset.eq("全部留出帖"),\n    ["split", "label", "n", "mae", "rmse", "r2"]].round(4))\ndisplay(pd.read_csv(ROOT / "results/extension_prediction_differences.csv").round(4))'),
        md('### 5. 逐作者剔除检验\n100次剔除仅考察点估计变化，不新增100轮显著性检验。'),
        code('summary["influence"] = ext.author_influence(posts)\ndisplay(pd.read_csv(ROOT / "results/extension_author_influence_summary.csv").round(4))'),
        md('### 6. 评论时间、回复角色与窗口\n不把未采集的回应当作零；7天窗口也不保证每帖都被完整观测7天。'),
        code('summary["comments"] = ext.comment_extensions(posts, comments)\ndisplay(pd.read_csv(ROOT / "results/extension_comment_roles.csv").round(4))\ndisplay(pd.read_csv(ROOT / "results/extension_window_networks.csv").round(4))\n(ROOT / "results/extension_summary.json").write_text(\n    json.dumps(summary, ensure_ascii=False, indent=2, default=int))\next.plot_extensions()'),
        md('### 7. 覆盖率与主题\n主题描述和回归占全部帖25.9%，其中部分主题主要来自重复记录模板；8条主题贡献近零的正文不强制归类。'),
        code('display(Image(filename=str(ROOT / "figures/08_text_coverage.png"), width=950))\ndisplay(Image(filename=str(ROOT / "figures/09_topics.png"), width=950))'),
        md('### 8. 留出误差与配对区间\n负ΔMAE表示误差下降；区间均包含零。'),
        code('display(Image(filename=str(ROOT / "figures/10_prediction_comparison.png"), width=950))\ndisplay(Image(filename=str(ROOT / "figures/11_prediction_uncertainty.png"), width=950))'),
        md('### 9. 作者影响和回复结构'),
        code('display(Image(filename=str(ROOT / "figures/12_author_influence.png"), width=950))\ndisplay(Image(filename=str(ROOT / "figures/13_comment_timing_roles.png"), width=950))'),
        md('### 10. 独立数值核查\n用原始预测重算指标，用重复次数法复算聚类自助区间，并检查训练IDF和直接最小二乘的作者剔除结果。'),
        code('import validate_extensions\nvalidate_extensions.main()\nchecks = json.loads((ROOT / "validation/extension_checks.json").read_text())\nassert all(row["passed"] for row in checks)\nprint("扩展核查全部通过：", len(checks), "项")'),
        md('## Takeaways\n1. 原词典检验、主题回归和留出预测从不同角度提供了有限的文本增量证据，没有识别出可复制的高赞表达策略。\n2. 积极表达词的负向OLS点估计不依赖单一作者，但仍需保留多重检验和PPML中的限制。\n3. 互动互惠主要围绕帖主回应展开；总体网络结构还取决于评论窗口与采集边界。\n4. 代码、完整参数、汇总输出及验证记录均可追溯；原文与逐帖预测不进入公开仓库。')
    ]
    nb=nbf.v4.new_notebook(cells=cells)
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}}
    nbf.write(nb,ROOT/'扩展实验.ipynb')
    print('Built extension notebook with',sum(c.cell_type=='code' for c in cells),'code cells.')


if __name__=='__main__':main()
