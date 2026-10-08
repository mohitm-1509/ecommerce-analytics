# Module 6, Step 1 — Feature Engineering: Methodology

---

## 1. Problem Setup: What Can We Know at Prediction Time?

The model predicts satisfaction **before delivery**. This constraint partitions every column in the dataset into two sets:

```
AVAILABLE at order placement               NOT AVAILABLE (would be data leakage)
──────────────────────────────              ────────────────────────────────────
Seller identity + past history              Actual delivery date
Product details (weight, dims, price)       Whether order was delivered late
Customer state, seller state                Review score (this IS the target)
Payment method + installments               Review text
Estimated delivery date                     Delivery carrier date
Order timestamp (dow, month, hour)
```

Any feature derived from the right column must be excluded. The test for every feature: **"Would an operations team have this number in hand the moment the order is placed?"**

---

## 2. Feature Categories and Justifications

### 2.1 Seller Historical Metrics (5 features)

These are the most powerful features because a seller's past behaviour is the best predictor of their future performance.

| Feature | Definition | Why include |
|---|---|---|
| `seller_prior_order_count` | Orders this seller fulfilled before this order | New sellers with few orders are riskier (less data, less experience) |
| `seller_prior_avg_review` | Avg review score from prior orders | Direct signal of seller quality |
| `seller_prior_avg_delivery_days` | Avg delivery time from prior orders | Slow sellers consistently produce slow deliveries |
| `seller_prior_unsatisfied_rate` | Fraction of prior orders scoring ≤2 | The feature most aligned with the target |
| `seller_prior_late_rate` | Fraction of prior orders delivered late | Late delivery is the #1 driver of dissatisfaction |

### 2.2 Product / Item Features (11 features)

| Feature | Why include |
|---|---|
| `num_items` | Multi-item orders have more points of failure |
| `num_sellers` | Orders split across sellers may have inconsistent quality |
| `total_price` | Higher-value orders carry higher expectations |
| `total_freight` | High freight signals long distance or heavy items |
| `freight_ratio` | Freight as % of price — above ~25% drives dissatisfaction (Module 3 finding) |
| `avg_weight_g` | Heavy items are harder to ship and more prone to damage |
| `avg_volume_cm3` | Bulky items face the same logistics challenges |
| `avg_name_length` | Proxy for product complexity/description quality |
| `avg_desc_length` | Longer descriptions set better expectations → fewer surprises |
| `avg_photos_qty` | More photos = better customer expectations |
| `product_category` | Category of the primary item — some categories (electronics, furniture) have systematically lower satisfaction |

### 2.3 Geographic Features (3 features)

| Feature | Why include |
|---|---|
| `customer_state` | Northern states have longer delivery times and higher freight |
| `seller_state` | São Paulo sellers generally ship faster |
| `is_same_state` | Same-state delivery is typically 3-5 days faster |

### 2.4 Delivery Estimate (1 feature)

| Feature | Why include |
|---|---|
| `estimated_delivery_days` | Set by the system at order time. Long estimates (>20 days) correlate with dissatisfaction even when met |

### 2.5 Time Features (3 features)

| Feature | Why include |
|---|---|
| `order_dow` | Weekend orders may ship later (Monday batch) |
| `order_month` | November–December (holiday season) stress logistics |
| `order_hour` | Late-night orders may indicate impulse purchases |

### 2.6 Payment Features (4 features)

| Feature | Why include |
|---|---|
| `payment_type` | Boleto customers wait for payment confirmation → delayed shipping |
| `max_installments` | High installments correlate with higher AOV and expectations |
| `total_payment` | Total order value (including freight) |
| `num_payment_types` | Multiple payment methods may indicate complex orders |

---

## 3. Seller Historical Metrics: Preventing Data Leakage

### The leakage problem

If we compute seller_avg_review from **all** orders, then for a training order placed in January 2017, we'd be using reviews from February 2017 onwards. The model would "see the future."

### The solution: `ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING`

```sql
WINDOW w_prior AS (
    PARTITION BY primary_seller_id
    ORDER BY order_purchase_timestamp, order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
)
```

This window function computes metrics using **only rows that appear before the current row** in the time-ordered sequence:

```
Seller A orders (time-ordered):
    Order 1 (Jan) → seller_prior_avg_review = NULL  (no prior orders)
    Order 2 (Feb) → seller_prior_avg_review = avg(review of Order 1)
    Order 3 (Mar) → seller_prior_avg_review = avg(reviews of Orders 1,2)
    Order 4 (Apr) → seller_prior_avg_review = avg(reviews of Orders 1,2,3)
```

### Why `order_id` as a secondary sort key

