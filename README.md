# Keep社区中的内容表达与互动反馈

本项目基于课程提供的Keep社区数据，围绕帖子内容与评论互动两条分析线展开：区分正文可观测范围，考察指定字面表达与点赞的条件关联，并把NMF成分作为探索性文本结构；以评论文本和有向加权网络描述回应内容及用户连接。原全样本模型保留为历史对照。

研究题目：**Keep社区中的内容表达与互动反馈——基于帖子文本、点赞与评论网络的分析**

## 报告与主要发现

- **真人编码入口**：[从这里开始](人工编码开始这里.md)、[字段与21个代码速查](docs/human-review/字段与代码速查.md)。两名编码者各自完成同一批160条，使用独立A／B包；包含正文的表格与证据备注模板只私下领取，不上传公开仓库。本地负责人运行`python code/package_human_review.py`生成两份交接ZIP，脚本不会将已填写表重新打包为空表。当前人工状态仍为待完成。

- **最新核心重建：分类与测量**：[实证重建报告PDF](分类测量重建_实证依据与验证报告.pdf)、[可编辑DOCX](分类测量重建_实证依据与验证报告.docx)、[Markdown](分类测量重建_实证依据与验证报告.md)、[编码手册PDF](分类编码手册_v1.pdf)、[手册原稿](分类编码手册_v1.md)。重新按作者划分开发／校准／留出角色，审读160＋80＋160条不同正文；冻结后对留出正文进行两份隔离上下文的同基座AI编码。将内容对象与表达行为分开，保留领域未指明、信息不足和其他明确内容；17细分叶展示聚合为5父组并保留其他槽，15表达行为允许并存。留出只检验父组与行为，未逐叶验证。新原型存在过度赋类及漏检，未推广为正式全样本语义标签；人工验证为pending。两份全文人审表及分歧材料保存在本地`validation/classification_rebuild/private/`，不随公开仓库分发。`make classification-evaluate`需已有私有样本、编码和模型；`make classification-report`用已保存聚合结果导出。旧词典和NMF的语义解释，以本次重建的测量边界为准；旧报告和PPT保留上一轮状态。

- **上一轮老师意见修订版**：[完整报告PDF](分析报告_老师意见修订版.pdf)、[可编辑DOCX](分析报告_老师意见修订版.docx)、[Markdown](分析报告_老师意见修订版.md)、[汇报PPTX](Keep社区内容表达与互动反馈_老师意见修订版.pptx)、[修改与新增分析清单](修订说明_新增分析与结论变化.md)。将方法复核落实到摘要、方法、正文结果、综合结论及汇报稿：补词典分类依据与VIF、三正文口径、主模型与主题样本分别的作者门槛、原始tag对照、多标签诊断、语义覆盖抽查和主题结构敏感性。旧主题名称降为探索性成分解释；候选人工分类尚未验证，不宣称已获得全样本新标签。评论网络部分沿用既有结果，本轮未全面重审。复现已有结果的修订交付：`make teacher-revision PYTHON=/path/to/python`。汇报稿增加方法页，不再按原12分钟版本标记；Office原生渲染状态见对应验证记录。

- **2026-10-29方法复核（当前解释以此为准，旧主题页需修订）**：[复核PDF](方法复核与修订结论.pdf)、[可编辑原稿](方法复核与修订结论.md)。复核老师提出的词典分类、共线性、主题重叠、少帖作者及原始tag，并重新检查分类覆盖与正文缺失。原五个NMF成分存在语义错配及模板／作者构成依赖，不能作为完整的真实内容分类；全样本与非空正文子样本的文字联合检验p分别约0.130和0.040，结论对可观测范围敏感。四字面特征VIF为1.11—1.75，剔除少帖作者影响较小。旧PPT、报告和模型作为历史结果保留，不将候选分类冒充已完成验证的新标签。候选规则见`code/revised_content_codebook.json`；本轮未全面重审评论网络。复现：`make teacher-feedback PYTHON=/path/to/python`；仅导出已有复核结果：`make teacher-feedback-report`。

