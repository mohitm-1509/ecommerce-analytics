"""
Module 3: Core Business Analysis — 18 SQL Queries across 5 Business Questions.

Every query is parameterised with {d} (dataset reference: project.dataset).
Queries are numbered Q01–Q18 and grouped by business question.

SQL techniques demonstrated:
    Multi-table JOINs (up to 5 tables), CTEs, Window functions (RANK, DENSE_RANK,
    NTILE, LAG, running SUM, PERCENT_RANK), QUALIFY, Named WINDOW clause,
    DATE_DIFF, DATE_TRUNC, FORMAT_TIMESTAMP, APPROX_QUANTILES, COUNTIF,
    CASE WHEN bucketing, Subqueries, HAVING, conditional aggregation.
"""

# ============================================================================
# BUSINESS QUESTION 1: Delivery Impact on Customer Satisfaction
# ============================================================================
# Core hypothesis: Late deliveries drive low review scores. If proven,
# Olist can prioritise logistics improvements for the highest ROI on
# customer satisfaction.
# ============================================================================

Q01_REVIEW_BY_DELIVERY_STATUS = """
-- Q01: Average review score — on-time vs late deliveries
-- Proves/disproves the core hypothesis with a single number comparison.
-- Uses COUNTIF for conditional aggregation instead of CASE WHEN + SUM.

SELECT
    CASE
        WHEN order_delivered_customer_date <= order_estimated_delivery_date
            THEN 'On-Time'
        ELSE 'Late'
    END                                                     AS delivery_status,
    COUNT(*)                                                AS order_count,
    ROUND(AVG(r.review_score), 2)                           AS avg_review_score,
    COUNTIF(r.review_score = 1)                             AS one_star_count,
    ROUND(COUNTIF(r.review_score = 1) / COUNT(*) * 100, 2) AS one_star_pct,
    COUNTIF(r.review_score = 5)                             AS five_star_count,
    ROUND(COUNTIF(r.review_score = 5) / COUNT(*) * 100, 2) AS five_star_pct
FROM `{d}.orders` o
JOIN `{d}.order_reviews` r ON o.order_id = r.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
  AND o.order_estimated_delivery_date IS NOT NULL
GROUP BY delivery_status
ORDER BY avg_review_score DESC
"""

Q02_REVIEW_BY_DELAY_BUCKET = """
-- Q02: Review score distribution across delivery delay buckets.
-- Bucketing reveals the non-linear relationship: a 1-day delay may be
-- forgiven, but 7+ days late is catastrophic for satisfaction.
-- Uses CTE for clarity and APPROX_QUANTILES for median.

WITH delivery_data AS (
    SELECT
        o.order_id,
        r.review_score,
        DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_estimated_delivery_date AS DATE),
            DAY
        ) AS delay_days
    FROM `{d}.orders` o
    JOIN `{d}.order_reviews` r ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
)
SELECT
    CASE
        WHEN delay_days <= -7  THEN '1. >7 days early'
        WHEN delay_days <= -1  THEN '2. 1-7 days early'
        WHEN delay_days = 0    THEN '3. On time (exact)'
        WHEN delay_days <= 7   THEN '4. 1-7 days late'
        WHEN delay_days <= 14  THEN '5. 8-14 days late'
        ELSE                        '6. >14 days late'
    END                                                         AS delay_bucket,
    COUNT(*)                                                    AS order_count,
    ROUND(AVG(review_score), 2)                                 AS avg_review,
    APPROX_QUANTILES(review_score, 2)[OFFSET(1)]                AS median_review,
    ROUND(COUNTIF(review_score <= 2) / COUNT(*) * 100, 1)       AS pct_low_score
FROM delivery_data
GROUP BY delay_bucket
ORDER BY delay_bucket
"""