If two orders from the same seller have identical timestamps (unlikely but possible), the window function needs a deterministic tiebreaker. `order_id` (a UUID) provides this. Without it, the database could include or exclude tied rows non-deterministically, introducing random leakage.

### Cold-start: first orders have NULL seller metrics

A seller's first order has no prior data. The 4 rate/average seller features (`seller_prior_avg_review`, `seller_prior_avg_delivery_days`, `seller_prior_unsatisfied_rate`, `seller_prior_late_rate`) will be NULL, while `seller_prior_order_count` will be 0 (COUNT returns 0 for an empty window frame). This is correct and realistic — in production, new sellers have no track record.

We handle NULLs in Step 2 (median imputation). The 0 count directly signals "new seller" to the model, while the imputed rates default to the training-set median.

### Production note

In a real system, seller metrics would be updated daily or weekly (not per-order). Our per-order window functions are more precise than production would be, which means our model's performance is slightly optimistic. The methodology doc acknowledges this.

---

## 4. Named WINDOW Clause

We reuse the same window specification 5 times (one for each seller metric). Instead of repeating the full `OVER(PARTITION BY ... ORDER BY ... ROWS BETWEEN ...)` clause 5 times, we use a Named WINDOW:

```sql
WINDOW w_prior AS (
    PARTITION BY c.primary_seller_id
    ORDER BY c.order_purchase_timestamp, c.order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
)
```

Benefits:
1. **DRY**: one definition, five references
2. **Optimisation**: BigQuery can recognise that all five functions share the same partitioning and make a single pass
3. **Consistency**: impossible to accidentally use a different sort order for one of the five

---

## 5. Primary Seller Selection

An order can contain items from multiple sellers. For seller historical metrics, we need one seller per order. We choose the **primary seller** — the seller with the highest-priced item:

```sql
ARRAY_AGG(oi.seller_id ORDER BY oi.price DESC LIMIT 1)[OFFSET(0)]
    AS primary_seller_id
```

### Why highest price, not most items?

Price is a better proxy for "which seller matters most to this customer's experience." A R$500 electronics item from Seller A and a R$5 accessory from Seller B — the customer's satisfaction is dominated by Seller A.

### Alternative: weighted average across all sellers

We could compute a price-weighted average of all sellers' metrics. This is more precise but adds significant SQL complexity for marginal gain. In the Olist dataset, 93% of orders have a single seller, so the primary-seller approach is correct for the vast majority of cases.

---

## 6. Review Deduplication

An order can have multiple reviews in the `order_reviews` table (e.g., a customer updates their review). A naive JOIN would produce duplicate rows — same order, same features, potentially different review scores — which inflates the dataset and creates conflicting training labels.

We deduplicate by picking the **latest review** per order:

```sql
JOIN (
    SELECT order_id, review_score,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY review_creation_date DESC) AS rn
    FROM order_reviews
    WHERE review_score IS NOT NULL
) r ON o.order_id = r.order_id AND r.rn = 1
```

This ensures exactly one row per order and uses the customer's most recent sentiment.

---

## 7. Target Variable: Binary vs Multiclass

### Decision: Binary classification (is_unsatisfied: review ≤ 2 vs ≥ 3)

### Why not multiclass (predict 1, 2, 3, 4, or 5)?

```
Multiclass                              Binary
5 classes, boundaries between           2 classes, one boundary
adjacent scores are blurry              at a meaningful threshold

Class confusion matrix:                 Class confusion matrix:
    1 vs 2: nearly identical signals        Unsatisfied vs Satisfied:
    4 vs 5: nearly identical signals        distinct behaviours

5 × more parameters to learn            Simple, well-studied
Needs ordinal handling or                Standard binary classifiers
    5 one-vs-rest classifiers            work out of the box
```

### Why cut at ≤ 2 (not ≤ 3)?

| Threshold | Unsatisfied % | Label |
|---|---|---|
| ≤ 1 | ~11% | Too strict — 2-star reviews also signal problems |
| **≤ 2** | **~13%** | **Captures clearly negative reviews** |
| ≤ 3 | ~25% | Too loose — 3-star reviews are neutral, not dissatisfied |

Review score 3 is ambiguous: "It was OK." Scores 1-2 are unambiguous: "It was bad." We model the clearly actionable signal.

---

## 8. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Feature engineering | 27 features from 6 tables, with clear reasoning |
| Data leakage prevention | Temporal window functions, feature availability analysis |
| SQL proficiency | CTEs, ARRAY_AGG, SAFE_DIVIDE, Named WINDOW, window frames |
| Domain understanding | Features mapped to business mechanisms |
| Production thinking | Cold-start handling, primary seller selection |
