# Module 3 — Core Business Analysis: Methodology

This document explains every SQL technique choice, why these 5 business questions, and the mathematical reasoning behind the analytical methods used in all 18 queries.

---

## 1. Why These 5 Business Questions?

We reverse-engineered the questions from **what Olist's management can control**:

| Business Lever | Who Owns It | Question |
|---|---|---|
| Logistics / shipping | Operations | BQ1: Delivery impact on satisfaction |
| Seller onboarding & quality | Marketplace team | BQ2: Seller segmentation |
| Regional expansion | Growth / Marketing | BQ3: Regional revenue trends |
| Product mix / catalogue | Merchandising | BQ4: Category profitability |
| Checkout / payment UX | Product team | BQ5: Payment method analysis |

Each question maps to a **specific team** and a **specific action they can take**. This is the difference between "I analysed data" and "I informed a business decision."

### Why not other questions?

| Rejected Question | Why Rejected |
|---|---|
| Customer Lifetime Value (CLV) | ~97% single-purchase customers. CLV models need repeat behaviour. |
| Cart abandonment / funnel | Dataset only contains completed orders. No funnel data. |
| Pricing elasticity | No A/B test data. Can't separate price effect from other factors. |
| Customer demographics | No age, gender, income data. |
| Competitor analysis | Single-marketplace dataset. No competitor data. |

---

## 2. SQL Technique Selection — Why Each Technique?

### 2a. QUALIFY vs Subquery for Window Function Filtering

**Traditional approach (works everywhere):**
```sql
SELECT * FROM (
    SELECT *, RANK() OVER (ORDER BY score) AS rnk
    FROM sellers
) sub
WHERE rnk <= 10
```

**BigQuery QUALIFY approach (used in Q05, Q08):**
```sql
SELECT *, RANK() OVER (ORDER BY score) AS rnk
FROM sellers
QUALIFY RANK() OVER (ORDER BY score) <= 10
```

**Why QUALIFY is superior:**

1. **One fewer nesting level**: The subquery approach wraps the entire SELECT in another SELECT. Each nesting level adds cognitive load. QUALIFY keeps the query flat.

2. **SQL execution order clarity**:
```
FROM → WHERE → GROUP BY → HAVING → WINDOW → QUALIFY → ORDER BY → LIMIT

QUALIFY sits after WINDOW, exactly where you want to filter window results.
HAVING filters GROUP BY results.
WHERE filters row-level conditions.
```

3. **Performance**: BigQuery's optimizer handles QUALIFY natively. The subquery approach may materialise the inner result set before filtering. QUALIFY can fuse the filter with the window computation.

4. **Interview signal**: QUALIFY is BigQuery/Snowflake-specific. Using it shows you know the platform, not just generic SQL.

---

### 2b. Named WINDOW Clause vs Repeated OVER()

**Without named WINDOW (Q03):**
```sql
SELECT
    late_pct,
    LAG(late_pct) OVER (ORDER BY order_month)           AS prev,
    late_pct - LAG(late_pct) OVER (ORDER BY order_month) AS delta
FROM monthly
```

**With named WINDOW (Q10, Q15):**
```sql
SELECT
    revenue,
    LAG(revenue) OVER w           AS prev_revenue,
    SAFE_DIVIDE(revenue - LAG(revenue) OVER w, LAG(revenue) OVER w) AS growth
FROM monthly_rev
WINDOW w AS (PARTITION BY state ORDER BY order_month)
```

**Why named WINDOW:**

1. **DRY principle**: The same `PARTITION BY state ORDER BY order_month` would be written 3 times without the named window. If the partitioning logic changes, you update one line instead of three.

2. **BigQuery optimisation**: When multiple window functions share the same WINDOW definition, BigQuery can compute them in a single pass over the data. With separate OVER() clauses, the optimizer must determine they're equivalent — named WINDOW makes this explicit.

3. **Readability**: `OVER w` is 6 characters. `OVER (PARTITION BY state ORDER BY order_month)` is 50 characters. Multiply by 3 columns and the query becomes wall-of-text.

**When NOT to use named WINDOW**: When you have only one window function in the query (Q03). The named window adds a line without reducing repetition.

---

### 2c. LAG vs Self-JOIN for Period-over-Period Comparison

**Self-JOIN approach:**
```sql
SELECT
    curr.month, curr.revenue,
    prev.revenue AS prev_revenue,
    (curr.revenue - prev.revenue) / prev.revenue * 100 AS growth
FROM monthly curr
LEFT JOIN monthly prev
    ON curr.state = prev.state
    AND curr.month = DATE_ADD(prev.month, INTERVAL 1 MONTH)
```

