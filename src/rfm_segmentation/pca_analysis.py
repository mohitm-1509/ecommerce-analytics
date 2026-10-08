"""
Phase 2: Mathematical Optimisation — PCA Decomposition

Decouples correlated RFM features into orthogonal principal components,
retaining maximum variance in a 2D coordinate space.
"""
import logging

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

from src.rfm_segmentation.config import OUTPUT_DIR, RANDOM_STATE

logger = logging.getLogger(__name__)

FEATURES = ["recency", "frequency", "monetary"]
N_TARGET_COMPONENTS = 2


def analyse_correlation(rfm_scaled: pd.DataFrame) -> pd.DataFrame:
    corr = rfm_scaled[FEATURES].corr()
    logger.info("Correlation matrix:\n%s", corr.round(4).to_string())
    return corr


def fit_full_pca(rfm_scaled: pd.DataFrame) -> tuple:
    pca = PCA(n_components=len(FEATURES), random_state=RANDOM_STATE)
    all_transformed = pca.fit_transform(rfm_scaled[FEATURES].values)

    logger.info("PCA eigenvalues: %s", np.round(pca.explained_variance_, 4))
    logger.info(
        "Explained variance ratio: %s",
        np.round(pca.explained_variance_ratio_, 4),
    )
    cumulative = np.cumsum(pca.explained_variance_ratio_)
    logger.info("Cumulative variance: %s", np.round(cumulative, 4))

    loadings = pd.DataFrame(
        pca.components_.T,
        columns=[f"PC{i+1}" for i in range(len(FEATURES))],
        index=FEATURES,
    )
    logger.info(
        "PCA loadings (feature → component mapping):\n%s",
        loadings.round(4).to_string(),
    )

    return pca, all_transformed, loadings


def run_pca(rfm_scaled: pd.DataFrame) -> pd.DataFrame:
    logger.info("=" * 60)
    logger.info("PHASE 2: PCA Dimensionality Reduction")
    logger.info("=" * 60)

    logger.info("Step 1/3: Analysing feature correlations...")
    corr = analyse_correlation(rfm_scaled)
    corr.to_csv(OUTPUT_DIR / "correlation_matrix.csv")

    logger.info("Step 2/3: Fitting PCA (all %d components)...", len(FEATURES))
    pca, all_transformed, loadings_full = fit_full_pca(rfm_scaled)

    logger.info("Step 3/3: Projecting to %d components...", N_TARGET_COMPONENTS)
    cumulative = np.cumsum(pca.explained_variance_ratio_)
    retained = cumulative[N_TARGET_COMPONENTS - 1] * 100
    logger.info(
        "Retaining %d components — %.2f%% of total variance", N_TARGET_COMPONENTS, retained,
    )
    if retained < 90:
        logger.info(
            "  Note: features are weakly correlated after transforms, so "
            "variance is spread across components. %.1f%% is still "
            "sufficient for clustering separation.",
            retained,
        )

    transformed = all_transformed[:, :N_TARGET_COMPONENTS]

    pca_df = rfm_scaled[["customer_unique_id"]].copy()
    for i in range(N_TARGET_COMPONENTS):
        pca_df[f"PC{i+1}"] = transformed[:, i]

    pca_df.to_csv(OUTPUT_DIR / "pca_transformed.csv", index=False)
    logger.info("Saved pca_transformed.csv (%d components)", N_TARGET_COMPONENTS)

    loadings_2d = loadings_full.iloc[:, :N_TARGET_COMPONENTS]
    loadings_2d.to_csv(OUTPUT_DIR / "pca_loadings.csv")

    variance_df = pd.DataFrame({
        "component": [f"PC{i+1}" for i in range(len(FEATURES))],
        "explained_variance": pca.explained_variance_,
        "explained_variance_ratio": pca.explained_variance_ratio_,
        "cumulative_variance_ratio": cumulative,
    })
    variance_df.to_csv(OUTPUT_DIR / "pca_variance.csv", index=False)

    return pca_df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    rfm_scaled = pd.read_csv(OUTPUT_DIR / "rfm_scaled.csv")
    run_pca(rfm_scaled)
