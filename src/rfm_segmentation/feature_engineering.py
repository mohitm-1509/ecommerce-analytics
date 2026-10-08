"""
Phase 1: Stream-to-Feature Engineering

Aggregates raw transactional data into customer-level RFM profiles,
handles skewness with Box-Cox / Yeo-Johnson transforms, and
standardises features with Z-score normalisation.
"""
import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.preprocessing import StandardScaler

from src.rfm_segmentation.config import DATA_DIR, OUTPUT_DIR, REFERENCE_DATE

logger = logging.getLogger(__name__)

FEATURES = ["recency", "frequency", "monetary"]
MIN_UNIQUE_FOR_TRANSFORM = 10


def load_transactions() -> pd.DataFrame:
    orders = pd.read_csv(DATA_DIR / "olist_orders_dataset.csv")
    customers = pd.read_csv(DATA_DIR / "olist_customers_dataset.csv")
    payments = pd.read_csv(DATA_DIR / "olist_order_payments_dataset.csv")

    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"]
    )

    delivered = orders[orders["order_status"] == "delivered"].copy()
    logger.info("Delivered orders: %d", len(delivered))

    merged = delivered.merge(customers, on="customer_id", how="inner")

    payment_per_order = (
        payments.groupby("order_id")["payment_value"].sum().reset_index()
    )
    merged = merged.merge(payment_per_order, on="order_id", how="inner")

    logger.info(
        "Transactions after merge: %d rows, %d unique customers",
        len(merged),
        merged["customer_unique_id"].nunique(),
    )
    return merged


def compute_rfm(transactions: pd.DataFrame) -> pd.DataFrame:
    reference_date = pd.Timestamp(REFERENCE_DATE)

    rfm = (
        transactions.groupby("customer_unique_id")
        .agg(
            recency=("order_purchase_timestamp", lambda x: (reference_date - x.max()).days),
            frequency=("order_id", "nunique"),
            monetary=("payment_value", "sum"),
        )
        .reset_index()
    )

    logger.info("RFM table: %d customers", len(rfm))
    logger.info(
        "RFM stats before cleaning:\n%s",
        rfm[FEATURES].describe().round(2).to_string(),
    )
    return rfm


def cap_outliers_percentile(
    rfm: pd.DataFrame, lower_pct: float = 0.01, upper_pct: float = 0.99,
) -> pd.DataFrame:
    rfm_capped = rfm.copy()
    for col in FEATURES:
        lower = rfm[col].quantile(lower_pct)
        upper = rfm[col].quantile(upper_pct)
        if lower == upper:
            logger.info("  %s: skipped (constant at percentile bounds)", col)
            continue
        before_count = ((rfm[col] < lower) | (rfm[col] > upper)).sum()
        rfm_capped[col] = rfm[col].clip(lower=lower, upper=upper)
        if before_count > 0:
            logger.info(
                "  %s: clipped %d values to [%.1f, %.1f]",
                col, before_count, lower, upper,
            )

    logger.info("Outlier capping complete. Rows preserved: %d", len(rfm_capped))
    return rfm_capped


def apply_transforms(rfm: pd.DataFrame) -> tuple:
    transform_info = {}
    rfm_transformed = rfm.copy()

    for col in FEATURES:
        original_skew = rfm[col].skew()
        values = rfm[col].values.astype(float)
        n_unique = len(np.unique(values))

        if values.std() == 0:
            logger.info("  %s: constant column, skipping transform", col)
            transform_info[col] = {"method": "none", "reason": "constant"}
            continue

        if n_unique < MIN_UNIQUE_FOR_TRANSFORM:
            logger.info(
                "  %s: only %d unique values (skew=%.4f), skipping power transform",
                col, n_unique, original_skew,
            )
            transform_info[col] = {
                "method": "none",
                "reason": f"low cardinality ({n_unique} unique)",
                "skew": round(original_skew, 4),
            }
            continue

        if (values > 0).all():
            transformed, lmbda = stats.boxcox(values)
            method = "box-cox"
        else:
            transformed, lmbda = stats.yeojohnson(values)
            method = "yeo-johnson"

        new_skew = pd.Series(transformed).skew()
        rfm_transformed[col] = transformed
        transform_info[col] = {
            "method": method,
            "lambda": round(lmbda, 4),
            "skew_before": round(original_skew, 4),
            "skew_after": round(new_skew, 4),
        }
        logger.info(
            "  %s: %s (λ=%.4f), skew %.4f → %.4f",
            col, method, lmbda, original_skew, new_skew,
        )

    return rfm_transformed, transform_info


def standardise(rfm_transformed: pd.DataFrame) -> tuple:
    scaler = StandardScaler()
    rfm_scaled = rfm_transformed.copy()
    rfm_scaled[FEATURES] = scaler.fit_transform(rfm_transformed[FEATURES])

    logger.info("After Z-score standardisation:")
    logger.info(
        "  Means:  %s",
        {f: round(rfm_scaled[f].mean(), 6) for f in FEATURES},
    )
    logger.info(
        "  Stds:   %s",
        {f: round(rfm_scaled[f].std(), 4) for f in FEATURES},
    )
    return rfm_scaled, scaler


def run_feature_engineering() -> pd.DataFrame:
    logger.info("=" * 60)
    logger.info("PHASE 1: RFM Feature Engineering")
    logger.info("=" * 60)

    logger.info("Step 1/4: Loading transactions...")
    transactions = load_transactions()

    logger.info("Step 2/4: Computing RFM metrics...")
    rfm = compute_rfm(transactions)

    logger.info("Step 3/4: Capping outliers (1st–99th percentile)...")
    rfm_capped = cap_outliers_percentile(rfm)

    logger.info("Step 4/4: Applying power transforms + Z-score...")
    rfm_transformed, transform_info = apply_transforms(rfm_capped)
    rfm_scaled, scaler = standardise(rfm_transformed)

    rfm_capped.to_csv(OUTPUT_DIR / "rfm_raw.csv", index=False)
    rfm_scaled.to_csv(OUTPUT_DIR / "rfm_scaled.csv", index=False)
    logger.info("Saved rfm_raw.csv and rfm_scaled.csv to %s", OUTPUT_DIR)

    return rfm_scaled


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    run_feature_engineering()
