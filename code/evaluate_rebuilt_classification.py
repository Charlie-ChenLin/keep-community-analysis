#!/usr/bin/env python3
"""Validate a frozen packet and report agreement, never an inferred gold standard.

Uses only the Python standard library. No source text is written to public results.
Default paths are relative to projects/group. JSON undefined statistics are null;
their CSV representation is NaN, with an explicit reason for undefined kappa.
"""

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


OBSERVATIONS = {"readable", "insufficient", "empty"}
DOMAIN_STATES = {"specified", "unspecified", "uncertain", "unavailable"}
AI_LIMITATION = (
    "两代理使用同一模型、上下文分离；此处仅为AI编码预验证。"
    "一致性不等于人类验证、构念效度或准确率；A/B均为各自参照，不能合成gold。"
)
HUMAN_LIMITATION = (
    "本报告读取独立填写的A/B人审表；程序不认证填写者身份。"
    "一致性不等于构念效度；规则分别与A/B比较，不合成人类gold。"
)


class ValidationError(ValueError):
    pass


def read_json(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resolve_path(root, value):
    path = Path(value)
    return path if path.is_absolute() else Path(root) / path


def normalize_id(value):
    if isinstance(value, bool) or value is None or not str(value).strip():
        raise ValidationError("sample_id must be a nonempty string or number")
    return str(value)


def load_codebook(path):
    raw = read_json(path)
    if not isinstance(raw, dict):
        raise ValidationError("codebook must be a JSON object")
    axes = {}
    seen = set()
    for axis in ("domains", "functions"):
        entries = raw.get(axis)
        if not isinstance(entries, list) or not entries:
            raise ValidationError("codebook requires nonempty %s array" % axis)
        axes[axis] = []
        for row in entries:
            if not isinstance(row, dict):
                raise ValidationError("codebook categories must be objects")
            code, label = row.get("code"), row.get("label")
            if not isinstance(code, str) or not code.strip() or not isinstance(label, str):
                raise ValidationError("every codebook category needs code and label")
            if code in seen:
                raise ValidationError("duplicate code across codebook axes: %s" % code)
            seen.add(code)
            axes[axis].append({"code": code, "label": label})
    return axes


def check_freeze(root, freeze_path, codebook_path, recognizer_path):
    """Require definition/config hashes and verify any listed model artifacts.

    Supported mandatory schemas:
      {codebook_sha256: ..., recognizer_sha256: ..., optional *_path: ...}
      {codebook: {path: ..., sha256: ...}, recognizer: {path: ..., sha256: ...}}
    Additional artifacts/files may be path->hash mappings or {path,sha256} lists.
    """
    freeze_path = Path(freeze_path)
    record = read_json(freeze_path)
    if not isinstance(record, dict):
        raise ValidationError("freeze_record must be a JSON object")
    checked = []
    effective = {}
    for name, fallback in (("codebook", codebook_path), ("recognizer", recognizer_path)):
        nested = record.get(name, {})
        nested = nested if isinstance(nested, dict) else {}
        value = record.get(name + "_path") or nested.get("path") or str(fallback)
        target = resolve_path(root, value).resolve()
        expected = record.get(name + "_sha256") or nested.get("sha256")
        if not expected:
            raise ValidationError("freeze_record is missing %s_sha256" % name)
        checked.append({"kind": name, "path": str(target), "sha256": str(expected).lower()})
        effective[name] = target
    for container in ("artifacts", "files", "artifact_sha256"):
        extras = record.get(container, [])
        if isinstance(extras, dict):
            extras = [dict(value, path=key) if isinstance(value, dict)
                      else {"path": key, "sha256": value} for key, value in extras.items()]
        if not isinstance(extras, list):
            raise ValidationError("freeze %s must be a mapping or list" % container)
        for item in extras:
            if not isinstance(item, dict) or not item.get("path") or not item.get("sha256"):
                raise ValidationError("every frozen artifact needs path and sha256")
            checked.append({"kind": "artifact", "path": str(resolve_path(root, item["path"]).resolve()),
                            "sha256": str(item["sha256"]).lower()})
    if record.get("model_sha256"):
        if not record.get("model_path"):
            raise ValidationError("model_sha256 requires model_path")
        checked.append({"kind": "model", "path": str(resolve_path(root, record["model_path"]).resolve()),
                        "sha256": str(record["model_sha256"]).lower()})
    for item in checked:
        if len(item["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in item["sha256"]):
            raise ValidationError("invalid frozen SHA256 for %s" % item["path"])
        if not Path(item["path"]).is_file() or sha256(item["path"]) != item["sha256"]:
            raise ValidationError("frozen file is missing or changed: %s" % item["path"])
    return {"path": str(freeze_path.resolve()), "sha256": sha256(freeze_path),
            "files": checked, "codebook_path": effective["codebook"],
            "recognizer_path": effective["recognizer"]}


def recheck_freeze(freeze):
    if sha256(freeze["path"]) != freeze["sha256"]:
        raise ValidationError("freeze_record changed during evaluation")
    for item in freeze["files"]:
        if sha256(item["path"]) != item["sha256"]:
            raise ValidationError("frozen file changed during evaluation: %s" % item["path"])


def freeze_summary(freeze):
    return {"record_path": freeze["path"], "record_sha256": freeze["sha256"],
            "verified": True, "files": freeze["files"],
            "extra_artifact_count": sum(x["kind"] not in {"codebook", "recognizer"} for x in freeze["files"]),
            "model_artifact_note": "仅能保证freeze_record实际列出的文件；额外训练模型也必须列入artifacts/files。"}


def load_blind(path):
    result = {}
    with Path(path).open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            sid = normalize_id(row.get("sample_id"))
            if sid in result:
                raise ValidationError("duplicate blind sample_id: %s" % sid)
            if not isinstance(row.get("text"), str):
                raise ValidationError("blind row %d text must be a string" % line_no)
            result[sid] = row["text"]
    if not result:
        raise ValidationError("blind input is empty")
    return result


def validate_ids(records, expected, source):
    indexed = {}
    for row in records:
        if not isinstance(row, dict):
            raise ValidationError("%s has a non-object record" % source)
        sid = normalize_id(row.get("sample_id"))
        if sid in indexed:
            raise ValidationError("%s duplicate sample_id: %s" % (source, sid))
        indexed[sid] = row
    missing, extra = set(expected) - set(indexed), set(indexed) - set(expected)
    if missing or extra:
        raise ValidationError("%s ID mismatch: missing=%d extra=%d" % (source, len(missing), len(extra)))
    return indexed


def load_annotations(path, blind, axes):
    raw = read_json(path)
    if not isinstance(raw, dict) or not isinstance(raw.get("records"), list):
        raise ValidationError("%s must contain a records array" % path)
    indexed = validate_ids(raw["records"], blind, str(path))
    all_codes = {x["code"] for entries in axes.values() for x in entries}
    for sid, row in indexed.items():
        if row.get("observation_state") not in OBSERVATIONS:
            raise ValidationError("%s invalid observation_state for %s" % (path, sid))
        if row.get("domain_state") not in DOMAIN_STATES:
            raise ValidationError("%s invalid domain_state for %s" % (path, sid))
        for axis in ("domains", "functions"):
            allowed = {x["code"] for x in axes[axis]}
            for key in (axis, "uncertain_" + axis):
                values = row.get(key)
                if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
                    raise ValidationError("%s %s must be a code array for %s" % (path, key, sid))
                if len(values) != len(set(values)) or set(values) - allowed:
                    raise ValidationError("%s duplicate/illegal %s for %s" % (path, key, sid))
            if set(row[axis]) & set(row["uncertain_" + axis]):
                raise ValidationError("%s positive and uncertain overlap for %s" % (path, sid))
        positives = row["domains"] + row["functions"]
        if (not blind[sid].strip()) != (row["observation_state"] == "empty"):
            raise ValidationError("%s empty-state/text mismatch for %s" % (path, sid))
        if row["observation_state"] == "empty" and positives:
            raise ValidationError("%s empty text cannot have positives for %s" % (path, sid))
        if row["domain_state"] in {"unspecified", "unavailable"} and row["domains"]:
            raise ValidationError("%s unspecified/unavailable domain has positives for %s" % (path, sid))
        if row["domain_state"] == "specified" and not row["domains"]:
            raise ValidationError("%s specified domain requires a positive domain for %s" % (path, sid))
        evidence = row.get("evidence")
        if not isinstance(evidence, dict) or set(evidence) - all_codes:
            raise ValidationError("%s invalid evidence mapping for %s" % (path, sid))
        for code, fragments in evidence.items():
            fragments = [fragments] if isinstance(fragments, str) else fragments
            if not isinstance(fragments, list) or not fragments or any(
                    not isinstance(x, str) or not x.strip() or x not in blind[sid] for x in fragments):
                raise ValidationError("%s nonliteral/empty evidence for %s code %s" % (path, sid, code))
        if any(code not in evidence for code in positives):
            raise ValidationError("%s positive lacks exact-substring evidence for %s" % (path, sid))
    return indexed


def exclusion_reasons(row, axis, code=None, prefix=""):
    reasons = []
    if row["observation_state"] != "readable":
        reasons.append(prefix + "observation_" + row["observation_state"])
    if axis == "domains" and row["domain_state"] != "specified":
        reasons.append(prefix + "domain_" + row["domain_state"])
    if code is not None and code in row["uncertain_" + axis]:
        reasons.append(prefix + "label_uncertain")
    return reasons


def agreement_statistics(n11, n10, n01, n00):
    n = n11 + n10 + n01 + n00
    agreement = (n11 + n00) / n if n else None
    positive_denom = 2 * n11 + n10 + n01
    positive_agreement = 2 * n11 / positive_denom if positive_denom else None
    a_positive, b_positive = n11 + n10, n11 + n01
    a_constant = bool(n and a_positive in (0, n))
    b_constant = bool(n and b_positive in (0, n))
    low_positive_support = min(a_positive, b_positive) < 5
    expected = None
    if not n:
        kappa, status = None, "undefined_no_evaluable_pairs"
    else:
        expected = (a_positive * b_positive + (n - a_positive) * (n - b_positive)) / (n * n)
        denominator = 1 - expected
        kappa = None if math.isclose(denominator, 0.0, rel_tol=0.0, abs_tol=1e-12) else (agreement - expected) / denominator
        status = "computed" if kappa is not None else "undefined_expected_agreement_one"
    flags = []
    if a_constant != b_constant:
        flags.append("one_rater_constant")
    if a_constant and b_constant:
        flags.append("both_raters_constant")
    if low_positive_support:
        flags.append("low_positive_support")
    return {"n": n, "n11": n11, "n10": n10, "n01": n01, "n00": n00,
            "a_positive": a_positive, "b_positive": b_positive,
            "agreement": agreement, "positive_agreement": positive_agreement,
            "expected_agreement": expected, "kappa": kappa, "kappa_status": status,
            "one_rater_constant": a_constant != b_constant,
            "both_raters_constant": a_constant and b_constant,
            "low_positive_support": low_positive_support, "interpretation_flags": flags}


def coverage_for(records, axes):
    return {"n": len(records),
            "observation_states": dict(Counter(r["observation_state"] for r in records.values())),
            "domain_states": dict(Counter(r["domain_state"] for r in records.values())),
            "axis_evaluable_before_label_uncertainty": {
                axis: sum(not exclusion_reasons(r, axis) for r in records.values()) for axis in axes}}


def build_agreement(a, b, axes, scope="ai"):
    labels, axis_coverage = [], {}
    for axis, entries in axes.items():
        axis_reasons, n_axis = Counter(), 0
        for sid in a:
            reasons = exclusion_reasons(a[sid], axis, prefix="a_") + exclusion_reasons(b[sid], axis, prefix="b_")
            if reasons:
                axis_reasons.update(set(reasons))
            else:
                n_axis += 1
        axis_coverage[axis] = {"total_pairs": len(a), "evaluable_before_label_uncertainty": n_axis,
                               "excluded_pairs": len(a) - n_axis, "exclusion_reasons": dict(axis_reasons)}
        for entry in entries:
            code = entry["code"]
            counts, reasons_count = Counter(), Counter()
            for sid in a:
                reasons = exclusion_reasons(a[sid], axis, code, "a_") + exclusion_reasons(b[sid], axis, code, "b_")
                if reasons:
                    reasons_count.update(set(reasons))
                    continue
                counts[(int(code in a[sid][axis]), int(code in b[sid][axis]))] += 1
            stats = agreement_statistics(counts[(1, 1)], counts[(1, 0)], counts[(0, 1)], counts[(0, 0)])
            labels.append(dict(entry, axis=axis, total_pairs=len(a),
                               a_positive_all=sum(code in r[axis] for r in a.values()),
                               b_positive_all=sum(code in r[axis] for r in b.values()),
                               excluded_pairs=len(a) - stats["n"], exclusion_reasons=dict(reasons_count), **stats))
    return {"scope": scope, "status": "completed", "n_samples": len(a),
            "interpretation": AI_LIMITATION if scope == "ai" else HUMAN_LIMITATION,
            "method": {"pair_eligibility": "Both observations readable; domains additionally require both domain_state=specified; label U/uncertain excluded per label.",
                       "unspecified_domains": "Excluded from domain binary comparisons; function comparisons remain eligible.",
                       "positive_agreement": "2*n11/(2*n11+n10+n01)",
                       "kappa_policy": "Cohen kappa=(Po-Pe)/(1-Pe); null/NaN only if no evaluable pairs or abs(1-Pe)<=1e-12. A single constant rater does not make kappa undefined.",
                       "support_flags": "one_rater_constant flags exactly one constant coder; low_positive_support flags fewer than 5 positives for either coder. These flags do not change kappa.",
                       "agreement_caveat": "High overall agreement may be driven by shared negatives; it does not establish positive-label reliability, accuracy, or validity. Inspect positive agreement, marginal counts, and support flags.",
                       "missing_statistics": "JSON null, CSV NaN; never silently replaced with zero.",
                       "reason_counts": "Reasons can overlap, so their sum can exceed excluded_pairs.",
                       "no_gold": True, "accuracy_reported": False},
            "coverage": {"a": coverage_for(a, axes), "b": coverage_for(b, axes), "paired": axis_coverage},
            "labels": labels}


def parse_bool(value):
    if isinstance(value, bool):
        return value
    if str(value).strip().lower() in {"1", "true"}:
        return True
    if str(value).strip().lower() in {"0", "false"}:
        return False
    raise ValidationError("prediction cells must be true/false or 1/0")


def parse_prediction(value):
    if value is None or str(value).strip().upper() in {"", "NA", "N/A", "U", "NULL", "NONE"}:
        return None
    return parse_bool(value)


def load_predictions(path, blind, axes):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        codes = {x["code"] for entries in axes.values() for x in entries}
        required = {"sample_id"} | {"pred_" + c for c in codes}
        auxiliary = {"pred_domain_specificity"}
        if required - set(fields) or {f[5:] for f in fields if f.startswith("pred_") and f not in auxiliary} - codes:
            raise ValidationError("prediction CSV has missing or illegal pred_<code> columns")
        indexed = validate_ids(list(reader), blind, "prediction CSV")
    return {sid: {code: parse_prediction(row["pred_" + code]) for code in codes} for sid, row in indexed.items()}


def wilson(successes, total):
    if not total:
        return [None, None]
    z, p = 1.959963984540054, successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def compare_predictions(predictions, reference, axes, name):
    rows = []
    for axis, entries in axes.items():
        for entry in entries:
            code, counts, exclusions = entry["code"], Counter(), Counter()
            for sid, row in reference.items():
                reasons = exclusion_reasons(row, axis, code)
                if predictions[sid][code] is None:
                    reasons.append("prediction_unavailable")
                if reasons:
                    exclusions.update(set(reasons))
                    continue
                counts[(int(predictions[sid][code]), int(code in row[axis]))] += 1
            tp, fp, fn, tn = counts[(1, 1)], counts[(1, 0)], counts[(0, 1)], counts[(0, 0)]
            precision = tp / (tp + fp) if tp + fp else None
            recall = tp / (tp + fn) if tp + fn else None
            f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else None
            rows.append(dict(entry, axis=axis, reference=name, n=tp + fp + fn + tn,
                             excluded_samples=len(reference) - tp - fp - fn - tn,
                             exclusion_reasons=dict(exclusions), TP=tp, FP=fp, FN=fn, TN=tn,
                             precision=precision, recall=recall, F1=f1,
                             precision_wilson95=wilson(tp, tp + fp), recall_wilson95=wilson(tp, tp + fn)))
    return rows


def write_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValidationError("refusing to write an empty metric table")
    fields = list(rows[0])
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: ("NaN" if v is None else json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
                             for k, v in row.items()})


def common_arguments(parser):
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--codebook", default="code/classification_codebook_v1.json")
    parser.add_argument("--recognizer", default="code/classification_recognizer_v1.json")
    parser.add_argument("--freeze-record", default="validation/classification_rebuild/freeze_record.json")
    parser.add_argument("--blind-input", default="validation/classification_rebuild/private/holdout_blind.jsonl")
    parser.add_argument("--predictions", default="results/rebuilt_prediction_holdout.csv")
    parser.add_argument("--output-dir", default="results")


def initialize(args):
    root = Path(args.project_root).resolve()
    freeze = check_freeze(root, resolve_path(root, args.freeze_record), resolve_path(root, args.codebook), resolve_path(root, args.recognizer))
    axes = load_codebook(freeze["codebook_path"])
    blind_path = resolve_path(root, args.blind_input)
    frozen_packet = read_json(freeze["path"]).get("holdout", {}).get("packet_sha256")
    if frozen_packet and sha256(blind_path) != frozen_packet:
        raise ValidationError("holdout packet differs from its release-time SHA256")
    blind = load_blind(blind_path)
    return root, freeze, axes, blind


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    common_arguments(parser)
    parser.add_argument("--coder-a", default="validation/classification_rebuild/private/holdout_coder_a.json")
    parser.add_argument("--coder-b", default="validation/classification_rebuild/private/holdout_coder_b.json")
    args = parser.parse_args(argv)
    try:
        root, freeze, axes, blind = initialize(args)
        a = load_annotations(resolve_path(root, args.coder_a), blind, axes)
        b = load_annotations(resolve_path(root, args.coder_b), blind, axes)
        report = build_agreement(a, b, axes)
        report["freeze"] = freeze_summary(freeze)
        report["input_hashes"] = {
            "blind_input_sha256": sha256(resolve_path(root, args.blind_input)),
            "coder_a_sha256": sha256(resolve_path(root, args.coder_a)),
            "coder_b_sha256": sha256(resolve_path(root, args.coder_b))}
        report["validation"] = {"complete_ids": True, "legal_codes": True,
                                "all_positive_evidence_exact_substrings": True}
        prediction_path = resolve_path(root, args.predictions)
        comparisons = []
        if prediction_path.is_file():
            predictions = load_predictions(prediction_path, blind, axes)
            comparisons = compare_predictions(predictions, a, axes, "AI_A") + compare_predictions(predictions, b, axes, "AI_B")
            report["rule_comparisons"] = {"interpretation": "相对A/B各自编码且预测非NA项的条件指标；不是准确率或gold性能。",
                                          "labels": comparisons, "prediction_sha256": sha256(prediction_path)}
        else:
            report["rule_comparisons"] = {"status": "not_available", "reason": "prediction CSV does not exist"}
        recheck_freeze(freeze)
        destination = resolve_path(root, args.output_dir)
        write_json(destination / "classification_ai_agreement.json", report)
        write_csv(destination / "classification_ai_agreement.csv", report["labels"])
        if comparisons:
            write_csv(destination / "classification_rule_vs_ai.csv", comparisons)
        print("AI prevalidation completed: %d samples; results in %s" % (len(blind), destination))
    except (ValidationError, OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "Validation failed: %s\n" % exc)


if __name__ == "__main__":
    main()
