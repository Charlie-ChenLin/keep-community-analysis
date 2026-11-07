#!/usr/bin/env python3
"""Unsupervised text-representation alternatives, never outcome-selected.

Fit on exact unique frozen cleaned texts and map to all eligible posts. Public
JSON contains aggregate diagnostics only. Components/clusters are numerical
representations and are not claimed to be validated semantic classes.
"""
from __future__ import annotations

import os
for _key in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_key] = '1'
import hashlib
import json
from pathlib import Path
import re
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import NMF, PCA, TruncatedSVD
from sklearn.exceptions import ConvergenceWarning
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler, normalize

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'validation/classification_rebuild/private/v3_refined_batches'
PRIVATE = ROOT / 'validation/classification_rebuild/private/variable_scheme_exploration/continuous'
OUT = ROOT / 'results/continuous_text_scheme_comparison.json'
SEED = 20261104


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lexical(text):
    return re.sub(r'[^A-Za-z0-9\u3400-\u9fff]+', ' ', text).strip().lower()


def character_ngrams(text):
    # Preserve span boundaries but never let a whitespace token become a broad
    # component. Do not join across punctuation or other removed material.
    return [span[i:i+n] for span in text.split() for n in (1, 2, 3)
            for i in range(len(span)-n+1)]


def vif(matrix):
    x = np.asarray(matrix, dtype=float)
    x -= x.mean(axis=0)
    sd = x.std(axis=0)
    if np.any(sd < 1e-12):
        return {'status': 'constant_feature'}
    x /= sd
    corr = x.T @ x / len(x)
    rank = int(np.linalg.matrix_rank(corr))
    if rank < corr.shape[0]:
        return {'status': 'rank_deficient', 'rank': rank, 'columns': corr.shape[0]}
    values = np.diag(np.linalg.inv(corr))
    return {'status': 'computed', 'min': float(values.min()), 'max': float(values.max())}


def compare_binary_pca():
    """Compress known v2 non-other labels, preserving uncertain as missing."""
    source = ROOT / 'validation/classification_rebuild/private/v2_direct_batches/post_labels.csv'
    schema = json.loads((ROOT / 'code/classification_schema_v2.json').read_text())
    codes = [k for k in schema['expression_labels'] if k != 'F_OTHER']
    labels = pd.read_csv(source, dtype=str, keep_default_na=False)
    labels = labels.loc[labels.input_status.eq('needs_model')].copy()
    positive = labels.expression_labels.map(lambda x: set(json.loads(x)) if x else set())
    uncertain = labels.uncertain_expression.map(lambda x: set(json.loads(x)) if x else set())
    matrix = np.array([[1 if k in p else np.nan if k in u else 0 for k in codes]
                       for p, u in zip(positive, uncertain)], dtype=float)
    readable = labels.observation_state.eq('readable').to_numpy()
    matrix[~readable] = np.nan
    complete = np.isfinite(matrix).all(axis=1)
    labels = labels.loc[complete].reset_index(drop=True)
    matrix = matrix[complete]
    # Direct coding is performed at unique-text level; assert that mapping has
    # not introduced disagreements before deduplicating the fit population.
    full = pd.DataFrame(matrix, columns=codes)
    full['sample_id'] = labels.sample_id
    if full.groupby('sample_id')[codes].nunique().to_numpy().max() != 1:
        raise ValueError('Mapped v2 exact text has inconsistent labels')
    fit_rows = ~full.sample_id.duplicated()
    fit_matrix = matrix[fit_rows]
    scaler = StandardScaler().fit(fit_matrix)
    x = scaler.transform(fit_matrix)
    xp = scaler.transform(matrix)
    result = {'source': 'v2 ten non-other expression indicators', 'label_codes': codes,
              'n_nonempty_posts': 5414, 'n_complete_posts': len(matrix),
              'n_complete_unique_texts': len(x), 'sample_retention_fraction': len(matrix)/5414,
              'n_excluded_posts_any_unknown_or_insufficient': int(5414-len(matrix)),
              'fit_unit': 'Exact unique readable texts for which all ten non-other labels are known.',
              'scaling': 'Center and divide each binary variable by its standard deviation on fit unique texts.',
              'input_sha256': sha(source), 'dimensions': {},
              'limits': ['PCA composites do not improve unknown-label coverage or validate the source AI classifications.',
                         'Standardization gives rare binary labels equal total variance and may magnify thinly supported labels.',
                         'PCA components are algebraically orthogonal on fit unique texts; mapped posts and regression controls can alter correlations.',
                         'PCA is not multiple correspondence analysis. No MCA has been computed.']}
    for dim in (3, 5):
        pca = PCA(n_components=dim, svd_solver='full').fit(x)
        unique_scores = pca.transform(x)
        post_scores = pca.transform(xp)
        reconstruction = pca.inverse_transform(unique_scores)
        per_label_retention = 1-np.mean((x-reconstruction)**2, axis=0)/np.mean(x*x, axis=0)
        unique_corr = np.corrcoef(unique_scores.T)
        post_corr = np.corrcoef(post_scores.T)
        result['dimensions'][str(dim)] = {'components': dim,
            'explained_variance_fraction': float(pca.explained_variance_ratio_.sum()),
            'per_component_explained_variance_fraction': pca.explained_variance_ratio_.tolist(),
            'coefficient_matrix_codes_in_declared_order': pca.components_.tolist(),
            'variance_retained_by_original_label_unique': dict(zip(codes, per_label_retention.tolist())),
            'max_abs_offdiagonal_correlation_fit_unique': float(np.abs(unique_corr-np.eye(dim)).max()),
            'max_abs_offdiagonal_correlation_mapped_posts': float(np.abs(post_corr-np.eye(dim)).max()),
            'feature_only_vif_mapped_posts': vif(post_scores.copy())}
        np.savez_compressed(PRIVATE/f'v2_binary_pca_{dim}.npz',
            sample_id=full.loc[fit_rows, 'sample_id'].to_numpy(dtype=str), scores=unique_scores)
    return result


