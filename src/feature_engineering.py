"""
Module 6, Step 1: Feature Engineering

Builds a training-ready dataset from BigQuery by joining orders, items,
products, sellers, payments, and reviews. Computes seller historical
metrics using window functions with ROWS PRECEDING to prevent data leakage.

Usage:
    python -m src.feature_engineering
"""
import logging

import pandas as pd
from google.cloud import bigquery

from src.config import GCP_PROJECT_ID, BQ_DATASET_ID, DATA_DIR

logger = logging.getLogger(__name__)

FEATURE_QUERY_TEMPLATE = """
WITH delivered_orders AS (
    SELECT
        o.order_id,
        o.order_purchase_timestamp,
        o.order_estimated_delivery_date,
        o.order_delivered_customer_date,
        c.customer_state,
        r.review_score
    FROM `{project}.{dataset}.orders` o
    JOIN `{project}.{dataset}.customers` c ON o.customer_id = c.customer_id
    JOIN (
        SELECT order_id, review_score,
               ROW_NUMBER() OVER (
                   PARTITION BY order_id
                   ORDER BY review_creation_date DESC
               ) AS rn
        FROM `{project}.{dataset}.order_reviews`
        WHERE review_score IS NOT NULL
    ) r ON o.order_id = r.order_id AND r.rn = 1
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
),

item_features AS (
    SELECT
        oi.order_id,
        COUNT(*)                        AS num_items,
        COUNT(DISTINCT oi.seller_id)    AS num_sellers,
        SUM(oi.price)                   AS total_price,
        SUM(oi.freight_value)           AS total_freight,
        SAFE_DIVIDE(
            SUM(oi.freight_value), SUM(oi.price)
        )                               AS freight_ratio,
        AVG(p.product_weight_g)         AS avg_weight_g,
        AVG(
            CAST(p.product_length_cm AS FLOAT64)
            * CAST(p.product_height_cm AS FLOAT64)
            * CAST(p.product_width_cm AS FLOAT64)
        )                               AS avg_volume_cm3,
        AVG(p.product_name_lenght)      AS avg_name_length,
        AVG(p.product_description_lenght) AS avg_desc_length,
        AVG(p.product_photos_qty)       AS avg_photos_qty,
        ARRAY_AGG(oi.seller_id ORDER BY oi.price DESC LIMIT 1)[OFFSET(0)]
                                        AS primary_seller_id,
        ARRAY_AGG(s.seller_state ORDER BY oi.price DESC LIMIT 1)[OFFSET(0)]
                                        AS seller_state,
        ARRAY_AGG(
            COALESCE(ct.product_category_name_english,
                     p.product_category_name, 'unknown')
            ORDER BY oi.price DESC LIMIT 1
        )[OFFSET(0)]                   AS product_category
    FROM `{project}.{dataset}.order_items` oi
    JOIN `{project}.{dataset}.products` p    ON oi.product_id = p.product_id
    JOIN `{project}.{dataset}.sellers` s     ON oi.seller_id = s.seller_id
    LEFT JOIN `{project}.{dataset}.category_translation` ct
        ON p.product_category_name = ct.product_category_name
    GROUP BY oi.order_id
),

payment_features AS (
    SELECT
        order_id,
        ARRAY_AGG(payment_type ORDER BY payment_value DESC LIMIT 1)[OFFSET(0)]
                                    AS payment_type,
        MAX(payment_installments)   AS max_installments,
        SUM(payment_value)          AS total_payment,
        COUNT(DISTINCT payment_type) AS num_payment_types
    FROM `{project}.{dataset}.order_payments`
    GROUP BY order_id
),

combined AS (
    SELECT
        d.order_id,
        d.order_purchase_timestamp,
        d.review_score,
        CASE WHEN d.review_score <= 2 THEN 1 ELSE 0 END AS is_unsatisfied,

        -- Geographic
        d.customer_state,
        i.seller_state,
        CASE WHEN d.customer_state = i.seller_state THEN 1 ELSE 0 END
            AS is_same_state,

        -- Delivery estimate (known at order time)
        DATE_DIFF(
            DATE(d.order_estimated_delivery_date),
            DATE(d.order_purchase_timestamp), DAY
        ) AS estimated_delivery_days,

        -- Time features
        EXTRACT(DAYOFWEEK FROM d.order_purchase_timestamp) AS order_dow,
        EXTRACT(MONTH FROM d.order_purchase_timestamp)     AS order_month,
        EXTRACT(HOUR FROM d.order_purchase_timestamp)      AS order_hour,

        -- Item / product features
        i.num_items,
        i.num_sellers,
        i.total_price,
        i.total_freight,
        i.freight_ratio,
        i.avg_weight_g,
        i.avg_volume_cm3,
        i.avg_name_length,
        i.avg_desc_length,
        i.avg_photos_qty,
        i.product_category,

        -- Payment features
        p.payment_type,
        p.max_installments,
        p.total_payment,
        p.num_payment_types,

        -- Internal columns for seller history (excluded from final output)
        i.primary_seller_id,
        DATE_DIFF(
            DATE(d.order_delivered_customer_date),
            DATE(d.order_purchase_timestamp), DAY
        ) AS _actual_delivery_days,
        CASE
            WHEN d.order_delivered_customer_date > d.order_estimated_delivery_date
            THEN 1 ELSE 0
        END AS _was_late

    FROM delivered_orders d
    JOIN item_features i       ON d.order_id = i.order_id
    LEFT JOIN payment_features p ON d.order_id = p.order_id
)

SELECT
    c.order_id,
    c.order_purchase_timestamp,
    c.review_score,
    c.is_unsatisfied,

    c.customer_state,
    c.seller_state,
    c.is_same_state,
    c.estimated_delivery_days,

    c.order_dow,
    c.order_month,
    c.order_hour,

    c.num_items,
    c.num_sellers,
    c.total_price,
    c.total_freight,
    c.freight_ratio,
    c.avg_weight_g,
    c.avg_volume_cm3,
    c.avg_name_length,
    c.avg_desc_length,
    c.avg_photos_qty,
    c.product_category,

    c.payment_type,
    c.max_installments,
    c.total_payment,
    c.num_payment_types,

    -- Seller historical metrics (PRIOR orders only, via named WINDOW)
    COUNT(*) OVER w_prior                       AS seller_prior_order_count,
    AVG(c.review_score) OVER w_prior            AS seller_prior_avg_review,
    AVG(c._actual_delivery_days) OVER w_prior   AS seller_prior_avg_delivery_days,
    SAFE_DIVIDE(
        SUM(c.is_unsatisfied) OVER w_prior,
        COUNT(*) OVER w_prior
    )                                           AS seller_prior_unsatisfied_rate,
    SAFE_DIVIDE(
        SUM(c._was_late) OVER w_prior,
        COUNT(*) OVER w_prior
    )                                           AS seller_prior_late_rate

FROM combined c
WINDOW w_prior AS (
    PARTITION BY c.primary_seller_id
    ORDER BY c.order_purchase_timestamp, c.order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
)
ORDER BY c.order_purchase_timestamp, c.order_id
"""

