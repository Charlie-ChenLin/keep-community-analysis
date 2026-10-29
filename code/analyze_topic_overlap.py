"""Respond to the topic-overlap question using the existing frozen NMF weights.

Run: OPENBLAS_NUM_THREADS=1 /opt/anaconda3/bin/python code/analyze_topic_overlap.py
No refitting, relabelling, outcome-based threshold selection, or overwriting of
the original topic results. Only aggregate teacher_topic_* files are written.
The new multi-label rules are exploratory descriptions, not semantic labels.
"""
from pathlib import Path
import hashlib
import importlib.metadata
import json

import numpy as np
import pandas as pd
import scipy.linalg as la
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"
TOPICS = [f"topic_{i}" for i in range(5)]
THRESHOLDS = [0.15, 0.20, 0.25]
PRIMARY_THRESHOLD = 0.20
FOCAL = ["log_length", "self_discipline", "social_address", "positive_expression", "question"]
CONTROLS = (
    "has_tag + emoji_count + course_ref + C(contentTypeStr) + C(type)"
    " + C(time_bin) + C(author) + C(date)"
)
BASE_RHS = " + ".join(FOCAL) + " + " + CONTROLS


def save_csv(frame, suffix):
    frame.to_csv(RESULT / f"teacher_topic_{suffix}.csv", index=False, encoding="utf-8-sig")


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fit_clustered(data, terms):
    fit = smf.ols("log_likes ~ " + BASE_RHS + " + " + " + ".join(terms), data=data).fit(
        cov_type="cluster",
        cov_kwds={"groups": data.author, "use_correction": True, "df_correction": True},
        use_t=True,
    )
    joint = fit.wald_test(" = 0, ".join(terms) + " = 0", scalar=True)
    intervals = fit.conf_int()
    rows = [
        {
            "term": term,
            "coef": float(fit.params[term]),
            "se_cluster": float(fit.bse[term]),
            "ci_low": float(intervals.loc[term, 0]),
            "ci_high": float(intervals.loc[term, 1]),
            "p": float(fit.pvalues[term]),
        }
        for term in terms
    ]
    q = multipletests([row["p"] for row in rows], method="fdr_bh")[1]
    for row, value in zip(rows, q):
        row["q_bh"] = float(value)
    return fit, float(joint.pvalue), rows


