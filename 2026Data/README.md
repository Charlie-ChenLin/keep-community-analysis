# 输入目录

本目录只跟踪说明与目录占位。请自行放入有权使用的课程数据：

```text
2026Data/
├── Keep Data/
│   ├── sample_post_2022.csv
│   └── sample_comment_2022.csv
└── KeepData_dictionary.pdf
```

两份CSV是完整分析必需的输入；字段字典PDF用于核对变量说明及生成本地课程提交包。其他课程数据集不参与本项目。

放好数据后，在仓库根目录执行`make check-data`。原始文件校验值与观测时间范围见根目录`DATA.md`。
