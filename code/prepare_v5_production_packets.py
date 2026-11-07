#!/usr/bin/env python3
"""Prepare outcome-blind v5 production reading packets without classifying.

All row-level exports remain under the repository's ignored private directory.
Every exact cleaned text is presented once; a private post map retains the
original population and multiplicity. Trial labels are never read or copied.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "validation/classification_rebuild/private"
SOURCE = PRIVATE / "v2_direct_batches"
TRIAL = PRIVATE / "variable_scheme_v5"
CODEBOOK = ROOT / "正文多维测量方案_v5_编码手册.md"
PROTOCOL = ROOT / "code/variable_scheme_v5_protocol.json"
DEFAULT_OUTPUT = PRIVATE / "variable_scheme_v5_production"
PUBLIC_OUTPUT = ROOT / "results/v5_production_preparation.json"
BATCH_SIZE = 50
EXPECTED_STATES = {
    "raw_body_unavailable": 3984,
    "needs_model": 5414,
    "cleaned_empty": 134,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def js(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def csv_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_json(path: Path, obj: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(obj, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def confined_output(value: str | Path) -> Path:
    """Reject symlink escapes and row-level exports outside the ignored root."""
    dest = Path(value).expanduser().resolve()
    private = PRIVATE.resolve()
    if dest == private or private not in dest.parents:
        raise ValueError("Output must be a new descendant of the ignored private directory")
    ignore_lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    if "/validation/classification_rebuild/private/" not in ignore_lines:
        raise ValueError("Expected private-directory ignore rule is absent")
    if dest.exists():
        raise FileExistsError("Output already exists; never overwrite a production packet directory")
    return dest


def validate_sources() -> tuple[dict[str, str], list[dict], list[dict], dict]:
    """Validate source text, whole-post map, and the trial's frozen lineage."""
    manifest = js(SOURCE / "manifest.json")
    batches = manifest["batches"]
    if len(batches) != 84 or manifest["batch_count"] != 84:
        raise ValueError("Expected exactly 84 frozen source batches")
    names = [item["name"] for item in batches]
    if len(set(names)) != 84 or set(names) != {path.name for path in (SOURCE / "inputs").glob("*.jsonl")}:
        raise ValueError("Source input files differ from the frozen batch manifest")
    texts = {}
    source_hashes = {}
    for item in batches:
        name = item["name"]
        if Path(name).name != name:
            raise ValueError("Invalid source batch filename")
        path = SOURCE / "inputs" / name
        digest = sha(path)
        records = jl(path)
        if digest != item["sha256"] or len(records) != item["rows"]:
            raise ValueError("A source batch hash or row count differs from its frozen manifest")
        for record in records:
            if set(record) != {"sample_id", "text"}:
                raise ValueError("Source reading packets must contain only text and anonymous IDs")
            sid, body = record["sample_id"], record["text"]
            if not isinstance(sid, str) or not sid or sid in texts:
                raise ValueError("Duplicate or invalid source text ID")
            if not isinstance(body, str) or not body.strip():
                raise ValueError("Empty or invalid cleaned source text")
            texts[sid] = body
        source_hashes[name] = digest
    if len(texts) != 4156 or len(set(texts.values())) != 4156 or manifest["nonempty_unique_texts"] != 4156:
        raise ValueError("Expected 4156 distinct exact cleaned texts")

    post_map = csv_rows(SOURCE / "id_map.csv")
    if len(post_map) != 9532 or len({row["postId"] for row in post_map}) != 9532:
        raise ValueError("Expected one mapping row for each of 9532 distinct original posts")
    if any(not row["postId"] for row in post_map):
        raise ValueError("Original post map contains an empty post ID")
    states = Counter(row["input_status"] for row in post_map)
    if dict(states) != EXPECTED_STATES or manifest["source_states"] != EXPECTED_STATES or manifest["total_posts"] != 9532:
        raise ValueError("Original post observation states differ from the frozen population")
    if sha(SOURCE / "id_map.csv") != manifest["id_map_sha256"]:
        raise ValueError("Original post map hash differs from the frozen manifest")
    for row in post_map:
        is_model = row["input_status"] == "needs_model"
        if is_model != bool(row["sample_id"]) or (is_model and row["sample_id"] not in texts):
            raise ValueError("Original post status and cleaned-text mapping disagree")
    if {row["sample_id"] for row in post_map if row["sample_id"]} != set(texts):
        raise ValueError("Some cleaned texts are unmapped or mapped texts are missing")

    freeze = js(TRIAL / "freeze.json")
    if sha(CODEBOOK) != freeze["codebook_sha256"] or sha(TRIAL / "frozen_codebook.md") != freeze["codebook_sha256"]:
        raise ValueError("Current codebook differs from the trial-frozen rules")
    if sha(PROTOCOL) != freeze["protocol_sha256"] or sha(TRIAL / "frozen_protocol.json") != freeze["protocol_sha256"]:
        raise ValueError("Current analysis protocol differs from the trial-frozen protocol")
    protocol = js(PROTOCOL)
    if protocol["version"] != "v5" or protocol["random_unique_texts"] != 200 or protocol["targeted_no_v3_positive_unique_texts"] != 60:
        raise ValueError("Unexpected v5 protocol identity or trial size")
    for relative, digest in freeze["source_sha256"].items():
        path = (ROOT / relative).resolve()
        if ROOT.resolve() not in path.parents or sha(path) != digest:
            raise ValueError("A source differs from the trial-frozen source lineage")
    excluded_ids = js(TRIAL / "excluded_ids.json")
    excluded_digest = hashlib.sha256("\n".join(sorted(excluded_ids)).encode("utf-8")).hexdigest()
    if (len(excluded_ids) != freeze["n_excluded"] or len(set(excluded_ids)) != len(excluded_ids)
            or set(excluded_ids) - set(texts) or excluded_digest != freeze["excluded_ids_sha256"]):
        raise ValueError("Trial exclusion manifest changed")

    metadata = js(TRIAL / "sample_metadata.json")
    trial_keys = csv_rows(TRIAL / "private_key.csv")
    if sha(TRIAL / "private_key.csv") != metadata["private_key_sha256"]:
        raise ValueError("Trial private mapping changed")
    if len(trial_keys) != 260 or len({row["source_id"] for row in trial_keys}) != 260 or len({row["sample_id"] for row in trial_keys}) != 260:
        raise ValueError("Expected 260 distinct v5 trial texts")
    if Counter(row["partition"] for row in trial_keys) != {"random": 200, "targeted_no_v3_positive": 60}:
        raise ValueError("Unexpected trial partition sizes")
    multiplicity = Counter(row["sample_id"] for row in post_map if row["sample_id"])
    if any(row["source_id"] not in texts or int(row["post_multiplicity"]) != multiplicity[row["source_id"]] for row in trial_keys):
        raise ValueError("Trial texts or multiplicity do not match the production population")
    for who in ("a", "b"):
        path = TRIAL / f"blind_{who}.jsonl"
        if sha(path) != metadata["blind_sha256"]:
            raise ValueError("Trial anonymous text packet changed")
        blind = jl(path)
        indexed = {row["sample_id"]: row["text"] for row in blind}
        if len(blind) != 260 or len(indexed) != 260 or set(indexed) != {row["sample_id"] for row in trial_keys}:
            raise ValueError("Trial anonymous text IDs do not match its private mapping")
        if any(indexed[row["sample_id"]] != texts[row["source_id"]] for row in trial_keys):
            raise ValueError("Trial anonymous text differs from its frozen production source")

    checks = {
        "n_source_batches": 84,
        "n_source_unique_texts": 4156,
        "n_original_posts": 9532,
        "n_nonempty_post_mappings": 5414,
        "source_states": dict(states),
        "n_trial_texts_in_production": 260,
        "n_trial_represented_posts": sum(multiplicity[row["source_id"]] for row in trial_keys),
        "source_batch_sha256": source_hashes,
        "source_manifest_sha256": sha(SOURCE / "manifest.json"),
        "source_map_sha256": sha(SOURCE / "id_map.csv"),
        "trial_freeze_sha256": sha(TRIAL / "freeze.json"),
        "trial_private_key_sha256": sha(TRIAL / "private_key.csv"),
        "codebook_sha256": sha(CODEBOOK),
        "protocol_sha256": sha(PROTOCOL),
        "validated_all_trial_frozen_source_files": len(freeze["source_sha256"]),
    }
    return texts, post_map, trial_keys, checks


