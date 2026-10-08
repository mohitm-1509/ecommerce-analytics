"""
RFM Segmentation Pipeline — Full Orchestrator

Runs all 4 phases end-to-end:
  Phase 1: RFM Feature Engineering (aggregate, transform, standardise)
  Phase 2: PCA Dimensionality Reduction (decorrelate, project to 2D)
  Phase 3: Clustering Optimisation (K-Means + DBSCAN comparison)
  Phase 4: Segment Profiling & SHAP Explainability

Usage:
    python -m src.rfm_segmentation.pipeline          # run all phases
    python -m src.rfm_segmentation.pipeline 1         # phase 1 only
    python -m src.rfm_segmentation.pipeline 1 2 3     # phases 1-3
    python -m src.rfm_segmentation.pipeline plots      # regenerate plots only
"""
import logging
import sys
import time

import pandas as pd

from src.rfm_segmentation.config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def run_pipeline(phases=None) -> None:
    overall_start = time.time()

    if phases is None:
        phases = [1, 2, 3, 4]

    rfm_scaled = None
    pca_df = None
    clustered = None

    if 1 in phases:
        from src.rfm_segmentation.feature_engineering import run_feature_engineering
        rfm_scaled = run_feature_engineering()

    if 2 in phases:
        from src.rfm_segmentation.pca_analysis import run_pca
        if rfm_scaled is None:
            path = OUTPUT_DIR / "rfm_scaled.csv"
            if not path.exists():
                logger.error("rfm_scaled.csv not found. Run phase 1 first.")
                return
            rfm_scaled = pd.read_csv(path)
        pca_df = run_pca(rfm_scaled)

    if 3 in phases:
        from src.rfm_segmentation.clustering import run_clustering
        if pca_df is None:
            path = OUTPUT_DIR / "pca_transformed.csv"
            if not path.exists():
                logger.error("pca_transformed.csv not found. Run phase 2 first.")
                return
            pca_df = pd.read_csv(path)
        clustered = run_clustering(pca_df)

    if 4 in phases:
        from src.rfm_segmentation.profiling import run_profiling
        if clustered is None:
            path = OUTPUT_DIR / "clustered_customers.csv"
            if not path.exists():
                logger.error("clustered_customers.csv not found. Run phase 3 first.")
                return
            clustered = pd.read_csv(path)
        rfm_raw_path = OUTPUT_DIR / "rfm_raw.csv"
        if not rfm_raw_path.exists():
            logger.error("rfm_raw.csv not found. Run phase 1 first.")
            return
        rfm_raw = pd.read_csv(rfm_raw_path)
        run_profiling(clustered, rfm_raw)

    from src.rfm_segmentation.visualisation import generate_all_plots
    generate_all_plots()

    total = time.time() - overall_start
    logger.info("=" * 60)
    logger.info("RFM segmentation pipeline complete. Total: %.1fs", total)
    logger.info("Outputs: %s", OUTPUT_DIR)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )

    args = sys.argv[1:]
    if not args:
        run_pipeline()
    elif args == ["plots"]:
        from src.rfm_segmentation.visualisation import generate_all_plots
        generate_all_plots()
    else:
        phases = [int(a) for a in args]
        run_pipeline(phases)