- **上一版汇报稿（12分钟，23页，主题解释及RQ2结论待按复核修订）**：[PPTX](Keep社区内容表达与互动反馈_12分钟合并版.pptx)、[PDF预览](Keep社区内容表达与互动反馈_12分钟合并版.pdf)、[逐页讲稿与版本页码对照](Keep社区内容表达与互动反馈_12分钟合并版_逐页讲稿与修改说明.txt)。基于22页版，合入`dyx`分支提交`1e751bd`的研究意义、评论覆盖与北京时间口径、三词类敏感性区间图、互惠及首周网络比较。新增1页互惠分析，保留三个RQ独立展开及完整统计指标；含转场讲述目标约11分34秒，实际以排练为准。旧版均保留，未改动`dyx`分支。源码为`code/build_12min_merged_presentation.js`，合并记录见`validation/slides_12min_dyx/merge_decisions.json`；PDF通过后台渲染生成。
- **保留的22页汇报版（12分钟）**：[PPTX](Keep社区内容表达与互动反馈_12分钟版.pptx)、[PDF预览](Keep社区内容表达与互动反馈_12分钟版.pdf)、[逐页讲稿与新旧页码对照](Keep社区内容表达与互动反馈_12分钟版_逐页讲稿与修改说明.txt)。在25页版上合并正文覆盖与清洗、直接回复口径与鼓励留言分析，撤出独立时序页；保留三个RQ的连续回答、回归方程、统计指标、敏感性分析、主题回归及成员分工。讲述预算10分50秒，另留30秒转场，目标11分20秒，实际以排练为准。旧版文件完整保留。源码为`code/build_12min_presentation.js`；`code/render_12min_presentation.py`使用LibreOffice在后台导出PDF，无需打开PowerPoint窗口（通过`SOFFICE_PATH`或`--soffice`指定可执行文件）。核查记录见`validation/slides_12min/`。
- **保留的25页完整汇报版（10—15分钟）**：[PPTX（25页，含成员分工）](Keep社区内容表达与互动反馈_最终汇报版.pptx)、[PDF预览](Keep社区内容表达与互动反馈_最终汇报版.pdf)、[逐页讲稿与时间安排](Keep社区内容表达与互动反馈_最终汇报版_逐页讲稿与修改说明.txt)。RQ1、RQ2、RQ3分别连续展开并各自收束，最后说明共同局限与成员贡献。陈霖负责问题提出、数据清洗与RQ1；董依心（dyx）负责RQ2与RQ3。生成脚本为`code/build_final_presentation.js`，汇总补充与版面核查记录见`validation/slides_rq_final/`。以下演示稿为历史版本。
- **独立答疑清单**：[PDF（28题、12页）](Keep社区内容表达与互动反馈_答疑清单.pdf)、[HTML阅读版](Keep社区内容表达与互动反馈_答疑清单.html)。包含现场短答、追问解释、易混淆之处、对应PPT页码与参考来源；PPML集中在第2页，也覆盖固定效应、聚类标准误、BH校正、主题模型与评论网络。答疑材料不占汇报正文页数，其中PPT页码对应25页完整汇报版；使用22页版或dyx合并版时，可查阅相应逐页讲稿中的页码对照；新增互惠分析见合并版第19页。生成脚本为`code/build_defense_qa.py`，题目来源为`validation/defense_qa/questions_final.json`。