Q03_MONTHLY_LATE_DELIVERY_TREND = """
-- Q03: Monthly late delivery % with month-over-month change using LAG.
-- Shows whether logistics is improving or deteriorating over time.
-- LAG() looks back one row (previous month) to compute the delta.

WITH monthly AS (
    SELECT
        DATE_TRUNC(CAST(order_purchase_timestamp AS DATE), MONTH)   AS order_month,
        COUNT(*)                                                    AS total_orders,
        COUNTIF(order_delivered_customer_date > order_estimated_delivery_date)
                                                                    AS late_orders,
        ROUND(
            COUNTIF(order_delivered_customer_date > order_estimated_delivery_date)
            / COUNT(*) * 100, 2
        )                                                           AS late_pct
    FROM `{d}.orders`
    WHERE order_delivered_customer_date IS NOT NULL
      AND order_estimated_delivery_date IS NOT NULL
    GROUP BY order_month
)
SELECT
    order_month,
    total_orders,
    late_orders,
    late_pct,
    LAG(late_pct) OVER (ORDER BY order_month)                       AS prev_month_late_pct,
    ROUND(
        late_pct - LAG(late_pct) OVER (ORDER BY order_month), 2
    )                                                               AS mom_change_pp
FROM monthly
ORDER BY order_month
"""

Q04_DELIVERY_DAYS_VS_REVIEW = """
-- Q04: Delivery time (in day buckets) correlated with review score.
-- Answers: "Is there a delivery sweet spot?" and "At what day count
-- does satisfaction drop off a cliff?"

WITH delivery_metrics AS (
    SELECT
        o.order_id,
        r.review_score,
        DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_purchase_timestamp AS DATE),
            DAY
        ) AS delivery_days
    FROM `{d}.orders` o
    JOIN `{d}.order_reviews` r ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
)
SELECT
    CASE
        WHEN delivery_days <= 7   THEN '01. ≤7 days'
        WHEN delivery_days <= 14  THEN '02. 8-14 days'
        WHEN delivery_days <= 21  THEN '03. 15-21 days'
        WHEN delivery_days <= 30  THEN '04. 22-30 days'
        WHEN delivery_days <= 45  THEN '05. 31-45 days'
        ELSE                           '06. >45 days'
    END                                                         AS delivery_bucket,
    COUNT(*)                                                    AS order_count,
    ROUND(AVG(review_score), 2)                                 AS avg_review,
    ROUND(AVG(delivery_days), 1)                                AS avg_days_in_bucket,
    ROUND(COUNTIF(review_score >= 4) / COUNT(*) * 100, 1)       AS pct_satisfied
FROM delivery_metrics
GROUP BY delivery_bucket
ORDER BY delivery_bucket
"""


# ============================================================================
# BUSINESS QUESTION 2: Seller Quality Segmentation
# ============================================================================
# Olist is a marketplace — seller quality directly impacts platform reputation.
# Segmenting sellers lets management reward top performers and intervene
# with (or delist) poor ones.
# ============================================================================

Q05_SELLER_PERFORMANCE = """
-- Q05: Seller performance scorecard — multi-table JOIN across 4 tables.
-- Computes revenue, order volume, avg review, and avg delivery days per seller.
-- QUALIFY filters to sellers with ≥10 orders (statistical reliability).

SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)                              AS order_count,
    ROUND(SUM(oi.price), 2)                                  AS total_revenue,
    ROUND(AVG(oi.price), 2)                                  AS avg_order_value,
    ROUND(AVG(r.review_score), 2)                            AS avg_review_score,
    ROUND(AVG(
        DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_purchase_timestamp AS DATE),
            DAY
        )
    ), 1)                                                    AS avg_delivery_days
FROM `{d}.sellers` s
JOIN `{d}.order_items` oi   ON s.seller_id = oi.seller_id
JOIN `{d}.orders` o         ON oi.order_id = o.order_id
JOIN `{d}.order_reviews` r  ON o.order_id = r.order_id
WHERE o.order_delivered_customer_date IS NOT NULL
GROUP BY s.seller_id, s.seller_city, s.seller_state
QUALIFY COUNT(DISTINCT oi.order_id) >= 10
ORDER BY total_revenue DESC
LIMIT 50
"""

