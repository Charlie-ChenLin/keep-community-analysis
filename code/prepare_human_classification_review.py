#!/usr/bin/env python3
"""Prepare independent private review sheets, or evaluate genuinely filled sheets.

Preparation never reads AI annotations or predictions. Fill every label with 0/1/U,
observation_state with readable/insufficient/empty, and domain_state with
specified/unspecified/uncertain/unavailable. Preserve sample_id, fulltext and hash.
Use --evaluate-human after independent human coding. All-blank or partial sheets
produce only a pending status, never human agreement or a synthesized gold set.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from evaluate_rebuilt_classification import (
    DOMAIN_STATES, OBSERVATIONS, HUMAN_LIMITATION, ValidationError,
    build_agreement, common_arguments, compare_predictions, freeze_summary,
    initialize, load_predictions, recheck_freeze, resolve_path, sha256,
    validate_ids, write_csv, write_json,
)


def label_columns(axes):
    return [(axis, entry["code"], ("domain_" if axis == "domains" else "function_") + entry["code"])
            for axis, entries in axes.items() for entry in entries]


def prepare_sheets(private_dir, blind, axes, codebook_hash):
    private_dir.mkdir(parents=True, exist_ok=True)
    paths = [private_dir / "human_review_A.csv", private_dir / "human_review_B.csv"]
    # Check both destinations before writing either, so a rerun preserves filled work.
    existing = [str(p) for p in paths if p.exists()]
    if existing:
        raise ValidationError("review sheets already exist; preserved without overwrite: " + ", ".join(existing))
    fields = ["sample_id", "fulltext", "observation_state", "domain_state"]
    fields += [column for _, _, column in label_columns(axes)] + ["codebook_sha256"]
    for path in paths:
        with path.open("x", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for sid, text in blind.items():
                row = {column: "" for column in fields}
                row.update(sample_id=sid, fulltext=text, codebook_sha256=codebook_hash)
                writer.writerow(row)
    return paths


def read_human_sheet(path, blind, axes, codebook_hash):
    if not path.is_file():
        return None, {"status": "pending", "reason": "sheet_missing", "filled_cells": 0}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"sample_id", "fulltext", "observation_state", "domain_state", "codebook_sha256"}
        required |= {column for _, _, column in label_columns(axes)}
        if required - set(reader.fieldnames or []):
            raise ValidationError("human sheet is missing required columns: %s" % path)
        rows = validate_ids(list(reader), blind, str(path))
    indexed, pending, total_filled = {}, Counter(), 0
    for sid, row in rows.items():
        row_complete = True
        if row["fulltext"] != blind[sid]:
            raise ValidationError("human sheet fulltext changed for sample %s" % sid)
        if row["codebook_sha256"] != codebook_hash:
            raise ValidationError("human sheet codebook hash mismatch for sample %s" % sid)
        observation = row["observation_state"].strip()
        domain_state = row["domain_state"].strip()
        if observation and observation not in OBSERVATIONS:
            raise ValidationError("human sheet has invalid observation_state for sample %s" % sid)
        if domain_state and domain_state not in DOMAIN_STATES:
            raise ValidationError("human sheet has invalid domain_state for sample %s" % sid)
        if observation in {"empty", "insufficient"} and domain_state and domain_state != "unavailable":
            raise ValidationError("human empty/insufficient observation requires unavailable domain_state for sample %s" % sid)
        if observation == "readable" and domain_state == "unavailable":
            raise ValidationError("human readable observation cannot have unavailable domain_state for sample %s" % sid)
        total_filled += int(bool(observation)) + int(bool(domain_state))
        if not observation:
            pending["blank_observation_state"] += 1
            row_complete = False
        if not domain_state:
            pending["blank_domain_state"] += 1
            row_complete = False
        annotation = {"sample_id": sid, "observation_state": observation, "domain_state": domain_state,
                      "domains": [], "functions": [], "uncertain_domains": [], "uncertain_functions": []}
        for axis, code, column in label_columns(axes):
            cell = row[column].strip().upper()
            if cell not in {"", "0", "1", "U"}:
                raise ValidationError("human label must be 0/1/U for sample %s code %s" % (sid, code))
            if not cell:
                pending["blank_label_cells"] += 1
                row_complete = False
            else:
                if observation in {"empty", "insufficient"} and cell != "U":
                    raise ValidationError("human empty/insufficient label must be U for sample %s code %s" % (sid, code))
                if axis == "domains" and domain_state in {"unspecified", "unavailable"} and cell != "U":
                    raise ValidationError("human unspecified/unavailable domain label must be U for sample %s code %s" % (sid, code))
                total_filled += 1
                if cell == "1":
                    annotation[axis].append(code)
                elif cell == "U":
                    annotation["uncertain_" + axis].append(code)
        if observation:
            if (not blind[sid].strip()) != (observation == "empty"):
                raise ValidationError("human empty-state/text mismatch for sample %s" % sid)
            if observation == "empty" and annotation["domains"] + annotation["functions"]:
                raise ValidationError("human empty text has positive labels for sample %s" % sid)
        if domain_state in {"unspecified", "unavailable"} and annotation["domains"]:
            raise ValidationError("human unspecified/unavailable domain has positives for sample %s" % sid)
        if row_complete and domain_state == "specified" and not annotation["domains"]:
            raise ValidationError("human specified domain requires a positive domain for sample %s" % sid)
        indexed[sid] = annotation
    if pending:
        return None, {"status": "pending", "reason": "all_annotation_cells_blank" if total_filled == 0 else "partially_filled",
                      "filled_cells": total_filled, "missing_cells": dict(pending), "complete_ids": True}
    return indexed, {"status": "filled", "filled_cells": total_filled, "complete_ids": True,
                     "provenance": "填写者需真实完成独立人工编码；程序不能确认填写者身份。"}


def evaluate_human(root, private_dir, output_dir, blind, axes, freeze, predictions_path):
    codebook_hash = sha256(freeze["codebook_path"])
    a, a_status = read_human_sheet(private_dir / "human_review_A.csv", blind, axes, codebook_hash)
    b, b_status = read_human_sheet(private_dir / "human_review_B.csv", blind, axes, codebook_hash)
    status = {"scope": "human_review", "status": "completed" if a is not None and b is not None else "pending",
              "a": a_status, "b": b_status, "interpretation": HUMAN_LIMITATION,
              "freeze": freeze_summary(freeze)}
    if a is None or b is None:
        status["human_agreement_evaluation_completed"] = False
        status["reason"] = "两份人审表均须真实独立填写完整；空白、未填完或缺表时不计算人类指标。"
        status["stale_outputs_not_updated"] = [p.name for pattern in (
            "classification_human_agreement.*", "classification_rule_vs_human.*") for p in output_dir.glob(pattern)]
        recheck_freeze(freeze)
        write_json(output_dir / "classification_human_validation_status.json", status)
        return status
    report = build_agreement(a, b, axes, scope="human")
    report["freeze"] = freeze_summary(freeze)
    report["review_sheet_status"] = {"a": a_status, "b": b_status}
    report["input_hashes"] = {"human_review_a_sha256": sha256(private_dir / "human_review_A.csv"),
                              "human_review_b_sha256": sha256(private_dir / "human_review_B.csv")}
    report["validation"] = {"complete_ids": True, "legal_codes": True, "source_text_unchanged": True,
                            "coder_identity_authenticated": False, "human_evidence_spans_collected": False}
    comparisons = []
    if predictions_path.is_file():
        predictions = load_predictions(predictions_path, blind, axes)
        comparisons = compare_predictions(predictions, a, axes, "human_A") + compare_predictions(predictions, b, axes, "human_B")
        report["rule_comparisons"] = {"interpretation": "规则相对每位人审员的条件指标；不是合成gold或总体准确率。",
                                      "labels": comparisons, "prediction_sha256": sha256(predictions_path)}
    else:
        report["rule_comparisons"] = {"status": "not_available", "reason": "prediction CSV does not exist"}
    recheck_freeze(freeze)
    write_json(output_dir / "classification_human_agreement.json", report)
    write_csv(output_dir / "classification_human_agreement.csv", report["labels"])
    if comparisons:
        write_csv(output_dir / "classification_rule_vs_human.csv", comparisons)
    status["human_agreement_evaluation_completed"] = True
    status["human_coder_identity_authenticated"] = False
    write_json(output_dir / "classification_human_validation_status.json", status)
    return status


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    common_arguments(parser)
    parser.add_argument("--private-dir", default="validation/classification_rebuild/private")
    parser.add_argument("--evaluate-human", action="store_true")
    args = parser.parse_args(argv)
    try:
        root, freeze, axes, blind = initialize(args)
        private_dir, output_dir = resolve_path(root, args.private_dir), resolve_path(root, args.output_dir)
        if args.evaluate_human:
            status = evaluate_human(root, private_dir, output_dir, blind, axes, freeze, resolve_path(root, args.predictions))
            print("Human review status: %s" % status["status"])
        else:
            recheck_freeze(freeze)
            paths = prepare_sheets(private_dir, blind, axes, sha256(freeze["codebook_path"]))
            recheck_freeze(freeze)
            print("Prepared independent blank private sheets: " + ", ".join(str(p) for p in paths))
    except (ValidationError, OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "Validation failed: %s\n" % exc)


if __name__ == "__main__":
    main()