- **15—20分钟正式汇报版**：[PPTX（18页）](演示文稿_Phase2_15-20分钟精简版.pptx)、[PDF预览](演示文稿_Phase2_15-20分钟精简版.pdf)、[逐页讲稿与时间安排](演示文稿_Phase2_15-20分钟精简版_逐页讲稿.txt)。18页全部为正式讲述内容，没有备用页或隐藏页；六章通过目录、页眉与PPT分节呈现。合并独立章节过渡和重复解释，保留编码与固定效应、表达反转及统计强度、主题作者构成、评论配对分母、网络角色与参与广度。逐页讲述预算17分10秒，另留50秒给转场与停顿，目标约18分钟，实际以排练为准。生成脚本`code/build_short_presentation.js`，后台验证见`validation/slides_insight_short/`。
- **新版汇报（章节清晰、讲述增强）**：[PPTX（37页）](演示文稿_Phase2_章节清晰_讲述增强版.pptx)、[PDF预览](演示文稿_Phase2_章节清晰_讲述增强版.pdf)、[逐页讲稿](演示文稿_Phase2_章节清晰_讲述增强版_逐页讲稿.txt)。以[排版优化版报告](分析报告_Phase2_中文新版_insight_v2_修改版_排版优化.pdf)为依据，分为研究设计与样本、文字表达与点赞、主题与作者构成、评论语言与直接承接、评论网络与互动形态、综合结论与建议六章。包含总目录、章节过渡页、常驻章名和源报告位置；核心页补充分析过程、数值结果和解释，每页另附演讲者备注。10个统计图为可编辑原生图表，原有24页演示稿保留。生成脚本见`code/build_insight_presentation.js`（依赖`pptxgenjs`与`jszip`），验证记录见`validation/slides_insight_v2/`。
- **独立分析师重写版 `_insight_v2`**：[PDF（21页）](分析报告_Phase2_中文新版_insight_v2.pdf)、[可编辑DOCX](分析报告_Phase2_中文新版_insight_v2.docx)、[Markdown](分析报告_Phase2_中文新版_insight_v2.md)、[HTML](分析报告_Phase2_中文新版_insight_v2.html)。以观察结果和对应洞察解释文字表达、作者构成、评论承接与参与广度，评论网络明确账号、方向、事件次数及不同观察范围的含义。沿用原有计算与13张图，详细统计和测量口径集中于附录，历史版本保留。重新导出：`python validation/report_insight_v2/render_report.py`；核查与证据映射见同目录。
- **业务重写版 `_v2`（data-analysis-report-writer）**：[PDF](分析报告_Phase2_中文新版_v2.pdf)、[可编辑DOCX](分析报告_Phase2_中文新版_v2.docx)、[Markdown](分析报告_Phase2_中文新版_v2.md)、[HTML](分析报告_Phase2_中文新版_v2.html)。沿用全部既有计算和13张图，以执行摘要提出决策判断；评论部分按语言、直接回复、网络与时间窗口衔接；建议补充优先级、交付成果及实施条件。未重算数据，前两版均保留。
- **独立新版（consulting-analysis Phase 2）**：[PDF](分析报告_Phase2_中文新版.pdf)、[可编辑DOCX](分析报告_Phase2_中文新版.docx)、[Markdown原稿](分析报告_Phase2_中文新版.md)、[HTML](分析报告_Phase2_中文新版.html)。保留原有七章和13张图，按发现、证据、解释及业务含义组织段落；帖子主题仍在第四章，评论文本与网络仍在第五章。旧版报告及演示稿保留。
- Phase 2版已删除附录，第一章以表格列明RQ与方法；第4.5节补充主题的作者等权比较，第5.5节补充根评论与帖主直接回复的词语顺序（业务重写版将其移至第5.2节）。相关结果见[补充分析Notebook](补充分析.ipynb)及[静态HTML](补充分析.html)，均属于描述性补充，不重新拟合原模型。
- [分析报告 PDF](分析报告.pdf)：正式报告，35页，按七章组织，附两级目录、页内跳转及PDF书签。
- [可编辑报告 DOCX](分析报告_可编辑.docx)：与HTML/PDF使用同一文字来源。
- [演示文稿 PPTX](演示文稿.pptx)及[阅读版 PDF](演示文稿.pdf)：24页，附演讲者备注；逐页讲稿见`汇报讲稿.txt`。
- [分析过程 Notebook](分析过程.ipynb)及[静态 HTML](分析过程.html)：保存已执行的代码、表格和图形。
- [扩展实验 Notebook](扩展实验.ipynb)及[静态 HTML](扩展实验.html)：正文覆盖、主题建模、留出预测、作者剔除及评论时序。
- [评论文本分析 Notebook](评论文本分析.ipynb)及[静态 HTML](评论文本分析.html)：评论清理、常见词、用户覆盖、字面表达及角色分布，保存5个已执行代码单元。