Q06_SELLER_TIERS = """
-- Q06: Seller segmentation into Gold / Silver / Bronze tiers using NTILE.
-- Composite score = normalised revenue (40%) + normalised review (40%)
--                   + normalised delivery speed (20%, inverted: fewer days = better).
-- NTILE(3) splits sellers into 3 equal groups on composite score.
-- Uses a named WINDOW clause for readability.

WITH seller_metrics AS (
    SELECT
        s.seller_id,
        s.seller_state,
        COUNT(DISTINCT oi.order_id)                          AS order_count,
        SUM(oi.price)                                        AS total_revenue,
        AVG(r.review_score)                                  AS avg_review,
        AVG(DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_purchase_timestamp AS DATE), DAY
        ))                                                   AS avg_delivery_days
    FROM `{d}.sellers` s
    JOIN `{d}.order_items` oi   ON s.seller_id = oi.seller_id
    JOIN `{d}.orders` o         ON oi.order_id = o.order_id
    JOIN `{d}.order_reviews` r  ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY s.seller_id, s.seller_state
    HAVING COUNT(DISTINCT oi.order_id) >= 10
),
normalised AS (
    SELECT
        *,
        -- Min-max normalisation to [0, 1] for each metric
        (total_revenue - MIN(total_revenue) OVER())
            / NULLIF(MAX(total_revenue) OVER() - MIN(total_revenue) OVER(), 0)
                                                             AS norm_revenue,
        (avg_review - MIN(avg_review) OVER())
            / NULLIF(MAX(avg_review) OVER() - MIN(avg_review) OVER(), 0)
                                                             AS norm_review,
        -- Invert delivery: lower days = higher score
        1 - (avg_delivery_days - MIN(avg_delivery_days) OVER())
            / NULLIF(MAX(avg_delivery_days) OVER() - MIN(avg_delivery_days) OVER(), 0)
                                                             AS norm_speed
    FROM seller_metrics
),
scored AS (
    SELECT
        *,
        ROUND(0.4 * norm_revenue + 0.4 * norm_review + 0.2 * norm_speed, 4)
                                                             AS composite_score,
        NTILE(3) OVER (ORDER BY
            0.4 * norm_revenue + 0.4 * norm_review + 0.2 * norm_speed DESC
        )                                                    AS tier_num
    FROM normalised
)
SELECT
    seller_id,
    seller_state,
    order_count,
    ROUND(total_revenue, 2)                                  AS total_revenue,
    ROUND(avg_review, 2)                                     AS avg_review,
    ROUND(avg_delivery_days, 1)                              AS avg_delivery_days,
    ROUND(composite_score, 3)                                AS composite_score,
    CASE tier_num
        WHEN 1 THEN 'Gold'
        WHEN 2 THEN 'Silver'
        WHEN 3 THEN 'Bronze'
    END                                                      AS tier
FROM scored
ORDER BY composite_score DESC
"""

Q07_TIER_SUMMARY = """
-- Q07: Aggregate statistics per seller tier.
-- Shows the gap between Gold and Bronze to quantify the business impact
-- of low-quality sellers on platform-wide metrics.

WITH seller_metrics AS (
    SELECT
        s.seller_id,
        COUNT(DISTINCT oi.order_id)                          AS order_count,
        SUM(oi.price)                                        AS total_revenue,
        AVG(r.review_score)                                  AS avg_review,
        AVG(DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_purchase_timestamp AS DATE), DAY
        ))                                                   AS avg_delivery_days
    FROM `{d}.sellers` s
    JOIN `{d}.order_items` oi   ON s.seller_id = oi.seller_id
    JOIN `{d}.orders` o         ON oi.order_id = o.order_id
    JOIN `{d}.order_reviews` r  ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
    GROUP BY s.seller_id
    HAVING COUNT(DISTINCT oi.order_id) >= 10
),
normalised AS (
    SELECT
        *,
        (total_revenue - MIN(total_revenue) OVER())
            / NULLIF(MAX(total_revenue) OVER() - MIN(total_revenue) OVER(), 0)
            AS norm_revenue,
        (avg_review - MIN(avg_review) OVER())
            / NULLIF(MAX(avg_review) OVER() - MIN(avg_review) OVER(), 0)
            AS norm_review,
        1 - (avg_delivery_days - MIN(avg_delivery_days) OVER())
            / NULLIF(MAX(avg_delivery_days) OVER() - MIN(avg_delivery_days) OVER(), 0)
            AS norm_speed
    FROM seller_metrics
),
tiered AS (
    SELECT
        *,
        NTILE(3) OVER (ORDER BY
            0.4 * norm_revenue + 0.4 * norm_review + 0.2 * norm_speed DESC
        ) AS tier_num
    FROM normalised
)
SELECT
    CASE tier_num WHEN 1 THEN 'Gold' WHEN 2 THEN 'Silver' WHEN 3 THEN 'Bronze' END
                                                             AS tier,
    COUNT(*)                                                 AS seller_count,
    ROUND(SUM(total_revenue), 2)                             AS tier_total_revenue,
    ROUND(AVG(total_revenue), 2)                             AS avg_seller_revenue,
    ROUND(AVG(avg_review), 2)                                AS avg_review_score,
    ROUND(AVG(avg_delivery_days), 1)                         AS avg_delivery_days,
    ROUND(AVG(order_count), 0)                               AS avg_orders_per_seller
FROM tiered
GROUP BY tier_num, tier
ORDER BY tier_num
"""

