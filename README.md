# Keep社区中的内容表达与互动反馈

本项目基于课程提供的Keep社区数据，围绕帖子内容与评论互动两条分析线展开：以词典主回归和主题回归考察文本与点赞的条件关联，以评论文本和有向加权网络描述回应内容及用户连接。

研究题目：**Keep社区中的内容表达与互动反馈——基于帖子文本、点赞与评论网络的分析**

## 报告与主要发现

- [分析报告 PDF](分析报告.pdf)：正式报告，35页，按七章组织，附两级目录、页内跳转及PDF书签。
- [可编辑报告 DOCX](分析报告_可编辑.docx)：与HTML/PDF使用同一文字来源。
- [演示文稿 PPTX](演示文稿.pptx)及[阅读版 PDF](演示文稿.pdf)：24页，附演讲者备注；逐页讲稿见`汇报讲稿.txt`。
- [分析过程 Notebook](分析过程.ipynb)及[静态 HTML](分析过程.html)：保存已执行的代码、表格和图形。
- [扩展实验 Notebook](扩展实验.ipynb)及[静态 HTML](扩展实验.html)：正文覆盖、主题建模、留出预测、作者剔除及评论时序。
- [评论文本分析 Notebook](评论文本分析.ipynb)及[静态 HTML](评论文本分析.html)：评论清理、常见词、用户覆盖、字面表达及角色分布，保存5个已执行代码单元。

样本包含100位作者的9,532条帖子，以及去重后的11,595条评论。主模型控制作者、发帖日期、内容形式等因素后，五项核心文本特征的联合检验不显著（p=0.130）。积极表达词虽呈负向关联，但经BH校正后q=0.079，且PPML计数模型的置信区间包含零。现有证据尚不足以支持通过特定词汇稳定提高点赞的策略。

评论网络包含2,932个有边节点、4,069条有向边，前10位账号接收54.0%的互动事件。该集中度受到样本边界和建边规则影响，仅用于描述已采集的互动关系。

2026-10-17新增的分析进一步表明：主题回归未提供明确关联证据；明确回复主要由帖主发出（89.0%），首周网络的互惠率为74.1%，与全部记录构成的49.6%不同。新增结果作为探索性补充，保留原五项检验作为主分析。

三个研究问题为：RQ1，样本帖子、表达方式及点赞如何分布；RQ2，不同文本特征与点赞是否相关；RQ3，采集到的评论主要表达什么、如何连接用户，互动集中在哪里。

报告保留七章、下设30个小节。第三章提供样本分布与数据边界；第四章统一回答RQ2，依次完成文本编码、特征分布、词典回归、敏感性检验及帖子主题分析与主题回归（第4.11—4.13节）；第五章“评论文本与互动网络分析”专门回答RQ3，先分析评论内容（第5.1—5.2节），再分析用户连接与互动集中度（第5.3—5.7节）；第六章综合解释证据及其适用范围；第七章提出与发现对应的建议。参考文献与分工附录列于正文之后。

2026-10-19增加评论文本分析：11,595条评论来自2,910位发言者，清理后字符数中位数为6，11.8%仅有标记或符号。其他用户发言的鼓励或赞许词命中率为16.9%，帖主发言的感谢词命中率为7.9%。字面规则可重叠，未经过独立人工语义效度验证，不用于测量情感或社会支持；内容与网络也未构成已验证的因果链条。

样本外预测属于另行开展的补充实验，保留在扩展实验Notebook、代码及结果文件中，未纳入当前正式报告和演示稿。正式报告中的TF-IDF用于NMF主题分析。

## 项目结构

