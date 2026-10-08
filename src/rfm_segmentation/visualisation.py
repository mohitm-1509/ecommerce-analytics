"""
Visualisation module for the RFM segmentation pipeline.

Generates all diagnostic and presentation plots:
- RFM distribution histograms (before/after transform)
- Correlation heatmap
- PCA scree plot and biplot
- Elbow + silhouette curves
- Cluster scatter plot on PCA space (with segment labels)
- Segment profile heatmap
- SHAP importance heatmap
"""
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from src.rfm_segmentation.config import OUTPUT_DIR

logger = logging.getLogger(__name__)

PLOT_DIR = OUTPUT_DIR / "plots"
PLOT_DIR.mkdir(parents=True, exist_ok=True)

FEATURES = ["recency", "frequency", "monetary"]

PALETTE = ["#1D9E75", "#7F77DD", "#D85A30", "#D4537E", "#378ADD",
           "#639922", "#BA7517", "#E24B4A", "#888780"]

plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.2,
    "font.size": 10,
})


def _safe_read(filename: str) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, index_col=0 if filename.endswith("_matrix.csv") or filename == "pca_loadings.csv" else None)


def plot_rfm_distributions(rfm_raw: pd.DataFrame, rfm_scaled: pd.DataFrame) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(14, 8))

    for i, col in enumerate(FEATURES):
        axes[0, i].hist(rfm_raw[col], bins=50, color="#5DCAA5", edgecolor="white", alpha=0.8)
        axes[0, i].set_title(f"{col} (raw)")
        skew = rfm_raw[col].skew()
        axes[0, i].annotate(f"skew={skew:.2f}", xy=(0.65, 0.9), xycoords="axes fraction", fontsize=9)

        axes[1, i].hist(rfm_scaled[col], bins=50, color="#7F77DD", edgecolor="white", alpha=0.8)
        axes[1, i].set_title(f"{col} (transformed + scaled)")
        skew = rfm_scaled[col].skew()
        axes[1, i].annotate(f"skew={skew:.2f}", xy=(0.65, 0.9), xycoords="axes fraction", fontsize=9)

    fig.suptitle("RFM distributions: before vs after transforms", fontsize=13, fontweight="bold")
    plt.tight_layout()
    fig.savefig(PLOT_DIR / "01_rfm_distributions.png")
    plt.close(fig)
    logger.info("Saved 01_rfm_distributions.png")


def plot_correlation_heatmap(corr: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(corr, annot=True, fmt=".3f", cmap="RdBu_r", center=0,
                square=True, linewidths=0.5, ax=ax)
    ax.set_title("RFM correlation matrix (post-transform)")
    fig.savefig(PLOT_DIR / "02_correlation_heatmap.png")
    plt.close(fig)
    logger.info("Saved 02_correlation_heatmap.png")


def plot_pca_variance(variance_df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))

    x = range(1, len(variance_df) + 1)
    bars = ax.bar(x, variance_df["explained_variance_ratio"] * 100,
                  color="#AFA9EC", edgecolor="white", label="Individual")
    ax.plot(x, variance_df["cumulative_variance_ratio"] * 100,
            "o-", color="#534AB7", linewidth=2, label="Cumulative")

    for bar, val in zip(bars, variance_df["explained_variance_ratio"]):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val*100:.1f}%", ha="center", fontsize=9)

    ax.axhline(y=90, color="#D85A30", linestyle="--", alpha=0.7, label="90% threshold")
    ax.set_xlabel("Principal component")
    ax.set_ylabel("Variance explained (%)")
    ax.set_title("PCA scree plot")
    ax.set_xticks(list(x))
    ax.set_xticklabels([f"PC{i}" for i in x])
    ax.legend()
    fig.savefig(PLOT_DIR / "03_pca_scree.png")
    plt.close(fig)
    logger.info("Saved 03_pca_scree.png")


def plot_pca_biplot(pca_df: pd.DataFrame, loadings: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 7))

    sample = pca_df.sample(n=min(5000, len(pca_df)), random_state=42)
    ax.scatter(sample["PC1"], sample["PC2"], s=3, alpha=0.3, color="#888780")

    scale = max(pca_df["PC1"].std(), pca_df["PC2"].std()) * 2
    for feat in loadings.index:
        ax.arrow(0, 0, loadings.loc[feat, "PC1"] * scale,
                 loadings.loc[feat, "PC2"] * scale,
                 head_width=0.08, head_length=0.05, fc="#D85A30", ec="#D85A30")
        ax.text(loadings.loc[feat, "PC1"] * scale * 1.15,
                loadings.loc[feat, "PC2"] * scale * 1.15,
                feat, fontsize=10, fontweight="bold", color="#993C1D")

    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.set_title("PCA biplot with feature loadings")
    ax.axhline(0, color="gray", linewidth=0.3)
    ax.axvline(0, color="gray", linewidth=0.3)
    fig.savefig(PLOT_DIR / "04_pca_biplot.png")
    plt.close(fig)
    logger.info("Saved 04_pca_biplot.png")


