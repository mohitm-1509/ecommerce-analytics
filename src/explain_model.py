"""
Module 6, Step 6: SHAP Explainability

Global analysis (which features matter most across all predictions) and
local analysis (why the model flagged a specific order).

Usage:
    python -m src.explain_model
"""
import json
import logging

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from src.config import DATA_DIR, PROJECT_ROOT
from src.train_model import prepare_data

logger = logging.getLogger(__name__)

MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

MAX_SHAP_SAMPLES = 5000


def load_model_and_data():
    model = xgb.XGBClassifier()
    model.load_model(str(MODELS_DIR / "xgb_satisfaction.json"))

    with open(MODELS_DIR / "model_metadata.json") as f:
        metadata = json.load(f)

    df = pd.read_csv(DATA_DIR / "features.csv",
                     parse_dates=["order_purchase_timestamp"])
    X_train, y_train, X_test, y_test, feature_cols, _ = prepare_data(df)

    return model, X_train, y_train, X_test, y_test, feature_cols, metadata


def explain_global(model, X_test, feature_cols):
    """SHAP summary: feature importance ranked by mean |SHAP|."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    if len(X_test) > MAX_SHAP_SAMPLES:
        rng = np.random.RandomState(42)
        idx = rng.choice(len(X_test), MAX_SHAP_SAMPLES, replace=False)
        X_shap = X_test.iloc[idx].copy()
        logger.info("Subsampled %d rows for SHAP (from %d)",
                     MAX_SHAP_SAMPLES, len(X_test))
    else:
        X_shap = X_test.copy()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_shap)
    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    # Beeswarm summary
    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_shap, feature_names=feature_cols,
                      show=False, max_display=20)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "shap_summary.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved shap_summary.png")

    # Bar importance
    plt.figure(figsize=(10, 8))
    shap.summary_plot(shap_values, X_shap, feature_names=feature_cols,
                      plot_type="bar", show=False, max_display=20)
    plt.tight_layout()
    plt.savefig(OUTPUTS_DIR / "shap_importance.png", dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved shap_importance.png")

    mean_abs = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        "feature": feature_cols,
        "mean_abs_shap": mean_abs,
    }).sort_values("mean_abs_shap", ascending=False)

    importance_df.to_csv(OUTPUTS_DIR / "shap_feature_importance.csv", index=False)

    print("\nTop 10 features by mean |SHAP value|:")
    print(importance_df.head(10).to_string(index=False))

    return explainer, shap_values, X_shap


def explain_local(model, explainer, X_test, y_test, feature_cols, metadata):
    """Waterfall plots for individual orders: one high-risk, one low-risk."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    threshold = metadata.get("optimal_threshold", 0.5)
    y_prob = model.predict_proba(X_test)[:, 1]
    expected_value = explainer.expected_value
    if isinstance(expected_value, np.ndarray):
        expected_value = float(expected_value[-1])

    # True positive: model correctly flagged an unsatisfied order
    tp_mask = (y_prob >= threshold) & (y_test.values == 1)
    if tp_mask.any():
        idx = int(np.where(tp_mask)[0][0])
        row = X_test.iloc[idx]
        sv = explainer.shap_values(row.values.reshape(1, -1))
        if isinstance(sv, list):
            sv = sv[1]
        sv = sv[0]

        explanation = shap.Explanation(
            values=sv,
            base_values=expected_value,
            data=row.values,
            feature_names=feature_cols,
        )
        plt.figure(figsize=(12, 6))
        shap.plots.waterfall(explanation, show=False, max_display=15)
        plt.title(f"High-Risk Order  (prob={y_prob[idx]:.3f}, actual=unsatisfied)")
        plt.tight_layout()
        plt.savefig(OUTPUTS_DIR / "shap_waterfall_high_risk.png",
                    dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved waterfall plot for high-risk order (test index %d)", idx)

    # True negative: model correctly did NOT flag a satisfied order
    tn_mask = (y_prob < threshold) & (y_test.values == 0)
    if tn_mask.any():
        idx = int(np.where(tn_mask)[0][0])
        row = X_test.iloc[idx]
        sv = explainer.shap_values(row.values.reshape(1, -1))
        if isinstance(sv, list):
            sv = sv[1]
        sv = sv[0]

        explanation = shap.Explanation(
            values=sv,
            base_values=expected_value,
            data=row.values,
            feature_names=feature_cols,
        )
        plt.figure(figsize=(12, 6))
        shap.plots.waterfall(explanation, show=False, max_display=15)
        plt.title(f"Low-Risk Order  (prob={y_prob[idx]:.3f}, actual=satisfied)")
        plt.tight_layout()
        plt.savefig(OUTPUTS_DIR / "shap_waterfall_low_risk.png",
                    dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved waterfall plot for low-risk order (test index %d)", idx)


def run_explanation():
    """Full SHAP pipeline."""
    model, X_train, y_train, X_test, y_test, feature_cols, metadata = (
        load_model_and_data()
    )
    explainer, shap_values, X_shap = explain_global(model, X_test, feature_cols)
    explain_local(model, explainer, X_test, y_test, feature_cols, metadata)
    logger.info("SHAP analysis complete. Plots saved to %s/", OUTPUTS_DIR)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    run_explanation()
