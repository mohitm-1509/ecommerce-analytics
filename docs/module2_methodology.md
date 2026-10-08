# Module 2 — Data Exploration & Quality Audit: Methodology

This document explains every technical decision in Module 2, why each profiling method was chosen, and the mathematical foundations behind the statistical checks.

---

## 1. Why SQL-Based Profiling over Pandas / ydata-profiling?

### Alternatives considered

| Method | Pros | Cons |
|---|---|---|
| **BigQuery SQL (chosen)** | Data stays server-side. Demonstrates SQL. Queries are versionable. | More verbose than pandas one-liners |
| `pandas` (`.describe()`, `.info()`, `.isnull()`) | Quick for small datasets. Familiar. | Must download all data locally. 1M-row geolocation table ≈ 200 MB in pandas memory. Doesn't show SQL skill. |
| `ydata-profiling` (formerly pandas-profiling) | Auto-generates HTML report with correlations | Black box — interviewer can't see your SQL. Heavy dependency (~15 packages). Profile of 1M rows can take 10+ minutes. |
| `great_expectations` | Industry-standard data validation framework | Enterprise tool — overkill for a portfolio project. Complex YAML config. Hides the actual SQL. |

### Decision rationale

**The primary goal of this project is to demonstrate SQL proficiency.** Writing profiling queries by hand shows the interviewer:
1. You understand `GROUP BY`, `HAVING`, `COUNTIF`, `APPROX_QUANTILES`, window functions
2. You can translate a data quality question into SQL
3. You don't need a library to understand your data

**Memory comparison:**

```
SQL approach:
    Data location:  BigQuery server (Google's infrastructure)
    Local memory:   O(result_set) ≈ kilobytes (aggregated results only)
    Network:        Sends query text (< 1 KB), receives aggregated rows (< 10 KB)

pandas approach:
    geolocation table alone:
        CSV on disk:    ~30 MB
        pandas DataFrame: ~200 MB (Python object overhead per cell)
            5 columns × 1,000,163 rows × ~40 bytes/cell ≈ 200 MB
    All 9 tables:       ~500-700 MB in memory

ydata-profiling:
    Memory:     3-5× the DataFrame size (internal copies for correlation, histograms)
    geolocation: ~600 MB - 1 GB during profiling
```

For a dataset with 1M+ rows in one table, SQL is not just cleaner — it's the only approach that doesn't require thinking about memory management.

---

## 2. The Six Profiling Categories — Why These Six?

Data quality is measured across well-established dimensions. The standard framework used in data engineering (documented by DAMA International and adopted by tools like Great Expectations, dbt-expectations, and Monte Carlo) defines six core dimensions:

| Dimension | What it measures | Our SQL check |
|---|---|---|
| **Completeness** | Are values present where expected? | Null analysis per column |
| **Uniqueness** | Are records properly deduplicated? | PK duplicate detection |
| **Validity** | Do values fall within expected ranges? | Numeric summaries + outlier detection |
| **Consistency** | Do related tables agree? | Referential integrity (Module 1) |
| **Timeliness** | Is data current? | Date range analysis |
| **Distribution** | Does the data match expected patterns? | Categorical & numeric distributions |

We don't invent categories — we follow the industry standard and implement each one as SQL.

---

## 3. Null Analysis — Methodology

### What we compute

For every column in every table:
```
null_count = COUNTIF(column IS NULL)
null_pct   = null_count / COUNT(*) × 100
```

### Why `COUNTIF(col IS NULL)` over `COUNT(*) - COUNT(col)`?

Both produce identical results. `COUNTIF` is preferred because:

1. **Readability**: `COUNTIF(col IS NULL)` reads as English — "count if column is null"
2. **BigQuery optimization**: `COUNTIF` is a BigQuery-native function that the query optimizer handles as a single pass, whereas `COUNT(*) - COUNT(col)` requires two separate aggregations

Mathematically equivalent proof:
```
Let N = total rows, N_valid = non-null rows, N_null = null rows
N = N_valid + N_null

Method A: COUNTIF(IS NULL)     = N_null
Method B: COUNT(*) - COUNT(col) = N - N_valid = N_null  ✓
```

### How to interpret null percentages