样本包含100位作者的9,532条帖子，以及去重后的11,595条评论。原全样本M3控制作者、日期和已记录情境后，五项文字特征联合p=0.130，积极表达BH q=0.079；原始正文可见的5,548帖对应联合p=0.067，清理后正文非空的5,414帖则为p=0.040，长度和积极表达在该模型内的BH q均约0.048。文字关联对正文可观测范围敏感，不能只用全样本结果概括所有正文，也不能据探索性样本口径的阈值变化推断因果。现有结果不足以推广为全体内容的稳定点赞效果。

评论网络包含2,932个有边节点、4,069条有向边，前10位账号接收54.0%的互动事件。该集中度受到样本边界和建边规则影响，仅用于描述已采集的互动关系。

2026-10-17新增的分析进一步表明：主题回归未提供明确关联证据；明确回复主要由帖主发出（89.0%），首周网络的互惠率为74.1%，与全部记录构成的49.6%不同。新增结果作为探索性补充，保留原五项检验作为主分析。

三个研究问题为：RQ1，样本帖子、表达方式及点赞如何分布；RQ2，不同文本特征与点赞是否相关；RQ3，采集到的评论主要表达什么、如何连接用户，互动集中在哪里。

旧版报告保留七章、下设30个小节。第三章提供样本分布与数据边界；第四章统一回答RQ2，依次完成文本编码、特征分布、词典回归、敏感性检验及帖子主题分析与主题回归（第4.11—4.13节）；第五章“评论文本与互动网络分析”专门回答RQ3，先分析评论内容（第5.1—5.2节），再分析用户连接与互动集中度（第5.3—5.7节）；第六章综合解释证据及其适用范围；第七章提出与发现对应的建议。旧版的参考文献与分工附录仍保留，新版已删除附录。

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
│   ├── analyze_supplements.py     # 作者等权主题与评论直接回应配对
│   ├── supplemental_config.json   # 两项补充的预设口径与时间窗
│   ├── validate_supplements.py    # 14项独立聚合与指向核查
│   ├── build_supplemental_notebook.py # 补充分析Notebook构建
│   ├── build_phase2_report.py     # 新版Markdown独立导出
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
├── 分析报告_Phase2_中文新版.{md,html,pdf,docx}
├── 分析报告_Phase2_中文新版_v2.{md,html,pdf,docx}
├── 分析过程.{ipynb,html}
├── 扩展实验.{ipynb,html}
├── 评论文本分析.{ipynb,html}
├── 补充分析.{ipynb,html}
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

命令按顺序完成主分析、扩展实验、评论文本分析、补充分析、四个Notebook的执行、两版报告导出和PPTX生成。完整计算不调用在线API。原分析的随机种子为20261016，扩展分析为20261017；实际库版本分别见`results/summary.json`和`results/extension_summary.json`。评论内容与本轮补充分析不进行随机抽样，来源校验值与口径分别见`results/comment_text_summary.json`和`results/supplemental_summary.json`。

