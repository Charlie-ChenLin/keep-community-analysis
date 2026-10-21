"""Render the insight edition with existing figures and compact table layout."""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('report_renderer', ROOT/'code/build_phase2_report.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)
renderer.CSS += """
table { break-inside: avoid; }
.cover > p:nth-of-type(n+4) { color: #263746; }
@media print {
 .chapter:has(> #heading-01) p { margin-bottom: 3mm; }
 .chapter:has(> #heading-01) figure { margin: 3mm 0; }
 .chapter:has(> #heading-01) h3 { margin-top: 6mm; margin-bottom: 3mm; }
}
"""
sys.argv = [str(ROOT/'code/build_phase2_report.py'), '--stem',
            '分析报告_Phase2_中文新版_insight_v2', '--validation-dir',
            'validation/report_insight_v2']
renderer.main()
