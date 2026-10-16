# 数据来源与本地复现

本研究使用课程提供的 Keep 社区数据。公开仓库保存代码、报告、图表、已执行 Notebook、汇总统计和匿名网络结果；原始数据、逐帖特征、逐帖预测、主题分配、正文例文、评论文本抽查记录、课程讲义和含原始数据的课程提交 ZIP 保留在本地。

运行完整分析时，请将有权使用的原始文件按以下位置放置：

```text
2026Data/
  Keep Data/
    sample_post_2022.csv
    sample_comment_2022.csv
  KeepData_dictionary.pdf
```

| 文件 | 规模 | SHA-256 |
| --- | --- | --- |
| `sample_post_2022.csv` | 9,532帖、100位作者 | `74f2ed2878852f00618db3ae0b9f8c468a4f760e603dcb98c8a286a47919582c` |
| `sample_comment_2022.csv` | 原始13,511行，去重后11,595条 | `7a7a7e1f2462fc457ed7110266fbacbd2998f0f302f86eef7ca1202c9da53355` |

文件名中的年份不等同于观测年份。帖子实际发表于2020年11—12月（UTC），评论最晚延续至北京时间2021年8月26日。

阅读报告、查看汇总结果或重新生成报告文字无需原始数据。运行`code/analyze.py`、`code/validate.py`和Notebook中的计算单元需要上述CSV。停用词副本随代码提供。

`code/package_submission.py`生成的是本地课程提交包，需要课程作业PDF、数据字典及参考讲义。讲义可放在`references/`下；该脚本也兼容原工作区的`materials/`目录。提交包与公开仓库的文件范围不同。