**LAG approach (chosen, Q03/Q10/Q15):**
```sql
SELECT
    month, revenue,
    LAG(revenue) OVER (PARTITION BY state ORDER BY month) AS prev_revenue
FROM monthly
```

**Why LAG is superior:**

1. **No self-JOIN**: Self-JOIN doubles the data scanned. BigQuery charges per byte scanned. LAG scans the table once.

```
Self-JOIN:  Bytes scanned = 2 × table_size (both copies)
LAG:        Bytes scanned = 1 × table_size

For monthly_rev with ~500 rows: negligible difference.
For a production table with 100M rows: 2× cost.
```

2. **Handles gaps automatically**: If a state has no orders in March, the self-JOIN on `month = DATE_ADD(prev.month, INTERVAL 1 MONTH)` produces NULL for March (correct) but also skips April's comparison to February. LAG with `ORDER BY month` compares April to February directly — it looks back one **row**, not one **calendar month**.

   This is actually a design choice. For this project, comparing to the previous available month is the right behaviour (we want to see recovery after a gap).

3. **Readability**: LAG(revenue) reads as "the previous revenue." The self-JOIN requires mentally tracing the join condition.

---

### 2d. NTILE vs Hard-Coded Thresholds for Segmentation

**Hard-coded thresholds:**
```sql
CASE
    WHEN total_revenue >= 10000 AND avg_review >= 4.0 THEN 'Gold'
    WHEN total_revenue >= 5000  AND avg_review >= 3.5 THEN 'Silver'
    ELSE 'Bronze'
END
```

**NTILE approach (chosen, Q06/Q07):**
```sql
NTILE(3) OVER (ORDER BY composite_score DESC)
```

**Why NTILE:**

1. **Data-driven boundaries**: Hard-coded thresholds are arbitrary. Why R$10,000 and not R$8,000? NTILE divides sellers into equal groups based on the actual distribution, so the boundaries adapt to the data.

2. **Guaranteed balanced groups**: NTILE(3) produces groups of size ⌊n/3⌋ or ⌈n/3⌉. Hard-coded thresholds can produce 5 Gold sellers and 500 Bronze sellers if the thresholds are poorly chosen.

3. **Composability**: NTILE works on any numeric score. If we change the weighting formula, the tiers adjust automatically. Hard-coded thresholds need manual recalibration.

**When hard-coded IS better**: When the business has established benchmarks (e.g., "SLA is 5 days, anything over is late"). In that case, the threshold has business meaning. For seller tiers, no such benchmark exists — we're discovering segments, not enforcing standards.

---

## 3. Composite Scoring — Mathematical Foundation (Q06)

### The Problem

Sellers have multiple performance dimensions:
- Revenue (higher = better)
- Average review score (higher = better)  
- Average delivery days (lower = better)

These metrics are on different scales:
```
Revenue:        R$100 — R$200,000   (range: 199,900)
Review score:   1.0 — 5.0           (range: 4.0)
Delivery days:  3 — 45              (range: 42)
```

You cannot simply average them: revenue would dominate because its range is 50,000× larger.

### Solution: Min-Max Normalisation + Weighted Sum

**Step 1: Min-Max Normalisation**

For each metric, transform values to the [0, 1] range:

```
x_normalised = (x - x_min) / (x_max - x_min)

Properties:
    - x_min maps to 0
    - x_max maps to 1
    - Linear transformation: preserves relative ordering
    - Scale-invariant: all metrics now on [0, 1]
```

**For delivery days (lower is better), invert:**
```
speed_normalised = 1 - (days - days_min) / (days_max - days_min)

This maps:
    fastest seller (days_min) → 1.0
    slowest seller (days_max) → 0.0
```

**Step 2: Weighted Sum**

```
composite = w₁ × norm_revenue + w₂ × norm_review + w₃ × norm_speed
```

**Why these weights: 0.4, 0.4, 0.2?**

| Weight | Metric | Justification |
|---|---|---|
| 0.4 | Revenue | Direct business value. Top-line contribution. |
| 0.4 | Review score | Customer satisfaction. Drives retention and platform reputation. |
| 0.2 | Delivery speed | Important but partially outside seller control (carrier, distance). |

Revenue and review are weighted equally because:
- A high-revenue seller with terrible reviews damages the brand (long-term loss exceeds short-term revenue)
- A high-review seller with low revenue still has unrealised potential (could scale with marketing support)

