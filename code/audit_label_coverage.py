"""Freeze outcome-blind text samples for checking the scope of content labels.

The sample is for a single AI-assisted semantic screening, not a gold standard.
Raw text and post IDs remain in ignored local files. No model is refitted here.
"""
from pathlib import Path
import hashlib
import json
import re

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "validation/teacher_feedback"
SEED = 20261029


def clean(value):
    s = "" if pd.isna(value) else str(value)
    s = s.replace("\\n", "\n").replace("\\r", " ")
    s = re.sub(r"https?://\S+", " ", s)
    s = re.sub(r"Ⓚ[^Ⓚ]*Ⓚ", " ", s)
    s = re.sub(r"\[[^\[\]]{1,12}\]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    QA.mkdir(parents=True, exist_ok=True)
    raw_path = ROOT / "2026Data/Keep Data/sample_post_2022.csv"
    paths = [raw_path, ROOT / "results/post_features.csv", ROOT / "results/extension_post_topics.csv"]
    raw = pd.read_csv(raw_path, dtype={"postId": str})
    p = pd.read_csv(paths[1], dtype={"postId": str})
    t = pd.read_csv(paths[2], dtype={"postId": str})
    p = p.merge(raw[["postId", "content", "hashTags"]], on="postId", validate="one_to_one")
    p["clean_text"] = p.content.map(clean)
    assert p.clean_text.str.replace(r"\s", "", regex=True).str.len().eq(p.length).all()
    p = p.merge(t.drop(columns="author"), on="postId", how="left", validate="one_to_one")
    cols = [f"topic_{i}" for i in range(5)]
    assigned = p[cols].notna().all(axis=1)
    p["dominant"] = -1
    p.loc[assigned, "dominant"] = p.loc[assigned, cols].to_numpy().argmax(axis=1)
    p["maximum_weight"] = p[cols].max(axis=1)
    samples = []
    # Equal allocations expose each small component; this is not a simple random
    # sample of all posts. Do not report an unweighted overall error rate.
    for k in range(5):
        frame = p.loc[p.dominant.eq(k)].sort_values("postId")
        take = frame.sample(n=12, random_state=SEED + k).sort_values("postId")
        for j, (_, row) in enumerate(take.iterrows(), 1):
            samples.append({"sample_id": f"T{k}-{j:02d}", "stratum": f"topic_{k}",
                            "population": len(frame), "inclusion_probability": 12 / len(frame),
                            **row[["postId", "clean_text", "hashTags", "dominant", "maximum_weight"]].to_dict()})
    frame = p.loc[~assigned & p.length.gt(0)].sort_values("postId")
    take = frame.sample(n=20, random_state=SEED + 10).sort_values("postId")
    for j, (_, row) in enumerate(take.iterrows(), 1):
        samples.append({"sample_id": f"U-{j:02d}", "stratum": "unassigned_nonempty",
                        "population": len(frame), "inclusion_probability": 20 / len(frame),
                        **row[["postId", "clean_text", "hashTags", "dominant", "maximum_weight"]].to_dict()})
    pd.DataFrame(samples).to_csv(QA / "label_review_private.csv", index=False, encoding="utf-8-sig")
    dcols = ["self_discipline", "social_address", "positive_expression", "question"]
    any_hit = p[dcols].max(axis=1).eq(1)
    summary = {
        "seed": SEED, "posts": len(p), "raw_body_available": int(p.has_text.sum()),
        "nonempty_clean_body": int(p.length.gt(0).sum()), "clean_empty": int(p.length.eq(0).sum()),
        "dictionary_any_hit": int(any_hit.sum()),
        "dictionary_no_hit_nonempty": int((~any_hit & p.length.gt(0)).sum()),
        "dictionary_no_hit_all": int((~any_hit).sum()),
        "nmf_assigned": int(assigned.sum()),
        "nmf_unassigned_nonempty": int((~assigned & p.length.gt(0)).sum()),
        "nmf_assigned_share_all": float(assigned.mean()),
        "nmf_assigned_share_nonempty": float(assigned.sum() / p.length.gt(0).sum()),
        "sample_by_stratum": pd.DataFrame(samples).groupby("stratum").size().to_dict(),
        "sample_note": "12 posts per dominant topic plus 20 nonempty unassigned posts, selected without likes. Equal topic allocations are not a simple random sample. Semantic screening is AI-assisted, single-pass, not independent human validation.",
        "input_sha256": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in paths},
    }
    annotations = json.loads((ROOT / 'code/label_review_annotations.json').read_text())
    assigned_samples = {s['sample_id'] for s in samples if s['stratum'] != 'unassigned_nonempty'}
    assert assigned_samples == set(annotations['assigned'])
    assert {s['sample_id'] for s in samples if s['stratum'] == 'unassigned_nonempty'} == set(annotations['unassigned_notes'])
    review_counts = {}
    for k in range(5):
        statuses = pd.Series([annotations['assigned'][s['sample_id']][0] for s in samples if s['stratum'] == f'topic_{k}'])
        review_counts[str(k)] = {status: int(statuses.eq(status).sum()) for status in annotations['definitions']}
    summary['single_ai_review'] = {'by_original_dominant_topic': review_counts,
                                  'total': {status: sum(x[status] for x in review_counts.values()) for status in annotations['definitions']},
                                  'caution': annotations['caution'], 'reviewer_type': annotations['reviewer_type']}
    (ROOT / "results/teacher_label_coverage_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    for s in samples:
        s = s.copy()
        s.pop("postId")
        s["clean_text"] = s["clean_text"][:500]
        print(json.dumps(s, ensure_ascii=False))


if __name__ == "__main__":
    main()