```text
.
├── README.md                       # 项目说明与复现步骤
├── DATA.md                         # 输入来源、观测时间与SHA-256
├── Makefile                        # 分步执行和完整复现命令
├── requirements.txt                # Python依赖
├── 2026Data/
│   ├── README.md
│   ├── Keep Data/
│   │   ├── .gitkeep
│   │   ├── sample_post_2022.csv      # 自行放入；不跟踪
│   │   └── sample_comment_2022.csv   # 自行放入；不跟踪
│   └── KeepData_dictionary.pdf      # 可选字段字典；不跟踪
├── references/                     # 本地课程讲义；含放置说明
├── code/
│   ├── check_inputs.py             # 输入检查，不依赖分析库
│   ├── analyze.py                  # 清洗、文本、模型、网络与图表
│   ├── text_dictionary.json         # 词典及操作性定义
│   ├── annotate_review.py          # 辅助语义抽查记录
│   ├── validate.py                 # 独立数值核查
│   ├── extend_analysis.py          # 五类扩展分析与预测对照
│   ├── extension_config.json        # 扩展参数、划分及固定随机种子
│   ├── topic_labels.json            # 不依据点赞命名的主题标题
│   ├── validate_extensions.py      # 扩展结果与训练IDF的独立核查
│   ├── build_extension_notebook.py # 扩展实验Notebook构建
│   ├── report_extensions.py        # 将扩展证据整合进报告与PPT
│   ├── report_structure.py         # 七章编排、分节与两级目录
│   ├── analyze_comment_text.py     # 评论文本、常见词与发言角色
│   ├── comment_text_config.json    # 评论字面规则与分析口径
│   ├── validate_comment_text.py    # 从原始输入独立复算19项检查
│   ├── build_comment_notebook.py   # 评论文本分析Notebook构建
│   ├── project_config.json         # 题目、成员和分工占位
│   ├── build_deliverables.py        # 报告、演示稿及Notebook构建
│   ├── render_outputs.py           # HTML转PDF与版面检查
│   ├── export_notebook.py          # Notebook静态HTML导出
│   ├── export_slides.applescript    # macOS下PowerPoint原生导出
│   └── package_submission.py       # 本地课程提交包
├── results/                        # 汇总结果与匿名网络表
├── figures/                        # 15张分析图，其中13张用于正式报告
├── validation/                     # 数值核查、版面核查与预览
├── 分析报告.{html,pdf}
├── 分析报告_可编辑.docx
├── 分析过程.{ipynb,html}
├── 扩展实验.{ipynb,html}
├── 评论文本分析.{ipynb,html}
├── 演示文稿.{pptx,pdf}
├── 汇报讲稿.txt
└── 互评报告模板.docx
```

公开仓库保留代码、报告、汇总统计和匿名网络结果。课程原始数据、逐帖特征、评论文本抽查记录、讲义原件及包含这些文件的提交ZIP保留在本地，具体范围见[数据说明](DATA.md)。数据目录及说明文件已纳入版本控制，克隆后可直接放入输入文件。

## 安装与数据配置

