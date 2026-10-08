"""
Module 4: Create BigQuery views optimised for Power BI consumption.

Why views instead of importing raw tables into Power BI:
1. Heavy JOINs run server-side in BigQuery (columnar engine, distributed).
   Power BI's VertiPaq engine is fast for filtering, not for joining 1M rows.
2. Smaller import size: aggregated views are kilobytes, not megabytes.
   Free Power BI tier limits datasets to 1 GB.
3. Single source of truth: dashboard logic lives in SQL (version-controlled),
   not buried in Power Query M steps.
4. Refresh speed: importing 5 small views takes seconds vs minutes for 9 tables.

Usage:
    python -m src.create_views          # create all views
    python -m src.create_views --drop   # drop and recreate
"""
import argparse
import logging

from google.cloud import bigquery

from src.config import BQ_DATASET_ID, GCP_PROJECT_ID

logger = logging.getLogger(__name__)
DATASET = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"


# ---------------------------------------------------------------------------
# View definitions
# ---------------------------------------------------------------------------

VIEWS = {

    # ------------------------------------------------------------------
    # V1: FACT — order-level metrics (one row per order)
    # Core fact table for Power BI. Pre-joins orders, items, reviews,
    # payments, customers, products, and category translation.
    # ------------------------------------------------------------------
    "v_fact_orders": f"""
CREATE OR REPLACE VIEW `{DATASET}.v_fact_orders` AS
WITH order_items_agg AS (
    SELECT
        oi.order_id,
        SUM(oi.price)                           AS total_price,
        SUM(oi.freight_value)                    AS total_freight,
        COUNT(oi.order_item_id)                  AS item_count,
        STRING_AGG(DISTINCT oi.seller_id)        AS seller_ids
    FROM `{DATASET}.order_items` oi
    GROUP BY oi.order_id
),
order_payments_agg AS (
    SELECT
        op.order_id,
        SUM(op.payment_value)                    AS total_payment,
        MAX(op.payment_installments)             AS max_installments,
        STRING_AGG(DISTINCT op.payment_type)     AS payment_types
    FROM `{DATASET}.order_payments` op
    GROUP BY op.order_id
)
SELECT
    o.order_id,
    o.order_status,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,

    -- Timestamps
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp)              AS order_date,
    FORMAT_DATE('%Y-%m', DATE(o.order_purchase_timestamp))
                                                  AS order_month,
    EXTRACT(YEAR FROM o.order_purchase_timestamp) AS order_year,
    EXTRACT(QUARTER FROM o.order_purchase_timestamp)
                                                  AS order_quarter,

    -- Delivery
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    DATE_DIFF(
        DATE(o.order_delivered_customer_date),
        DATE(o.order_purchase_timestamp), DAY
    )                                             AS delivery_days,
    DATE_DIFF(
        DATE(o.order_delivered_customer_date),
        DATE(o.order_estimated_delivery_date), DAY
    )                                             AS delay_days,
    CASE
        WHEN o.order_delivered_customer_date IS NULL THEN 'Not Delivered'
        WHEN o.order_delivered_customer_date
             <= o.order_estimated_delivery_date    THEN 'On-Time'
        ELSE 'Late'
    END                                           AS delivery_status,

    -- Financials
    oia.total_price                               AS revenue,
    oia.total_freight                             AS freight,
    oia.total_price - oia.total_freight           AS margin_proxy,
    oia.item_count,
    opa.total_payment,
    opa.max_installments,
    opa.payment_types,

    -- Review
    r.review_score,
    r.review_comment_message IS NOT NULL          AS has_review_comment

FROM `{DATASET}.orders` o
JOIN `{DATASET}.customers` c          ON o.customer_id = c.customer_id
LEFT JOIN order_items_agg oia         ON o.order_id = oia.order_id
LEFT JOIN order_payments_agg opa      ON o.order_id = opa.order_id
LEFT JOIN `{DATASET}.order_reviews` r ON o.order_id = r.order_id
""",

    # ------------------------------------------------------------------
    # V2: Seller scorecard with tier assignment
    # ------------------------------------------------------------------
    "v_seller_scorecard": f"""
CREATE OR REPLACE VIEW `{DATASET}.v_seller_scorecard` AS
WITH seller_metrics AS (
    SELECT
        s.seller_id,
        s.seller_city,
        s.seller_state,
        COUNT(DISTINCT oi.order_id)                          AS order_count,
        SUM(oi.price)                                        AS total_revenue,
        AVG(oi.price)                                        AS avg_item_price,
        AVG(r.review_score)                                  AS avg_review_score,
        AVG(DATE_DIFF(
            DATE(o.order_delivered_customer_date),
            DATE(o.order_purchase_timestamp), DAY
        ))                                                   AS avg_delivery_days,
        COUNTIF(o.order_delivered_customer_date
                > o.order_estimated_delivery_date)           AS late_orders,
        COUNTIF(r.review_score <= 2)                         AS low_review_count
    FROM `{DATASET}.sellers` s
    JOIN `{DATASET}.order_items` oi   ON s.seller_id = oi.seller_id
    JOIN `{DATASET}.orders` o         ON oi.order_id = o.order_id
    LEFT JOIN `{DATASET}.order_reviews` r ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY s.seller_id, s.seller_city, s.seller_state
),
normalised AS (
    SELECT
        *,
        (total_revenue - MIN(total_revenue) OVER())
            / NULLIF(MAX(total_revenue) OVER() - MIN(total_revenue) OVER(), 0)
            AS norm_revenue,
        (avg_review_score - MIN(avg_review_score) OVER())
            / NULLIF(MAX(avg_review_score) OVER() - MIN(avg_review_score) OVER(), 0)
            AS norm_review,
        1.0 - (avg_delivery_days - MIN(avg_delivery_days) OVER())
            / NULLIF(MAX(avg_delivery_days) OVER() - MIN(avg_delivery_days) OVER(), 0)
            AS norm_speed
    FROM seller_metrics
    WHERE order_count >= 10
)
SELECT
    seller_id,
    seller_city,
    seller_state,
    order_count,
    ROUND(total_revenue, 2)       AS total_revenue,
    ROUND(avg_item_price, 2)      AS avg_item_price,
    ROUND(avg_review_score, 2)    AS avg_review_score,
    ROUND(avg_delivery_days, 1)   AS avg_delivery_days,
    late_orders,
    low_review_count,
    ROUND(0.4 * norm_revenue + 0.4 * norm_review + 0.2 * norm_speed, 4)
                                  AS composite_score,
    CASE NTILE(3) OVER (ORDER BY
        0.4 * norm_revenue + 0.4 * norm_review + 0.2 * norm_speed DESC)
        WHEN 1 THEN 'Gold'
        WHEN 2 THEN 'Silver'
        WHEN 3 THEN 'Bronze'
    END                           AS tier
FROM normalised
""",

    # ------------------------------------------------------------------
    # V3: Category-level metrics
    # ------------------------------------------------------------------
    "v_category_metrics": f"""
CREATE OR REPLACE VIEW `{DATASET}.v_category_metrics` AS
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name)
                                                  AS category_english,
    p.product_category_name                       AS category_pt,
    FORMAT_DATE('%Y-%m', DATE(o.order_purchase_timestamp))
                                                  AS order_month,
    EXTRACT(YEAR FROM o.order_purchase_timestamp)  AS order_year,
    EXTRACT(QUARTER FROM o.order_purchase_timestamp)
                                                  AS order_quarter,
    COUNT(DISTINCT oi.order_id)                    AS order_count,
    ROUND(SUM(oi.price), 2)                        AS revenue,
    ROUND(SUM(oi.freight_value), 2)                AS freight,
    ROUND(SUM(oi.price) - SUM(oi.freight_value), 2)
                                                  AS margin_proxy,
    ROUND(AVG(oi.price), 2)                        AS avg_price,
    ROUND(AVG(oi.freight_value), 2)                AS avg_freight,
    ROUND(AVG(r.review_score), 2)                  AS avg_review_score
FROM `{DATASET}.order_items` oi
JOIN `{DATASET}.orders` o              ON oi.order_id = o.order_id
JOIN `{DATASET}.products` p            ON oi.product_id = p.product_id
LEFT JOIN `{DATASET}.category_translation` ct
    ON p.product_category_name = ct.product_category_name
LEFT JOIN `{DATASET}.order_reviews` r  ON o.order_id = r.order_id
WHERE o.order_status = 'delivered'
GROUP BY category_english, category_pt, order_month, order_year, order_quarter
""",

    # ------------------------------------------------------------------
    # V4: Delivery SLA metrics by state and month
    # ------------------------------------------------------------------
    "v_delivery_sla": f"""
CREATE OR REPLACE VIEW `{DATASET}.v_delivery_sla` AS
SELECT
    c.customer_state                               AS state,
    FORMAT_DATE('%Y-%m', DATE(o.order_purchase_timestamp))
                                                   AS order_month,
    COUNT(*)                                       AS total_orders,
    COUNTIF(o.order_delivered_customer_date
            <= o.order_estimated_delivery_date)     AS on_time_orders,
    COUNTIF(o.order_delivered_customer_date
            > o.order_estimated_delivery_date)      AS late_orders,
    ROUND(
        COUNTIF(o.order_delivered_customer_date
                <= o.order_estimated_delivery_date)
        / COUNT(*) * 100, 2
    )                                              AS on_time_pct,
    ROUND(AVG(DATE_DIFF(
        DATE(o.order_delivered_customer_date),
        DATE(o.order_purchase_timestamp), DAY
    )), 1)                                         AS avg_delivery_days,
    ROUND(AVG(r.review_score), 2)                  AS avg_review_score
FROM `{DATASET}.orders` o
JOIN `{DATASET}.customers` c          ON o.customer_id = c.customer_id
LEFT JOIN `{DATASET}.order_reviews` r ON o.order_id = r.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY state, order_month
""",

    # ------------------------------------------------------------------
    # V5: Dimension — Brazilian states (for map visualisations)
    # ------------------------------------------------------------------
    "v_dim_states": f"""
CREATE OR REPLACE VIEW `{DATASET}.v_dim_states` AS
SELECT DISTINCT
    customer_state                                 AS state_code,
    CASE customer_state
        WHEN 'AC' THEN 'Acre'
        WHEN 'AL' THEN 'Alagoas'
        WHEN 'AM' THEN 'Amazonas'
        WHEN 'AP' THEN 'Amapá'
        WHEN 'BA' THEN 'Bahia'
        WHEN 'CE' THEN 'Ceará'
        WHEN 'DF' THEN 'Distrito Federal'
        WHEN 'ES' THEN 'Espírito Santo'
        WHEN 'GO' THEN 'Goiás'
        WHEN 'MA' THEN 'Maranhão'
        WHEN 'MG' THEN 'Minas Gerais'
        WHEN 'MS' THEN 'Mato Grosso do Sul'
        WHEN 'MT' THEN 'Mato Grosso'
        WHEN 'PA' THEN 'Pará'
        WHEN 'PB' THEN 'Paraíba'
        WHEN 'PE' THEN 'Pernambuco'
        WHEN 'PI' THEN 'Piauí'
        WHEN 'PR' THEN 'Paraná'
        WHEN 'RJ' THEN 'Rio de Janeiro'
        WHEN 'RN' THEN 'Rio Grande do Norte'
        WHEN 'RO' THEN 'Rondônia'
        WHEN 'RR' THEN 'Roraima'
        WHEN 'RS' THEN 'Rio Grande do Sul'
        WHEN 'SC' THEN 'Santa Catarina'
        WHEN 'SE' THEN 'Sergipe'
        WHEN 'SP' THEN 'São Paulo'
        WHEN 'TO' THEN 'Tocantins'
        ELSE customer_state
    END                                            AS state_name
FROM `{DATASET}.customers`
""",
}


def create_all_views(drop_first: bool = False) -> None:
    client = bigquery.Client(project=GCP_PROJECT_ID)

    if drop_first:
        for view_name in VIEWS:
            ref = f"{DATASET}.{view_name}"
            client.delete_table(ref, not_found_ok=True)
            logger.info("Dropped: %s", ref)

    for view_name, ddl in VIEWS.items():
        logger.info("Creating view: %s", view_name)
        client.query(ddl).result()
        logger.info("  ✓ %s created", view_name)

    logger.info("All %d views created in %s", len(VIEWS), DATASET)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--drop", action="store_true", help="Drop views before recreating")
    args = parser.parse_args()
    create_all_views(drop_first=args.drop)