def prepare(output: str | Path = DEFAULT_OUTPUT) -> dict:
    dest = confined_output(output)
    texts, post_map, trial_keys, checks = validate_sources()
    multiplicity = Counter(row["sample_id"] for row in post_map if row["sample_id"])
    trial_lookup = {row["source_id"]: row["sample_id"] for row in trial_keys}
    ids = {source_id: f"V5P{index:06d}" for index, source_id in enumerate(sorted(texts), 1)}
    # Every exact text, including all 260 trial texts, is read again in production.
    packets = [{"sample_id": ids[source_id], "text": texts[source_id]} for source_id in sorted(texts)]
    unique_key = [
        {"sample_id": ids[source_id], "source_id": source_id,
         "post_multiplicity": multiplicity[source_id],
         "text_sha256": hashlib.sha256(texts[source_id].encode("utf-8")).hexdigest(),
         "trial_sample_id": trial_lookup.get(source_id, "")}
        for source_id in sorted(texts)
    ]
    whole_post_map = [
        {"postId": row["postId"], "sample_id": ids.get(row["sample_id"], ""),
         "input_status": row["input_status"],
         "post_multiplicity": multiplicity.get(row["sample_id"], 0)}
        for row in post_map
    ]

    # Validation is complete before creating anything. mkdir refuses even an
    # existing empty directory; a failed/incomplete export is never overwritten.
    dest.mkdir(parents=True, exist_ok=False)
    (dest / "inputs").mkdir()
    shutil.copyfile(CODEBOOK, dest / "frozen_codebook.md")
    shutil.copyfile(PROTOCOL, dest / "frozen_protocol.json")
    write_csv(dest / "private_key.csv", unique_key)
    write_csv(dest / "post_map.csv", whole_post_map)
    batch_info = []
    for offset in range(0, len(packets), BATCH_SIZE):
        batch = packets[offset:offset + BATCH_SIZE]
        path = dest / "inputs" / f"batch_{len(batch_info) + 1:04d}.jsonl"
        with path.open("x", encoding="utf-8") as handle:
            for row in batch:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        batch_info.append({"name": path.name, "rows": len(batch), "sha256": sha(path)})

    policy = {
        "coverage": "All 4156 exact cleaned texts are included once, then mapped to 5414 nonempty posts; all 9532 original posts remain in post_map.csv with observation status.",
        "trial_texts": "All 260 trial texts are included for a uniform full-corpus reread. Trial labels are comparison material, never imported as production answers or treated as a gold standard.",
        "coder_inputs": "Give coders only frozen_codebook.md and anonymous inputs/*.jsonl. Do not release the private key, multiplicity, trial membership, earlier labels, authors, media, tags or outcomes.",
        "duplicates": "Identical cleaned text receives one semantic coding, mapped back with original multiplicity. Do not code duplicate posts independently or count mapped duplicates as independent coding validation.",
        "missing": "No text packet is created for 3984 raw-body-unavailable or 134 cleaned-empty posts; preserve those states rather than giving them semantic negative labels.",
        "classification": "Preparation only. No production classification, merged production labels, human validation or new likes regression is performed by this script.",
    }
    write_json(dest / "source_integrity.json", checks)
    manifest = {
        "status": "prepared_not_classified",
        "version": "v5",
        "batch_size": BATCH_SIZE,
        "n_batches": len(batch_info),
        "n_unique_texts": len(packets),
        "n_original_posts": len(whole_post_map),
        "n_nonempty_post_mappings": sum(bool(row["sample_id"]) for row in whole_post_map),
        "n_trial_texts_included": len(trial_keys),
        "source_states": checks["source_states"],
        "frozen_codebook_sha256": sha(dest / "frozen_codebook.md"),
        "frozen_protocol_sha256": sha(dest / "frozen_protocol.json"),
        "source_integrity_sha256": sha(dest / "source_integrity.json"),
        "private_key_sha256": sha(dest / "private_key.csv"),
        "post_map_sha256": sha(dest / "post_map.csv"),
        "batches": batch_info,
        "policy": policy,
    }
    write_json(dest / "manifest.json", manifest)
    # Read-back checks make mapping and packet completeness part of preparation.
    reloaded = [row for info in batch_info for row in jl(dest / "inputs" / info["name"])]
    if reloaded != packets or sum(info["rows"] for info in batch_info) != 4156 or len(batch_info) != 84:
        raise ValueError("Exported production packets failed read-back validation")
    if csv_rows(dest / "post_map.csv") != [{key: str(value) for key, value in row.items()} for row in whole_post_map]:
        raise ValueError("Exported original-post mapping failed read-back validation")
    if sha(dest / "frozen_codebook.md") != checks["codebook_sha256"] or sha(dest / "frozen_protocol.json") != checks["protocol_sha256"]:
        raise ValueError("Exported rules or protocol hash differs from the trial freeze")

    # This public receipt intentionally contains counts/hashes and no source IDs,
    # original posts, reading evidence, raw labels or row-level text hashes.
    public = {
        "status": "production_packets_prepared_not_classified",
        "version": "v5",
        "n_source_batches_verified": checks["n_source_batches"],
        "n_trial_frozen_source_files_verified": checks["validated_all_trial_frozen_source_files"],
        "n_unique_texts_prepared": len(packets),
        "n_batches_prepared": len(batch_info),
        "batch_size": BATCH_SIZE,
        "last_batch_size": batch_info[-1]["rows"],
        "n_original_posts_mapped": len(whole_post_map),
        "n_nonempty_post_mappings": 5414,
        "source_states": checks["source_states"],
        "n_trial_texts_included_for_fresh_reading": len(trial_keys),
        "n_trial_represented_posts": checks["n_trial_represented_posts"],
        "n_unique_texts_with_multiplicity_gt_one": sum(value > 1 for value in multiplicity.values()),
        "maximum_text_multiplicity": max(multiplicity.values()),
        "n_production_texts_classified": 0,
        "production_semantic_coverage_not_yet_estimated": True,
        "trial_labels_read_or_imported": False,
        "trial_labels_are_gold_standard": False,
        "all_raw_exports_inside_ignored_private_root": True,
        "source_manifest_sha256": checks["source_manifest_sha256"],
        "source_map_sha256": checks["source_map_sha256"],
        "trial_freeze_sha256": checks["trial_freeze_sha256"],
        "frozen_codebook_sha256": checks["codebook_sha256"],
        "frozen_protocol_sha256": checks["protocol_sha256"],
        "production_manifest_sha256": sha(dest / "manifest.json"),
        "production_post_map_sha256": sha(dest / "post_map.csv"),
        "production_private_key_sha256": sha(dest / "private_key.csv"),
        "production_source_integrity_sha256": sha(dest / "source_integrity.json"),
    }
    PUBLIC_OUTPUT.parent.mkdir(exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=PUBLIC_OUTPUT.parent,
                                     prefix=".v5_preparation_", suffix=".tmp", delete=False) as handle:
        json.dump(public, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(PUBLIC_OUTPUT)
    return public


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="New export directory under the ignored classification_rebuild/private root")
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
