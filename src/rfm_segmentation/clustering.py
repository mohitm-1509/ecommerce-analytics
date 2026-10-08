"""
Phase 3: Stable Deterministic Clustering

Determines optimal K using Elbow + Silhouette analysis, fits K-Means on
PCA space, and benchmarks against DBSCAN for algorithm comparison.
"""
import logging

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import (
    silhouette_score,
    calinski_harabasz_score,
    davies_bouldin_score,
)
from sklearn.neighbors import NearestNeighbors

from src.rfm_segmentation.config import K_RANGE, RANDOM_STATE, OUTPUT_DIR

logger = logging.getLogger(__name__)

SIL_SAMPLE_SIZE = 10000


def elbow_analysis(X: np.ndarray) -> pd.DataFrame:
    results = []
    for k in K_RANGE:
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE)
        labels = km.fit_predict(X)
        if k > 1:
            sil = silhouette_score(
                X, labels, sample_size=SIL_SAMPLE_SIZE, random_state=RANDOM_STATE,
            )
            ch = calinski_harabasz_score(X, labels)
            db = davies_bouldin_score(X, labels)
        else:
            sil, ch, db = 0.0, 0.0, float("inf")
        results.append({
            "k": k,
            "inertia": round(km.inertia_, 2),
            "silhouette": round(sil, 4),
            "calinski_harabasz": round(ch, 2),
            "davies_bouldin": round(db, 4),
        })
        logger.info(
            "  K=%d: inertia=%.0f, silhouette=%.4f, CH=%.1f, DB=%.4f",
            k, km.inertia_, sil, ch, db,
        )
    return pd.DataFrame(results)


def select_optimal_k(metrics: pd.DataFrame) -> int:
    best_sil_k = int(metrics.loc[metrics["silhouette"].idxmax(), "k"])
    best_sil_score = metrics["silhouette"].max()
    logger.info("Best K by silhouette: %d (score=%.4f)", best_sil_k, best_sil_score)

    best_ch_k = int(metrics.loc[metrics["calinski_harabasz"].idxmax(), "k"])
    logger.info(
        "Best K by Calinski-Harabasz: %d (score=%.1f)",
        best_ch_k,
        metrics.loc[metrics["calinski_harabasz"].idxmax(), "calinski_harabasz"],
    )

    best_db_k = int(metrics.loc[metrics["davies_bouldin"].idxmin(), "k"])
    logger.info(
        "Best K by Davies-Bouldin: %d (score=%.4f)",
        best_db_k,
        metrics.loc[metrics["davies_bouldin"].idxmin(), "davies_bouldin"],
    )

    optimal_k = best_sil_k
    logger.info("Selected K=%d (silhouette-optimal — best cluster separation)", optimal_k)
    return optimal_k


def fit_kmeans(X: np.ndarray, k: int) -> tuple:
    km = KMeans(n_clusters=k, n_init=20, random_state=RANDOM_STATE)
    labels = km.fit_predict(X)
    logger.info(
        "K-Means (K=%d) cluster sizes: %s",
        k, dict(zip(*np.unique(labels, return_counts=True))),
    )
    return km, labels


