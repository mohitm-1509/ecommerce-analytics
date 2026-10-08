"""
Module 6, Steps 2-5: Data Preparation, Class Imbalance, Training, Threshold Tuning

Pipeline: load features → encode → split by time → train baseline (LR) →
          train XGBoost with CV → tune threshold on precision-recall curve →
          save model + metadata + plots.

Usage:
    python -m src.train_model
"""
import json
import logging
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    matthews_corrcoef,
    precision_recall_curve,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder

from src.config import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
FEATURE_FILE = DATA_DIR / "features.csv"

TIME_SPLIT_DATE = "2018-04-01"

CATEGORICAL_COLS = [
    "customer_state", "seller_state", "product_category", "payment_type",
]
DROP_COLS = [
    "order_id", "order_purchase_timestamp", "review_score", "is_unsatisfied",
]
TARGET_COL = "is_unsatisfied"

PARAM_COMBOS = [
    {
        "max_depth": 3, "learning_rate": 0.1, "n_estimators": 200,
        "min_child_weight": 3, "subsample": 0.8, "colsample_bytree": 0.8,
        "reg_alpha": 0, "reg_lambda": 1.0,
    },
    {
        "max_depth": 5, "learning_rate": 0.05, "n_estimators": 300,
        "min_child_weight": 1, "subsample": 0.8, "colsample_bytree": 0.8,
        "reg_alpha": 0.1, "reg_lambda": 1.0,
    },
    {
        "max_depth": 7, "learning_rate": 0.01, "n_estimators": 500,
        "min_child_weight": 5, "subsample": 0.9, "colsample_bytree": 0.7,
        "reg_alpha": 1.0, "reg_lambda": 2.0,
    },
    {
        "max_depth": 5, "learning_rate": 0.05, "n_estimators": 300,
        "min_child_weight": 3, "subsample": 0.7, "colsample_bytree": 0.7,
        "reg_alpha": 1.0, "reg_lambda": 5.0,
    },
    {
        "max_depth": 3, "learning_rate": 0.05, "n_estimators": 300,
        "min_child_weight": 5, "subsample": 0.9, "colsample_bytree": 0.9,
        "reg_alpha": 0.1, "reg_lambda": 2.0,
    },
    {
        "max_depth": 7, "learning_rate": 0.1, "n_estimators": 200,
        "min_child_weight": 1, "subsample": 0.8, "colsample_bytree": 0.8,
        "reg_alpha": 0, "reg_lambda": 1.0,
    },
]


# ---------------------------------------------------------------------------
# Step 2: Data Preparation
# ---------------------------------------------------------------------------

def load_features() -> pd.DataFrame:
    df = pd.read_csv(FEATURE_FILE, parse_dates=["order_purchase_timestamp"])
    logger.info("Loaded %d rows × %d columns from %s",
                len(df), len(df.columns), FEATURE_FILE.name)
    return df


def prepare_data(df: pd.DataFrame):
    """Encode categoricals, impute nulls, time-based split.

    Returns X_train, y_train, X_test, y_test, feature_cols, encoders.
    Designed to be importable by explain_model.py and model_evaluation.py.
    """
    df = df.copy()

    encoders = {}
    for col in CATEGORICAL_COLS:
        if col in df.columns:
            le = LabelEncoder()
            df[col] = df[col].fillna("unknown").astype(str)
            df[col] = le.fit_transform(df[col])
            encoders[col] = le

    train_mask = df["order_purchase_timestamp"] < TIME_SPLIT_DATE
    test_mask = df["order_purchase_timestamp"] >= TIME_SPLIT_DATE

    feature_cols = [c for c in df.columns if c not in DROP_COLS]

    X_train = df.loc[train_mask, feature_cols].copy()
    y_train = df.loc[train_mask, TARGET_COL].copy()
    X_test = df.loc[test_mask, feature_cols].copy()
    y_test = df.loc[test_mask, TARGET_COL].copy()

    medians = {}
    for col in X_train.columns:
        if X_train[col].isnull().any():
            med = X_train[col].median()
            medians[col] = med
            X_train[col] = X_train[col].fillna(med)
    for col in X_test.columns:
        if X_test[col].isnull().any():
            med = medians.get(col, X_test[col].median())
            X_test[col] = X_test[col].fillna(med)

    logger.info("Train: %d rows (%.1f%% unsatisfied)",
                len(X_train), y_train.mean() * 100)
    logger.info("Test:  %d rows (%.1f%% unsatisfied)",
                len(X_test), y_test.mean() * 100)

    return X_train, y_train, X_test, y_test, feature_cols, encoders


# ---------------------------------------------------------------------------
# Step 3: Class Imbalance — compute scale_pos_weight
# ---------------------------------------------------------------------------

