# Keep 社区文本与互动网络小组项目

已按照《小组项目作业.pdf》完成描述统计、非结构化文本转结构化、回归、文本与网络分析、结果解释和建议。全部产出位于本目录，原始输入未修改。

本仓库公开项目代码、报告和汇总结果。课程原始数据、逐帖记录、讲义与本地提交ZIP未上传；完整计算的输入文件及校验值见[数据说明](DATA.md)。

## 先看哪些文件

- `分析报告.pdf`：20页正式报告。
- `演示文稿.pptx`：16页可编辑演示稿，每页含演讲者备注。
- `汇报讲稿.txt`：逐页讲稿和建议用时。
- `分析报告_可编辑.docx`：方便填成员信息及修改文字；分页以正式PDF为准。
- `分析报告.html`：正式PDF的同源排版稿，需要与`figures/`同目录使用。
- `分析过程.ipynb`、`分析过程.html`：已从头执行并保留输出的分析过程及无需Jupyter的浏览版本。
- `results/`、`figures/`：可检查的特征、统计表、模型结果和7张图。
- `code/`：清洗、词典、分析、独立验证、排版和打包程序。
- `validation/`：独立数值复核、页面布局核查、运行日志和预览图。

## 提交前填写

组号、小组成员姓名及学号暂未确定，封面和末页已保留`【待填写】`占位。

`code/project_config.json`保存这些信息和可调整的四人分工建议。请按实际人数、完成情况和课程汇报时长修改。它不代表真实贡献记录。更新配置后可重建报告和PPT；也可直接修改DOCX/PPTX。DOCX的手工修改不会自动进入HTML/PDF。

原作业要求每位成员参与汇报；每人的互评必须依据真实贡献独立完成。`互评报告模板.docx`是空白模板，并未代填评价。ZIP名中的组号也要更换。

课程PDF写明11月10日23:59提交、11月15日前互评，但没有明确年份；本项目不推断该日期是否适用于当前学期，请以课程平台通知为准。

## 研究结论与口径

研究题目：什么样的健身分享更容易获得点赞？

- 使用课程提供的100位作者、9532条帖子；抽样机制未知。帖子发布时间为2020年11—12月UTC，本地时间末尾跨至2021-01-01；不是2022/2026年样本。
- 评论13511行中1916行为完全重复，去重后11595条。仅1323帖有采集到的评论，其余不赋为零评论。
- 3984帖无可用正文；保留并设置指示变量。8286帖点赞高于浏览数，因字段口径不可确认，不计算点赞率。
- 主模型控制作者、日期、形式、业务类型、时段及辅助文本标记，按100位作者聚类。五项核心文本特征联合检验p=0.130；积极表达词原始p=0.016，BH q=0.079，PPML区间跨零。没有充分证据支持稳定的高赞词汇策略。
- 评论网络2932节点、4069边、11511次非自我互动，前10位接收54.0%。结果受作者抽样和根评论建边规则影响，不是平台总体影响力。
- 文本词典只是字面代理。40个分层检查单元由Codex辅助核查语义边界，非独立人工双编码，不声称准确率。

## 运行环境

推荐Python 3.11；分析实际使用版本见`results/summary.json`。安装：

```bash
python -m pip install -r requirements.txt
```

不需要在线API、爬虫、数据库或付费模型。统计分析可以离线运行。PDF打印需本机Chrome/Chromium与Playwright；字体推荐可显示中文的TrueType字体。Mac默认字体路径是`/Library/Fonts/Arial Unicode.ttf`，其他系统可设置：

```bash
export REPORT_FONT='/你的中文字体绝对路径.ttf'
export CHROME_PATH='/你的Chrome或Chromium可执行文件路径'
```

## 完整复现

先进入本目录，再按顺序执行：

```bash
python code/analyze.py
python code/annotate_review.py
python code/validate.py
python code/build_deliverables.py
python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 分析过程.ipynb
python code/export_notebook.py
python code/render_outputs.py
python code/package_submission.py
```

`build_deliverables.py`会重新生成Notebook模板，故其后需要执行Notebook。每个代码单元和模型均实际运行；报告和PPT读取同一批已生成的结果，不使用演示数据。模型为确定性计算；分层抽查和网络布局的随机种子为20261016。

如果只修改组员配置而不想重跑Notebook，在Python中调用`build_deliverables.write_html(build_deliverables.report_pages())`、`write_docx(...)`和`write_slides()`，再运行`render_outputs.py`与`package_submission.py`即可。直接运行构建脚本的标准完整流程更方便复现。

分析输入路径为`2026Data/Keep Data/`。停用词在工作目录可读取课程微博数据中的原文件；提交包使用相同内容的`code/stopwords.txt`，无需其余数据集。根目录数据字典和`references/`中的课程参考资料仅在ZIP中额外随附。

`演示文稿.pdf`若存在，是PowerPoint原生导出的便携阅读副本，重建PPT后需要用PowerPoint重新导出；不是核心复现步骤的必需输入。PPTX本身始终由本地Python脚本生成。

Mac已安装PowerPoint时，可执行`osascript code/export_slides.applescript "$PWD/演示文稿.pptx" "$PWD/演示文稿.pdf"`重新导出。打包程序会检查已有演示PDF是否晚于PPTX，以免附上旧版本。

## 可复核文件

| 文件 | 说明 |
| --- | --- |
| `results/summary.json` | 时间范围、数据质量计数、网络统计、原文件哈希、实际库版本 |
| `results/post_features.csv` | 每帖一行的模型输入，作者匿名化 |
| `code/text_dictionary.json` | 完整词表与匹配定义 |
| `results/text_coding_review.csv` | 40个检查单元及辅助语义判断 |
| `results/regression_coefficients.csv` | 主模型、基础规格、全部敏感性规格的系数、SE、p、95%区间及主模型BH q |
| `results/model_fit.csv` | 样本量、作者数、矩阵秩、R²、聚类自由度和PPML收敛情况 |
| `results/network_edges.csv` | 匿名有向加权边表 |
| `results/network_nodes.csv` | 匿名节点、入出度、加权入出度及PageRank |
| `validation/numerical_checks.json` | 13项独立数值核查，含手算聚类协方差与t推断 |
| `validation/report_geometry.json` | HTML各页正文与页脚位置，核对溢出 |

参考文献与讲义页码均列于报告。本地作业包不包含未使用的B站、微博、密室、知乎等数据集。公开仓库的文件范围见DATA.md；课程提交和个人互评由小组另行完成。