Delivery speed gets lower weight because:
- Sellers control packaging/dispatch time but not carrier transit time
- Regional distance effects are unfair to sellers far from customers
- It's already partially captured in review score (late delivery → bad review)

**Why not equal weights (⅓, ⅓, ⅓)?**

Equal weighting assumes all metrics are equally important AND equally actionable. Delivery speed is less actionable by the seller, so weighting it equally would penalise sellers in remote states for geography rather than performance.

### Alternative: Z-Score Normalisation (Standardisation)

```
z = (x - μ) / σ
```

**Why not chosen:**
- Z-scores produce negative values and values > 1, making the composite score harder to interpret
- Z-scores assume normally distributed data. Revenue is heavily right-skewed (few high-revenue sellers)
- Min-max is more intuitive: "this seller is at 0.75 out of 1.0" is clearer than "this seller is at z = 0.82"

### Alternative: Rank-Based Normalisation (PERCENT_RANK)

```
PERCENT_RANK() OVER (ORDER BY revenue)
```

**Why not chosen for the composite (but used in Q08):**
- PERCENT_RANK discards magnitude: a seller with R$100K revenue and one with R$200K revenue might have ranks 0.95 and 0.96 — nearly identical despite 2× the revenue
- For the composite score, we want magnitude to matter: a seller with twice the revenue should score higher on the revenue dimension
- We DO use PERCENT_RANK in Q08 for identifying the bottom 5% — there, rank position is exactly what we need

---

## 4. SAFE_DIVIDE — Why Not Regular Division? (Q10, Q15)

```sql
-- Crashes if prev_revenue = 0:
(revenue - prev_revenue) / prev_revenue

-- Returns NULL if prev_revenue = 0:
SAFE_DIVIDE(revenue - prev_revenue, prev_revenue)
```

A new state with zero revenue in its first month would cause a division-by-zero error. `SAFE_DIVIDE` is BigQuery-specific and returns NULL instead of failing.

**Why not NULLIF?**

```sql
(revenue - prev_revenue) / NULLIF(prev_revenue, 0)
```

This is the portable alternative (works in PostgreSQL, MySQL, etc.). We use `SAFE_DIVIDE` because:
1. It's the BigQuery idiom — shows platform knowledge
2. More readable: `SAFE_DIVIDE(a, b)` vs `a / NULLIF(b, 0)`
3. Handles edge cases including NaN and Infinity

---

## 5. DATE_TRUNC vs EXTRACT vs FORMAT_TIMESTAMP

Three ways to aggregate by time period:

| Function | Output | Use Case |
|---|---|---|
| `DATE_TRUNC(date, MONTH)` | `2017-03-01` (DATE) | When you need a sortable date for ORDER BY and LAG |
| `EXTRACT(MONTH FROM ts)` | `3` (INTEGER) | When you need the component (month number, quarter number) |
| `FORMAT_TIMESTAMP('%Y-%m', ts)` | `'2017-03'` (STRING) | When you need a display label |

