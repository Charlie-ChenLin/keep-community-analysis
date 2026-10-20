"""Create the independently runnable companion for the two bounded supplements."""
from pathlib import Path
import nbformat as nbf

ROOT=Path(__file__).resolve().parents[1]


def main():
    md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
    notebook=nbf.v4.new_notebook(cells=[
        md('# Keep社区：主题作者权重与评论直接回应补充分析\n\n## tl;dr\n作者等权后，运动与训练交流仍是最大主题；靠墙静蹲记录的占比从3.4%降为0.6%。命中鼓励或赞许词的根评论中，43.5%观察到7天内帖主直接回复；在这些最早观测回复中，26.7%命中感谢词。未命中组对应为56.3%和6.4%。这是描述性配对结果，不是鼓励用语的因果效果。'),
        md('## Context & Methods\n第四章的主题比较补充RQ2；第五章的直接回应补充RQ3。两项分析分别使用冻结的帖子主题权重和原始评论，不混合统计单位。\n\n### Key Assumptions\n主题样本为已有2,470帖、86位作者；不重拟合NMF、不新增回归检验。作者等权只针对这个有效正文样本。\n\n评论以外来根评论为单位；只有帖主对该根评论ID及其作者的直接回复才纳入。时间窗从根评论起算168小时，与原网络从发帖起算的首周窗口不同。未观测不当作真实没有回应；最早观测回复不等于实际首次回复。字面词典沿用既有规则，未进行独立语义验证。\n\n### 1. 环境与配置'),
        code('from pathlib import Path\nimport sys, json\nimport pandas as pd\nfrom IPython.display import display\nROOT=Path.cwd()\nif not (ROOT/"code/analyze_supplements.py").exists():\n    ROOT=ROOT/"projects/group"\nsys.path.insert(0,str(ROOT/"code"))\nimport analyze_supplements as analysis\ndisplay(pd.DataFrame([{"分析":key,"口径":str(value)} for key,value in analysis.CONFIG.items() if key!="analysis_date"]))'),
        md('## Data\n### 2. 读取来源并运行两项补充计算\n输入为课程两份CSV、results/extension_post_topics.csv与既有词典。主题缓存可由make experiments生成；原始数据配置见DATA.md。只写出supplemental_开头的聚合结果，不修改原模型或图表，也不导出评论、用户ID或配对明细。'),
        code('topics, replies, summary=analysis.run()\ndisplay(pd.DataFrame([{ "范围":"主题", "规模":summary["topic_comparison"]["documents"], "单位":"帖子" },{ "范围":"评论配对", "规模":summary["direct_reply_comparison"]["external_roots"], "单位":"外来根评论" }]))\nprint("来源校验值及窗口定义保存在results/supplemental_summary.json。")'),
        md('## Results\n### 3. 帖子等权与作者等权的主题分布\n先确定每条正文的主导主题；帖子等权按帖子数计算，作者等权先在每位作者内计算占比，再对86位作者平均。精确数值以五行对照表展示，不改动原有主题图。'),
        code('view=topics[["label","documents","post_equal_share","author_equal_share","difference_percentage_points"]].copy()\nfor key in ["post_equal_share","author_equal_share"]:view[key]=view[key].map(lambda value:f"{value:.1%}")\nview["difference_percentage_points"]=view["difference_percentage_points"].map(lambda value:f"{value:+.2f}")\nview.columns=["主题","主导文档数","帖子等权","作者等权","占比差（百分点）"]\ndisplay(view)'),
        md('主题最大值的分类与原结果一致。作者等权改变的是观察对象的权重，未改变每条正文的主题或点赞回归；这项比较检验高产作者对主题占比的影响，不估计平台用户偏好。\n\n### 4. 外来根评论与帖主的直接回应\n字段中的空字符串或字面量null按缺失识别。reply、replyUserId、parentId与所属帖子均须匹配，回复时间不早于根评论且间隔不超过168小时。同一最早时点的多条记录按任一感谢词命中处理；本次没有同一根评论的最早回复时间并列。'),
        code('view=replies[["root_group","roots","post_authors","observed_direct_replies","observed_direct_reply_share","thanks_in_first_reply","thanks_among_observed_first_replies"]].copy()\nfor key in ["observed_direct_reply_share","thanks_among_observed_first_replies"]:view[key]=view[key].map(lambda value:f"{value:.1%}")\nview.columns=["根评论组别","根评论数","涉及帖主数","观察到直接回复","直接回复占比","最早回复含感谢词","已回复组的感谢命中率"]\ndisplay(view)'),
        md('### 5. 独立核查\n用csv、字典计数与逐词包含重新读取来源，不调用分析脚本的聚合助手。核查主题分母、既有主导文档数、文本清理、根评论口径、用户指向、回复时间和两级感谢率分母。'),
        code('import validate_supplements\nchecks=validate_supplements.main()\nassert all(row["passed"] for row in checks)\ndisplay(pd.DataFrame(checks))'),
        md('## Takeaways\n主题分析显示主要内容格局对作者等权较稳定，较小的模板化主题更受作者构成影响。评论分析确认了部分可核对的词语顺序共现，但鼓励命中组的直接回复观察占比较低，不能概括为“更容易获得回复”。两组涉及的帖主、内容及采集覆盖不同，感谢率还以已观察到回复为条件；不作因果解释，也不把未命中或未观测当作真实语义和行为的缺席。')
    ])
    notebook.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3'}}
    nbf.validate(notebook);nbf.write(notebook,ROOT/'补充分析.ipynb')


if __name__=='__main__':main()