Q08_BOTTOM_SELLERS_IMPACT = """
-- Q08: Bottom 5% of sellers by review score — their impact on the platform.
-- Uses PERCENT_RANK to identify the worst performers.
-- QUALIFY filters directly on the window result (no subquery needed).

WITH seller_stats AS (
    SELECT
        s.seller_id,
        s.seller_state,
        COUNT(DISTINCT oi.order_id)                          AS order_count,
        ROUND(SUM(oi.price), 2)                              AS total_revenue,
        ROUND(AVG(r.review_score), 2)                        AS avg_review,
        COUNTIF(r.review_score <= 2)                         AS low_review_count,
        PERCENT_RANK() OVER (ORDER BY AVG(r.review_score))   AS review_percentile
    FROM `{d}.sellers` s
    JOIN `{d}.order_items` oi   ON s.seller_id = oi.seller_id
    JOIN `{d}.orders` o         ON oi.order_id = o.order_id
    JOIN `{d}.order_reviews` r  ON o.order_id = r.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY s.seller_id, s.seller_state
    HAVING COUNT(DISTINCT oi.order_id) >= 5
)
SELECT
    seller_id,
    seller_state,
    order_count,
    total_revenue,
    avg_review,
    low_review_count,
    ROUND(review_percentile * 100, 1) AS review_percentile_pct
FROM seller_stats
WHERE review_percentile <= 0.05
ORDER BY avg_review, total_revenue DESC
"""


# ============================================================================
# BUSINESS QUESTION 3: Regional Revenue Trends
# ============================================================================
# Brazil is geographically vast. Shipping costs, delivery times, and customer
# behaviour vary dramatically by state. Regional analysis informs where to
# invest in logistics hubs and marketing.
# ============================================================================

Q09_REVENUE_BY_STATE = """
-- Q09: Revenue, order count, and AOV by customer state.
-- Includes market share calculation using a window function SUM.

SELECT
    c.customer_state                                         AS state,
    COUNT(DISTINCT o.order_id)                               AS order_count,
    COUNT(DISTINCT c.customer_unique_id)                     AS unique_customers,
    ROUND(SUM(oi.price), 2)                                  AS total_revenue,
    ROUND(SUM(oi.freight_value), 2)                          AS total_freight,
    ROUND(AVG(oi.price), 2)                                  AS avg_order_value,
    ROUND(
        SUM(oi.price) / SUM(SUM(oi.price)) OVER() * 100, 2
    )                                                        AS revenue_share_pct
FROM `{d}.customers` c
JOIN `{d}.orders` o      ON c.customer_id = o.customer_id
JOIN `{d}.order_items` oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY total_revenue DESC
"""