建议使用Python 3.11或3.12。在仓库根目录创建环境并安装依赖：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
make install
```

Windows可使用`.venv\Scripts\activate`激活环境；没有Make时可按下表直接运行Python命令。

将两份课程CSV放入`2026Data/Keep Data/`，保持原文件名，然后执行：

```bash
make check-data
```

该命令检查文件是否齐全，并核对DATA.md记录的SHA-256。文件名含“2022”，但帖子实际发表于2020年11—12月（UTC）；本地日期的末尾跨至2021-01-01。分析不使用其余课程数据集。

## 复现分析

完成输入配置后，运行：

```bash
make reproduce
```

命令按顺序完成主分析、扩展实验、评论文本分析、三个Notebook的执行、报告导出和PPTX生成。完整计算不调用在线API。原分析的随机种子为20261016，扩展分析为20261017；实际库版本分别见`results/summary.json`和`results/extension_summary.json`。评论内容分析不进行随机抽样，来源校验值与口径见`results/comment_text_summary.json`。

| 目标 | 用途 | 对应命令 |
| --- | --- | --- |
| `make analyze` | 清洗、文本编码、全部模型、网络与数值核查 | `python code/analyze.py`，再运行`annotate_review.py`、`validate.py` |
| `make validate` | 独立复核现有数值结果 | `python code/validate.py` |
| `make experiments` | 执行五类扩展分析及16项扩展核查 | `python code/extend_analysis.py`，再运行`code/validate_extensions.py` |
| `make comments` | 计算评论文本汇总、两张图及19项核查 | `python code/analyze_comment_text.py`，再运行`code/validate_comment_text.py` |
| `make comment-notebook` | 构建、执行评论文本Notebook并导出HTML | `python code/build_comment_notebook.py`，执行`评论文本分析.ipynb`后导出 |
| `make notebook` | 重新执行Notebook并导出静态HTML | `python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 分析过程.ipynb`，再运行`code/export_notebook.py` |
| `make extension-notebook` | 构建、执行扩展实验Notebook并导出HTML | `python code/build_extension_notebook.py`，执行`扩展实验.ipynb`后运行`code/export_notebook.py --input 扩展实验.ipynb` |
| `make report` | 根据已有结果生成HTML、DOCX和PDF | `python code/build_deliverables.py --report-only`，再运行`code/render_outputs.py` |
| `make slides` | 根据已有结果生成PPTX与讲稿 | `python code/build_deliverables.py --slides-only` |
| `make slides-pdf` | 可选：用PowerPoint导出PPT阅读版 | 仅适用于已安装PowerPoint的macOS |

`make report`和`make slides`可以使用仓库现有汇总结果，无需原始CSV。只改报告文字时，使用`make report`即可保留已执行的Notebook和现有演示稿。无参数运行`build_deliverables.py`则会重建全部交付物及Notebook模板，之后需要重新执行Notebook。

PDF导出需要Chrome/Chromium。脚本优先使用`CHROME_PATH`指定的浏览器或本机Chrome；没有本机浏览器时，可安装Playwright提供的Chromium：

```bash
python -m playwright install chromium
```

图表需要中文字体。macOS默认使用`/Library/Fonts/Arial Unicode.ttf`；其他系统可安装中文字体，并按需设置：

```bash
export REPORT_FONT='/绝对路径/中文字体.ttf'
export CHROME_PATH='/绝对路径/Chrome或Chromium可执行文件'
```

`REPORT_FONT`用于Matplotlib图表。HTML/PDF使用系统中的中文字体；跨系统导出时应检查字体是否正确显示。PPTX重建后，原有演示PDF需要重新导出。

## 方法与核查

- 正文中的词典变量是字面表达的代理，不是心理或情感量表。40个分层检查单元由Codex辅助核查语义边界，未采用独立人工双编码。
- 正文缺失的3,984帖保留并设指示变量；仅1,323帖有采集到的评论，其余不赋为零评论。
- 点赞与记录浏览数的统计口径无法确认，因此不计算点赞率。
- 主模型采用作者与日期固定效应，标准误按100位作者聚类；五项核心特征进行BH校正。
- `validation/numerical_checks.json`记录13项独立核查，包括另一套矩阵计算对系数、聚类标准误、p值和置信区间的复算。
- `validation/extension_checks.json`记录16项扩展核查：主题权重、留出划分、16组误差指标、作者聚类自助区间、作者剔除的直接最小二乘比较，以及训练集TF-IDF逆文档频率复算。
- `validation/report_geometry.json`记录PDF来源HTML的正文与页脚位置；预览图用于人工检查排版。
- `validation/comment_text_checks.json`记录19项复核：ID去重与关联、符号记录、长度、12组角色与字面规则统计、20个高频词项的评论频数及用户覆盖。
- `validation/report_toc_checks.json`核对七章、30个小节及39个目录链接的实际PDF目标；`report_structure_checks.json`记录分析表格与图形的完整性、研究问题对应关系及Word标题层级。

主要结果文件为`results/regression_coefficients.csv`、`results/model_fit.csv`、`results/text_features_summary.csv`及`results/summary.json`。原始输入与逐帖中间文件需要本地数据；公开仓库中的Notebook保留了可直接阅读的执行输出。

扩展结果以`results/extension_`开头。NMF先用2,478条正文拟合，再排除8条成分贡献近零的正文；2,470帖进入主题描述和回归。主题数固定为5，预测岭回归α固定为10，未用测试结果选择参数。留出预测为回顾性评估，不能替代具有统一观察窗的实际部署验证。逐帖预测、主题分配及原文示例只保留本地，不进入公开仓库。

24页演示稿的完整讲解约需18—22分钟；可根据课程时长选取内容。分工表仍需按实际人数和贡献填写。

## 课程提交

组号、姓名、学号和实际分工尚未确定，统一保存在`code/project_config.json`中。请按真实情况填写后重新生成报告和演示稿；DOCX/PPTX中的直接修改不会自动写回代码来源。

`make submission`用于生成本地课程提交ZIP，还需要作业PDF、字段字典和参考讲义，放置方式见`references/README.md`。压缩包包含原始课程数据，已通过`.gitignore`排除。若目录内存在演示PDF，打包前需确认它已根据最新PPTX导出。

`互评报告模板.docx`仅为空白模板，须由各成员依据实际贡献独立填写。原作业PDF注明11月10日23:59提交、11月15日前互评，但未标明年份，具体日期以课程平台通知为准。
