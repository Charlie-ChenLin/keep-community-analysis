"""Scoped checks of author fixed effects and independent hashtag fields.

Run: OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python code/analyze_author_tags_feedback.py
Existing results are read only. Supplementary models keep the original five-term
family, author/date FE, author-clustered t inference and within-model BH adjustment.
"""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re
import sys

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"
PREFIX = "teacher_author_tags_"
FOCAL = ["log_length", "self_discipline", "social_address", "positive_expression", "question"]
DICTIONARY = json.loads((ROOT / "code/text_dictionary.json").read_text())
RHS = " + ".join(FOCAL + ["has_text", "has_tag", "emoji_count", "course_ref"]) + " + C(contentTypeStr) + C(type) + C(time_bin) + C(author) + C(date)"


def clean_text(value):
    # Independently implement the documented body cleaning to check saved features.
    s = "" if pd.isna(value) else str(value)
    s = s.replace("\\n", "\n").replace("\\r", " ")
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"Ⓚ[^Ⓚ]*Ⓚ", " ", s)
    s = re.sub(r"\[[^\[\]]{1,12}\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def encode(texts):
    out = pd.DataFrame(index=texts.index)
    out["length"] = texts.str.replace(r"\s", "", regex=True).str.len()
    out["log_length"] = np.log1p(out.length)
    for term in FOCAL[1:]:
        words = DICTIONARY[term]
        pattern = "|".join(words) if term == "self_discipline" else "|".join(map(re.escape, words))
        out[term] = texts.str.contains(pattern, regex=True).astype(int)
    return out


def write_csv(df, name):
    df.to_csv(RESULT / (PREFIX + name + ".csv"), index=False, encoding="utf-8-sig")


def main():
    source_files = [ROOT / "2026Data/Keep Data/sample_post_2022.csv", RESULT / "post_features.csv", ROOT / "code/text_dictionary.json", ROOT / "code/analyze.py", RESULT / "regression_coefficients.csv"]
    before_hash = {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in source_files}
    raw = pd.read_csv(source_files[0])
    saved = pd.read_csv(RESULT / "post_features.csv")
    p = saved.merge(raw[["postId", "userId", "content", "hashTags"]], on="postId", validate="one_to_one")
    checks = []

    def check(name, passed, detail=None):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})
        if not passed:
            raise AssertionError(name)

    check("one-to-one raw/saved post coverage", len(p) == len(raw) == len(saved))
    check("anonymous authors map one-to-one to source authors", p.groupby("author").userId.nunique().eq(1).all() and p.groupby("userId").author.nunique().eq(1).all())
    body = p.content.map(clean_text)
    decoded_body = encode(body)
    check("all saved body dictionary indicators independently reproduced", np.array_equal(decoded_body[FOCAL[1:]].to_numpy(), p[FOCAL[1:]].to_numpy()))
    check("saved body lengths independently reproduced", np.array_equal(decoded_body.length.to_numpy(), p.length.to_numpy()))
    tags = p.hashTags.map(lambda s: json.loads(s.replace('""', '"')))
    check("all hashtag values parsed as arrays of strings", tags.map(lambda x: isinstance(x, list) and all(isinstance(t, str) for t in x)).all())
    check("saved has_tag agrees with nonempty parsed array", np.array_equal(tags.map(bool).astype(int), p.has_tag))
    p["tag_count"] = tags.map(len)
    counts = p.groupby("author").size().sort_index()
    raw_counts = raw.groupby("userId").size()
    check("author count distribution independently reproduced from raw IDs", sorted(counts.tolist()) == sorted(raw_counts.tolist()))
    author_rows = pd.DataFrame({"author": counts.index, "posts": counts.values})
    grouped = p.groupby("author")
    for term in FOCAL[1:]:
        author_rows[term + "_varies"] = grouped[term].nunique().gt(1).reindex(counts.index).astype(int).to_numpy()
    author_rows["log_length_varies"] = grouped.log_length.nunique().gt(1).reindex(counts.index).astype(int).to_numpy()
    write_csv(author_rows, "author_counts")
    low_rows = []
    for cutoff in [1, 2, 5, 10, 20]:
        low = counts[counts.le(cutoff)]
        low_rows.append({"at_most_posts": cutoff, "authors": len(low), "posts": int(low.sum()), "share_posts": float(low.sum()/len(p))})
    write_csv(pd.DataFrame(low_rows), "small_author_counts")
    within_rows = []
    for term in FOCAL:
        varies = grouped[term].nunique().gt(1)
        within_rows.append({"term": term, "authors_within_variation": int(varies.sum()), "posts_in_varying_authors": int(p.author.isin(varies.index[varies]).sum()), "total_authors": len(counts), "note": "Unadjusted author-within variation; other controls can further affect usable variation."})
    write_csv(pd.DataFrame(within_rows), "within_variation")

    tag_frequency = Counter()
    tag_authors = defaultdict(set)
    for author, arr in zip(p.author, tags):
        for tag in set(arr):
            tag_frequency[tag] += 1
            tag_authors[tag].add(author)
    # Outcome-free rule: at least 30 posts and at least 5 distinct sample authors.
    selected = sorted([t for t in tag_frequency if tag_frequency[t] >= 30 and len(tag_authors[t]) >= 5], key=lambda t: (-tag_frequency[t], t))
    tag_rows = []
    tag_columns = []
    for i, tag in enumerate(selected):
        name = f"tag_identity_{i:02d}"
        p[name] = tags.map(lambda arr: int(tag in arr))
        tag_columns.append(name)
        tag_rows.append({"tag": tag, "term": name, "posts": tag_frequency[tag], "authors": len(tag_authors[tag]), "within_varying_authors": int(p.groupby("author")[name].nunique().gt(1).sum())})
    write_csv(pd.DataFrame(tag_rows), "selected_tags")
    write_csv(pd.DataFrame([{"tag": t, "posts": n, "authors": len(tag_authors[t]), "selected": t in selected} for t, n in tag_frequency.most_common()]), "tag_frequency")

    combined = body + " " + tags.map(lambda arr: " ".join(arr))
    combined_encoded = encode(combined)
    tagged = p.copy()
    for term in FOCAL + ["length"]:
        tagged[term] = combined_encoded[term]
    tagged["has_text"] = (p.has_text.eq(1) | p.has_tag.eq(1)).astype(int)
    change_rows = []
    for term in FOCAL[1:]:
        old = p[term].eq(1)
        new = tagged[term].eq(1)
        change_rows.append({"term": term, "body_hits": int(old.sum()), "body_plus_tag_hits": int(new.sum()), "new_tag_only_hits": int((new & ~old).sum()), "new_hits_with_missing_body": int((new & ~old & p.has_text.eq(0)).sum()), "lost_hits": int((old & ~new).sum())})
    write_csv(pd.DataFrame(change_rows), "tag_recoding_changes")
    check("appending tags cannot lose existing body dictionary hits", all(r["lost_hits"] == 0 for r in change_rows))

    specs = [("baseline_body", p, RHS, "Original body-only model, already controls has_tag"),
             ("authors_ge5", p[p.author.isin(counts.index[counts.ge(5)])].copy(), RHS, "Exclude authors with fewer than 5 posts"),
             ("authors_ge10", p[p.author.isin(counts.index[counts.ge(10)])].copy(), RHS, "Exclude authors with fewer than 10 posts"),
             ("body_tag_identity_controls", p, RHS + " + " + " + ".join(tag_columns), "Original body coding plus outcome-free frequent hashtag identity indicators"),
             ("body_plus_tags_recoded", tagged, RHS, "Redefine text as body plus tags; new measurement scope, supplementary only")]
    model_rows, coef_rows = [], []
    original_coeff = pd.read_csv(RESULT / "regression_coefficients.csv")
    original_coeff = original_coeff[original_coeff.model.eq("M3_作者与日期固定效应")].set_index("term")
    for name, frame, rhs, note in specs:
        fit = smf.ols("log_likes ~ " + rhs, data=frame).fit(cov_type="cluster", cov_kwds={"groups": frame.author, "use_correction": True, "df_correction": True}, use_t=True)
        rank = int(np.linalg.matrix_rank(fit.model.exog))
        check(name + " design full column rank", rank == len(fit.params), {"rank": rank, "columns": len(fit.params)})
        check(name + " expected row count", int(fit.nobs) == len(frame))
        joint = fit.wald_test(" = 0, ".join(FOCAL) + " = 0", scalar=True)
        q = multipletests([fit.pvalues[t] for t in FOCAL], method="fdr_bh")[1]
        ci = fit.conf_int()
        for term, qval in zip(FOCAL, q):
            coef_rows.append({"model": name, "term": term, "coef": float(fit.params[term]), "se_cluster": float(fit.bse[term]), "p": float(fit.pvalues[term]), "q_bh_five": float(qval), "ci_low": float(ci.loc[term, 0]), "ci_high": float(ci.loc[term, 1]), "delta_from_baseline_body": float(fit.params[term] - original_coeff.loc[term, "coef"])})
        model_rows.append({"model": name, "n": int(fit.nobs), "authors": int(frame.author.nunique()), "parameters": len(fit.params), "rank": rank, "cluster_inference_df": int(frame.author.nunique()) - 1, "r_squared": float(fit.rsquared), "joint_five_p": float(joint.pvalue), "joint_five_F": float(joint.statistic), "note": note})
        if name == "baseline_body":
            check("baseline coefficients agree with saved main model", np.allclose([fit.params[t] for t in FOCAL], original_coeff.loc[FOCAL, "coef"], atol=1e-10, rtol=1e-9))
            check("baseline cluster SE agree with saved main model", np.allclose([fit.bse[t] for t in FOCAL], original_coeff.loc[FOCAL, "se_cluster"], atol=1e-10, rtol=1e-9))
        print(f"Completed {name}: n={int(fit.nobs)}, authors={frame.author.nunique()}, joint p={float(joint.pvalue):.6g}", flush=True)
    write_csv(pd.DataFrame(model_rows), "model_fit")
    write_csv(pd.DataFrame(coef_rows), "coefficients")
    check("all original source files unchanged", all(hashlib.sha256(f.read_bytes()).hexdigest() == before_hash[str(f.relative_to(ROOT))] for f in source_files))
    output = {
        "source_hashes": before_hash,
        "selection_rules": {"small_author_robustness": "Retain authors with >=5 or >=10 observed posts; thresholds not selected by inference.", "hashtag_identity_controls": "Tags in >=30 posts and >=5 authors, selected solely from exposure frequency; 9 indicators plus original has_tag.", "tag_count_control": "Not used: 5207 posts have one tag, two have two tags; a count control beyond has_tag is identified by only 2 posts."},
        "author_distribution": {k: float(v) for k, v in counts.describe(percentiles=[.05, .1, .25, .5, .75, .9, .95]).to_dict().items()},
        "small_author_counts": low_rows,
        "within_variation": within_rows,
        "tag_summary": {"tagged_posts": int(p.has_tag.sum()), "tagged_share": float(p.has_tag.mean()), "unique_tags": len(tag_frequency), "selected_tag_identity_controls": len(selected), "tag_count_distribution": {str(k): int(v) for k, v in p.tag_count.value_counts().sort_index().items()}, "missing_body_with_tags": int((p.has_text.eq(0) & p.has_tag.eq(1)).sum()), "combined_text_available": int(tagged.has_text.sum()), "literal_hash_in_body_posts": int(p.content.fillna("").str.contains("#", regex=False).sum())},
        "selected_tags": tag_rows,
        "tag_recoding_changes": change_rows,
        "model_fit": model_rows,
        "coefficients": coef_rows,
        "interpretation": ["Two singleton authors have no within-author variation and contribute no author-within slope information; excluding low-count authors checks a distinct concern from the existing equal-author weighting analysis.", "Few posts per author does not mechanically invalidate OLS author fixed effects; slope estimates rely on within-author variation, and rare indicators can be supported by substantially fewer than 100 authors.", "Observed post counts are within this course sample, not complete lifetime author activity.", "The original main model already includes hashtag presence; controlling selected tag identities retains original body-only measurement and remains observational.", "Appending tags changes the text construct and turns prompt phrases into measured words; results cannot establish that original body expressions have those associations.", "Supplementary five-test BH adjustments are within each model, not a single correction across all exploratory model/term comparisons."],
        "validation": {"passed": all(c["passed"] for c in checks), "checks": len(checks)},
        "python": sys.executable,
    }
    (RESULT / (PREFIX + "summary.json")).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (RESULT / (PREFIX + "validation.json")).write_text(json.dumps({"passed": all(c["passed"] for c in checks), "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output["tag_summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