**Our usage:**
- **Q03, Q10, Q11**: `DATE_TRUNC` — because LAG needs a sortable date value to look back one row correctly. A string `'2017-03'` sorts correctly, but an integer `3` wraps around (December 12 → January 1 wouldn't be adjacent).
- **Q14**: `EXTRACT(YEAR, QUARTER)` — because we're comparing quarters across years, so we need year and quarter as separate columns.

---

## 6. Margin Proxy — Why `price - freight_value`? (Q13)

**True profit margin:**
```
Margin = Revenue - COGS - Freight - Platform Fee - Returns - ...
```

We don't have COGS (cost of goods sold), platform fees, or return data. So we compute a **proxy**:

```
Margin Proxy = price - freight_value
```

This is NOT actual profit. It measures **how much of the customer's payment goes to product value vs shipping**. A category where freight is 40% of price is structurally less profitable than one where freight is 5%.

**Why this is still useful:**
- Identifies categories where freight is eating revenue (heavy items like furniture)
- Guides the "should we subsidise freight?" decision
- Relative comparison between categories is valid even without COGS

**What we explicitly state in the output:** This is a margin proxy, not actual margin. COGS data is not available.

---

## 7. Filter Choices — Why `order_status = 'delivered'`?

The orders table includes multiple statuses:

```
delivered:     ~97%
shipped:       ~1%
canceled:      ~0.6%
unavailable:   ~0.1%
processing:    ~0.1%
...
```

**For revenue queries (Q09-Q15):** We filter to `delivered` because:
- Revenue should only count completed transactions
- Cancelled orders didn't generate actual revenue
- "Shipped" orders haven't been confirmed received

**For delivery queries (Q01-Q04):** We filter to `order_delivered_customer_date IS NOT NULL` because:
- We need the actual delivery date to compute delivery time
- This is more precise than `order_status = 'delivered'` (catches edge cases where status might be inconsistent)

**For payment queries (Q16-Q18):** We don't filter by status because:
- Payment was made regardless of delivery outcome
- Cancelled-after-payment orders are interesting for payment analysis (refund patterns)

---

## 8. Aggregation Level — Why Monthly? (Q03, Q10, Q11)

| Level | Rows per state | Noise | Signal |
|---|---|---|---|
| Daily | ~750 per state | Very high (weekday/weekend, random variation) | Hidden in noise |
| Weekly | ~107 per state | Moderate | Visible but noisy |
| **Monthly** | ~25 per state | Low | Clear trends |
| Quarterly | ~8 per state | Very low | Too few points for trend analysis |

**Why monthly is optimal:**

The dataset spans ~25 months (Sep 2016 - Oct 2018). Monthly aggregation gives:
- Enough data points for LAG comparisons (24+ periods)
- Smooth enough to see trends without moving averages
- Standard business reporting cadence (monthly reviews are universal)

Daily aggregation for 27 states × 750 days = 20,250 rows — too noisy for a dashboard. Quarterly gives only 8 points — too few for meaningful LAG (only 7 QoQ comparisons).

**Mathematical justification (Central Limit Theorem):**

With ~4,000 orders/month nationally, and ~25 states, the average state has ~160 orders/month. The standard error of the monthly mean decreases with √n:

```
SE = σ / √n

At n = 160 orders/month:  SE = σ / √160 ≈ σ / 12.6
At n = 5 orders/day:      SE = σ / √5   ≈ σ / 2.2

Monthly means are ~5.7× more precise than daily means.
```

This means monthly aggregation reduces sampling noise by a factor of ~6, making trends visible that would be invisible at the daily level.

---

## 9. SQL Technique Coverage Summary

| Technique | Queries | Total Uses |
|---|---|---|
| Multi-table JOIN (3-5 tables) | Q05, Q06, Q07, Q08, Q09, Q10, Q12, Q13, Q14, Q15, Q18 | 11 |
| CTE (WITH clause) | Q02, Q03, Q04, Q06, Q07, Q08, Q10, Q11, Q15, Q17 | 10 |
| Window: LAG | Q03, Q10, Q15 | 3 |
| Window: NTILE | Q06, Q07 | 2 |
| Window: RANK / DENSE_RANK | Q12 | 1 |
| Window: PERCENT_RANK | Q08 | 1 |
| Window: Running SUM | Q11 | 1 |
| Window: SUM for shares | Q09, Q16 | 2 |
| Named WINDOW clause | Q10, Q15 | 2 |
| QUALIFY | Q05 | 1 |
| SAFE_DIVIDE | Q10, Q15 | 2 |
| COUNTIF | Q01, Q02, Q03, Q04, Q18 | 5 |
| CASE WHEN bucketing | Q01, Q02, Q04, Q06, Q07, Q17 | 6 |
| DATE_TRUNC | Q03, Q10, Q11, Q15 | 4 |
| EXTRACT | Q14 | 1 |
| DATE_DIFF | Q02, Q04, Q05, Q06, Q07, Q12 | 6 |
| APPROX_QUANTILES | Q02, Q17 | 2 |
| HAVING | Q06, Q07, Q08, Q13, Q15 | 5 |
| Subquery in WHERE | Q10, Q14 | 2 |

**18 queries demonstrating 19 distinct SQL techniques.** This covers the full range of what UK DA/DS roles test for in SQL assessments.

---

## 10. What This Module Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| SQL fluency | 18 queries spanning simple aggregation to multi-CTE window function chains |
| Business translation | 5 real questions → specific, actionable analysis |
| BigQuery-specific knowledge | QUALIFY, SAFE_DIVIDE, APPROX_QUANTILES, Named WINDOW, COUNTIF |
| Analytical thinking | Not just "here are numbers" but "here's why late delivery causes 2× more 1-star reviews" |
| Data modelling | Joins across 4-5 tables correctly, handles cardinality, avoids fan-out |
| Communication | Query names and comments explain the business purpose, not just the SQL |
