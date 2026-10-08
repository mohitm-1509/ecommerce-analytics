"""
Module 6, Step 7: Business Impact Estimation

Connects model predictions to revenue via a cost-benefit framework:
    - True Positive  → intervention prevents a bad review     (save R$75, pay R$8)
    - False Positive → unnecessary intervention               (pay R$8)
    - False Negative → missed bad review, damage posted       (lose R$75)
    - True Negative  → no action needed, correct              (R$0)

Usage:
    python -m src.model_evaluation
"""
import json
import logging

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import confusion_matrix

from src.config import DATA_DIR, PROJECT_ROOT
from src.train_model import prepare_data

logger = logging.getLogger(__name__)

MODELS_DIR = PROJECT_ROOT / "models"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

COST_INTERVENTION = 8.0
COST_BAD_REVIEW = 75.0
ANNUAL_ORDERS = 50_000


def run_evaluation():
    """Compute and print cost-benefit analysis of the prediction model."""
    model = xgb.XGBClassifier()
    model.load_model(str(MODELS_DIR / "xgb_satisfaction.json"))

    with open(MODELS_DIR / "model_metadata.json") as f:
        metadata = json.load(f)

    df = pd.read_csv(DATA_DIR / "features.csv",
                     parse_dates=["order_purchase_timestamp"])
    _, _, X_test, y_test, _, _ = prepare_data(df)

    threshold = metadata.get("optimal_threshold", 0.5)
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    total_test = len(y_test)

    # ---- metrics ----
    recall = tp / (tp + fn) if (tp + fn) else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    false_alarm = fp / (fp + tn) if (fp + tn) else 0

    # ---- cost-benefit on test set ----
    no_model = (tp + fn) * COST_BAD_REVIEW
    with_model = fn * COST_BAD_REVIEW + (tp + fp) * COST_INTERVENTION
    test_savings = no_model - with_model

    # ---- annualise ----
    scale = ANNUAL_ORDERS / total_test
    annual_savings = test_savings * scale

    # ---- print report ----
    sep = "=" * 60
    print(f"\n{sep}")
    print("BUSINESS IMPACT ANALYSIS — Customer Satisfaction Prediction")
    print(sep)

    print(f"\nThreshold: {threshold:.3f}")
    print(f"\nConfusion matrix (test set, n={total_test:,}):")
    print(f"  True Positives  (caught bad reviews):    {tp:>6,}")
    print(f"  False Positives (unnecessary upgrades):   {fp:>6,}")
    print(f"  False Negatives (missed bad reviews):     {fn:>6,}")
    print(f"  True Negatives  (correct no-action):      {tn:>6,}")

    print(f"\nModel performance:")
    print(f"  Bad-review catch rate (recall):  {recall:>7.1%}")
    print(f"  Intervention precision:          {precision:>7.1%}")
    print(f"  False alarm rate:                {false_alarm:>7.1%}")

    print(f"\nCost assumptions:")
    print(f"  Cost of intervention (express shipping):  R${COST_INTERVENTION:.0f}")
    print(f"  Cost of a bad review (lost conversions):  R${COST_BAD_REVIEW:.0f}")

    print(f"\nCost-benefit (test period):")
    print(f"  Without model (all bad reviews posted):  R${no_model:>10,.0f}")
    print(f"  With model (interventions + misses):     R${with_model:>10,.0f}")
    print(f"  Net savings:                             R${test_savings:>10,.0f}")

    print(f"\nAnnualised projection ({ANNUAL_ORDERS:,} orders/year):")
    print(f"  Estimated annual savings:                R${annual_savings:>10,.0f}")

    print(f"\nInterpretation:")
    print(f"  The model catches {recall:.0%} of orders that would get bad reviews.")
    print(f"  Of flagged orders, {precision:.0%} actually needed intervention.")
    print(f"  Cost per prevented bad review: R${COST_INTERVENTION:.0f} "
          f"(vs R${COST_BAD_REVIEW:.0f} cost of the review itself).")
    total_intervention_cost = (tp + fp) * COST_INTERVENTION
    roi = test_savings / total_intervention_cost if total_intervention_cost > 0 else 0
    print(f"  ROI: every R$1 spent on intervention saves "
          f"R${roi:.1f} in prevented damage.")

    # ---- save JSON report ----
    OUTPUTS_DIR.mkdir(exist_ok=True)
    report = {
        "threshold": threshold,
        "test_set_size": total_test,
        "confusion_matrix": {
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        },
        "metrics": {
            "recall": round(recall, 4),
            "precision": round(precision, 4),
            "false_alarm_rate": round(false_alarm, 4),
        },
        "cost_assumptions": {
            "cost_per_intervention_BRL": COST_INTERVENTION,
            "cost_per_bad_review_BRL": COST_BAD_REVIEW,
            "annual_order_volume": ANNUAL_ORDERS,
        },
        "test_period": {
            "without_model_BRL": round(no_model, 2),
            "with_model_BRL": round(with_model, 2),
            "net_savings_BRL": round(test_savings, 2),
        },
        "annualised_savings_BRL": round(annual_savings, 2),
        "roi_per_dollar_spent": round(roi, 2),
    }
    path = OUTPUTS_DIR / "business_impact.json"
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report saved to %s", path)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    run_evaluation()
