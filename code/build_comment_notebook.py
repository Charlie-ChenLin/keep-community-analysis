"""Build the inspectable companion for comment content analysis (RQ3)."""
from pathlib import Path
import json
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]


def main():
    s=json.loads((ROOT/'results/comment_text_summary.json').read_text())
    md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
    nb=nbf.v4.new_notebook()
    nb.cells=[
        md(f'# Keep社区：评论文本分析\n\n## tl;dr\n在{s["comments"]:,}条去重评论中，清理后字符数中位数为{s["median_clean_length"]:.0f}；{s["markers_or_symbols_only_share"]:.1%}仅有标记或符号。其他用户发言的鼓励或赞许词命中率为16.9%，帖主发言的感谢词命中率为7.9%。这些结果描述字面表达，不估计情感、社会支持或因果效果。'),
        md('## Context & Methods\n对应RQ3：评论主要表达什么、用户如何连接、互动集中在哪里？本Notebook负责评论内容，关系结构见主分析及扩展实验Notebook。\n\n### Key Assumptions\n- 来源：2026Data/Keep Data/sample_comment_2022.csv；通过sample_post_2022.csv识别所属帖主。\n- 按cmtId去重；不同ID下的重复短句和84次自我互动保留。\n- 统一全半角，移除URL和方括号标记，词项每条评论至多计一次。\n- 规则见code/comment_text_config.json；四类特征可重叠，未进行独立人工语义验证。\n- 角色按每条评论界定；同一用户可在不同帖子中切换角色，用户覆盖不能相加。\n\n### 1. 环境与配置'),
        code('from pathlib import Path\nimport sys, json\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT = Path.cwd()\nif not (ROOT / "code/analyze_comment_text.py").exists():\n    ROOT = ROOT / "projects/group"\nsys.path.insert(0, str(ROOT / "code"))\nimport analyze_comment_text as comments\ndisplay(pd.DataFrame([{ "特征": rule["label"], "规则": "、".join(rule["terms"]) } for rule in comments.CFG["features"].values()]))'),
        md('## Data\n### 2. 重新读取输入并计算汇总\n只输出汇总表和图形；原始评论、ID及逐条特征均不写入公开结果。'),
        code('summary = comments.analyze()\nkeys = ["raw_comments", "comments", "duplicate_ids_removed", "missing_content", "senders", "posts", "markers_or_symbols_only", "median_clean_length", "repeated_normalized_text_comments"]\ndisplay(pd.DataFrame({"指标": keys, "数值": [summary[key] for key in keys]}))\nprint("来源及规则SHA-256保存在results/comment_text_summary.json。")'),
        md('## Results\n### 3. 常见词与发言用户覆盖\n每条评论内词项去重后计数；至少覆盖5位发言者。频数不能直接替代参与广度。'),
        code('terms = pd.read_csv(ROOT / "results/comment_text_terms.csv")\ndisplay(terms.head(12).round(4))\ndisplay(Image(filename=str(ROOT / "figures/14_comment_words.png"), width=950))'),
        md('“加油”出现在612条评论、覆盖431位用户；“谢谢”出现在359条评论、覆盖53位用户。不同短句的次数与覆盖人数并不成比例。'),
        md('### 4. 字面表达与角色\n分母为该角色的全部已采集评论。规则可重叠，问号不代表真实提问；角色差异不是干预效果。'),
        code('features = pd.read_csv(ROOT / "results/comment_text_features.csv")\ndisplay(features[["role", "label", "n", "hits", "share", "senders_hit"]].round(4))\ndisplay(Image(filename=str(ROOT / "figures/15_comment_expressions.png"), width=950))'),
        md('### 5. 独立复核\n另从原始输入用向量化清理、逐词包含规则及词项展开聚合重算，不调用分析函数的统计助手。'),
        code('import validate_comment_text\nchecks = validate_comment_text.main()\nassert all(row["passed"] for row in checks)\ndisplay(pd.DataFrame(checks))'),
        md('## Takeaways\n评论中的短句与字面表达可以帮助描述已采集交流。其他用户与帖主的表达分布不同，但未验证逐线程的“鼓励—感谢”链条。评论内容与网络是RQ3的两个侧面；不能据此解释点赞回归的系数或识别健康、留存效果。'),
    ]
    nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
                 'language_info':{'name':'python','version':'3'}}
    nbf.validate(nb);nbf.write(nb,ROOT/'评论文本分析.ipynb')


if __name__=='__main__':main()