def main():
    paths = {
        "posts": RESULT / "post_features.csv",
        "frozen_weights": RESULT / "extension_post_topics.csv",
        "original_topic_coefficients": RESULT / "extension_topic_regression.csv",
        "original_topic_summary": RESULT / "extension_summary.json",
        "labels": ROOT / "code/topic_labels.json",
    }
    posts = pd.read_csv(paths["posts"])
    frozen = pd.read_csv(paths["frozen_weights"])
    labels = json.loads(paths["labels"].read_text())["labels"]
    original = json.loads(paths["original_topic_summary"].read_text())["topics"]
    assert posts.postId.is_unique and frozen.postId.is_unique
    assert frozen.postId.isin(posts.postId).all()
    data = posts.merge(frozen.rename(columns={"author": "source_author"}), on="postId", validate="one_to_one")
    assert data.groupby("author").source_author.nunique().eq(1).all()
    assert data.groupby("source_author").author.nunique().eq(1).all()
    assert data.has_text.eq(1).all(), "The original topic model excludes constant has_text."
    weights = data[TOPICS].to_numpy()
    assert np.isfinite(weights).all() and (weights >= 0).all() and (weights <= 1).all()
    assert np.allclose(weights.sum(axis=1), 1, atol=1e-12)
    dominant = weights.argmax(axis=1)
    frozen_dominant_counts = np.bincount(dominant, minlength=5)
    reference = int(frozen_dominant_counts.argmax())
    assert reference == original["reference_topic"] == 2

    # Independent refit of the original continuous-weight parameterization.
    continuous_terms = [term for i, term in enumerate(TOPICS) if i != reference]
    continuous_fit, continuous_p, continuous_rows = fit_clustered(data, continuous_terms)
    original_coefficients = pd.read_csv(paths["original_topic_coefficients"])
    errors = []
    for row in continuous_rows:
        topic = int(row["term"].split("_")[-1])
        old = original_coefficients.loc[original_coefficients.topic.eq(topic)].iloc[0]
        for field in ["coef", "se_cluster", "ci_low", "ci_high", "p", "q_bh"]:
            errors.append(abs(row[field] - float(old[field])))
    assert max(errors) < 1e-9
    assert abs(continuous_p - original["joint_topic_p"]) < 1e-9

    prevalence_rows, pair_rows, distribution_rows, model_rows, coefficient_rows = [], [], [], [], []
    threshold_summaries = []
    for threshold in THRESHOLDS:
        # Do not assume an all-zero group exists: verify the observed label counts.
        binary = (weights >= threshold).astype(int)
        binary_terms = [f"topic_present_{i}" for i in range(5)]
        counts = binary.sum(axis=1)
        assert (counts >= 1).all()
        for i, term in enumerate(binary_terms):
            data[term] = binary[:, i]
            prevalence_rows.append({
                "threshold": threshold, "topic": i, "label": labels[str(i)],
                "documents": int(binary[:, i].sum()), "share": float(binary[:, i].mean()),
                "authors": int(data.loc[data[term].eq(1), "author"].nunique()),
                "denominator": len(data),
            })
        for i in range(5):
            for j in range(i + 1, 5):
                intersection = int((binary[:, i] * binary[:, j]).sum())
                union = int(((binary[:, i] + binary[:, j]) > 0).sum())
                pair_rows.append({
                    "threshold": threshold, "topic_a": i, "topic_b": j,
                    "label_a": labels[str(i)], "label_b": labels[str(j)],
                    "intersection_documents": intersection,
                    "share_all": intersection / len(data),
                    "jaccard": intersection / union if union else None,
                })
        for n in range(6):
            distribution_rows.append({"threshold": threshold, "active_topics": n,
                                      "documents": int((counts == n).sum()), "share": float((counts == n).mean())})
        fit, joint_p, coefficients = fit_clustered(data, binary_terms)
        full_rank = int(np.linalg.matrix_rank(fit.model.exog))
        assert full_rank == len(fit.params), "Do not report aliased coefficients."
        binary_rank = int(np.linalg.matrix_rank(np.column_stack([np.ones(len(binary)), binary])))
        assert binary_rank == 6
        # VIF after conditioning on all non-topic terms: additional inflation due
        # to the other four indicators, distinct from control/FE predictability.
        control_fit = smf.ols("log_likes ~ " + BASE_RHS, data=data)
        cmat = control_fit.exog
        u, singular, _ = la.svd(cmat, full_matrices=False)
        basis = u[:, singular > singular.max() * max(cmat.shape) * np.finfo(float).eps]
        residual = binary - basis @ (basis.T @ binary)
        corr = np.corrcoef(residual.T)
        conditional_vif = np.diag(np.linalg.inv(corr))
        for i, row in enumerate(coefficients):
            row.update({"threshold": threshold, "topic": i, "label": labels[str(i)],
                        "pct_likes_plus1_for_0_to_1": float(100 * np.expm1(row["coef"])),
                        "conditional_topic_vif": float(conditional_vif[i])})
            coefficient_rows.append(row)
        model = {"threshold": threshold, "documents": len(data), "authors": int(data.author.nunique()),
                 "joint_topic_p": joint_p, "r_squared": float(fit.rsquared),
                 "design_rank": full_rank, "parameters": len(fit.params),
                 "intercept_plus_five_indicators_rank": binary_rank,
                 "min_conditional_vif": float(min(conditional_vif)),
                 "max_conditional_vif": float(max(conditional_vif)),
                 "min_bh_q": min(row["q_bh"] for row in coefficients),
                 "multi_topic_documents": int((counts >= 2).sum()),
                 "multi_topic_share": float((counts >= 2).mean()),
                 "sum_prevalence": float(binary.mean(axis=0).sum()),
                 "no_label_documents": int((counts == 0).sum())}
        model_rows.append(model)
        threshold_summaries.append(model)

    save_csv(pd.DataFrame(prevalence_rows), "prevalence")
    save_csv(pd.DataFrame(pair_rows), "cooccurrence")
    save_csv(pd.DataFrame(distribution_rows), "label_count_distribution")
    save_csv(pd.DataFrame(model_rows), "models")
    save_csv(pd.DataFrame(coefficient_rows), "regression")
    checks = {
        "frozen_post_ids_unique": bool(frozen.postId.is_unique),
        "one_to_one_join_preserves_all_topic_rows": len(data) == len(frozen),
        "original_and_anonymous_authors_map_one_to_one": True,
        "weights_finite_and_in_unit_interval": True,
        "weights_sum_to_one_max_error": float(np.max(abs(weights.sum(1) - 1))),
        "continuous_coefficient_max_error": float(max(errors)),
        "continuous_joint_p_error": float(abs(continuous_p - original["joint_topic_p"])),
        "continuous_design_rank": int(np.linalg.matrix_rank(continuous_fit.model.exog)),
        "continuous_parameters": len(continuous_fit.params),
        "all_multilabel_designs_full_rank": all(row["design_rank"] == row["parameters"] for row in model_rows),
        "all_five_indicator_plus_intercept_ranks_equal_six": all(row["intercept_plus_five_indicators_rank"] == 6 for row in model_rows),
    }
    summary = {
        "purpose": "老师反馈：主题含义可并存，明确连续权重、主导分类与探索性多标签的区别。",
        "as_of": "2026-10-29",
        "documents": len(data), "authors": int(data.author.nunique()),
        "all_posts": len(posts), "excluded_from_frozen_assigned_topics": len(posts) - len(data),
        "fitted_documents_original": original["fitted_documents"],
        "near_zero_contribution_excluded_original": original["near_zero_contribution_documents"],
        "fractional_weight_documents": int((((weights > 0) & (weights < 1)).any(axis=1)).sum()),
        "fractional_weight_entries": int(((weights > 0) & (weights < 1)).sum()),
        "original_dominant_counts": frozen_dominant_counts.tolist(),
        "labels": labels,
        "primary_threshold": PRIMARY_THRESHOLD,
        "thresholds": THRESHOLDS,
        "threshold_definition": "topic_present_k = 1 if the frozen normalized NMF weight w_k >= threshold; else 0",
        "threshold_selection": "Exploratory, outcome-independent convenience thresholds; 0.20=1/5. Chosen after the original analysis; not preregistered or semantically validated.",
        "original_continuous_model": {
            "reference_topic": reference, "reference_label": labels[str(reference)],
            "joint_topic_p": continuous_p,
            "coefficient_interpretation": "A 0.10 rise of w_k replacing 0.10 of reference-topic weight with all other weights and covariates fixed; 100*(exp(0.10*theta_k)-1) is the conditional geometric-mean change in likes+1.",
            "why_omit_one_weight": "Five normalized weights sum to one, so five weights plus intercept are exactly collinear. This compositional constraint does not imply mutually exclusive semantics.",
        },
        "multilabel_model": {
            "formula": "log_likes ~ " + BASE_RHS + " + " + " + ".join(f"topic_present_{i}" for i in range(5)),
            "no_reference_topic": "All five binary indicators enter together; their row sums vary. Full-rank checks, rather than k-1 dummy coding, determine estimability.",
            "coefficient_interpretation": "Conditional 0-to-1 indicator contrast with other four indicators and covariates held fixed; not a contrast to a single reference topic and not a causal effect.",
            "uncertainty": "Author-clustered t inference, finite-sample correction, 95% individual intervals; BH correction across five topic coefficients at each threshold. Uncertainty from NMF estimation and threshold choice is not included.",
            "multiple_thresholds": "Threshold results are sensitivity diagnostics. No significance search or selection among thresholds; five-term BH is per specification, not across the full family of sensitivity models.",
            "no_all_zero_group": "At thresholds 0.15, 0.20, 0.25, every assigned post has at least one label; coefficients are conditional contrasts, not comparisons to an observed no-topic group.",
        },
        "threshold_results": threshold_summaries,
        "scope": "All proportions use the 2,470 assigned-text posts, not all 9,532 posts. The original eight near-zero-contribution documents and all other ineligible posts remain unassigned, rather than being coded as five observed zeros.",
        "checks": checks,
        "input_sha256": {key: sha256(path) for key, path in paths.items()},
        "package_versions": {key: importlib.metadata.version(key) for key in ["numpy", "pandas", "scipy", "statsmodels"]},
    }
    (RESULT / "teacher_topic_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"threshold_results": threshold_summaries, "checks": checks}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