FEATURE_COLUMNS = [
    "customer_state", "seller_state", "is_same_state",
    "estimated_delivery_days",
    "order_dow", "order_month", "order_hour",
    "num_items", "num_sellers", "total_price", "total_freight",
    "freight_ratio", "avg_weight_g", "avg_volume_cm3",
    "avg_name_length", "avg_desc_length", "avg_photos_qty",
    "product_category",
    "payment_type", "max_installments", "total_payment", "num_payment_types",
    "seller_prior_order_count", "seller_prior_avg_review",
    "seller_prior_avg_delivery_days", "seller_prior_unsatisfied_rate",
    "seller_prior_late_rate",
]


def build_feature_table() -> pd.DataFrame:
    """Run the feature query on BigQuery and save results to CSV."""
    client = bigquery.Client(project=GCP_PROJECT_ID)
    query = FEATURE_QUERY_TEMPLATE.format(
        project=GCP_PROJECT_ID,
        dataset=BQ_DATASET_ID,
    )

    logger.info("Running feature engineering query on BigQuery...")
    df = client.query(query).to_dataframe()
    logger.info("Query returned %d rows, %d columns", len(df), len(df.columns))

    DATA_DIR.mkdir(exist_ok=True)
    output_path = DATA_DIR / "features.csv"
    df.to_csv(output_path, index=False)
    logger.info("Feature table saved to %s (%.1f MB)",
                output_path, output_path.stat().st_size / 1e6)

    unsatisfied_rate = df["is_unsatisfied"].mean()
    logger.info("Class balance: %.1f%% unsatisfied (target=1), %.1f%% satisfied",
                unsatisfied_rate * 100, (1 - unsatisfied_rate) * 100)
    logger.info("Date range: %s to %s",
                df["order_purchase_timestamp"].min(),
                df["order_purchase_timestamp"].max())

    null_cols = df[FEATURE_COLUMNS].isnull().sum()
    null_cols = null_cols[null_cols > 0]
    if len(null_cols) > 0:
        logger.info("Columns with nulls:\n%s", null_cols.to_string())
    else:
        logger.info("No null values in feature columns")

    return df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    build_feature_table()
