"""
All SQL queries for Module 2: Data Exploration & Quality Audit.

Every query runs in BigQuery. Organised into 6 categories:
1. Table overview (metadata from __TABLES__ and INFORMATION_SCHEMA)
2. Completeness (null counts and percentages per column)
3. Uniqueness (duplicate detection on primary keys)
4. Distributions (categorical value counts, numeric summaries)
5. Temporal (date ranges, order timeline)
6. Outliers (IQR-based detection on numeric columns)

All queries are parameterised with {dataset} which gets replaced at runtime.
"""


# ---------------------------------------------------------------------------
# 1. TABLE OVERVIEW
# ---------------------------------------------------------------------------

TABLE_OVERVIEW = """
SELECT
    table_id                                          AS table_name,
    row_count,
    ROUND(size_bytes / 1024 / 1024, 2)                AS size_mb,
    TIMESTAMP_MILLIS(last_modified_time)               AS last_modified
FROM `{dataset}.__TABLES__`
ORDER BY row_count DESC
"""

COLUMN_METADATA = """
SELECT
    table_name,
    column_name,
    data_type,
    is_nullable
FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
ORDER BY table_name, ordinal_position
"""


# ---------------------------------------------------------------------------
# 2. COMPLETENESS — null analysis per table
# ---------------------------------------------------------------------------
# These are generated dynamically per table because each table has different
# columns. See build_null_analysis_query() in data_profiling.py.
#
# Template for one column inside the SELECT:
NULL_COLUMN_TEMPLATE = """
    COUNTIF({col} IS NULL) AS {col}_nulls,
    ROUND(COUNTIF({col} IS NULL) / COUNT(*) * 100, 2) AS {col}_null_pct"""


# ---------------------------------------------------------------------------
# 3. UNIQUENESS — duplicate detection
# ---------------------------------------------------------------------------

# Primary key uniqueness: should return 0 rows if PK is truly unique
PK_DUPLICATES = """
SELECT
    {pk_col}        AS duplicate_key,
    COUNT(*)        AS occurrence_count
FROM `{dataset}.{table}`
GROUP BY {pk_col}
HAVING COUNT(*) > 1
ORDER BY occurrence_count DESC
LIMIT 20
"""

# Geolocation: known to have multiple lat/lng per zip code
GEOLOCATION_DUPLICATION = """
SELECT
    geolocation_zip_code_prefix,
    COUNT(*)                        AS total_rows,
    COUNT(DISTINCT geolocation_lat) AS distinct_lats,
    COUNT(DISTINCT geolocation_lng) AS distinct_lngs
FROM `{dataset}.geolocation`
GROUP BY geolocation_zip_code_prefix
HAVING COUNT(*) > 1
ORDER BY total_rows DESC
LIMIT 20
"""

GEOLOCATION_DEDUP_STATS = """
SELECT
    COUNT(*)                                          AS total_rows,
    COUNT(DISTINCT geolocation_zip_code_prefix)       AS distinct_zip_codes,
    ROUND(COUNT(*) / COUNT(DISTINCT geolocation_zip_code_prefix), 1)
                                                      AS avg_rows_per_zip
FROM `{dataset}.geolocation`
"""


# ---------------------------------------------------------------------------
# 4. DISTRIBUTIONS
# ---------------------------------------------------------------------------

# 4a. Categorical distributions
ORDER_STATUS_DIST = """
SELECT
    order_status,
    COUNT(*)                                            AS order_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct
FROM `{dataset}.orders`
GROUP BY order_status
ORDER BY order_count DESC
"""

PAYMENT_TYPE_DIST = """
SELECT
    payment_type,
    COUNT(*)                                            AS payment_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct,
    ROUND(AVG(payment_value), 2)                        AS avg_value,
    ROUND(AVG(payment_installments), 1)                 AS avg_installments
FROM `{dataset}.order_payments`
GROUP BY payment_type
ORDER BY payment_count DESC
"""

REVIEW_SCORE_DIST = """
SELECT
    review_score,
    COUNT(*)                                            AS review_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct
FROM `{dataset}.order_reviews`
GROUP BY review_score
ORDER BY review_score
"""

