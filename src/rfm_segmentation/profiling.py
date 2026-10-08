"""
Phase 4: Segment Profiling & Explainability

Profiles each cluster using original RFM values, assigns business labels
using normalised RFM thresholds, and runs SHAP explainability via a
Random Forest proxy classifier.
"""
import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score

from src.rfm_segmentation.config import OUTPUT_DIR, RANDOM_STATE

logger = logging.getLogger(__name__)

FEATURES = ["recency", "frequency", "monetary"]


def build_profile_table(
    clustered: pd.DataFrame,
    rfm_raw: pd.DataFrame,
) -> tuple:
    merged = clustered[["customer_unique_id", "cluster"]].merge(
        rfm_raw, on="customer_unique_id", how="inner",
    )

    profiles = (
        merged.groupby("cluster")[FEATURES]
        .agg(["mean", "median", "std"])
        .round(2)
    )
    profiles.columns = ["_".join(c) for c in profiles.columns]
    profiles["count"] = merged.groupby("cluster")["customer_unique_id"].count()
    profiles["pct"] = (profiles["count"] / profiles["count"].sum() * 100).round(1)
    profiles = profiles.reset_index()

    logger.info(
        "Cluster profiles (original scale):\n%s", profiles.to_string(index=False),
    )
    return profiles, merged


def assign_labels(profiles: pd.DataFrame) -> pd.DataFrame:
    p = profiles.copy()

    rng = lambda s: s.max() - s.min() + 1e-9
    r_norm = 1 - (p["recency_mean"] - p["recency_mean"].min()) / rng(p["recency_mean"])
    f_norm = (p["frequency_mean"] - p["frequency_mean"].min()) / rng(p["frequency_mean"])
    m_norm = (p["monetary_mean"] - p["monetary_mean"].min()) / rng(p["monetary_mean"])

    labels = []
    for i in range(len(p)):
        r, v = r_norm.iloc[i], (f_norm.iloc[i] + m_norm.iloc[i]) / 2
        if r >= 0.5 and v >= 0.5:
            labels.append("Champions")
        elif r >= 0.5:
            labels.append("Potential loyalists")
        elif v >= 0.5:
            labels.append("At-risk spenders")
        else:
            labels.append("Hibernating")

    p["segment_label"] = labels

    logger.info(
        "Segment labels assigned:\n%s",
        p[
            ["cluster", "segment_label", "count", "pct",
             "recency_mean", "frequency_mean", "monetary_mean"]
        ].to_string(index=False),
    )
    return p


def run_shap_explainability(merged: pd.DataFrame) -> pd.DataFrame:
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed, skipping explainability")
        return pd.DataFrame()

    X = merged[FEATURES].values
    y = merged["cluster"].values

    rf = RandomForestClassifier(
        n_estimators=200, max_depth=10, random_state=RANDOM_STATE, n_jobs=-1,
    )
    cv_scores = cross_val_score(rf, X, y, cv=5, scoring="accuracy")
    logger.info(
        "Proxy RF accuracy (5-fold CV): %.4f +/- %.4f",
        cv_scores.mean(), cv_scores.std(),
    )

    rf.fit(X, y)

    explainer = shap.TreeExplainer(rf)
    shap_values = explainer.shap_values(X)

    cluster_labels = sorted(merged["cluster"].unique())
    importance_rows = []

    if isinstance(shap_values, list):
        shap_array = np.array(shap_values)
    else:
        shap_array = shap_values

    for i, cluster_id in enumerate(cluster_labels):
        if shap_array.ndim == 3 and shap_array.shape[0] == len(cluster_labels):
            sv = np.abs(shap_array[i]).mean(axis=0)
        elif shap_array.ndim == 3 and shap_array.shape[2] == len(cluster_labels):
            sv = np.abs(shap_array[:, :, i]).mean(axis=0)
        else:
            mask = y == cluster_id
            sv = np.abs(shap_array[mask]).mean(axis=0)

        for j, feat in enumerate(FEATURES):
            importance_rows.append({
                "cluster": cluster_id,
                "feature": feat,
                "mean_abs_shap": round(float(sv[j]), 4),
            })

    importance_df = pd.DataFrame(importance_rows)
    logger.info(
        "SHAP feature importance per cluster:\n%s",
        importance_df.pivot(
            index="cluster", columns="feature", values="mean_abs_shap",
        ).round(4).to_string(),
    )
    return importance_df


def run_profiling(clustered: pd.DataFrame, rfm_raw: pd.DataFrame) -> None:
    logger.info("=" * 60)
    logger.info("PHASE 4: Segment Profiling & Explainability")
    logger.info("=" * 60)

    logger.info("Step 1/3: Building cluster profiles...")
    profiles, merged = build_profile_table(clustered, rfm_raw)

    logger.info("Step 2/3: Assigning business segment labels...")
    profiles = assign_labels(profiles)
    profiles.to_csv(OUTPUT_DIR / "segment_profiles.csv", index=False)

    logger.info("Step 3/3: SHAP explainability (proxy RF classifier)...")
    importance = run_shap_explainability(merged)
    if not importance.empty:
        importance.to_csv(OUTPUT_DIR / "shap_importance.csv", index=False)

    logger.info("Saved segment_profiles.csv and shap_importance.csv")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    clustered = pd.read_csv(OUTPUT_DIR / "clustered_customers.csv")
    rfm_raw = pd.read_csv(OUTPUT_DIR / "rfm_raw.csv")
    run_profiling(clustered, rfm_raw)
