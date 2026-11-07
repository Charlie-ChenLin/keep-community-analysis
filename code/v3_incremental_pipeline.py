#!/usr/bin/env python3
"""Prepare and audit direct model-assisted v3 text coding; never classify text.

Inputs are the already deduplicated v2 anonymous batches.  All row-level input,
coding evidence and post-ID mappings remain in the ignored private directory.
The v3 codebook/schema are frozen separately after design.  Unprocessed or
unreadable records are *unknown*, never implicit negatives.  Full merge is
refused until every original anonymous text has a complete valid annotation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = (ROOT / 'validation/classification_rebuild/private').resolve()
V2 = PRIVATE / 'v2_direct_batches'
V3 = PRIVATE / 'v3_refined_batches'
STATES = {'raw_body_unavailable', 'cleaned_empty', 'needs_model'}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def private_child(path):
    result = Path(path).resolve()
    if result == PRIVATE or not result.is_relative_to(PRIVATE):
        raise ValueError('run directory must be inside the ignored private directory')
    return result


def write_atomic(path, data):
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(data, encoding='utf-8')
    temp.replace(path)


def write_json(path, value):
    write_atomic(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def read_jsonl(path):
    result = []
    with path.open(encoding='utf-8') as f:
        for lineno, line in enumerate(f, 1):
            if line.strip():
                try:
                    result.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path.name} line {lineno}: invalid JSON') from exc
    return result


def read_map(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    ids = [r['postId'] for r in rows]
    if not ids or any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('missing or duplicate original post IDs')
    for row in rows:
        state = row['input_status']
        if state not in STATES or (state == 'needs_model') != bool(row['sample_id']):
            raise ValueError('ID map has an invalid input status or missing sample ID')
    return rows


def categorical_specs(schema):
    """Normalize the published v3 schema or an explicit extension schema."""
    categories = schema.get('categorical_fields', {})
    if not isinstance(categories, dict):
        raise ValueError('categorical_fields must be an object')
    result = dict(categories)
    if 'exhortation_target_values' in schema:
        published = {'values': schema['exhortation_target_values'],
                     'parent_label': 'V3_EXHORT',
                     'not_applicable_value': 'not_applicable',
                     'unknown_value': 'uncertain',
                     'insufficient_value': 'uncertain',
                     'evidence_required_values': []}
        if 'exhortation_target' in result and result['exhortation_target'] != published:
            raise ValueError('conflicting exhortation target declarations')
        result['exhortation_target'] = published
    return result


def validate_schema(schema):
    labels = schema.get('labels')
    if (not isinstance(labels, dict) or not labels
            or any(not isinstance(k, str) or not k or not isinstance(v, str) or not v for k, v in labels.items())):
        raise ValueError('schema requires nonempty labels object mapping codes to names')
    if not isinstance(schema.get('schema_version'), str) or not schema['schema_version']:
        raise ValueError('schema_version is required')
    categories = categorical_specs(schema)
    reserved = {'sample_id', 'observation_state', 'positive_labels', 'uncertain_labels',
                'evidence', 'note', 'all_labels_reviewed', 'categorical_evidence', 'postId', 'input_status'}
    for name, definition in categories.items():
        if (not isinstance(name, str) or not name or name in reserved or name in labels
                or not isinstance(definition, dict)):
            raise ValueError('invalid or duplicate categorical field name')
        values = definition.get('values')
        if (not isinstance(values, list) or not values or len(values) != len(set(values))
                or any(not isinstance(v, str) or not v for v in values)):
            raise ValueError(f'{name}: categorical values must be unique nonempty strings')
        parent = definition.get('parent_label')
        na, unknown = definition.get('not_applicable_value'), definition.get('unknown_value')
        if parent not in labels or na not in values or unknown not in values or na == unknown:
            raise ValueError(f'{name}: parent label, not-applicable or unknown value invalid')
        insufficient_value = definition.get('insufficient_value')
        if insufficient_value is not None and insufficient_value != unknown:
            raise ValueError(f'{name}: insufficient must remain null or use the unknown value')
        required_evidence = definition.get('evidence_required_values', [])
        if (not isinstance(required_evidence, list) or len(required_evidence) != len(set(required_evidence))
                or set(required_evidence) - set(values) or {na, unknown} & set(required_evidence)):
            raise ValueError(f'{name}: evidence-required values are invalid')
    return schema


def prepare(path):
    path = private_child(path)
    if path.exists():
        raise ValueError('v3 run already exists; never overwrite frozen work')
    v2_manifest_path = V2 / 'manifest.json'
    manifest = json.loads(v2_manifest_path.read_text(encoding='utf-8'))
    v2_map = V2 / 'id_map.csv'
    if sha(v2_map) != manifest['id_map_sha256']:
        raise ValueError('v2 post-ID mapping no longer matches its frozen hash')
    mappings = read_map(v2_map)
    batches, all_ids = [], set()
    # Validate *all* source batches before creating a new run.
    for batch in manifest['batches']:
        source = V2 / 'inputs' / batch['name']
        if sha(source) != batch['sha256']:
            raise ValueError(f'v2 source batch modified: {source.name}')
        rows = read_jsonl(source)
        ids = [r.get('sample_id') for r in rows]
        if (len(rows) != batch['rows'] or any(not isinstance(i, str) or not i for i in ids)
                or len(ids) != len(set(ids)) or all_ids.intersection(ids)
                or any(not isinstance(r.get('text'), str) or not r['text'].strip() for r in rows)):
            raise ValueError(f'bad ID, text, row count or duplicate in {source.name}')
        all_ids.update(ids)
        batches.append({'name': source.name, 'rows': len(rows), 'sha256': sha(source)})
    mapped_ids = {r['sample_id'] for r in mappings if r['input_status'] == 'needs_model'}
    if mapped_ids != all_ids or len(all_ids) != manifest['nonempty_unique_texts']:
        raise ValueError('v2 batch IDs and full-post mapping do not reconcile')
    if len(mappings) != manifest['total_posts']:
        raise ValueError('v2 mapping count does not match the frozen population')

    (path / 'inputs').mkdir(parents=True)
    (path / 'outputs').mkdir()
    for item in batches:
        shutil.copyfile(V2 / 'inputs' / item['name'], path / 'inputs' / item['name'])
    shutil.copyfile(v2_map, path / 'id_map.csv')
    result = {
        'purpose': 'Preparation only; no model, rule or semantic prediction has run',
        'v2_manifest_sha256': sha(v2_manifest_path),
        'id_map_sha256': sha(path / 'id_map.csv'),
        'total_posts': len(mappings),
        'input_status_counts': dict(Counter(r['input_status'] for r in mappings)),
        'n_unique_texts': len(all_ids), 'n_batches': len(batches), 'batches': batches,
        'schema_status': 'not_yet_frozen',
        'privacy': 'Inputs, per-post mappings, output evidence and labels are private.',
    }
    write_json(path / 'input_manifest.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'batches'}, ensure_ascii=False, indent=2))


def freeze(path, schema_path, codebook_path):
    path = private_child(path)
    manifest_path = path / 'frozen_manifest.json'
    if manifest_path.exists() or (path / 'frozen_schema.json').exists() or (path / 'frozen_codebook.md').exists():
        raise ValueError('v3 schema or codebook is already frozen; use a new run')
    if any((path / 'outputs').iterdir()):
        raise ValueError('cannot freeze after batch outputs exist')
    info = json.loads((path / 'input_manifest.json').read_text(encoding='utf-8'))
    schema_path, codebook_path = Path(schema_path).resolve(), Path(codebook_path).resolve()
    schema = validate_schema(json.loads(schema_path.read_text(encoding='utf-8')))
    labels = schema['labels']
    if not codebook_path.is_file() or not codebook_path.read_text(encoding='utf-8').strip():
        raise ValueError('a nonempty Markdown codebook is required')
    if sha(path / 'id_map.csv') != info['id_map_sha256']:
        raise ValueError('prepared ID map changed before freezing')
    shutil.copyfile(schema_path, path / 'frozen_schema.json')
    shutil.copyfile(codebook_path, path / 'frozen_codebook.md')
    result = {'schema_version': schema['schema_version'], 'label_codes': list(labels),
              'schema_sha256': sha(path / 'frozen_schema.json'),
              'codebook_sha256': sha(path / 'frozen_codebook.md'),
              'input_manifest_sha256': sha(path / 'input_manifest.json'),
              'scope': 'AI-assisted coding only; no human validity or accuracy implied'}
    write_json(manifest_path, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def check_row(row, text, schema):
    """Validate one completed text. Missing class means negative only when fully reviewed."""
    required = {'sample_id', 'observation_state', 'positive_labels', 'uncertain_labels',
                'evidence', 'note', 'all_labels_reviewed'}
    required.update(categorical_specs(schema))
    if not isinstance(row, dict) or not required.issubset(row):
        raise ValueError('required annotation fields are missing')
    if not isinstance(row['sample_id'], str) or not row['sample_id']:
        raise ValueError('sample_id must be a nonempty string')
    state = row['observation_state']
    if state not in {'readable', 'insufficient'}:
        raise ValueError('observation_state must be readable or insufficient')
    pos, unknown = row['positive_labels'], row['uncertain_labels']
    if (not isinstance(pos, list) or not isinstance(unknown, list)
            or any(not isinstance(x, str) for x in pos + unknown)):
        raise ValueError('positive and uncertain labels must be string lists')
    if len(pos) != len(set(pos)) or len(unknown) != len(set(unknown)):
        raise ValueError('duplicate labels')
    if (set(pos) | set(unknown)) - set(schema['labels']):
        raise ValueError('label not in frozen codebook')
    if set(pos) & set(unknown):
        raise ValueError('positive and uncertain labels overlap')
    if type(row['all_labels_reviewed']) is not bool:
        raise ValueError('all_labels_reviewed must be boolean')
    if state == 'readable' and not row['all_labels_reviewed']:
        raise ValueError('readable text must explicitly attest all labels were reviewed')
    if state == 'insufficient' and (pos or unknown):
        raise ValueError('insufficient text must keep all labels unavailable')
    evidence = row['evidence']
    if not isinstance(evidence, dict) or set(evidence) != set(pos):
        raise ValueError('exactly one evidence string is required for each positive label')
    if any(not isinstance(v, str) or not v.strip() or v not in text for v in evidence.values()):
        raise ValueError('evidence must be an exact nonempty substring of the text')
    if not isinstance(row['note'], str):
        raise ValueError('note must be a string')
    categories = categorical_specs(schema)
    categorical_evidence = row.get('categorical_evidence', {})
    if not isinstance(categorical_evidence, dict):
        raise ValueError('categorical_evidence must be an object')
    evidence_fields = set()
    for name, definition in categories.items():
        value = row[name]
        if state == 'insufficient':
            if value != definition.get('insufficient_value'):
                raise ValueError(f'{name}: insufficient text must use the schema unknown value')
            continue
        if value not in definition['values']:
            raise ValueError(f'{name}: categorical value is invalid')
        parent = definition['parent_label']
        na, unknown_value = definition['not_applicable_value'], definition['unknown_value']
        if parent in pos and value == na:
            raise ValueError(f'{name}: positive parent cannot be not-applicable')
        if parent in unknown and value != unknown_value:
            raise ValueError(f'{name}: uncertain parent requires the uncertain value')
        if parent not in pos and parent not in unknown and value != na:
            raise ValueError(f'{name}: negative parent requires not-applicable')
        if value in definition.get('evidence_required_values', []):
            evidence_fields.add(name)
    if set(categorical_evidence) != evidence_fields:
        raise ValueError('categorical evidence must be supplied exactly for required fields')
    if any(not isinstance(v, str) or not v.strip() or v not in text for v in categorical_evidence.values()):
        raise ValueError('categorical evidence must be an exact nonempty text substring')
    return row


def verify_frozen(path):
    path = private_child(path)
    meta = json.loads((path / 'input_manifest.json').read_text(encoding='utf-8'))
    frozen = json.loads((path / 'frozen_manifest.json').read_text(encoding='utf-8'))
    if sha(path / 'input_manifest.json') != frozen['input_manifest_sha256']:
        raise ValueError('input manifest changed')
    if sha(path / 'id_map.csv') != meta['id_map_sha256']:
        raise ValueError('post mapping changed')
    if sha(path / 'frozen_schema.json') != frozen['schema_sha256']:
        raise ValueError('schema changed after freezing')
    if sha(path / 'frozen_codebook.md') != frozen['codebook_sha256']:
        raise ValueError('codebook changed after freezing')
    schema = validate_schema(json.loads((path / 'frozen_schema.json').read_text(encoding='utf-8')))
    if list(schema['labels']) != frozen['label_codes']:
        raise ValueError('schema codes do not match frozen codes')
    return meta, schema


def check_batch(path, entry, schema):
    source = path / 'inputs' / entry['name']
    target = path / 'outputs' / entry['name']
    if sha(source) != entry['sha256']:
        raise ValueError(f'{entry["name"]}: input changed')
    if not target.is_file():
        raise ValueError(f'{entry["name"]}: no completed output')
    inputs = read_jsonl(source)
    expected = {r['sample_id']: r['text'] for r in inputs}
    if len(inputs) != entry['rows'] or len(expected) != len(inputs):
        raise ValueError(f'{entry["name"]}: input IDs or counts invalid')
    result = read_jsonl(target)
    ids = [r.get('sample_id') if isinstance(r, dict) else None for r in result]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ValueError(f'{entry["name"]}: output IDs missing, repeated or unexpected')
    for row in result:
        try:
            check_row(row, expected[row['sample_id']], schema)
        except ValueError as exc:
            raise ValueError(f'{entry["name"]}, {row["sample_id"]}: {exc}') from exc
    return result


def audit(path, batch_name=None, merge=False):
    path = private_child(path)
    meta, schema = verify_frozen(path)
    targets = [b for b in meta['batches'] if batch_name is None or b['name'] == batch_name]
    if not targets:
        raise ValueError('batch is not in the frozen input manifest')
    records, errors = [], []
    for target in targets:
        try:
            records.extend(check_batch(path, target, schema))
        except (ValueError, OSError, KeyError, TypeError) as exc:
            errors.append(str(exc))
    if errors:
        print(json.dumps({'status': 'incomplete_or_invalid', 'checked_batches': len(targets),
                          'valid_batches': len(targets)-len(errors), 'errors': errors},
                         ensure_ascii=False, indent=2))
        return 1
    if not merge:
        print(json.dumps({'status': 'valid', 'checked_batches': len(targets),
                          'rows': len(records)}, ensure_ascii=False))
        return 0
    if batch_name:
        raise ValueError('merge requires every batch')
    if len(records) != meta['n_unique_texts'] or len({r['sample_id'] for r in records}) != len(records):
        raise ValueError('missing or duplicate IDs across batches')
    by_id = {r['sample_id']: r for r in records}
    mappings = read_map(path / 'id_map.csv')
    if len(mappings) != meta['total_posts'] or {r['sample_id'] for r in mappings if r['sample_id']} != set(by_id):
        raise ValueError('post mapping does not reconcile with completed annotations')
    if (path / 'merged_unique.jsonl').exists() or (path / 'post_labels.csv').exists():
        raise ValueError('merged output already exists; do not overwrite it')
    write_atomic(path / 'merged_unique.jsonl', ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records))
    output = path / 'post_labels.csv'
    temp = output.with_name(output.name + '.tmp')
    fields = (['postId', 'sample_id', 'input_status', 'observation_state']
              + list(schema['labels']) + list(categorical_specs(schema)))
    summary = {code: Counter() for code in schema['labels']}
    with temp.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for mapping in mappings:
            record = by_id.get(mapping['sample_id'])
            row = {key: mapping[key] for key in ('postId', 'sample_id', 'input_status')}
            row['observation_state'] = record['observation_state'] if record else ''
            for code in schema['labels']:
                # Blank is unknown, not zero.  An unobserved body or an
                # insufficient body cannot establish any semantic absence.
                value = ''
                if record and record['observation_state'] == 'readable':
                    value = ('1' if code in record['positive_labels'] else
                             '' if code in record['uncertain_labels'] else '0')
                row[code] = value
                summary[code]['positive' if value == '1' else 'negative' if value == '0' else 'unknown'] += 1
            for name in categorical_specs(schema):
                row[name] = record[name] if record and record[name] is not None else ''
            writer.writerow(row)
    temp.replace(output)
    result = {'status': 'AI_annotations_unvalidated', 'n_posts': len(mappings),
              'n_nonempty_posts': sum(r['input_status'] == 'needs_model' for r in mappings),
              'n_unique_coded': len(records),
              'counts_by_label': {k: dict(v) for k, v in summary.items()},
              'output_hashes': {k: sha(path / k) for k in ('merged_unique.jsonl', 'post_labels.csv')},
              'caveat': 'AI labels are not human-verified; unknown and missing remain unknown.'}
    write_json(path / 'merge_summary.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--run-dir', default=str(V3))
    p = sub.add_parser('freeze')
    p.add_argument('--run-dir', default=str(V3))
    p.add_argument('--schema', required=True)
    p.add_argument('--codebook', required=True)
    p = sub.add_parser('check')
    p.add_argument('--run-dir', default=str(V3))
    p.add_argument('--batch')
    p = sub.add_parser('merge')
    p.add_argument('--run-dir', default=str(V3))
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare(args.run_dir)
            return 0
        if args.command == 'freeze':
            freeze(args.run_dir, args.schema, args.codebook)
            return 0
        return audit(args.run_dir, getattr(args, 'batch', None), args.command == 'merge')
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('ERROR:', exc)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
