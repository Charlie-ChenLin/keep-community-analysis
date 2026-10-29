"""Independent counts and manual clustered-OLS check for the topic addendum."""
from pathlib import Path
from collections import Counter
import csv
import json

import numpy as np
import pandas as pd
import patsy
import scipy.linalg as la
from scipy.stats import f as f_distribution, t as t_distribution


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"
QA = ROOT / "validation/teacher_feedback"


def records(name):
    with (RESULT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    frozen = records("extension_post_topics.csv")
    prevalence = records("teacher_topic_prevalence.csv")
    distributions = records("teacher_topic_label_count_distribution.csv")
    pairs = records("teacher_topic_cooccurrence.csv")
    summary = json.loads((RESULT / "teacher_topic_summary.json").read_text())
    count_checks = 0
    for threshold in summary["thresholds"]:
        labels = [tuple(float(row[f"topic_{i}"]) >= threshold for i in range(5)) for row in frozen]
        histogram = Counter(sum(row) for row in labels)
        for row in prevalence:
            if float(row["threshold"]) != threshold:
                continue
            i = int(row["topic"])
            assert sum(int(label[i]) for label in labels) == int(row["documents"])
            count_checks += 1
        for row in distributions:
            if float(row["threshold"]) == threshold:
                assert histogram[int(row["active_topics"])] == int(row["documents"])
                count_checks += 1
        for row in pairs:
            if float(row["threshold"]) != threshold:
                continue
            i, j = int(row["topic_a"]), int(row["topic_b"])
            assert sum(int(label[i] and label[j]) for label in labels) == int(row["intersection_documents"])
            count_checks += 1

    # Build the same documented design but solve QR normal equations and the
    # cluster sandwich directly, without statsmodels' fit or covariance helpers.
    posts = pd.read_csv(RESULT / "post_features.csv")
    weights = pd.read_csv(RESULT / "extension_post_topics.csv").drop(columns="author")
    data = posts.merge(weights, on="postId", validate="one_to_one")
    for i in range(5):
        data[f"topic_present_{i}"] = data[f"topic_{i}"].ge(0.20).astype(int)
    topic_terms = [f"topic_present_{i}" for i in range(5)]
    formula = summary["multilabel_model"]["formula"]
    y, design = patsy.dmatrices(formula, data, return_type="dataframe")
    x = design.to_numpy()
    outcome = y.to_numpy().ravel()
    q, r = la.qr(x, mode="economic")
    beta = la.solve_triangular(r, q.T @ outcome)
    resid = outcome - x @ beta
    inverse_r = la.solve_triangular(r, np.eye(r.shape[0]))
    bread = inverse_r @ inverse_r.T
    scores = x * resid[:, None]
    author_scores = pd.DataFrame(scores).groupby(data.author.to_numpy()).sum().to_numpy()
    g, n, k = len(author_scores), len(x), x.shape[1]
    factor = g / (g - 1) * (n - 1) / (n - k)
    covariance = factor * bread @ (author_scores.T @ author_scores) @ bread
    positions = [design.columns.get_loc(term) for term in topic_terms]
    estimates = beta[positions]
    ses = np.sqrt(np.diag(covariance)[positions])
    p_values = 2 * t_distribution.sf(abs(estimates / ses), df=g - 1)
    critical = t_distribution.ppf(0.975, df=g - 1)
    joint_f = float(estimates @ la.solve(covariance[np.ix_(positions, positions)], estimates) / len(positions))
    joint_p = float(f_distribution.sf(joint_f, len(positions), g - 1))
    saved = pd.read_csv(RESULT / "teacher_topic_regression.csv").query("threshold == 0.20").sort_values("topic")
    differences = {
        "coef": float(np.max(abs(estimates - saved.coef))),
        "se_cluster": float(np.max(abs(ses - saved.se_cluster))),
        "p": float(np.max(abs(p_values - saved.p))),
        "ci_low": float(np.max(abs(estimates - critical * ses - saved.ci_low))),
        "ci_high": float(np.max(abs(estimates + critical * ses - saved.ci_high))),
    }
    stored_model = next(row for row in summary["threshold_results"] if row["threshold"] == 0.20)
    differences["joint_p"] = abs(joint_p - stored_model["joint_topic_p"])
    assert max(differences.values()) < 1e-9, differences
    QA.mkdir(parents=True, exist_ok=True)
    result = {
        "count_method": "stdlib CSV iteration and boolean tuples, independently of the analysis vectorization",
        "count_checks_passed": count_checks,
        "manual_model_method": "Patsy documented design, scipy QR coefficients, manually aggregated cluster scores and sandwich covariance with G/(G-1)*(N-1)/(N-K) correction; t/F df=G-1",
        "manual_main_threshold": 0.20,
        "manual_model_n": n, "manual_model_clusters": g, "manual_model_parameters": k,
        "max_absolute_difference": differences,
        "all_checks_passed": True,
    }
    (QA / "topic_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