Q10_MOM_REVENUE_BY_STATE = """
-- Q10: Month-over-month revenue growth for top 5 states using LAG.
-- LAG(revenue, 1) fetches the previous month's revenue.
-- Growth % = (current - previous) / previous × 100.
-- Pre-filters to top 5 states to keep the result set focused.

WITH top_states AS (
    SELECT c.customer_state
    FROM `{d}.customers` c
    JOIN `{d}.orders` o      ON c.customer_id = o.customer_id
    JOIN `{d}.order_items` oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY c.customer_state
    ORDER BY SUM(oi.price) DESC
    LIMIT 5
),
monthly_rev AS (
    SELECT
        c.customer_state                                     AS state,
        DATE_TRUNC(CAST(o.order_purchase_timestamp AS DATE), MONTH)
                                                             AS order_month,
        ROUND(SUM(oi.price), 2)                              AS revenue
    FROM `{d}.customers` c
    JOIN `{d}.orders` o      ON c.customer_id = o.customer_id
    JOIN `{d}.order_items` oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
      AND c.customer_state IN (SELECT customer_state FROM top_states)
    GROUP BY state, order_month
)
SELECT
    state,
    order_month,
    revenue,
    LAG(revenue) OVER w                                      AS prev_month_revenue,
    ROUND(
        SAFE_DIVIDE(
            revenue - LAG(revenue) OVER w,
            LAG(revenue) OVER w
        ) * 100, 1
    )                                                        AS mom_growth_pct
FROM monthly_rev
WINDOW w AS (PARTITION BY state ORDER BY order_month)
ORDER BY state, order_month
"""

Q11_RUNNING_TOTAL_BY_STATE = """
-- Q11: Cumulative (running total) revenue by state over months.
-- Uses SUM() OVER with ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW.
-- Shows how each state's contribution accumulates over the dataset period.

WITH monthly_rev AS (
    SELECT
        c.customer_state                                     AS state,
        DATE_TRUNC(CAST(o.order_purchase_timestamp AS DATE), MONTH)
                                                             AS order_month,
        ROUND(SUM(oi.price), 2)                              AS monthly_revenue
    FROM `{d}.customers` c
    JOIN `{d}.orders` o      ON c.customer_id = o.customer_id
    JOIN `{d}.order_items` oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY state, order_month
)
SELECT
    state,
    order_month,
    monthly_revenue,
    SUM(monthly_revenue) OVER (
        PARTITION BY state
        ORDER BY order_month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    )                                                        AS cumulative_revenue
FROM monthly_rev
ORDER BY state, order_month
"""

Q12_FREIGHT_EFFICIENCY_BY_STATE = """
-- Q12: Freight cost as % of order value by state.
-- High freight % = expensive to serve that region.
-- Includes avg delivery days to check if expensive freight at least buys speed.
-- DENSE_RANK ranks states by freight ratio (worst first).

SELECT
    c.customer_state                                         AS state,
    COUNT(DISTINCT o.order_id)                               AS orders,
    ROUND(SUM(oi.price), 2)                                  AS total_revenue,
    ROUND(SUM(oi.freight_value), 2)                          AS total_freight,
    ROUND(SUM(oi.freight_value) / SUM(oi.price) * 100, 2)   AS freight_pct_of_revenue,
    ROUND(AVG(oi.freight_value), 2)                          AS avg_freight,
    ROUND(AVG(
        DATE_DIFF(
            CAST(o.order_delivered_customer_date AS DATE),
            CAST(o.order_purchase_timestamp AS DATE), DAY
        )
    ), 1)                                                    AS avg_delivery_days,
    DENSE_RANK() OVER (
        ORDER BY SUM(oi.freight_value) / SUM(oi.price) DESC
    )                                                        AS freight_rank
FROM `{d}.customers` c
JOIN `{d}.orders` o      ON c.customer_id = o.customer_id
JOIN `{d}.order_items` oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
ORDER BY freight_pct_of_revenue DESC
"""


# ============================================================================
# BUSINESS QUESTION 4: Product Category Profitability
# ============================================================================
# Not all categories are created equal. Some generate high revenue but also
# high freight costs (heavy items). Understanding the margin proxy
# (revenue - freight) per category guides product strategy.
# ============================================================================