def plot_elbow_silhouette(metrics: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(17, 5))

    axes[0].plot(metrics["k"], metrics["inertia"], "o-", color="#534AB7", linewidth=2)
    axes[0].set_xlabel("Number of clusters (K)")
    axes[0].set_ylabel("Inertia (WCSS)")
    axes[0].set_title("Elbow method")
    axes[0].set_xticks(metrics["k"].tolist())

    axes[1].plot(metrics["k"], metrics["silhouette"], "s-", color="#1D9E75", linewidth=2)
    axes[1].set_xlabel("Number of clusters (K)")
    axes[1].set_ylabel("Silhouette score")
    axes[1].set_title("Silhouette analysis")
    axes[1].set_xticks(metrics["k"].tolist())
    best_k = int(metrics.loc[metrics["silhouette"].idxmax(), "k"])
    best_s = metrics["silhouette"].max()
    axes[1].axvline(best_k, color="#D85A30", linestyle="--", alpha=0.7)
    axes[1].annotate(
        f"Best: K={best_k} ({best_s:.3f})",
        xy=(best_k, best_s), xytext=(best_k + 0.8, best_s - 0.015),
        fontsize=9, arrowprops=dict(arrowstyle="->", color="#993C1D"),
    )

    axes[2].plot(metrics["k"], metrics["davies_bouldin"], "D-", color="#D85A30", linewidth=2)
    axes[2].set_xlabel("Number of clusters (K)")
    axes[2].set_ylabel("Davies-Bouldin index (lower = better)")
    axes[2].set_title("Davies-Bouldin index")
    axes[2].set_xticks(metrics["k"].tolist())

    plt.tight_layout()
    fig.savefig(PLOT_DIR / "05_elbow_silhouette.png")
    plt.close(fig)
    logger.info("Saved 05_elbow_silhouette.png")


def plot_cluster_scatter(clustered: pd.DataFrame, profiles: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(9, 7))

    label_map = {}
    if not profiles.empty and "segment_label" in profiles.columns:
        label_map = dict(zip(profiles["cluster"], profiles["segment_label"]))

    n_clusters = clustered["cluster"].nunique()
    colors = PALETTE[:n_clusters]

    for i in sorted(clustered["cluster"].unique()):
        mask = clustered["cluster"] == i
        name = label_map.get(i, f"Cluster {i}")
        ax.scatter(
            clustered.loc[mask, "PC1"],
            clustered.loc[mask, "PC2"],
            s=5, alpha=0.4, color=colors[i], label=name,
        )

    ax.set_xlabel("PC1 (spending behaviour)")
    ax.set_ylabel("PC2 (recency)")
    ax.set_title("Customer segments in PCA space")
    ax.legend(markerscale=4, framealpha=0.8)
    fig.savefig(PLOT_DIR / "06_cluster_scatter.png")
    plt.close(fig)
    logger.info("Saved 06_cluster_scatter.png")


def plot_segment_heatmap(profiles: pd.DataFrame) -> None:
    mean_cols = [c for c in profiles.columns if c.endswith("_mean")]
    if "segment_label" in profiles.columns:
        labels = profiles["segment_label"]
    else:
        labels = profiles["cluster"].astype(str)

    data = profiles[mean_cols].copy()
    data.index = labels
    data.columns = [c.replace("_mean", "") for c in mean_cols]

    normalised = data.apply(
        lambda x: (x - x.min()) / (x.max() - x.min() + 1e-9), axis=0,
    )

    fig, ax = plt.subplots(figsize=(8, max(4, len(profiles) * 0.8 + 1)))
    sns.heatmap(
        normalised, annot=data.round(1).values, fmt="",
        cmap="YlOrRd", linewidths=0.5, ax=ax,
    )
    ax.set_title("Segment profiles (normalised heatmap, annotations = raw means)")
    ax.set_ylabel("")
    fig.savefig(PLOT_DIR / "07_segment_heatmap.png")
    plt.close(fig)
    logger.info("Saved 07_segment_heatmap.png")


def plot_shap_heatmap(importance: pd.DataFrame) -> None:
    if importance.empty:
        return

    pivot = importance.pivot(index="cluster", columns="feature", values="mean_abs_shap")
    fig, ax = plt.subplots(figsize=(7, max(4, len(pivot) * 0.8 + 1)))
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="Purples", linewidths=0.5, ax=ax)
    ax.set_title("SHAP feature importance per cluster")
    ax.set_ylabel("Cluster")
    fig.savefig(PLOT_DIR / "08_shap_heatmap.png")
    plt.close(fig)
    logger.info("Saved 08_shap_heatmap.png")


def generate_all_plots() -> None:
    logger.info("Generating all visualisations...")

    rfm_raw = _safe_read("rfm_raw.csv")
    rfm_scaled = _safe_read("rfm_scaled.csv")
    if not rfm_raw.empty and not rfm_scaled.empty:
        plot_rfm_distributions(rfm_raw, rfm_scaled)

    corr = _safe_read("correlation_matrix.csv")
    if not corr.empty:
        plot_correlation_heatmap(corr)

    variance = _safe_read("pca_variance.csv")
    if not variance.empty:
        plot_pca_variance(variance)

    pca_df = _safe_read("pca_transformed.csv")
    loadings = _safe_read("pca_loadings.csv")
    if not pca_df.empty and not loadings.empty:
        plot_pca_biplot(pca_df, loadings)

    metrics = _safe_read("clustering_metrics.csv")
    if not metrics.empty:
        plot_elbow_silhouette(metrics)

    clustered = _safe_read("clustered_customers.csv")
    profiles = _safe_read("segment_profiles.csv")
    if not clustered.empty:
        plot_cluster_scatter(clustered, profiles)

    if not profiles.empty:
        plot_segment_heatmap(profiles)

    shap_path = OUTPUT_DIR / "shap_importance.csv"
    if shap_path.exists():
        importance = pd.read_csv(shap_path)
        plot_shap_heatmap(importance)

    logger.info("All plots saved to %s", PLOT_DIR)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    generate_all_plots()