def main():
    started = time.monotonic()
    PRIVATE.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted((SOURCE / 'inputs').glob('*.jsonl')):
        rows.extend(json.loads(line) for line in path.read_text().splitlines() if line.strip())
    unique = pd.DataFrame(rows)
    if len(unique) != 4156 or unique.sample_id.duplicated().any() or unique.text.duplicated().any():
        raise ValueError('Unexpected unique-text universe')
    unique['lexical'] = unique.text.map(lexical)
    unique['lexical_length'] = unique.lexical.str.replace(r'\s+', '', regex=True).str.len()
    mapping = pd.read_csv(SOURCE / 'id_map.csv', dtype=str, keep_default_na=False)
    posts = pd.read_csv(ROOT / 'results/post_features.csv', dtype={'postId': str})
    data = posts.merge(mapping, on='postId', validate='one_to_one')
    data = data.loc[data.input_status.eq('needs_model')].copy()
    if len(data) != 5414:
        raise ValueError('Nonempty universe mismatch')
    index = pd.Series(np.arange(len(unique)), index=unique.sample_id)
    mapped = data.sample_id.map(index).to_numpy(dtype=int)
    vectorizer = TfidfVectorizer(analyzer=character_ngrams, min_df=2,
                                 max_df=.98, max_features=20000, lowercase=True,
                                 dtype=np.float64)
    x = vectorizer.fit_transform(unique.lexical)
    active = np.asarray(x.getnnz(axis=1)).ravel() > 0
    xm = x[active]
    active_index = np.full(len(unique), -1, dtype=int)
    active_index[active] = np.arange(active.sum())
    post_active = active[mapped]
    valid_map = active_index[mapped[post_active]]
    pa = data.loc[post_active].reset_index(drop=True)
    raw_vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(1, 3), min_df=1,
                                     max_features=20000, lowercase=True)
    raw = raw_vectorizer.fit_transform(unique.text)
    raw_active = np.asarray(raw.getnnz(axis=1)).ravel() > 0
    length_unique = unique.lexical_length.to_numpy()
    lengths = length_unique[mapped]
    strata = {}
    for name, mask in [('zero_lexical_chars', lengths == 0), ('one_to_four_chars', (lengths > 0) & (lengths <= 4)),
                       ('five_to_nineteen_chars', (lengths >= 5) & (lengths <= 19)), ('twenty_plus_chars', lengths >= 20)]:
        strata[name] = {'posts': int(mask.sum()), 'with_nonzero_lexical_vector': int((mask & post_active).sum())}
    result = {
        'status': 'exploratory_unsupervised_not_human_validated',
        'seed': SEED, 'n_nonempty_posts': len(data), 'n_unique_texts': len(unique),
        'fit_unit': 'Exact unique cleaned text; fitted without likes, author labels or historical semantic labels.',
        'vectorization': {'analyzer': 'character', 'ngram_range': [1, 3], 'min_df': 2,
                          'max_df': .98, 'max_features': 20000, 'vocabulary_size': x.shape[1],
                          'lexical_preprocessing': 'Keep Chinese characters, ASCII letters and digits; create within-span 1-3 character ngrams, no whitespace or cross-span tokens.',
                          'nonzero_unique': int(active.sum()), 'nonzero_posts': int(post_active.sum()),
                          'nonzero_post_fraction': float(post_active.mean()),
                          'raw_character_vector_nonzero_posts': int(raw_active[mapped].sum()),
                          'raw_character_note': 'Raw characters include punctuation and symbols; representation coverage is not semantic interpretability.',
                          'zero_lexical_character_posts': int((lengths == 0).sum()),
                          'positive_lexical_chars_but_zero_vector_posts': int(((lengths > 0) & ~post_active).sum()),
                          'length_strata': strata},
        'nmf': {}, 'svd': {}, 'kmeans': {},
        'input_sha256': {'post_features': sha(ROOT / 'results/post_features.csv'), 'id_map': sha(SOURCE / 'id_map.csv'),
                         'frozen_manifest': sha(SOURCE / 'frozen_manifest.json'),
                         'input_batches': {p.name: sha(p) for p in sorted((SOURCE / 'inputs').glob('*.jsonl'))}},
        'limits': ['Nonzero vector coverage is neither category accuracy nor semantic validation.',
                   'Character components mix content, wording, templates and style; no human semantic class names are assigned.',
                   'Exact deduplication does not remove near templates or fully balance authors.',
                   'No likes models or p-value-based dimension selection are performed.',
                   'Seed stability is an algorithm diagnostic and does not establish semantic reliability.',
                   'KMeans seed stability and silhouette are conditional on one fixed normalized 12-dimensional SVD space, not stability to SVD seeds, sampling, or the original character space. L2 normalization can amplify weak text projections.',
                   'Feature-only VIF does not replace a regression design audit with metadata and author/date effects.']}
    z = None
    for dim in (5, 8, 12):
        model = TruncatedSVD(n_components=dim, n_iter=7, random_state=SEED)
        u = model.fit_transform(xm)
        up = u[valid_map]
        energy = np.sum(u*u, axis=1)
        result['svd'][str(dim)] = {'components': dim,
            'explained_variance_fraction': float(model.explained_variance_ratio_.sum()),
            'median_retained_squared_row_norm_unique': float(np.median(energy)),
            'nonzero_projected_posts': int((np.linalg.norm(up, axis=1) > 1e-12).sum()),
            'feature_only_vif': vif(up.copy()),
            'interpretation': 'Signed latent coordinates; algebraic compression, not probabilities or validated expression categories.'}
        np.savez_compressed(PRIVATE / f'svd_{dim}.npz', unique_sample_id=unique.loc[active, 'sample_id'].to_numpy(dtype=str), scores=u)
        if dim == 12:
            z = normalize(u)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ConvergenceWarning)
            nmf = NMF(n_components=dim, init='nndsvda', solver='cd', max_iter=300, tol=1e-4, random_state=SEED)
            w = nmf.fit_transform(xm)
        h = nmf.components_
        contribution = w * h.sum(axis=1)
        denom = contribution.sum(axis=1, keepdims=True)
        weights = np.divide(contribution, denom, out=np.zeros_like(contribution), where=denom > 1e-12)
        wp = weights[valid_map]
        component_cosine = normalize(h) @ normalize(h).T
        off = component_cosine[np.triu_indices(dim, k=1)]
        dom = wp.argmax(axis=1)
        clusters = []
        for k in range(dim):
            d = pa.loc[dom == k]
            author_counts = d.author.value_counts()
            clusters.append({'component': k, 'dominant_posts': len(d), 'authors': int(d.author.nunique()),
                'largest_author_share': float(author_counts.iloc[0] / len(d)) if len(d) else None})
        # Drop the most prevalent dominant component before feature-only VIF.
        reference = int(np.bincount(dom, minlength=dim).argmax())
        result['nmf'][str(dim)] = {'components': dim, 'iterations': int(nmf.n_iter_),
            'convergence_warning': any(issubclass(v.category, ConvergenceWarning) for v in caught),
            'relative_frobenius_reconstruction_error': float(nmf.reconstruction_err_ / np.sqrt(xm.multiply(xm).sum())),
            'nonzero_weight_posts': int((wp.sum(axis=1) > 0).sum()),
            'median_max_normalized_weight_posts': float(np.median(wp.max(axis=1))),
            'post_fraction_max_weight_below_0_5': float((wp.max(axis=1) < .5).mean()),
            'max_component_cosine_similarity': float(off.max()),
            'median_component_cosine_similarity': float(np.median(off)),
            'dominant_component_diagnostics': clusters,
            'reference_component_for_vif': reference,
            'feature_only_vif_drop_reference': vif(np.delete(wp, reference, axis=1).copy()),
            'composition_note': 'Nonzero component contributions normalized to sum one; intercept plus all components is rank deficient.',
            'interpretation': 'Relative numerical character-component contributions, not calibrated semantic membership probabilities.'}
        np.savez_compressed(PRIVATE / f'nmf_{dim}.npz', unique_sample_id=unique.loc[active, 'sample_id'].to_numpy(dtype=str), scores=weights)
        vocab = vectorizer.get_feature_names_out()
        private_inspection = []
        for k in range(dim):
            top_terms = vocab[np.argsort(h[k])[-15:][::-1]].tolist()
            # Highly weighted examples are for interpretation, not validation.
            example_indices = np.argsort(contribution[:, k])[-6:][::-1]
            source_rows = unique.loc[active].reset_index(drop=True).iloc[example_indices]
            private_inspection.append({'component': k, 'top_character_ngrams': top_terms,
                'examples': source_rows[['sample_id', 'text']].to_dict('records')})
        (PRIVATE / f'nmf_{dim}_inspection.json').write_text(json.dumps(private_inspection, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps({'finished_dimension': dim, 'elapsed_seconds': round(time.monotonic()-started, 1)}), flush=True)
    for k in (5, 8, 12):
        first = KMeans(n_clusters=k, n_init=10, max_iter=300, random_state=SEED).fit(z)
        second = KMeans(n_clusters=k, n_init=10, max_iter=300, random_state=SEED+1).fit(z)
        labels = first.labels_
        mapped_labels = labels[valid_map]
        diag = []
        for label in range(k):
            d = pa.loc[mapped_labels == label]
            counts = d.author.value_counts()
            diag.append({'cluster': label, 'posts': len(d), 'unique_texts': int((labels == label).sum()),
                         'authors': int(d.author.nunique()),
                         'largest_author_share': float(counts.iloc[0]/len(d)) if len(d) else None,
                         'median_lexical_length': float(np.median(lengths[post_active][mapped_labels == label])) if len(d) else None})
        result['kmeans'][str(k)] = {'clusters': k, 'representation': 'L2-normalized 12-dimensional SVD of lexical character TF-IDF',
            'assigned_posts': int(post_active.sum()),
            'silhouette_cosine_sample_1500': float(silhouette_score(z, labels, metric='cosine', sample_size=min(1500, len(z)), random_state=SEED)),
            'adjusted_rand_index_between_seeds_unique': float(adjusted_rand_score(labels, second.labels_)),
            'cluster_diagnostics': diag,
            'interpretation': 'Forced exclusive clusters on nonzero features; assignment coverage does not validate class meaning or exclusivity.'}
        pd.DataFrame({'sample_id': unique.loc[active, 'sample_id'], 'cluster': labels}).to_csv(PRIVATE / f'kmeans_{k}.csv', index=False)
    result['v2_binary_pca'] = compare_binary_pca()
    result['elapsed_seconds'] = float(time.monotonic()-started)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'output': str(OUT), 'nonzero_posts': int(post_active.sum()), 'elapsed_seconds': round(result['elapsed_seconds'], 1)}))


if __name__ == '__main__':
    main()
