PYTHON ?= python
.DEFAULT_GOAL := help
.NOTPARALLEL:
.PHONY: help install check-data analyze validate experiments comments comment-notebook extension-notebook supplemental supplemental-notebook notebook report report-phase2 slides slides-pdf reproduce submission

help:
	@printf '%s\n' 'make supplemental  主题作者权重、评论直接回应及独立核查' 'make supplemental-notebook  执行补充分析Notebook并导出HTML'
	@printf '%s\n' 'make report-phase2  只导出独立中文新版，不重算、不覆盖旧版'
	@printf '%s\n' 'make install      安装Python依赖' 'make check-data   检查本地课程CSV及SHA-256' 'make analyze      清洗、文本编码、回归、网络及数值核查' 'make experiments  执行扩展分析与预测对照' 'make comments     评论文本汇总、图表与独立核查' 'make comment-notebook    执行评论文本Notebook并导出HTML' 'make notebook     执行主分析Notebook' 'make extension-notebook  执行扩展实验Notebook' 'make report       用已有结果生成报告HTML、DOCX和PDF' 'make slides       用已有结果生成PPTX及讲稿' 'make slides-pdf   macOS下用PowerPoint导出演示PDF' 'make reproduce    依次完成分析、Notebook、报告和PPTX' 'make submission   使用本地课程原件打包提交ZIP'

install:
	$(PYTHON) -m pip install -r requirements.txt

check-data:
	$(PYTHON) code/check_inputs.py --verify-hashes

analyze: check-data
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) code/analyze.py
	$(PYTHON) code/annotate_review.py
	$(PYTHON) code/validate.py

validate: check-data
	$(PYTHON) code/validate.py

experiments: check-data
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) code/extend_analysis.py
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) code/validate_extensions.py

extension-notebook: check-data
	$(PYTHON) code/build_extension_notebook.py
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 扩展实验.ipynb
	$(PYTHON) code/export_notebook.py --input 扩展实验.ipynb

comments: check-data
	$(PYTHON) code/analyze_comment_text.py
	$(PYTHON) code/validate_comment_text.py

supplemental: check-data
	$(PYTHON) code/analyze_supplements.py
	$(PYTHON) code/validate_supplements.py

supplemental-notebook: check-data
	$(PYTHON) code/build_supplemental_notebook.py
	$(PYTHON) -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 补充分析.ipynb
	$(PYTHON) code/export_notebook.py --input 补充分析.ipynb

comment-notebook: check-data
	$(PYTHON) code/build_comment_notebook.py
	$(PYTHON) -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 评论文本分析.ipynb
	$(PYTHON) code/export_notebook.py --input 评论文本分析.ipynb

notebook: check-data
	OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 $(PYTHON) -m jupyter nbconvert --execute --to notebook --inplace --ExecutePreprocessor.timeout=600 分析过程.ipynb
	$(PYTHON) code/export_notebook.py

report:
	$(PYTHON) code/build_deliverables.py --report-only
	$(PYTHON) code/render_outputs.py

report-phase2:
	$(PYTHON) code/build_phase2_report.py

slides:
	$(PYTHON) code/build_deliverables.py --slides-only

slides-pdf:
	@command -v osascript >/dev/null || { printf '%s\n' '此可选目标需要macOS及Microsoft PowerPoint。'; exit 1; }
	osascript code/export_slides.applescript "$(CURDIR)/演示文稿.pptx" "$(CURDIR)/演示文稿.pdf"

reproduce: analyze experiments comments supplemental notebook extension-notebook comment-notebook supplemental-notebook report slides report-phase2

submission:
	$(PYTHON) code/package_submission.py
