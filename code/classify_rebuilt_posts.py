#!/usr/bin/env python3
"""Fit a text-only provisional detector, then predict a separately frozen packet.

--fit reads only development/calibration text and annotations, never holdout or
population files. --predict requires the frozen codebook/config/model hashes.
NA means unsupported or out of scope; zero means no detected signal, not a
semantic negative. Logistic scores are not semantic correctness probabilities.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from evaluate_rebuilt_classification import (
    ValidationError, check_freeze, exclusion_reasons, freeze_summary,
    load_annotations, load_blind, load_codebook, normalize_id, read_json,
    recheck_freeze, resolve_path, sha256, write_json,
)


SEED = 20261029
THRESHOLDS = [0.35, 0.5, 0.65, 0.8]
LIMITATION = (
    "仅正文的AI开发初筛识别器，状态not-ready-human；分数不是语义正确概率。"
    "类别由独立语料归纳与codebook定义，训练及阈值仅决定检测规则。"
    "AI-only预验证不能替代人工效度验证，不可用于正式主题回归。"
    "NA表示未支持、正文不可处理或领域未通过适用性门控；0只表示未检出信号，不证明语义不存在。"
)


def dependencies():
    try:
        import joblib
        import sklearn
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
    except ImportError as exc:
        raise ValidationError("scikit-learn and joblib are required: %s" % exc)
    return joblib, sklearn, TfidfVectorizer, LogisticRegression


def body_state(text):
    if not text.strip():
        return "empty"
    return "text_present" if any(c.isalpha() for c in text) else "symbols_or_digits_only"


def f1_counts(truth, predictions):
    tp = sum(int(y == 1 and p == 1) for y, p in zip(truth, predictions))
    fp = sum(int(y == 0 and p == 1) for y, p in zip(truth, predictions))
    fn = sum(int(y == 1 and p == 0) for y, p in zip(truth, predictions))
    denominator = 2 * tp + fp + fn
    return {"TP": tp, "FP": fp, "FN": fn, "F1": 2 * tp / denominator if denominator else None}


def eligibility(annotation, text, axis, code):
    if body_state(text) != "text_present":
        return ["body_" + body_state(text)]
    if axis == "gate":
        reasons = []
        if annotation["observation_state"] != "readable":
            reasons.append("observation_" + annotation["observation_state"])
        if annotation["domain_state"] not in {"specified", "unspecified"}:
            reasons.append("domain_" + annotation["domain_state"])
        return reasons
    return exclusion_reasons(annotation, axis, code)


def training_view(blind, annotations, axis, code):
    ids, values, exclusions = [], [], Counter()
    for sid, text in blind.items():
        reasons = eligibility(annotations[sid], text, axis, code)
        if reasons:
            exclusions.update(set(reasons))
            continue
        ids.append(sid)
        values.append(int(annotations[sid]["domain_state"] == "specified") if axis == "gate"
                      else int(code in annotations[sid][axis]))
    return ids, values, {"eligible": len(ids), "positive": sum(values),
                         "negative": len(values) - sum(values), "excluded": len(blind) - len(ids),
                         "exclusion_reasons": dict(exclusions)}


def calibrate(model, matrix, labels, diagnostic):
    if diagnostic["positive"] < 3 or diagnostic["negative"] < 3:
        return {"threshold": 0.5, "calibration_status": "uncalibrated_insufficient_support",
                "threshold_trials": []}
    scores = model.predict_proba(matrix)[:, 1]
    trials = [dict(threshold=t, **f1_counts(labels, [int(s >= t) for s in scores])) for t in THRESHOLDS]
    selected = max(trials, key=lambda x: (x["F1"] if x["F1"] is not None else -1, x["threshold"]))
    return {"threshold": selected["threshold"], "calibration_status": "calibrated_AI_only",
            "threshold_trials": trials}


def fit(args):
    root = Path(args.project_root).resolve()
    freeze_path = resolve_path(root, args.freeze_record)
    if freeze_path.exists():
        raise ValidationError("packet is already frozen; fitting this version is disabled")
    joblib, sklearn, TfidfVectorizer, LogisticRegression = dependencies()
    codebook_path = resolve_path(root, args.codebook)
    axes = load_codebook(codebook_path)
    source_paths = {"development_input": resolve_path(root, args.development_input),
                    "development_coding": resolve_path(root, args.development_coding),
                    "calibration_input": resolve_path(root, args.calibration_input),
                    "calibration_coding": resolve_path(root, args.calibration_coding)}
    if any("holdout" in p.name.lower() or "population" in p.name.lower() for p in source_paths.values()):
        raise ValidationError("fit input names must identify development/calibration, never holdout/population")
    before = {name: sha256(path) for name, path in source_paths.items()}
    codebook_hash = sha256(codebook_path)
    development = load_blind(source_paths["development_input"])
    calibration = load_blind(source_paths["calibration_input"])
    if set(development) & set(calibration):
        raise ValidationError("development and calibration sample IDs overlap")
    dev_annotations = load_annotations(source_paths["development_coding"], development, axes)
    cal_annotations = load_annotations(source_paths["calibration_coding"], calibration, axes)
    vocabulary_ids = [sid for sid, text in development.items()
                      if dev_annotations[sid]["observation_state"] == "readable" and body_state(text) == "text_present"]
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=2,
                                 max_features=16000, sublinear_tf=True)
    vocabulary_status = "fitted_development_only"
    try:
        vectorizer.fit([development[sid] for sid in vocabulary_ids])
    except ValueError as exc:
        if "empty vocabulary" not in str(exc) and "no terms remain" not in str(exc).lower() and "max_df" not in str(exc):
            raise
        vectorizer = None
        vocabulary_status = "unsupported_empty_development_vocabulary"
    models, diagnostics = {}, []
    entries = [("gate", {"code": "domain_specificity", "label": "领域适用性门控"})]
    entries += [(axis, entry) for axis, classes in axes.items() for entry in classes]
    for axis, entry in entries:
        code = entry["code"]
        train_ids, train_labels, train_diagnostic = training_view(development, dev_annotations, axis, code)
        cal_ids, cal_labels, cal_diagnostic = training_view(calibration, cal_annotations, axis, code)
        row = dict(entry, axis=axis, development=train_diagnostic, calibration=cal_diagnostic,
                   supported=False, threshold=None, calibration_status="not_supported",
                   threshold_trials=[], keep_manual_candidate=True)
        if train_diagnostic["positive"] < 5 or train_diagnostic["negative"] < 5:
            row["unsupported_reason"] = "development_requires_at_least_5_positive_and_5_negative"
        elif vectorizer is None:
            row["unsupported_reason"] = "development_vocabulary_unavailable"
        else:
            model = LogisticRegression(C=1.0, class_weight="balanced", solver="liblinear",
                                       random_state=SEED, max_iter=1000)
            model.fit(vectorizer.transform([development[sid] for sid in train_ids]), train_labels)
            if cal_ids:
                cal_matrix = vectorizer.transform([calibration[sid] for sid in cal_ids])
                choice = calibrate(model, cal_matrix, cal_labels, cal_diagnostic)
            else:
                choice = {"threshold": 0.5, "calibration_status": "uncalibrated_insufficient_support", "threshold_trials": []}
            models[code] = model
            row.update(supported=True, keep_manual_candidate=False, **choice)
        diagnostics.append(row)
    for name, path in source_paths.items():
        if sha256(path) != before[name]:
            raise ValidationError("fit source changed during training: %s" % name)
    if sha256(codebook_path) != codebook_hash:
        raise ValidationError("codebook changed during training")
    model_path = resolve_path(root, args.model)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    package = {"schema_version": "1.0", "vectorizer": vectorizer, "models": models,
               "codebook_sha256": codebook_hash,
               "codes": {axis: [x["code"] for x in classes] for axis, classes in axes.items()}}
    joblib.dump(package, model_path)
    vocabulary = {word: int(index) for word, index in vectorizer.vocabulary_.items()} if vectorizer is not None else {}
    vocabulary_hash = hashlib.sha256(json.dumps(vocabulary, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    configuration = {
        "schema_version": "1.0", "version": "classification_recognizer_v1", "status": "not-ready-human",
        "interpretation": LIMITATION, "training_source": "AI-only development and calibration annotations",
        "semantic_class_definition": "codebook only; classifier fit/calibration does not choose semantic classes",
        "features": {"source": "正文 only", "forbidden_features": ["likes", "comments", "author", "interaction_counts", "legacy_labels"],
                     "vectorizer": "TfidfVectorizer", "analyzer": "char", "ngram_range": [2, 4],
                     "min_df": 2, "max_features": 16000, "sublinear_tf": True},
        "estimator": {"name": "LogisticRegression", "C": 1.0, "class_weight": "balanced",
                      "solver": "liblinear", "random_state": SEED, "max_iter": 1000},
        "threshold_selection": {"candidates": THRESHOLDS, "objective": "calibration F1", "tie_break": "higher_threshold",
                                "minimum_calibration_positive": 3, "minimum_calibration_negative": 3, "fallback": 0.5},
        "training_minimum": {"positive": 5, "negative": 5},
        "eligibility": {"domains": "readable text; domain_state=specified; label not uncertain",
                        "functions": "readable text; label not uncertain",
                        "domain_specificity": "readable text; specified positive versus unspecified negative; uncertain/unavailable excluded"},
        "codebook_path": str(codebook_path.resolve()), "codebook_sha256": codebook_hash,
        "model_path": str(model_path.resolve()), "model_sha256": sha256(model_path),
        "implementation_sha256": sha256(Path(__file__)),
        "input_sha256": before, "sample_counts": {"development": len(development), "calibration": len(calibration),
                                                   "vocabulary_development_readable": len(vocabulary_ids)},
        "vocabulary": {"status": vocabulary_status, "size": len(vocabulary), "sha256": vocabulary_hash,
                       "private_location": "classifier_v1.joblib: vectorizer.vocabulary_", "fit_scope": "development only"},
        "software": {"scikit_learn": sklearn.__version__, "joblib": joblib.__version__},
        "labels": diagnostics, "holdout_accessed": False,
        "required_freeze": "freeze this config, codebook and model artifact before holdout prediction"}
    write_json(resolve_path(root, args.recognizer), configuration)
    write_json(resolve_path(root, args.output_dir) / "classification_rebuild_training.json", configuration)
    print("Fit completed using development/calibration only; %d supported label models plus gate=%s." %
          (sum(x["supported"] for x in diagnostics if x["axis"] != "gate"), diagnostics[0]["supported"]))


def load_population(path, id_column=None, text_column=None):
    rows = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        id_column = id_column or next((c for c in ("sample_id", "post_id", "note_id", "id") if c in fields), None)
        text_column = text_column or next((c for c in ("clean_text", "text", "body", "fulltext", "content") if c in fields), None)
        if id_column not in fields or text_column not in fields:
            raise ValidationError("population requires an ID and body-text column; use --id-column/--text-column")
        for row in reader:
            sid = normalize_id(row.get(id_column))
            if sid in rows:
                raise ValidationError("population has duplicate IDs")
            text = row.get(text_column)
            if not isinstance(text, str):
                raise ValidationError("population body must be a string")
            rows[sid] = text
    return rows


def score_records(texts, axes, configuration, package):
    diagnostics = {row["code"]: row for row in configuration["labels"]}
    vectorizer, models = package["vectorizer"], package["models"]
    valid_ids = [sid for sid, text in texts.items() if body_state(text) == "text_present"]
    scores = {}
    if vectorizer is not None and valid_ids:
        matrix = vectorizer.transform([texts[sid] for sid in valid_ids])
        for code, model in models.items():
            scores[code] = dict(zip(valid_ids, [float(x) for x in model.predict_proba(matrix)[:, 1]]))
    full_rows, minimal_rows = [], []
    summary = {"scope": "model_detection_only", "n_rows": len(texts), "body_states": dict(Counter(body_state(t) for t in texts.values())),
               "domain_scope_states": {}, "labels": {entry["code"]: {"axis": axis, "label": entry["label"], "states": {}}
                                                         for axis, entries in axes.items() for entry in entries}}
    scopes = Counter()
    label_states = {code: Counter() for code in summary["labels"]}
    for sid, text in texts.items():
        state = body_state(text)
        gate_score = scores.get("domain_specificity", {}).get(sid)
        gate = None if gate_score is None else int(gate_score >= diagnostics["domain_specificity"]["threshold"])
        gate_status = "body_" + state if state != "text_present" else "gate_unsupported" if gate is None else "gate_passed" if gate else "gate_not_passed"
        scopes[gate_status] += 1
        full = {"sample_id": sid, "body_state": state, "domain_scope_state": gate_status,
                "pred_domain_specificity": gate, "score_domain_specificity": gate_score}
        minimal = {"sample_id": sid, "pred_domain_specificity": gate}
        for axis, entries in axes.items():
            for entry in entries:
                code = entry["code"]
                score = scores.get(code, {}).get(sid)
                raw = None if score is None else int(score >= diagnostics[code]["threshold"])
                if state != "text_present":
                    prediction, label_state = None, "body_" + state
                elif not diagnostics[code]["supported"]:
                    prediction, label_state = None, "unsupported_development"
                elif axis == "domains" and gate != 1:
                    prediction, label_state = None, "gate_unsupported" if gate is None else "outside_domain_scope"
                else:
                    prediction, label_state = raw, "signal_detected" if raw else "signal_not_detected"
                full["pred_" + code] = minimal["pred_" + code] = prediction
                full["score_" + code] = score
                full["status_" + code] = label_state
                if axis == "domains":
                    full["raw_pred_" + code] = minimal["raw_pred_" + code] = raw
                label_states[code][label_state] += 1
        full_rows.append(full)
        minimal_rows.append(minimal)
    summary["domain_scope_states"] = dict(scopes)
    for code in label_states:
        summary["labels"][code]["states"] = dict(label_states[code])
        summary["labels"][code]["supported"] = diagnostics[code]["supported"]
        summary["labels"][code]["threshold"] = diagnostics[code]["threshold"]
    return full_rows, minimal_rows, summary


def write_prediction_csv(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValidationError("refusing an empty prediction output")
    with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: "NA" if value is None else value for key, value in row.items()} for row in rows)


def predict(args):
    root = Path(args.project_root).resolve()
    freeze = check_freeze(root, resolve_path(root, args.freeze_record), resolve_path(root, args.codebook), resolve_path(root, args.recognizer))
    axes = load_codebook(freeze["codebook_path"])
    configuration = read_json(freeze["recognizer_path"])
    if configuration.get("codebook_sha256") != sha256(freeze["codebook_path"]):
        raise ValidationError("recognizer was fitted against a different codebook")
    if configuration.get("implementation_sha256") != sha256(Path(__file__)):
        raise ValidationError("classifier implementation changed since fit")
    model_path = resolve_path(root, configuration["model_path"])
    if sha256(model_path) != configuration.get("model_sha256"):
        raise ValidationError("model artifact hash differs from frozen config")
    joblib, _, _, _ = dependencies()
    package = joblib.load(model_path)
    if package["codebook_sha256"] != configuration["codebook_sha256"]:
        raise ValidationError("model/codebook hash mismatch")
    expected_codes = {axis: [entry["code"] for entry in entries] for axis, entries in axes.items()}
    if package["codes"] != expected_codes:
        raise ValidationError("model category axes differ from codebook")
    holdout_path = resolve_path(root, args.holdout_input)
    population_path = resolve_path(root, args.population_input)
    input_hashes = {"holdout_sha256": sha256(holdout_path), "population_sha256": sha256(population_path)}
    holdout = load_blind(holdout_path)
    population = load_population(population_path, args.id_column, args.text_column)
    if args.expected_population_size is not None and len(population) != args.expected_population_size:
        raise ValidationError("population size %d differs from expected %d" % (len(population), args.expected_population_size))
    _, holdout_predictions, holdout_summary = score_records(holdout, axes, configuration, package)
    population_predictions, _, population_summary = score_records(population, axes, configuration, package)
    recheck_freeze(freeze)
    if sha256(model_path) != configuration["model_sha256"]:
        raise ValidationError("model changed during prediction")
    if sha256(holdout_path) != input_hashes["holdout_sha256"] or sha256(population_path) != input_hashes["population_sha256"]:
        raise ValidationError("prediction input changed during prediction")
    output = resolve_path(root, args.output_dir)
    write_prediction_csv(output / "rebuilt_prediction_holdout.csv", holdout_predictions)
    write_prediction_csv(output / "rebuilt_content_features.csv", population_predictions)
    summary = {"schema_version": "1.0", "status": "not-ready-human", "interpretation": LIMITATION,
               "freeze": freeze_summary(freeze), "model_sha256_verified": configuration["model_sha256"],
               "input_sha256": input_hashes, "holdout": holdout_summary, "body_population": population_summary,
               "scope_warning": "分母为本轮文本处理与模型适用状态；检测计数不是全样本真实主题分布。",
               "raw_domain_predictions": "raw_pred_<domain> ignores specificity gate and is diagnostic only; gated predictions may be NA.",
               "holdout_annotations_accessed": False, "formal_topic_regression_ready": False}
    write_json(output / "classification_rebuild_recognition.json", summary)
    print("Frozen prediction completed: holdout=%d population=%d; AI-only screening, not ready for formal regression." % (len(holdout), len(population)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--fit", action="store_true")
    modes.add_argument("--predict", action="store_true")
    parser.add_argument("--project-root", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--codebook", default="code/classification_codebook_v1.json")
    parser.add_argument("--recognizer", default="code/classification_recognizer_v1.json")
    parser.add_argument("--freeze-record", default="validation/classification_rebuild/freeze_record.json")
    parser.add_argument("--model", default="validation/classification_rebuild/private/classifier_v1.joblib")
    parser.add_argument("--development-input", default="validation/classification_rebuild/private/development_blind.jsonl")
    parser.add_argument("--development-coding", default="validation/classification_rebuild/private/development_coding.json")
    parser.add_argument("--calibration-input", default="validation/classification_rebuild/private/calibration_blind.jsonl")
    parser.add_argument("--calibration-coding", default="validation/classification_rebuild/private/calibration_coding.json")
    parser.add_argument("--holdout-input", default="validation/classification_rebuild/private/holdout_blind.jsonl")
    parser.add_argument("--population-input", default="validation/classification_rebuild/private/body_population.csv")
    parser.add_argument("--id-column")
    parser.add_argument("--text-column")
    parser.add_argument("--expected-population-size", type=int, default=9532)
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args(argv)
    try:
        fit(args) if args.fit else predict(args)
    except (ValidationError, OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, "Classification failed: %s\n" % exc)


if __name__ == "__main__":
    main()