Q13_CATEGORY_PROFITABILITY = """
-- Q13: Revenue, freight, and margin proxy by product category.
-- Margin proxy = price - freight_value (no COGS data available).
-- Joins to category_translation for English names.

SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name)
                                                             AS category,
    COUNT(DISTINCT oi.order_id)                              AS order_count,
    ROUND(SUM(oi.price), 2)                                  AS total_revenue,
    ROUND(SUM(oi.freight_value), 2)                          AS total_freight,
    ROUND(SUM(oi.price) - SUM(oi.freight_value), 2)          AS margin_proxy,
    ROUND(
        (SUM(oi.price) - SUM(oi.freight_value))
        / NULLIF(SUM(oi.price), 0) * 100, 1
    )                                                        AS margin_pct,
    ROUND(AVG(oi.price), 2)                                  AS avg_price,
    ROUND(AVG(oi.freight_value), 2)                          AS avg_freight
FROM `{d}.order_items` oi
JOIN `{d}.products` p          ON oi.product_id = p.product_id
LEFT JOIN `{d}.category_translation` ct
    ON p.product_category_name = ct.product_category_name
GROUP BY category
HAVING COUNT(DISTINCT oi.order_id) >= 50
ORDER BY total_revenue DESC
LIMIT 25
"""

Q14_CATEGORY_SEASONALITY = """
-- Q14: Quarterly revenue by top 10 product categories.
-- Reveals seasonal patterns: do some categories spike in Q4 (holiday season)?
-- Uses EXTRACT(QUARTER) for aggregation.

WITH top_categories AS (
    SELECT
        COALESCE(ct.product_category_name_english, p.product_category_name) AS category
    FROM `{d}.order_items` oi
    JOIN `{d}.products` p ON oi.product_id = p.product_id
    LEFT JOIN `{d}.category_translation` ct
        ON p.product_category_name = ct.product_category_name
    GROUP BY category
    ORDER BY SUM(oi.price) DESC
    LIMIT 10
)
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name)
                                                             AS category,
    EXTRACT(YEAR FROM o.order_purchase_timestamp)            AS year,
    EXTRACT(QUARTER FROM o.order_purchase_timestamp)         AS quarter,
    COUNT(DISTINCT oi.order_id)                              AS order_count,
    ROUND(SUM(oi.price), 2)                                  AS quarterly_revenue
FROM `{d}.order_items` oi
JOIN `{d}.orders` o            ON oi.order_id = o.order_id
JOIN `{d}.products` p          ON oi.product_id = p.product_id
LEFT JOIN `{d}.category_translation` ct
    ON p.product_category_name = ct.product_category_name
WHERE o.order_status = 'delivered'
  AND COALESCE(ct.product_category_name_english, p.product_category_name)
      IN (SELECT category FROM top_categories)
GROUP BY category, year, quarter
ORDER BY category, year, quarter
"""

Q15_CATEGORY_GROWTH = """
-- Q15: Quarter-over-quarter revenue growth by category using LAG.
-- Identifies categories that are gaining or losing momentum.

WITH quarterly AS (
    SELECT
        COALESCE(ct.product_category_name_english, p.product_category_name)
                                                             AS category,
        DATE_TRUNC(CAST(o.order_purchase_timestamp AS DATE), QUARTER)
                                                             AS quarter_start,
        ROUND(SUM(oi.price), 2)                              AS revenue
    FROM `{d}.order_items` oi
    JOIN `{d}.orders` o            ON oi.order_id = o.order_id
    JOIN `{d}.products` p          ON oi.product_id = p.product_id
    LEFT JOIN `{d}.category_translation` ct
        ON p.product_category_name = ct.product_category_name
    WHERE o.order_status = 'delivered'
    GROUP BY category, quarter_start
    HAVING COUNT(DISTINCT oi.order_id) >= 10
)
SELECT
    category,
    quarter_start,
    revenue,
    LAG(revenue) OVER w                                      AS prev_quarter_revenue,
    ROUND(
        SAFE_DIVIDE(revenue - LAG(revenue) OVER w, LAG(revenue) OVER w) * 100, 1
    )                                                        AS qoq_growth_pct
FROM quarterly
WINDOW w AS (PARTITION BY category ORDER BY quarter_start)
ORDER BY category, quarter_start
"""


# ============================================================================
# BUSINESS QUESTION 5: Payment Method Analysis
# ============================================================================
# Brazil has unique payment culture: "boleto bancário" (bank slip) is widely
# used alongside credit cards. Installment purchases ("parcelamento") are
# standard. Understanding payment patterns informs checkout UX and financing
# strategy.
# ============================================================================