TOP_PRODUCT_CATEGORIES = """
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name)
                                                        AS category,
    COUNT(*)                                            AS product_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct
FROM `{dataset}.products` p
LEFT JOIN `{dataset}.category_translation` ct
    ON p.product_category_name = ct.product_category_name
GROUP BY category
ORDER BY product_count DESC
LIMIT 20
"""

CUSTOMER_STATE_DIST = """
SELECT
    customer_state,
    COUNT(*)                                            AS customer_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct
FROM `{dataset}.customers`
GROUP BY customer_state
ORDER BY customer_count DESC
LIMIT 10
"""

SELLER_STATE_DIST = """
SELECT
    seller_state,
    COUNT(*)                                            AS seller_count,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER() * 100, 2)    AS pct
FROM `{dataset}.sellers`
GROUP BY seller_state
ORDER BY seller_count DESC
LIMIT 10
"""

# 4b. Numeric summaries (5-number summary + mean + stddev)
NUMERIC_SUMMARY = """
SELECT
    '{col_label}'                                       AS metric,
    COUNT({col})                                        AS n,
    ROUND(MIN({col}), 2)                                AS min_val,
    ROUND(APPROX_QUANTILES({col}, 4)[OFFSET(1)], 2)    AS q1,
    ROUND(APPROX_QUANTILES({col}, 4)[OFFSET(2)], 2)    AS median,
    ROUND(APPROX_QUANTILES({col}, 4)[OFFSET(3)], 2)    AS q3,
    ROUND(MAX({col}), 2)                                AS max_val,
    ROUND(AVG({col}), 2)                                AS mean_val,
    ROUND(STDDEV({col}), 2)                             AS stddev_val
FROM `{dataset}.{table}`
WHERE {col} IS NOT NULL
"""

# Columns to profile with NUMERIC_SUMMARY
NUMERIC_PROFILES = [
    ("order_items", "price", "Item Price (R$)"),
    ("order_items", "freight_value", "Freight Value (R$)"),
    ("order_payments", "payment_value", "Payment Value (R$)"),
    ("order_payments", "payment_installments", "Payment Installments"),
    ("products", "product_weight_g", "Product Weight (g)"),
    ("products", "product_length_cm", "Product Length (cm)"),
    ("products", "product_height_cm", "Product Height (cm)"),
    ("products", "product_width_cm", "Product Width (cm)"),
    ("products", "product_photos_qty", "Product Photos Qty"),
    ("products", "product_name_lenght", "Product Name Length"),
    ("products", "product_description_lenght", "Product Desc Length"),
]


# ---------------------------------------------------------------------------
# 5. TEMPORAL — date ranges and order timeline
# ---------------------------------------------------------------------------

ORDER_DATE_RANGE = """
SELECT
    MIN(order_purchase_timestamp)                       AS earliest_order,
    MAX(order_purchase_timestamp)                       AS latest_order,
    DATE_DIFF(
        CAST(MAX(order_purchase_timestamp) AS DATE),
        CAST(MIN(order_purchase_timestamp) AS DATE),
        DAY
    )                                                   AS span_days,
    COUNT(DISTINCT DATE(order_purchase_timestamp))      AS active_days
FROM `{dataset}.orders`
"""

ORDERS_PER_MONTH = """
SELECT
    FORMAT_TIMESTAMP('%Y-%m', order_purchase_timestamp)  AS order_month,
    COUNT(*)                                            AS order_count,
    ROUND(SUM(oi.price), 2)                             AS total_revenue,
    ROUND(AVG(oi.price), 2)                             AS avg_item_price
FROM `{dataset}.orders` o
JOIN `{dataset}.order_items` oi ON o.order_id = oi.order_id
GROUP BY order_month
ORDER BY order_month
"""

