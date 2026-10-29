"""Scoped final evidence/coverage checks, independently counting source CSV rows."""
from collections import Counter
import ast
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    checks = []
    def check(name, ok):
        checks.append({'check': name, 'passed': bool(ok)})
        assert ok, name
    def read(path):
        return json.loads((ROOT/path).read_text())
    def sha(path):
        return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    for name in ['analyze_dictionary_diagnostics.py', 'analyze_author_tags_feedback.py', 'analyze_topic_overlap.py', 'audit_label_coverage.py', 'audit_topic_structure.py', 'analyze_complete_body.py', 'analyze_topic_author_support.py', 'build_teacher_feedback_report.py']:
        ast.parse((ROOT/'code'/name).read_text())
    check('new Python scripts parse', True)
    d = read('results/teacher_feedback_dictionary.json')
    for x in d['inputs']:
        check('unchanged input '+x['path'], sha(x['path']) == x['sha256'])
    a = read('results/teacher_author_tags_summary.json')
    for path, value in a['source_hashes'].items():
        check('unchanged author/tag source '+path, sha(path) == value)
    old = read('validation/slides_12min_dyx/render_checks.json')
    for ext in ['pptx', 'pdf']:
        check('old presentation '+ext+' unchanged', sha(f'Keep社区内容表达与互动反馈_12分钟合并版.{ext}') == old[ext+'_sha256'])
    c = read('results/teacher_label_coverage_summary.json')
    check('coverage partitions reconcile', c['clean_empty'] + c['nmf_unassigned_nonempty'] + c['nmf_assigned'] == c['posts'])
    check('review sample reconciles', sum(c['single_ai_review']['total'].values()) == 60)
    check('dictionary independent checks passed', all(x['passed'] for x in read('validation/teacher_feedback/dictionary_checks.json')))
    check('topic independent checks passed', read('validation/teacher_feedback/topic_checks.json')['all_checks_passed'])
    check('author/tag checks passed', read('results/teacher_author_tags_validation.json')['passed'])
    # Independently count raw body/author/tag coverage with stdlib iteration.
    raw = list(csv.DictReader((ROOT/'2026Data/Keep Data/sample_post_2022.csv').open(encoding='utf-8-sig', newline='')))
    authors = Counter()
    body_n = 0
    nonempty_n = 0
    tag_n = 0
    tags = set()
    for row in raw:
        authors[row['userId']] += 1
        text = row['content'].replace('\\n', '\n').replace('\\r', ' ')
        body_n += bool(text.strip())
        text = re.sub(r'https?://\S+', ' ', text)
        text = re.sub(r'Ⓚ[^Ⓚ]*Ⓚ', ' ', text)
        text = re.sub(r'\[[^\[\]]{1,12}\]', ' ', text)
        nonempty_n += bool(re.sub(r'\s+', '', text))
        arr = json.loads(row['hashTags'].replace('""', '"'))
        tag_n += bool(arr)
        tags.update(arr)
    check('raw CSV body coverage independent count', body_n == c['raw_body_available'] == 5548 and nonempty_n == c['nonempty_clean_body'] == 5414)
    check('raw CSV tag coverage independent count', tag_n == a['tag_summary']['tagged_posts'] == 5209 and len(tags) == a['tag_summary']['unique_tags'] == 269)
    check('raw CSV author count independent count', len(authors) == 100 and min(authors.values()) == 1 and max(authors.values()) == 783)
    check('raw CSV singleton count independent count', sum(n == 1 for n in authors.values()) == 2)
    cm = read('results/teacher_complete_body_model.json')
    iv = cm['independent_verification']
    check('complete body matrix and manual sandwich reproduced', max(iv['max_focal_coefficient_error'],iv['max_focal_se_error'],iv['joint_p_error']) < 1e-10)
    check('all three missingness populations exposed', [x['n'] for x in cm['models']] == [9532,5548,5414])
    check('NMF original weights independently reproduced', read('results/teacher_topic_structure_summary.json')['frozen_weight_max_error'] < 1e-8)
    check('candidate codebook is explicitly unvalidated', '尚未验证' in read('code/revised_content_codebook.json')['status'])
    ta=read('results/teacher_topic_author_support.json')
    check('topic authors recomputed within topic sample', ta['topic_authors']==86 and ta['small_author_counts'][0]['authors']==10)
    check('topic author threshold designs are full rank', all(x['rank']==x['parameters'] for x in ta['models']))
    target = ROOT/'validation/teacher_feedback/integration_checks.json'
    target.write_text(json.dumps({'checks':checks,'all_passed':True},ensure_ascii=False,indent=2)+'\n')
    print('Passed', len(checks), 'scoped integration checks')


if __name__ == '__main__':
    main()