Q16_PAYMENT_OVERVIEW = """
-- Q16: Payment type breakdown with AOV and total revenue.
-- Answers: Which payment methods drive the most revenue?

SELECT
    p.payment_type,
    COUNT(DISTINCT p.order_id)                               AS order_count,
    ROUND(SUM(p.payment_value), 2)                           AS total_value,
    ROUND(AVG(p.payment_value), 2)                           AS avg_payment_value,
    ROUND(
        SUM(p.payment_value) / SUM(SUM(p.payment_value)) OVER() * 100, 2
    )                                                        AS value_share_pct,
    ROUND(AVG(p.payment_installments), 1)                    AS avg_installments
FROM `{d}.order_payments` p
WHERE p.payment_type != 'not_defined'
GROUP BY p.payment_type
ORDER BY total_value DESC
"""

Q17_INSTALLMENT_VS_ORDER_VALUE = """
-- Q17: Do more installments correlate with higher order values?
-- Groups credit card orders by installment count and shows AOV per group.
-- Tests the hypothesis: customers split larger purchases into more installments.

WITH credit_orders AS (
    SELECT
        p.order_id,
        MAX(p.payment_installments)                          AS installments,
        SUM(p.payment_value)                                 AS order_value
    FROM `{d}.order_payments` p
    WHERE p.payment_type = 'credit_card'
      AND p.payment_installments > 0
    GROUP BY p.order_id
)
SELECT
    CASE
        WHEN installments = 1       THEN '01. Single payment'
        WHEN installments <= 3      THEN '02. 2-3 installments'
        WHEN installments <= 6      THEN '03. 4-6 installments'
        WHEN installments <= 10     THEN '04. 7-10 installments'
        ELSE                             '05. 11+ installments'
    END                                                      AS installment_group,
    COUNT(*)                                                 AS order_count,
    ROUND(AVG(order_value), 2)                               AS avg_order_value,
    ROUND(APPROX_QUANTILES(order_value, 2)[OFFSET(1)], 2)   AS median_order_value,
    ROUND(MIN(order_value), 2)                               AS min_order_value,
    ROUND(MAX(order_value), 2)                               AS max_order_value
FROM credit_orders
GROUP BY installment_group
ORDER BY installment_group
"""

Q18_PAYMENT_BY_STATE = """
-- Q18: Payment type preference by customer state.
-- Reveals regional payment culture differences.
-- Uses conditional aggregation to pivot payment types into columns.
-- Ranks states by total order value.

SELECT
    c.customer_state                                         AS state,
    COUNT(DISTINCT o.order_id)                               AS total_orders,
    ROUND(
        COUNTIF(p.payment_type = 'credit_card')
        / COUNT(*) * 100, 1
    )                                                        AS credit_card_pct,
    ROUND(
        COUNTIF(p.payment_type = 'boleto')
        / COUNT(*) * 100, 1
    )                                                        AS boleto_pct,
    ROUND(
        COUNTIF(p.payment_type = 'voucher')
        / COUNT(*) * 100, 1
    )                                                        AS voucher_pct,
    ROUND(
        COUNTIF(p.payment_type = 'debit_card')
        / COUNT(*) * 100, 1
    )                                                        AS debit_card_pct,
    ROUND(AVG(p.payment_installments), 1)                    AS avg_installments
FROM `{d}.customers` c
JOIN `{d}.orders` o       ON c.customer_id = o.customer_id
JOIN `{d}.order_payments` p ON o.order_id = p.order_id
WHERE p.payment_type != 'not_defined'
GROUP BY c.customer_state
ORDER BY total_orders DESC
"""


# ============================================================================
# Query registry for the runner
# ============================================================================

