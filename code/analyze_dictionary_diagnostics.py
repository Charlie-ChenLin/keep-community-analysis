"""Audit the four frozen dictionary/rule indicators after teacher feedback.

Run from any directory with the project's numpy/pandas environment. This script
does not re-fit, change or overwrite any existing model or feature definition.
It writes aggregate diagnostics, with no original text or user identifiers.
"""
from itertools import combinations
from pathlib import Path
import hashlib
import json
import platform
import re

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"
QA = ROOT / "validation/teacher_feedback"
KEYS = ["self_discipline", "social_address", "positive_expression", "question"]
NUMERIC = ["log_length"] + KEYS + ["has_text", "has_tag", "emoji_count", "course_ref"]
CATEGORICAL = ["contentTypeStr", "type", "time_bin", "author", "date"]
DEFINITIONS = {
    "self_discipline": {
        "label": "自律／目标词命中", "classification_axis": "目标与行动表述",
        "rationale": "以坚持、目标、计划、完成等词识别运动记录中的目标追求和行动进度，与RQ2关注的内容表达相对应。",
        "examples": ["坚持", "目标", "打卡", "完成"],
        "semantic_limit": "加油也可能用于鼓励他人；命中不等于作者具有自律人格或真实完成训练。",
    },
    "social_address": {
        "label": "社交称呼／互助词命中", "classification_axis": "面向他人的称呼与互动邀请",
        "rationale": "以大家、一起、谢谢、请教等词识别对读者的称呼、感谢、互助和邀请交流的字面线索。",
        "examples": ["大家", "一起", "谢谢", "请教"],
        "semantic_limit": "感谢可能同时带有积极含义；命中不等于已发生互助，也不代表关系强度。",
    },
    "positive_expression": {
        "label": "积极表达词命中", "classification_axis": "积极感受与赞许的表面用词",
        "rationale": "以开心、快乐、喜欢、棒等词识别积极感受和赞许，区别于说什么目标、对谁说及是否使用问号。",
        "examples": ["开心", "快乐", "喜欢", "棒"],
        "semantic_limit": "未处理否定、反讽和子串歧义；命中不是经过验证的情绪或情感判断。",
    },
    "question": {
        "label": "问号出现", "classification_axis": "句式标点线索",
        "rationale": "正文含中文或英文问号即记1，用作疑问句式的可观察标记；它是标点规则，与前三类词汇规则性质不同。",
        "examples": ["?", "？"],
        "semantic_limit": "反问、修辞问句也会命中，未使用问号的提问会漏判；不等于求助意图。",
    },
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_csv(frame, name):
    frame.to_csv(RESULT / name, index=False, encoding="utf-8-sig")


def matrix_product(a, b):
    # Some macOS Accelerate builds emit spurious FP flags; check actual output.
    with np.errstate(all="ignore"):
        out = a @ b
    if not np.isfinite(out).all():
        raise ArithmeticError("Non-finite matrix product")
    return out


def main():
    QA.mkdir(parents=True, exist_ok=True)
    dictionary_path = ROOT / "code/text_dictionary.json"
    feature_path = RESULT / "post_features.csv"
    source_path = ROOT / "2026Data/Keep Data/sample_post_2022.csv"
    dictionary = json.loads(dictionary_path.read_text())
    f = pd.read_csv(feature_path)
    n = len(f)
    checks = []

    def check(label, ok, detail=None):
        checks.append({"check": label, "passed": bool(ok), "detail": detail})
        if not ok:
            raise AssertionError(label + ": " + str(detail))

    check("冻结逐帖特征主键唯一且四变量为0/1", f.postId.is_unique and f[KEYS].isin([0, 1]).all().all())

    # Check observed rule assignments directly against original records.
    # Do not import analyze.py or its text-processing helpers.
    raw = pd.read_csv(source_path).set_index("postId")
    check("原始帖子与冻结特征主键完全一致", len(raw) == n and set(raw.index) == set(f.postId))
    content = raw.loc[f.postId, "content"].fillna("").astype(str)
    reconstructed = []
    for body in content:
        body = body.replace("\\n", "\n").replace("\\r", " ")
        for pattern in (r"https?://\S+", r"Ⓚ[^Ⓚ]*Ⓚ", r"\[[^\[\]]{1,12}\]"):
            body = re.sub(pattern, " ", body)
        body = " ".join(body.split())
        row = {}
        for key in KEYS:
            if key == "self_discipline":
                row[key] = int(any(re.search(term, body) is not None for term in dictionary[key]))
            else:
                row[key] = int(any(term in body for term in dictionary[key]))
        reconstructed.append(row)
    independently_coded = pd.DataFrame(reconstructed)
    coding_errors = (independently_coded.to_numpy() != f[KEYS].to_numpy()).sum(axis=0)
    check("从原始正文独立逐词匹配复核四变量", int(coding_errors.sum()) == 0,
          {key: int(value) for key, value in zip(KEYS, coding_errors)})

    # Exact M3 design: includes all original fixed effects and controls.
    x = pd.concat([
        pd.Series(1.0, index=f.index, name="Intercept"), f[NUMERIC],
        pd.get_dummies(f[CATEGORICAL], drop_first=True, dtype=float)
    ], axis=1)
    a = x.to_numpy(float)
    rank = int(np.linalg.matrix_rank(a))
    expected = pd.read_csv(RESULT / "model_fit.csv").set_index("model").loc["M3_作者与日期固定效应"]
    check("完整主模型设计矩阵与冻结模型行数、列数、秩一致",
          int(expected["n"]) == n and int(expected["parameters"]) == x.shape[1]
          and int(expected["rank"]) == rank == x.shape[1],
          {"rows": n, "columns": x.shape[1], "rank": rank})
    gram_inverse = np.linalg.inv(matrix_product(a.T, a))
    full_vif = {
        key: float(gram_inverse[x.columns.get_loc(key), x.columns.get_loc(key)]
                   * np.square(f[key] - f[key].mean()).sum())
        for key in KEYS
    }

    # FWL residualization: remove all other M3 columns jointly, including length.
    z = x.drop(columns=KEYS).to_numpy(float)
    binary = f[KEYS].to_numpy(float)
    residual = binary - matrix_product(z, np.linalg.lstsq(z, binary, rcond=None)[0])
    corr_raw = f[KEYS].corr()
    demeaned = f[KEYS] - f.groupby("author")[KEYS].transform("mean")
    corr_within = demeaned.corr()
    corr_residual = pd.DataFrame(residual, columns=KEYS).corr()
    raw_four_vif = np.diag(np.linalg.inv(corr_raw.to_numpy()))
    residual_four_vif = np.diag(np.linalg.inv(corr_residual.to_numpy()))

    # Independent checks: direct auxiliary regression vs Gram/FWL algorithms.
    vif_errors = []
    residual_vif_errors = []
    for j, key in enumerate(KEYS):
        column = x.columns.get_loc(key)
        others = np.delete(a, column, axis=1)
        auxiliary_residual = a[:, column] - matrix_product(
            others, np.linalg.lstsq(others, a[:, column], rcond=None)[0])
        direct_vif = np.square(f[key] - f[key].mean()).sum() / np.square(auxiliary_residual).sum()
        vif_errors.append(abs(float(direct_vif) - full_vif[key]))
        r_others = np.delete(residual, j, axis=1)
        r_aux = residual[:, j] - matrix_product(
            r_others, np.linalg.lstsq(r_others, residual[:, j], rcond=None)[0])
        direct_adjusted_vif = np.square(residual[:, j]).sum() / np.square(r_aux).sum()
        residual_vif_errors.append(abs(float(direct_adjusted_vif) - residual_four_vif[j]))
    check("四项完整VIF由独立辅助回归复核", max(vif_errors) < 1e-8,
          {"max_abs_error": max(vif_errors)})
    check("四项控制后VIF由残差辅助回归复核", max(residual_vif_errors) < 1e-8,
          {"max_abs_error": max(residual_vif_errors)})
    check("控制后残差与控制设计矩阵正交", float(np.abs(matrix_product(z.T, residual)).max()) < 1e-7)
    old_corr = pd.read_csv(RESULT / "within_author_feature_correlations.csv").set_index("term")
    check("作者内相关与既有结果核对", np.allclose(corr_within, old_corr.loc[KEYS, KEYS], atol=1e-12))

    pair_rows = []
    for left, right in combinations(KEYS, 2):
        both = int((f[left].eq(1) & f[right].eq(1)).sum())
        union = int((f[left].eq(1) | f[right].eq(1)).sum())
        common_terms = sorted(set(dictionary[left]).intersection(dictionary[right]))
        pair_rows.append({
            "feature_a": left, "feature_b": right,
            "n_both": both, "share_all_both": both / n, "n_either": union,
            "jaccard": both / union,
            "n_a_only": int((f[left].eq(1) & f[right].eq(0)).sum()),
            "n_b_only": int((f[left].eq(0) & f[right].eq(1)).sum()),
            "n_neither": int((f[left].eq(0) & f[right].eq(0)).sum()),
            "phi_all": float(corr_raw.loc[left, right]),
            "correlation_within_author": float(corr_within.loc[left, right]),
            "correlation_residual_controls": float(corr_residual.loc[left, right]),
            "exact_shared_term_count": len(common_terms), "exact_shared_terms": "|".join(common_terms),
        })
    pairs = pd.DataFrame(pair_rows)
    check("六组共现四格表逐一还原全样本", (pairs[["n_both", "n_a_only", "n_b_only", "n_neither"]].sum(axis=1) == n).all())
    # Direct contingency-table phi is independent of pandas correlation.
    direct_phi = (pairs.n_both * pairs.n_neither - pairs.n_a_only * pairs.n_b_only) / np.sqrt(
        (pairs.n_both + pairs.n_a_only) * (pairs.n_both + pairs.n_b_only)
        * (pairs.n_neither + pairs.n_a_only) * (pairs.n_neither + pairs.n_b_only))
    check("六组φ相关由四格表独立核对", np.allclose(direct_phi, pairs.phi_all, atol=1e-12))
    save_csv(pairs, "teacher_feedback_dictionary_pairs.csv")

    vif_rows = []
    definitions = []
    for j, key in enumerate(KEYS):
        row = {
            "feature": key, "label": DEFINITIONS[key]["label"],
            "vif_full_main_model": full_vif[key],
            "vif_four_unadjusted": float(raw_four_vif[j]),
            "vif_four_after_controls": float(residual_four_vif[j]),
            "n_hit": int(f[key].sum()), "share_all": float(f[key].mean()),
            "share_visible": float(f.loc[f.has_text.eq(1), key].mean()),
            "authors_with_within_variation": int(f.groupby("author")[key].nunique().gt(1).sum()),
        }
        vif_rows.append(row)
        definitions.append({**row, **DEFINITIONS[key], "terms": dictionary[key]})
    save_csv(pd.DataFrame(vif_rows), "teacher_feedback_dictionary_vif.csv")
    hit_count = f[KEYS].sum(axis=1)
    histogram = {str(k): int(hit_count.eq(k).sum()) for k in range(5)}
    check("多重命中分布还原样本总数与四变量总命中数",
          sum(histogram.values()) == n and sum(int(k) * v for k, v in histogram.items()) == int(f[KEYS].sum().sum()))

    input_paths = [feature_path, dictionary_path, source_path, ROOT / "code/analyze.py", RESULT / "model_fit.csv"]
    output = {
        "purpose": "回应老师关于四个词典变量的分类理由及共线性疑问；基于冻结M3设计，不改动原始编码与模型。",
        "model": "M3_作者与日期固定效应", "n_posts": n, "n_authors": int(f.author.nunique()),
        "design_columns": int(x.shape[1]), "design_rank": rank,
        "definitions": definitions,
        "classification_note": "三类词汇规则加一类问号标点规则，分别描述目标行动、面向他人、积极表述和疑问标点；为研究者制定的操作性编码，未经过独立语义效度验证，不构成四个独立心理因子。",
        "overlap_note": "四个变量允许同帖同时为1，无需互斥或加总为1；无完全相同词项不代表语义互斥。加油、谢谢等仍有跨维度解释空间。",
        "summary": {
            "max_abs_phi_all": float(pairs.phi_all.abs().max()),
            "max_abs_correlation_within_author": float(pairs.correlation_within_author.abs().max()),
            "max_abs_correlation_residual_controls": float(pairs.correlation_residual_controls.abs().max()),
            "min_vif_full_main_model": min(full_vif.values()), "max_vif_full_main_model": max(full_vif.values()),
            "max_vif_four_after_controls": float(max(residual_four_vif)),
            "exact_shared_term_count_all_pairs": int(pairs.exact_shared_term_count.sum()),
            "n_posts_multiple_indicators": int(hit_count.ge(2).sum()),
            "share_posts_multiple_indicators": float(hit_count.ge(2).mean()),
            "n_posts_any_indicator": int(hit_count.ge(1).sum()), "hit_count_histogram": histogram,
        },
        "conclusion": "四个现有规则在本样本及完整M3设计中未呈现明显数值共线性，不支持仅因担心重复而合并。该结果不证明语义独立，也不能排除漏判、误判或共同未测因素。",
        "methods": {
            "phi_all": "在9,532条帖子中计算二元变量Pearson相关，即φ系数；作者内相关先按作者去均值。",
            "vif_full_main_model": "VIF_j=1/(1-R_j²)，R_j²来自该词典变量对完整M3中全部其余设计列（含截距）的辅助回归；由(X'X)^(-1)对角元乘以该变量中心化平方和计算，另以最小二乘辅助回归独立复核。",
            "vif_four_after_controls": "先将四变量分别投影剔除长度、正文可见性、话题标签、表情、课程标记、媒体、帖子类型、时段、作者和日期固定效应，再用四残差的相关矩阵逆矩阵对角元计算；仅描述控制后四变量彼此的冗余，不能替代完整M3 VIF。",
            "interpretation": "完整M3 VIF用于判断与所有已纳入解释变量的线性重复，语义分类是否合理仍需人工标注验证。VIF属于设计矩阵诊断，不是聚类稳健标准误的修正系数。",
            "reference": "https://www.statsmodels.org/v0.14.6/generated/statsmodels.stats.outliers_influence.variance_inflation_factor.html",
        },
        "reproduce": "python code/analyze_dictionary_diagnostics.py",
        "software": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__},
        "inputs": [{"path": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in input_paths],
        "validation": {"path": "validation/teacher_feedback/dictionary_checks.json", "checks_passed": len(checks)},
    }
    (RESULT / "teacher_feedback_dictionary.json").write_text(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    (QA / "dictionary_checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"checks_passed": len(checks), **output["summary"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
