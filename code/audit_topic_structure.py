"""Diagnose K choice, repeated text, author weights and reconstruction coverage.

These are exploratory diagnostics of the old topics, not validated replacement
labels. Exact duplicate and author-balanced fits use the same frozen TF-IDF
vocabulary/IDF to isolate changes in factorization weighting.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import logging
import re

import jieba
import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.optimize import linear_sum_assignment

from audit_label_coverage import clean

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results"


def main():
    cfg = json.loads((ROOT / "code/extension_config.json").read_text())
    c = cfg["nmf"]
    raw = pd.read_csv(ROOT / "2026Data/Keep Data/sample_post_2022.csv", dtype={"postId": str})
    raw["clean_text"] = raw.content.map(clean)
    jieba.setLogLevel(logging.ERROR)
    jieba.dt.tmp_dir = str(RESULT)
    stop = set((ROOT / "code/stopwords.txt").read_text(encoding="utf-8-sig").split())
    stop.update('今天 每天 一个 自己 这个 那个 真的 还是 就是 什么 没有 可以 一下 已经 感觉 一天 还有 这样 不要 现在 时候 怎么 然后 因为 所以 但是 不是 只是 这些 那些'.split())
    tokens = raw.clean_text.map(lambda text: [w for w in jieba.lcut(re.sub(r'@[^\s@]+', ' ', text))
                                            if len(w) >= 2 and re.fullmatch(r'[\u4e00-\u9fff]+', w) and w not in stop])
    eligible = tokens.map(len).ge(c["min_tokens"])
    docs = raw.loc[eligible].copy()
    words = tokens.loc[eligible]
    v = TfidfVectorizer(tokenizer=str.split, token_pattern=None, lowercase=False,
                        min_df=c["min_df"], max_df=c["max_df"], max_features=c["max_features"])
    x = v.fit_transform(words.map(' '.join))
    nonzero = x.getnnz(axis=1) > 0
    docs = docs.iloc[np.flatnonzero(nonzero)].copy()
    words = words.iloc[np.flatnonzero(nonzero)]
    x = x[nonzero]
    vocabulary = v.get_feature_names_out()
    def fit(matrix, k):
        m = NMF(n_components=k, init='nndsvdar', max_iter=c['max_iter'], random_state=cfg['seed'], tol=1e-4)
        m.fit(matrix)
        return m
    original = fit(x, 5)
    contribution = original.transform(x) * original.components_.sum(axis=1)[None, :]
    # fit_transform and transform have different stopping tolerances. Independently
    # reproduce the original fit_transform weights before comparing saved outputs.
    original_w = original.fit_transform(x)
    contribution = original_w * original.components_.sum(axis=1)[None, :]
    assigned = contribution.sum(axis=1) > c['minimum_total_topic_contribution']
    weights = contribution[assigned] / contribution[assigned].sum(axis=1, keepdims=True)
    frozen = pd.read_csv(RESULT / 'extension_post_topics.csv', dtype={'postId': str})
    derived = pd.DataFrame(weights, columns=[f'topic_{i}' for i in range(5)])
    derived['postId'] = docs.loc[assigned, 'postId'].to_numpy()
    joined = frozen.merge(derived, on='postId', validate='one_to_one', suffixes=('_old', '_new'))
    error = max(np.max(np.abs(joined[f'topic_{i}_old'] - joined[f'topic_{i}_new'])) for i in range(5))
    assert len(joined) == len(frozen) == 2470 and error < 1e-8, error
    rows, comparison = [], []
    def record(name, model, fit_rows):
        h = model.components_
        for i in range(len(h)):
            rows.append({'fit': name, 'k': len(h), 'component': i, 'fitting_rows': fit_rows,
                         'keywords': '、'.join(vocabulary[h[i].argsort()[-12:][::-1]])})
        if len(h) == 5:
            a = original.components_ / np.linalg.norm(original.components_, axis=1, keepdims=True)
            b = h / np.linalg.norm(h, axis=1, keepdims=True)
            rr, cc = linear_sum_assignment(-(a @ b.T))
            for i, j in zip(rr, cc):
                comparison.append({'fit': name, 'original_component': int(i), 'matched_component': int(j),
                                   'cosine_similarity': float(a[i] @ b[j])})
    record('original_k5', original, len(docs))
    for k in [3, 4, 6, 7, 8]:
        record(f'k{k}', fit(x, k), len(docs))
    unique = ~docs.clean_text.duplicated()
    record('exact_text_deduplicated_k5', fit(x[np.flatnonzero(unique)], 5), int(unique.sum()))
    counts = docs.groupby('userId').userId.transform('size').to_numpy()
    # Squared-error NMF on row-scaled X gives each author's rows equal total
    # objective weight. It does not solve nonrepresentative author sampling.
    balanced = x.multiply((1 / np.sqrt(counts))[:, None]).tocsr()
    record('author_equal_objective_k5', fit(balanced, 5), len(docs))
    pd.DataFrame(rows).to_csv(RESULT / 'teacher_topic_structure_terms.csv', index=False, encoding='utf-8-sig')
    pd.DataFrame(comparison).to_csv(RESULT / 'teacher_topic_structure_similarity.csv', index=False, encoding='utf-8-sig')
    den = np.sqrt(np.asarray(x.multiply(x).sum(axis=1)).ravel())
    predicted = original_w @ original.components_
    sq_error = np.asarray(x.multiply(x).sum(axis=1)).ravel() - 2 * np.asarray(x.multiply(predicted).sum(axis=1)).ravel() + (predicted ** 2).sum(axis=1)
    relative_error = np.sqrt(np.maximum(sq_error, 0)) / den
    used = set(vocabulary)
    coverage = words.map(lambda a: sum(w in used for w in a) / len(a))
    dup = docs.clean_text.value_counts()
    summary = {
        'fitted_documents': len(docs), 'assigned': int(assigned.sum()), 'unique_clean_texts_fitted': int(unique.sum()),
        'duplicate_text_rows_beyond_first': int((~unique).sum()),
        'largest_exact_template_documents': int(dup.iloc[0]), 'top10_exact_templates_documents': int(dup.head(10).sum()),
        'frozen_weight_max_error': float(error),
        'reconstruction_relative_error_quantiles': {str(q): float(np.quantile(relative_error, q)) for q in [.25, .5, .75, .9]},
        'retained_token_coverage_quantiles': {str(q): float(coverage.quantile(q)) for q in [.25, .5, .75, .9]},
        'k_values_checked': [3, 4, 5, 6, 7, 8],
        'selection_note': 'K was fixed at 5 in the old configuration. These alternative fits diagnose dependence on K/weighting; no K is selected by likes, fit error alone, or significance. No replacement taxonomy is declared validated.',
        'weight_note': 'Normalized document weights are relative component contributions, not probabilities of label correctness. Even a value of 1 can follow from poor reconstruction of a sparse document.',
        'dedup_note': 'Exact cleaned-text deduplication only; near-duplicate templates remain. Same vocabulary/IDF used across alternatives.',
        'author_weight_note': 'Frobenius NMF trained on X_i/sqrt(n_author), so author objective weights sum equally. IDF is still from original rows; this is a scoped diagnostic, not a fully author-balanced text pipeline.',
        'component_comparisons': comparison,
        'source_hashes': {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in [ROOT/'code/extension_config.json', ROOT/'code/stopwords.txt', RESULT/'extension_post_topics.csv']},
    }
    (RESULT / 'teacher_topic_structure_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main()