| Null % | Interpretation | Action |
|---|---|---|
| 0% | Complete | No action needed |
| 0-5% | Minor gaps | Acceptable for most analyses; note in documentation |
| 5-30% | Significant missingness | Investigate cause; consider imputation or exclusion |
| 30%+ | Structurally optional | Column is likely optional by design (e.g., review comments) |

### Expected findings in Olist

- `order_approved_at`: ~0.16% null — orders placed but payment not yet approved
- `order_delivered_carrier_date`: ~1.78% null — orders not yet shipped
- `order_delivered_customer_date`: ~3.16% null — orders not yet delivered (includes cancelled/processing)
- `review_comment_title`: ~87% null — most customers skip the title field
- `review_comment_message`: ~58% null — many customers skip the comment
- `product_category_name`: ~0.29% null — some products have no category

These nulls are **not errors** — they reflect the natural lifecycle of an order (not all orders reach delivery) and optional form fields (not all customers write reviews). The profiling report flags them so we can make informed decisions in Module 3.

---

## 4. Duplicate Detection — Methodology

### Primary key uniqueness check

For each table with a defined primary key:
```sql
SELECT pk_col, COUNT(*) AS cnt
FROM table
GROUP BY pk_col
HAVING COUNT(*) > 1
```

If this returns 0 rows, the PK is unique. If it returns rows, we have a data quality issue.

**Expected result:** All PKs should be unique in the Olist dataset. The one exception is geolocation.

### The Geolocation Problem

The `geolocation` table has **~1M rows but only ~19K unique zip codes**. This means:

```
Duplication ratio = total_rows / distinct_zip_codes
                  = 1,000,163 / ~19,015
                  ≈ 52.6 rows per zip code
```

**Why does this happen?**
Each zip code has multiple GPS readings (from different devices, at different times). These readings cluster around the same point but aren't identical.

**Why it matters for analysis:**
If you JOIN `orders → customers → geolocation` on `zip_code_prefix`, each customer row fans out to ~52 geolocation rows. This causes:
- `COUNT(*)` to be inflated by 52×
- `SUM(price)` to be inflated by 52×
- Revenue reports to be wildly wrong

**Deduplication strategy (documented here, applied in Module 3):**
```sql
-- Take the median lat/lng per zip code (robust to outlier readings)
SELECT
    geolocation_zip_code_prefix,
    APPROX_QUANTILES(geolocation_lat, 2)[OFFSET(1)]  AS lat,
    APPROX_QUANTILES(geolocation_lng, 2)[OFFSET(1)]  AS lng,
    ANY_VALUE(geolocation_city)                       AS city,
    ANY_VALUE(geolocation_state)                      AS state
FROM geolocation
GROUP BY geolocation_zip_code_prefix
```

Why **median** over mean?
- Mean is sensitive to outlier GPS readings (a single incorrect reading of lat=0 pulls the centroid toward the equator)
- Median is robust: `breakdown_point = 50%` — half the data must be corrupted to move the median
- For a cluster of GPS readings around a true location, median ≈ true location

Mathematical robustness:
```
Let x₁, x₂, ..., xₙ be GPS readings sorted by latitude.
Median = x_{⌈n/2⌉}

If one reading is corrupted: x₁ = 0 (equator instead of São Paulo ≈ -23.5°)
    Mean shifts:  Δmean = (0 - x₁_true) / n → can be significant if n is small
    Median:       unchanged (same middle element, unless n < 3)

Breakdown point:
    Mean:   1/n  (one corrupted point moves the estimate)
    Median: ⌊(n-1)/2⌋/n ≈ 50%  (half the data must be corrupted)
```

---

## 5. Distribution Analysis — Why These Distributions?

### Categorical distributions

We profile categorical columns that will be used as **dimensions** (GROUP BY targets) or **filters** (WHERE conditions) in Module 3:

| Column | Why profile it? |
|---|---|
| `order_status` | Need to know if we should filter to "delivered" only, or include all statuses |
| `payment_type` | Business question 5 depends on payment type distribution |
| `review_score` | Business question 1 (delivery → satisfaction) uses this as the outcome variable |
| `product_category_name` | Business question 4 (category profitability) groups by this |
| `customer_state` / `seller_state` | Business question 3 (regional trends) groups by these |

We DON'T profile every column's distribution — only the ones we'll actually use. Profiling `customer_id` distribution is meaningless (each value appears once).

### Numeric 5-number summary

For each numeric column, we compute the **5-number summary** plus mean and standard deviation:

```
{min, Q1, median, Q3, max}  +  {mean, stddev}
```

**Why the 5-number summary over just mean/stddev?**

Mean and standard deviation assume a symmetric (roughly normal) distribution. E-commerce price data is **right-skewed** (many cheap items, few expensive ones):

```
Price distribution (expected shape):

Frequency
    │ ██
    │ ████
    │ ██████
    │ ████████
    │ ██████████
    │ ████████████
    │ ██████████████
    │ ████████████████
    │ ████████████████████
    │ ████████████████████████████████████·····
    └──────────────────────────────────────────── Price
    $0          $100         $500        $6735

    mean ≈ R$120   (pulled right by expensive items)
    median ≈ R$100 (more representative of "typical" order)
```

For skewed distributions:
- **Median** is a better measure of central tendency than mean
- **Q1-Q3 (IQR)** is a better measure of spread than standard deviation
- **Min/Max** reveal the range (and potential data entry errors)

We report both (5-number + mean/stddev) so the reader can compare and infer skewness:
```
If mean > median → right-skewed (common for prices, weights)
If mean ≈ median → approximately symmetric
If mean < median → left-skewed (rare in this dataset)
```

### `APPROX_QUANTILES` vs `PERCENTILE_CONT`

BigQuery offers two functions for percentile calculation:

| Function | How it works | Performance |
|---|---|---|
| `APPROX_QUANTILES(x, 4)` | Uses the **KLL sketch** algorithm (Karnin, Lang, Liberty 2016). Space complexity: O(1/ε × log(εn)). Returns approximate quantiles. | Fast: single pass, O(n) time, O(log n) space |
| `PERCENTILE_CONT(0.5) OVER()` | Sorts all values, picks exact percentile. | Slow: requires full sort, O(n log n) time, O(n) space |

For the Olist dataset:
```
geolocation table: n = 1,000,163 rows

APPROX_QUANTILES:  ~1 second  (single pass, no sort)
PERCENTILE_CONT:   ~5 seconds (full sort of 1M values)
```

**Accuracy of APPROX_QUANTILES:**
The KLL sketch guarantees that the returned quantile rank is within ε of the true rank. For BigQuery's implementation, ε ≈ 0.01, meaning:
```
If true median is at rank 500,000 out of 1,000,000
Approximate median is at rank 500,000 ± 10,000
```

For our use case (profiling, not billing), this accuracy is more than sufficient. We use `APPROX_QUANTILES` for all percentile calculations.

---

## 6. Outlier Detection — IQR Method

### Why IQR over Z-Score?

Two standard methods for outlier detection:

| Method | Formula | Assumption |
|---|---|---|
| **Z-Score** | z = (x - μ) / σ; outlier if \|z\| > 3 | Data is normally distributed |
| **IQR** (chosen) | Outlier if x < Q1 - 1.5×IQR or x > Q3 + 1.5×IQR | No distributional assumption |

**Z-Score fails for skewed data:**

```
Example: Olist item prices
    Most prices: R$10 - R$200
    Some prices: R$1,000 - R$6,735
    
    mean (μ) = R$120.65
    stddev (σ) = R$183.63  (inflated by the right tail)
    
    Z-score threshold: μ + 3σ = 120.65 + 3(183.63) = R$671.54
    
    Problem: A R$500 item (genuinely expensive but not unreasonable) 
    has z = (500 - 120.65) / 183.63 = 2.07 → NOT flagged
    But σ itself is inflated by the outliers we're trying to detect.
    This is circular: outliers inflate σ, which raises the threshold,
    which hides the outliers.
```

This is called the **masking effect**: extreme outliers inflate σ, causing moderate outliers to appear normal.

**IQR is robust to this:**
```
Q1 and Q3 are resistant to extreme values (breakdown point ≈ 25%)

IQR = Q3 - Q1 (the middle 50% of data)
Lower = Q1 - 1.5 × IQR
Upper = Q3 + 1.5 × IQR
```

The 1.5 multiplier comes from John Tukey's original work (Exploratory Data Analysis, 1977). For normally distributed data:
```
Q1 ≈ μ - 0.6745σ
Q3 ≈ μ + 0.6745σ
IQR ≈ 1.349σ

Upper fence = Q3 + 1.5 × IQR
            = (μ + 0.6745σ) + 1.5(1.349σ)
            = μ + 2.698σ

This corresponds to ≈ 0.7% of data outside the upper fence
(for normally distributed data), which matches the common
definition of "unusual but not impossible" observations.
```