def compute_scale_pos_weight(y: pd.Series) -> float:
    neg = int((y == 0).sum())
    pos = int((y == 1).sum())
    ratio = neg / pos
    logger.info("Class counts  — satisfied: %d, unsatisfied: %d (ratio %.2f:1)",
                neg, pos, ratio)
    return ratio


# ---------------------------------------------------------------------------
# Step 4: Model Training
# ---------------------------------------------------------------------------

def train_baseline(X_train, y_train, X_test, y_test) -> dict:
    """Logistic regression baseline with class_weight='balanced'."""
    lr = LogisticRegression(
        max_iter=2000, class_weight="balanced",
        solver="lbfgs", random_state=42,
    )
    lr.fit(X_train, y_train)
    y_pred = lr.predict(X_test)
    y_prob = lr.predict_proba(X_test)[:, 1]

    auc_pr = average_precision_score(y_test, y_prob)
    auc_roc = roc_auc_score(y_test, y_prob)
    mcc = matthews_corrcoef(y_test, y_pred)

    logger.info("=== Logistic Regression Baseline ===")
    logger.info("\n%s", classification_report(y_test, y_pred, digits=3))
    logger.info("AUC-PR: %.4f | AUC-ROC: %.4f | MCC: %.4f", auc_pr, auc_roc, mcc)

    return {"auc_pr": auc_pr, "auc_roc": auc_roc, "mcc": mcc}


def train_xgboost(X_train, y_train, scale_pos_weight: float):
    """Hyperparameter selection via TimeSeriesSplit CV, then train final model."""
    tscv = TimeSeriesSplit(n_splits=5)

    best_score = -1.0
    best_params = {}
    results = []

    for i, params in enumerate(PARAM_COMBOS):
        model = xgb.XGBClassifier(
            **params,
            objective="binary:logistic",
            scale_pos_weight=scale_pos_weight,
            eval_metric="aucpr",
            random_state=42,
            tree_method="hist",
        )
        scores = cross_val_score(
            model, X_train, y_train,
            cv=tscv, scoring="average_precision", n_jobs=-1,
        )
        mean_score = scores.mean()
        std_score = scores.std()
        results.append((i, mean_score, std_score, params))
        logger.info("Combo %d/%d: AUC-PR = %.4f ± %.4f (depth=%d, lr=%.3f, n=%d)",
                     i + 1, len(PARAM_COMBOS), mean_score, std_score,
                     params["max_depth"], params["learning_rate"],
                     params["n_estimators"])
        if mean_score > best_score:
            best_score = mean_score
            best_params = params

    logger.info("Best CV AUC-PR: %.4f  params: %s", best_score, best_params)

    final_model = xgb.XGBClassifier(
        **best_params,
        objective="binary:logistic",
        scale_pos_weight=scale_pos_weight,
        eval_metric="aucpr",
        random_state=42,
        tree_method="hist",
    )
    final_model.fit(X_train, y_train)
    logger.info("Final model trained on %d rows", len(X_train))

    return final_model, best_params, best_score


# ---------------------------------------------------------------------------
# Step 5: Threshold Tuning
# ---------------------------------------------------------------------------

def tune_threshold(model, X_test, y_test):
    """Optimise classification threshold using precision-recall trade-off.

    Returns optimal_threshold, y_prob, and the full PR-curve arrays.
    """
    y_prob = model.predict_proba(X_test)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)

    # F1 optimal
    f1_scores = np.where(
        (precisions + recalls) > 0,
        2 * precisions * recalls / (precisions + recalls),
        0,
    )
    best_f1_idx = int(np.argmax(f1_scores))
    best_f1_thr = float(thresholds[min(best_f1_idx, len(thresholds) - 1)])

    # F2 optimal (weighs recall 2× more than precision)
    beta = 2.0
    f2_scores = np.where(
        (beta**2 * precisions + recalls) > 0,
        (1 + beta**2) * precisions * recalls / (beta**2 * precisions + recalls),
        0,
    )
    best_f2_idx = int(np.argmax(f2_scores))
    best_f2_thr = float(thresholds[min(best_f2_idx, len(thresholds) - 1)])

    logger.info("Best F1 threshold: %.3f (F1=%.4f)", best_f1_thr,
                f1_scores[best_f1_idx])
    logger.info("Best F2 threshold: %.3f (F2=%.4f)", best_f2_thr,
                f2_scores[best_f2_idx])

    optimal_threshold = best_f2_thr

    y_pred_tuned = (y_prob >= optimal_threshold).astype(int)
    logger.info("=== XGBoost @ Tuned Threshold (%.3f) ===", optimal_threshold)
    logger.info("\n%s", classification_report(y_test, y_pred_tuned, digits=3))
    logger.info("MCC: %.4f", matthews_corrcoef(y_test, y_pred_tuned))

    y_pred_default = (y_prob >= 0.5).astype(int)
    logger.info("=== XGBoost @ Default Threshold (0.50) ===")
    logger.info("\n%s", classification_report(y_test, y_pred_default, digits=3))

    return (optimal_threshold, best_f1_thr, y_prob,
            precisions, recalls, thresholds, f1_scores, f2_scores)