DELIVERY_TIME_STATS = """
SELECT
    COUNT(*)                                            AS delivered_orders,
    ROUND(AVG(
        DATE_DIFF(
            CAST(order_delivered_customer_date AS DATE),
            CAST(order_purchase_timestamp AS DATE),
            DAY
        )
    ), 1)                                               AS avg_delivery_days,
    MIN(DATE_DIFF(
        CAST(order_delivered_customer_date AS DATE),
        CAST(order_purchase_timestamp AS DATE),
        DAY
    ))                                                  AS min_delivery_days,
    MAX(DATE_DIFF(
        CAST(order_delivered_customer_date AS DATE),
        CAST(order_purchase_timestamp AS DATE),
        DAY
    ))                                                  AS max_delivery_days,
    COUNTIF(order_delivered_customer_date > order_estimated_delivery_date)
                                                        AS late_deliveries,
    ROUND(
        COUNTIF(order_delivered_customer_date > order_estimated_delivery_date)
        / COUNT(*) * 100, 2
    )                                                   AS late_delivery_pct
FROM `{dataset}.orders`
WHERE order_delivered_customer_date IS NOT NULL
"""


# ---------------------------------------------------------------------------
# 6. OUTLIERS — IQR method
# ---------------------------------------------------------------------------
# IQR = Q3 - Q1
# Lower bound = Q1 - 1.5 * IQR
# Upper bound = Q3 + 1.5 * IQR
# Points outside [lower, upper] are outliers.

OUTLIER_IQR = """
WITH quartiles AS (
    SELECT
        APPROX_QUANTILES({col}, 4)[OFFSET(1)] AS q1,
        APPROX_QUANTILES({col}, 4)[OFFSET(3)] AS q3
    FROM `{dataset}.{table}`
    WHERE {col} IS NOT NULL
),
bounds AS (
    SELECT
        q1,
        q3,
        q3 - q1                     AS iqr,
        q1 - 1.5 * (q3 - q1)       AS lower_bound,
        q3 + 1.5 * (q3 - q1)       AS upper_bound
    FROM quartiles
)
SELECT
    '{col_label}'                                       AS metric,
    b.q1,
    b.q3,
    ROUND(b.iqr, 2)                                     AS iqr,
    ROUND(b.lower_bound, 2)                              AS lower_bound,
    ROUND(b.upper_bound, 2)                              AS upper_bound,
    COUNTIF(t.{col} < b.lower_bound)                     AS outliers_below,
    COUNTIF(t.{col} > b.upper_bound)                     AS outliers_above,
    COUNTIF(t.{col} < b.lower_bound OR t.{col} > b.upper_bound)
                                                         AS total_outliers,
    ROUND(
        COUNTIF(t.{col} < b.lower_bound OR t.{col} > b.upper_bound)
        / COUNT(t.{col}) * 100, 2
    )                                                    AS outlier_pct
FROM `{dataset}.{table}` t
CROSS JOIN bounds b
WHERE t.{col} IS NOT NULL
GROUP BY b.q1, b.q3, b.iqr, b.lower_bound, b.upper_bound
"""

# Columns to run IQR outlier detection on
OUTLIER_PROFILES = [
    ("order_items", "price", "Item Price"),
    ("order_items", "freight_value", "Freight Value"),
    ("order_payments", "payment_value", "Payment Value"),
    ("products", "product_weight_g", "Product Weight"),
]


# ---------------------------------------------------------------------------
# 7. REPEAT CUSTOMERS
# ---------------------------------------------------------------------------

REPEAT_CUSTOMER_RATE = """
WITH customer_orders AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT o.order_id) AS order_count
    FROM `{dataset}.customers` c
    JOIN `{dataset}.orders` o ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
)
SELECT
    COUNT(*)                                            AS total_unique_customers,
    COUNTIF(order_count = 1)                            AS one_time_buyers,
    COUNTIF(order_count >= 2)                           AS repeat_buyers,
    ROUND(COUNTIF(order_count >= 2) / COUNT(*) * 100, 2)
                                                        AS repeat_rate_pct,
    MAX(order_count)                                    AS max_orders_by_one_customer
FROM customer_orders
"""


# ---------------------------------------------------------------------------
# PRIMARY KEY DEFINITIONS (for duplicate checks)
# ---------------------------------------------------------------------------

PRIMARY_KEYS = {
    "customers": "customer_id",
    "orders": "order_id",
    "order_reviews": "review_id",
    "products": "product_id",
    "sellers": "seller_id",
    "category_translation": "product_category_name",
}