For our **skewed** price data, IQR adapts automatically:
```
If prices are clustered between R$20 and R$200:
    Q1 ≈ R$40,  Q3 ≈ R$150
    IQR = R$110
    Upper fence = R$150 + 1.5(110) = R$315
    
    → Items above R$315 are flagged for investigation
    → This is a reasonable threshold for "unusually expensive"
```

### What we do with outliers

We **flag, not remove**. Outliers in e-commerce data often represent:
- Legitimate high-value purchases (electronics, furniture)
- Data entry errors (price = R$0.01, freight = R$400)
- Bulk orders

Module 3 queries will handle outliers case-by-case:
- Revenue totals: include all (outliers are real revenue)
- Averages for customer analysis: use MEDIAN or trim extremes
- Delivery time analysis: cap at 60 days (orders beyond that are likely data issues)

---

## 7. Temporal Analysis — Why These Date Checks?

### Order date range

We verify the data spans **September 2016 to October 2018** (as documented on Kaggle). If the date range is different, either:
- We loaded the wrong dataset version
- Timestamp parsing failed during load (dates might be STRING "2017-01-01" instead of TIMESTAMP)

### Orders per month

Monthly aggregation reveals:
1. **Seasonality** — are there holiday spikes? (Black Friday in November, Christmas)
2. **Growth trajectory** — is Olist growing month-over-month?
3. **Data completeness** — a month with suspiciously few orders suggests missing data

### Delivery time statistics

Delivery performance is the basis of Business Question 1 (Module 3). We need to understand the baseline:
- Average delivery time (to set expectations)
- Late delivery percentage (the core metric)
- Min/max delivery days (to catch impossible values like negative days or 365+ days)

---

## 8. Repeat Customer Analysis — Why It Matters

The Olist dataset has a known characteristic: **~97% of customers buy only once**. This is critical because:

1. **CLV models won't work** — you need repeat purchases to model lifetime value
2. **Retention analysis is limited** — "repeat purchase rate" is the only retention metric available
3. **The ~3% repeat buyers are disproportionately valuable** — worth segmenting in Module 7

We compute this in Module 2 (not Module 3) because it's a **data characteristic**, not a business insight. It shapes which analyses are possible.

Note on `customer_id` vs `customer_unique_id`:
```
customer_id:        unique per order (same customer can have different IDs across orders)
customer_unique_id: unique per person (stable across orders)

To count repeat purchases, we GROUP BY customer_unique_id, not customer_id.
Using customer_id would show 0% repeat rate (every ID appears once by definition).
```

---

## 9. Query Organisation — Why Separate `eda_queries.py`?

### Alternatives

| Approach | Trade-off |
|---|---|
| **SQL in separate file (chosen)** | Queries are readable, diffable, reusable. Can be copied to BigQuery console for ad-hoc runs. |
| SQL embedded in Python strings inline | Hard to read. No syntax highlighting. Mixing logic with presentation. |
| `.sql` files on disk | Clean separation but requires file I/O to load. Harder to parameterise. |
| ORM (SQLAlchemy / ibis) | Abstracts away the SQL — defeats the purpose of demonstrating SQL skill. |

We chose **SQL as Python constants in a dedicated module** because:
1. Queries get Python string formatting (`{dataset}`, `{table}`) for parameterisation
2. They're importable from other modules
3. The Python file is version-controlled with the rest of the project
4. An interviewer can read `eda_queries.py` and see pure SQL without Python noise

---

## 10. What This Module Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| SQL proficiency | 15+ distinct query patterns (COUNTIF, APPROX_QUANTILES, window functions, CTEs, CROSS JOIN) |
| Data quality thinking | Systematic 6-dimension profiling framework |
| Statistical foundations | IQR vs Z-Score reasoning, median vs mean for skewed data, breakdown point analysis |
| BigQuery-specific knowledge | INFORMATION_SCHEMA, __TABLES__, APPROX_QUANTILES (KLL sketch), COUNTIF |
| Documentation discipline | Every finding is expected or explained — no "I found nulls" without "here's why and what to do" |
| Engineering quality | Parameterised queries, modular code, CLI with section filters |