def fit_dbscan(X: np.ndarray, sample_size: int = 15000) -> tuple:
    rng = np.random.RandomState(RANDOM_STATE)
    if len(X) > sample_size:
        idx = rng.choice(len(X), sample_size, replace=False)
        X_sample = X[idx]
        logger.info("DBSCAN: using %d-sample subset for efficiency", sample_size)
    else:
        X_sample = X

    nn = NearestNeighbors(n_neighbors=10)
    nn.fit(X_sample)
    distances, _ = nn.kneighbors(X_sample)
    sorted_dists = np.sort(distances[:, -1])

    best_sil = -1.0
    best_result = None

    for pct in [75, 85, 90, 95]:
        eps = float(np.percentile(sorted_dists, pct))
        db = DBSCAN(eps=eps, min_samples=10)
        labels = db.fit_predict(X_sample)
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        non_noise = labels != -1

        if n_clusters >= 2 and non_noise.sum() > n_clusters:
            sil = silhouette_score(X_sample[non_noise], labels[non_noise])
            if sil > best_sil:
                best_sil = sil
                best_result = (labels, n_clusters, non_noise, eps)

    if best_result is None:
        logger.info("DBSCAN: no valid clustering found across eps candidates")
        return np.full(len(X_sample), -1), {
            "n_clusters": 0, "n_noise": len(X_sample), "eps": 0,
            "silhouette": 0.0, "calinski_harabasz": 0.0,
            "davies_bouldin": float("inf"),
        }

    labels, n_clusters, non_noise, eps = best_result
    n_noise = (labels == -1).sum()
    logger.info(
        "DBSCAN best eps=%.4f: %d clusters, %d noise points (%.1f%%)",
        eps, n_clusters, n_noise, n_noise / len(labels) * 100,
    )

    ch = calinski_harabasz_score(X_sample[non_noise], labels[non_noise])
    dbi = davies_bouldin_score(X_sample[non_noise], labels[non_noise])

    info = {
        "n_clusters": n_clusters,
        "n_noise": int(n_noise),
        "eps": round(eps, 4),
        "silhouette": round(best_sil, 4),
        "calinski_harabasz": round(ch, 2),
        "davies_bouldin": round(dbi, 4),
    }
    logger.info("DBSCAN metrics: silhouette=%.4f, CH=%.1f, DB=%.4f", best_sil, ch, dbi)
    return labels, info


def run_clustering(pca_df: pd.DataFrame) -> pd.DataFrame:
    logger.info("=" * 60)
    logger.info("PHASE 3: Clustering & Optimisation")
    logger.info("=" * 60)

    pc_cols = [c for c in pca_df.columns if c.startswith("PC")]
    X = pca_df[pc_cols].values

    logger.info(
        "Step 1/4: Elbow + multi-metric analysis (K=%d..%d)...",
        K_RANGE.start, K_RANGE.stop - 1,
    )
    metrics = elbow_analysis(X)
    metrics.to_csv(OUTPUT_DIR / "clustering_metrics.csv", index=False)

    logger.info("Step 2/4: Selecting optimal K...")
    optimal_k = select_optimal_k(metrics)

    logger.info("Step 3/4: Fitting final K-Means (K=%d)...", optimal_k)
    km, km_labels = fit_kmeans(X, optimal_k)

    km_sil = silhouette_score(
        X, km_labels, sample_size=SIL_SAMPLE_SIZE, random_state=RANDOM_STATE,
    )
    km_ch = calinski_harabasz_score(X, km_labels)
    km_db = davies_bouldin_score(X, km_labels)

    logger.info("Step 4/4: DBSCAN comparison...")
    _, db_info = fit_dbscan(X)

    comparison = pd.DataFrame([
        {
            "algorithm": "K-Means", "k": optimal_k,
            "silhouette": round(km_sil, 4),
            "calinski_harabasz": round(km_ch, 2),
            "davies_bouldin": round(km_db, 4),
        },
        {
            "algorithm": "DBSCAN", "k": db_info["n_clusters"],
            "silhouette": db_info["silhouette"],
            "calinski_harabasz": db_info["calinski_harabasz"],
            "davies_bouldin": db_info["davies_bouldin"],
        },
    ])
    comparison.to_csv(OUTPUT_DIR / "algorithm_comparison.csv", index=False)
    logger.info("Algorithm comparison:\n%s", comparison.to_string(index=False))

    result = pca_df.copy()
    result["cluster"] = km_labels

    centroids = pd.DataFrame(km.cluster_centers_, columns=pc_cols)
    centroids["cluster"] = range(optimal_k)
    centroids.to_csv(OUTPUT_DIR / "cluster_centroids.csv", index=False)

    result.to_csv(OUTPUT_DIR / "clustered_customers.csv", index=False)
    logger.info("Saved clustered_customers.csv with %d clusters", optimal_k)

    return result


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    pca_df = pd.read_csv(OUTPUT_DIR / "pca_transformed.csv")
    run_clustering(pca_df)