ALL_QUERIES = {
    "BQ1: Delivery Impact on Customer Satisfaction": [
        ("Q01", "Review Score by Delivery Status (On-Time vs Late)", Q01_REVIEW_BY_DELIVERY_STATUS),
        ("Q02", "Review Score by Delay Bucket", Q02_REVIEW_BY_DELAY_BUCKET),
        ("Q03", "Monthly Late Delivery % Trend (LAG)", Q03_MONTHLY_LATE_DELIVERY_TREND),
        ("Q04", "Delivery Days vs Review Score", Q04_DELIVERY_DAYS_VS_REVIEW),
    ],
    "BQ2: Seller Quality Segmentation": [
        ("Q05", "Seller Performance Scorecard (4-table JOIN)", Q05_SELLER_PERFORMANCE),
        ("Q06", "Seller Tier Segmentation (NTILE + Composite Score)", Q06_SELLER_TIERS),
        ("Q07", "Tier Summary Statistics", Q07_TIER_SUMMARY),
        ("Q08", "Bottom 5% Sellers Impact (PERCENT_RANK + QUALIFY)", Q08_BOTTOM_SELLERS_IMPACT),
    ],
    "BQ3: Regional Revenue Trends": [
        ("Q09", "Revenue by State with Market Share", Q09_REVENUE_BY_STATE),
        ("Q10", "MoM Revenue Growth by State (LAG + Named WINDOW)", Q10_MOM_REVENUE_BY_STATE),
        ("Q11", "Cumulative Revenue by State (Running Total)", Q11_RUNNING_TOTAL_BY_STATE),
        ("Q12", "Freight Efficiency by State (DENSE_RANK)", Q12_FREIGHT_EFFICIENCY_BY_STATE),
    ],
    "BQ4: Product Category Profitability": [
        ("Q13", "Category Revenue, Freight, and Margin Proxy", Q13_CATEGORY_PROFITABILITY),
        ("Q14", "Category Seasonality (Quarterly Revenue)", Q14_CATEGORY_SEASONALITY),
        ("Q15", "Category QoQ Growth (LAG + Named WINDOW)", Q15_CATEGORY_GROWTH),
    ],
    "BQ5: Payment Method Analysis": [
        ("Q16", "Payment Type Breakdown", Q16_PAYMENT_OVERVIEW),
        ("Q17", "Installments vs Order Value Correlation", Q17_INSTALLMENT_VS_ORDER_VALUE),
        ("Q18", "Payment Type by State (Conditional Aggregation)", Q18_PAYMENT_BY_STATE),
    ],
}

# SQL techniques used per query — for the methodology doc and interview prep
TECHNIQUE_MAP = {
    "Q01": ["Multi-table JOIN", "CASE WHEN", "COUNTIF", "Conditional aggregation"],
    "Q02": ["CTE", "DATE_DIFF", "CASE WHEN bucketing", "APPROX_QUANTILES"],
    "Q03": ["CTE", "COUNTIF", "LAG window function", "DATE_TRUNC"],
    "Q04": ["CTE", "DATE_DIFF", "CASE WHEN", "COUNTIF"],
    "Q05": ["4-table JOIN", "QUALIFY", "COUNT DISTINCT", "DATE_DIFF"],
    "Q06": ["3 chained CTEs", "Min-max normalisation in SQL", "NTILE", "Composite scoring", "Named WINDOW"],
    "Q07": ["3 chained CTEs", "NTILE", "Tier aggregation"],
    "Q08": ["CTE", "PERCENT_RANK", "HAVING", "Percentile filtering"],
    "Q09": ["3-table JOIN", "Window SUM for market share", "COUNT DISTINCT"],
    "Q10": ["CTE subquery", "LAG", "SAFE_DIVIDE", "Named WINDOW clause"],
    "Q11": ["CTE", "Running SUM", "ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW"],
    "Q12": ["3-table JOIN", "DENSE_RANK", "Ratio calculation", "DATE_DIFF"],
    "Q13": ["3-table JOIN", "LEFT JOIN", "NULLIF", "HAVING", "Margin proxy"],
    "Q14": ["CTE subquery filter", "EXTRACT YEAR/QUARTER", "4-table JOIN"],
    "Q15": ["CTE", "LAG", "SAFE_DIVIDE", "Named WINDOW", "DATE_TRUNC QUARTER"],
    "Q16": ["Window SUM for share", "Conditional aggregation"],
    "Q17": ["CTE", "CASE WHEN bucketing", "APPROX_QUANTILES median", "MAX aggregation"],
    "Q18": ["3-table JOIN", "COUNTIF pivot", "Conditional percentage"],
}