| 目标 | 用途 | 对应命令 |
| --- | --- | --- |
| `make analyze` | 清洗、文本编码、全部模型、网络与数值核查 | `python code/analyze.py`，再运行`annotate_review.py`、`validate.py` |
| `make validate` | 独立复核现有数值结果 | `python code/validate.py` |
| `make experiments` | 执行五类扩展分析及16项扩展核查 | `python code/extend_analysis.py`，再运行`code/validate_extensions.py` |
| `make comments` | 计算评论文本汇总、两张图及19项核查 | `python code/analyze_comment_text.py`，再运行`code/validate_comment_text.py` |
| `make supplemental` | 冻结主题的作者权重比较、评论直接回应及14项核查 | `python code/analyze_supplements.py`，再运行`code/validate_supplements.py` |
| `make supplemental-notebook` | 构建并执行补充分析Notebook，导出静态HTML | `python code/build_supplemental_notebook.py`，执行`补充分析.ipynb`后导出 |
| `make comment-notebook` | 构建、执行评论文本Notebook并导出HTML | `python code/build_comment_notebook.py`，执行`评论文本分析.ipynb`后导出 |
| `make notebook` | 重新执行Notebook并导出静态HTML | `python -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 分析过程.ipynb`，再运行`code/export_notebook.py` |
| `make extension-notebook` | 构建、执行扩展实验Notebook并导出HTML | `python code/build_extension_notebook.py`，执行`扩展实验.ipynb`后运行`code/export_notebook.py --input 扩展实验.ipynb` |
| `make report` | 根据已有结果生成HTML、DOCX和PDF | `python code/build_deliverables.py --report-only`，再运行`code/render_outputs.py` |
| `make slides` | 根据已有结果生成PPTX与讲稿 | `python code/build_deliverables.py --slides-only` |
| `make slides-pdf` | 可选：用PowerPoint导出PPT阅读版 | 仅适用于已安装PowerPoint的macOS |

`make report`和`make slides`可以使用仓库现有汇总结果，无需原始CSV。只改报告文字时，使用`make report`即可保留已执行的Notebook和现有演示稿。无参数运行`build_deliverables.py`则会重建全部交付物及Notebook模板，之后需要重新执行Notebook。

独立新版的正文来源为`分析报告_Phase2_中文新版.md`。运行`make report-phase2`只将该原稿和既有PNG导出为同名HTML、DOCX、PDF，并核对目录链接，不读取原始CSV、不执行统计或重新绘图，也不覆盖旧版。该目标只负责文档导出，需在已有图表就位后执行；完整的`make reproduce`会在最后调用它。

业务重写版另存为`分析报告_Phase2_中文新版_v2.md`，使用`make report-v2`导出同名HTML、DOCX和PDF。该命令只处理文稿及既有图片，不运行数据分析或Notebook，也不覆盖前两版；目录核查和预览保存在`validation/report_v2/`。该版本保留七个主体章节、RQ表格及主题与评论分章，不设附录，将综合结论集中在第六章，并以第七章的具体行动收束全文。

补充计算由独立目标`make supplemental`执行，口径保存在`code/supplemental_config.json`。主题比较需要已有的本地`results/extension_post_topics.csv`；缺少时先运行`make experiments`生成，完整的`make reproduce`已按此顺序安排，并在末尾导出新版报告。新增评论比较以每条外来根评论为单位，只纳入ID、用户指向、所属帖子和时间均匹配的帖主直接回复，168小时从根评论起算；这与原网络从发帖起算的首周窗口不同。聚合结果可公开阅读，原始文本、真实用户ID及配对明细不导出。

补充表中的`observed_direct_replies`是观察到符合条件直接回复的根评论数，每条根评论最多计1次；感谢率以这些已观察到直接回复的根评论为分母。涉及帖主数和去重发言人数均可在命中、未命中两组重叠，不能跨组相加。主题表的占比差为作者等权占比减去帖子等权占比，使用未舍入数值计算。

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

24页演示稿的完整讲解约需18—22分钟；可根据课程时长选取内容。该历史版本的分工表仍为占位；最终汇报版已按确认的贡献填写。

## 课程提交

旧版自动生成模板中的组号、姓名、学号和分工占位统一保存在`code/project_config.json`中。请按真实情况填写后重新生成报告和演示稿；DOCX/PPTX中的直接修改不会自动写回代码来源。

`make submission`用于生成本地课程提交ZIP，还需要作业PDF、字段字典和参考讲义，放置方式见`references/README.md`。压缩包包含原始课程数据，已通过`.gitignore`排除。若目录内存在演示PDF，打包前需确认它已根据最新PPTX导出。

`互评报告模板.docx`仅为空白模板，须由各成员依据实际贡献独立填写。原作业PDF注明11月10日23:59提交、11月15日前互评，但未标明年份，具体日期以课程平台通知为准。