# ---------------------------------------------------------------------------
# Plotting helpers
# ---------------------------------------------------------------------------

def plot_precision_recall(precisions, recalls, thresholds,
                          f1_scores, f2_scores,
                          f1_thr, f2_thr, auc_pr):
    """Save precision-recall curve with F1/F2 optimal thresholds."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Left: PR curve
    ax1.plot(recalls, precisions, color="#2563EB", linewidth=2)
    ax1.set_xlabel("Recall")
    ax1.set_ylabel("Precision")
    ax1.set_title(f"Precision-Recall Curve (AUC-PR = {auc_pr:.3f})")
    ax1.set_xlim([0, 1])
    ax1.set_ylim([0, 1])
    ax1.grid(alpha=0.3)

    # Right: F1 / F2 vs threshold
    plot_thresholds = thresholds[:len(f1_scores) - 1]
    ax2.plot(plot_thresholds, f1_scores[:len(plot_thresholds)],
             label="F1", color="#2563EB", linewidth=2)
    ax2.plot(plot_thresholds, f2_scores[:len(plot_thresholds)],
             label="F2", color="#10B981", linewidth=2)
    ax2.axvline(f1_thr, color="#2563EB", linestyle="--", alpha=0.7,
                label=f"F1 optimal ({f1_thr:.2f})")
    ax2.axvline(f2_thr, color="#10B981", linestyle="--", alpha=0.7,
                label=f"F2 optimal ({f2_thr:.2f})")
    ax2.set_xlabel("Threshold")
    ax2.set_ylabel("Score")
    ax2.set_title("F1 / F2 vs Classification Threshold")
    ax2.legend()
    ax2.grid(alpha=0.3)

    plt.tight_layout()
    path = OUTPUTS_DIR / "precision_recall_curve.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved %s", path)


def plot_feature_importance(model, feature_cols):
    """Save XGBoost built-in feature importance plot."""
    OUTPUTS_DIR.mkdir(exist_ok=True)

    importance = model.feature_importances_
    sorted_idx = np.argsort(importance)
    top_n = min(20, len(sorted_idx))
    top_idx = sorted_idx[-top_n:]

    fig, ax = plt.subplots(figsize=(8, max(6, top_n * 0.35)))
    ax.barh(range(top_n),
            importance[top_idx],
            color="#2563EB", edgecolor="none")
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_cols[i] for i in top_idx])
    ax.set_xlabel("Feature Importance (gain)")
    ax.set_title("Top Features — XGBoost")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    path = OUTPUTS_DIR / "feature_importance.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("Saved %s", path)


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------

def save_artifacts(model, best_params, optimal_threshold, feature_cols,
                   baseline_metrics, cv_score, scale_pw):
    MODELS_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)

    model.save_model(str(MODELS_DIR / "xgb_satisfaction.json"))

    metadata = {
        "best_params": best_params,
        "optimal_threshold": optimal_threshold,
        "feature_columns": feature_cols,
        "time_split_date": TIME_SPLIT_DATE,
        "categorical_columns": CATEGORICAL_COLS,
        "scale_pos_weight": scale_pw,
        "cv_auc_pr": cv_score,
        "baseline_auc_pr": baseline_metrics["auc_pr"],
    }
    with open(MODELS_DIR / "model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    logger.info("Model saved to %s", MODELS_DIR / "xgb_satisfaction.json")
    logger.info("Metadata saved to %s", MODELS_DIR / "model_metadata.json")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def run_training():
    """Full training pipeline (Steps 2–5)."""
    start = time.time()

    df = load_features()
    X_train, y_train, X_test, y_test, feature_cols, encoders = prepare_data(df)

    baseline_metrics = train_baseline(X_train, y_train, X_test, y_test)

    spw = compute_scale_pos_weight(y_train)
    model, best_params, cv_score = train_xgboost(X_train, y_train, spw)

    (optimal_threshold, f1_thr, y_prob,
     precisions, recalls, thresholds,
     f1_scores, f2_scores) = tune_threshold(model, X_test, y_test)

    auc_pr = average_precision_score(y_test, y_prob)
    auc_roc = roc_auc_score(y_test, y_prob)

    plot_precision_recall(precisions, recalls, thresholds,
                          f1_scores, f2_scores,
                          f1_thr, optimal_threshold, auc_pr)
    plot_feature_importance(model, feature_cols)

    save_artifacts(model, best_params, optimal_threshold, feature_cols,
                   baseline_metrics, cv_score, spw)

    elapsed = time.time() - start
    logger.info("Training pipeline complete in %.1f seconds", elapsed)

    return model, X_train, y_train, X_test, y_test, feature_cols


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    run_training()
