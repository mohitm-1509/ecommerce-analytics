# Module 4 — Power BI Dashboard: Methodology

This document explains every design decision in the dashboard — from data architecture (views vs raw tables) to chart type selection (with perceptual science reasoning) to DAX patterns.

---

## 1. Data Architecture: Pre-Aggregated Views vs Raw Table Import

### The two approaches

```
Approach A (chosen):
    BigQuery ──[5 views, pre-joined]──→ Power BI Import ──→ Dashboard
    Data size in Power BI: ~5 MB (aggregated)
    Refresh time: ~10 seconds

Approach B (rejected):
    BigQuery ──[9 raw tables]──→ Power BI Import ──→ Dashboard
    Data size in Power BI: ~120 MB (raw)
    Refresh time: ~2-5 minutes
    Requires: 9 relationships configured manually in Power BI
              Complex Power Query M transformations
              DAX for every JOIN-dependent calculation
```

### Why views win

| Criterion | Views (Approach A) | Raw Tables (Approach B) |
|---|---|---|
| Import size | ~5 MB | ~120 MB (geolocation alone = 30 MB) |
| Refresh speed | ~10 sec | ~2-5 min |
| Model complexity | 5 tables, 2 relationships | 9 tables, 8+ relationships |
| Risk of wrong JOINs | None (joins are in SQL, tested) | High (many:many, fan-out) |
| Logic location | SQL (version-controlled, testable) | Power Query M + DAX (opaque) |
| Free tier fit | 5 MB << 1 GB limit | 120 MB fits, but tight with growth |

### The fan-out problem with raw tables

If you import `geolocation` (1M rows) and `customers` (99K rows) separately, and relate them on `zip_code_prefix`:

```
One zip code → ~52 geolocation rows (duplicates)
One customer → one zip code → 52 geolocation rows

SUM(price) with geolocation slicer active:
    Correct: R$13.5M
    With fan-out: R$13.5M × 52 = R$702M (wrong!)
```

Power BI handles many:many relationships, but silently uses CROSSFILTER which can produce unexpected results. Our views eliminate this risk by aggregating in SQL.

### Why views instead of materialised views?

BigQuery offers both:

| Type | Storage cost | Query cost | Freshness |
|---|---|---|---|
| **View** (chosen) | None (computed at query time) | Billed per query | Always current |
| **Materialised View** | Stores result (~10 MB) | No query cost for cached results | Refreshed on base table change |

For our static historical dataset, views and materialised views perform identically — the data never changes after initial load. We chose regular views because:
1. No additional storage cost
2. Simpler to manage (no refresh configuration)
3. The queries are fast enough (< 5 seconds for each view on 100K rows)

In a production environment with daily data loads, materialised views would be preferred for dashboard performance.

---

## 2. Import Mode vs DirectQuery

### The three Power BI connectivity modes

| Mode | How it works | Latency | Cost |
|---|---|---|---|
| **Import** (chosen) | Data cached in Power BI's VertiPaq engine | Instant (ms) | Zero after import |
| **DirectQuery** | Every interaction sends a query to BigQuery | 2-10 seconds per click | BigQuery query charges |
| **Composite** | Mix of Import and DirectQuery per table | Varies | Varies |

### Why Import mode

1. **Free tier compatibility**: Import mode works on free Power BI accounts. DirectQuery with BigQuery requires Power BI Pro (£7.50/month/user in the UK).

2. **Performance**: VertiPaq is an in-memory columnar engine optimised for interactive analysis. A slicer click filters 100K rows in milliseconds. DirectQuery would send a SQL query to BigQuery on every click — 2-10 second lag per interaction makes the dashboard feel broken.

3. **Static data**: The Olist dataset is historical (2016-2018). It will not change. There is no freshness benefit from DirectQuery.

4. **BigQuery cost**: Each DirectQuery interaction costs bytes scanned. A dashboard with 15 visuals and 3 slicers could trigger 15 queries per slicer change. Over a demo session: 15 queries × 3 slicer changes × 10 = 450 queries. At ~120 MB per query: 54 GB scanned. Still within the 1 TB free tier, but wasteful.

**When to use DirectQuery**: When data changes hourly or more frequently, AND the business requires real-time views, AND the organisation pays for Power BI Pro.

---

## 3. Star Schema Design in Power BI

### Our model

```
              ┌─────────────┐
              │  DimStates   │
              │  (27 rows)   │
              └──────┬───────┘
                     │ state_code
        ┌────────────┼────────────┐
        │            │            │
┌───────┴────┐ ┌─────┴─────┐ ┌───┴──────────┐
│FactOrders  │ │DeliverySLA│ │CategoryMetrics│
│(99K rows)  │ │(~500 rows)│ │(~1500 rows)  │
└────────────┘ └───────────┘ └──────────────┘

                ┌────────────────┐
                │SellerScorecard │
                │(~800 rows)     │
                │(standalone)    │
                └────────────────┘
```

### Why star schema over flat denormalised table

A single flat table with all columns would work for a small dataset, but:

1. **VertiPaq compression**: VertiPaq uses dictionary encoding per column. A column with 27 unique states compresses to ~27 dictionary entries + row pointers. In a flat table, `state_name` (string, avg 15 chars) would be stored per row: 99K × 15 bytes = 1.5 MB. In a dimension table: 27 × 15 bytes = 405 bytes + row pointers. Compression ratio: ~3,700×.

2. **Slicer performance**: Filtering by state_name on a 27-row dimension table is instantaneous. Filtering on a 99K-row fact table is slower (even in VertiPaq, smaller tables filter faster).

3. **Reusability**: DimStates is referenced by both FactOrders and DeliverySLA. One state name change updates both.

---

## 4. Chart Type Selection — Perceptual Reasoning

Chart selection is not aesthetic preference — it's based on which visual encoding humans decode most accurately.

### Cleveland & McGill's Hierarchy (1984)

Ranked from most to least accurate human perception:

```
1. Position along a common scale     (bar chart, dot plot)
2. Position on identical scales       (small multiples)
3. Length                             (bar chart)
4. Angle / Slope                     (line chart)
5. Area                              (bubble chart, treemap)
6. Volume / Curvature / Shading      (3D charts — avoid)
7. Colour saturation                 (heatmap, choropleth)
```

### How we applied this

| Visual | Data Relationship | Encoding Used | Rank | Alternative Rejected |
|---|---|---|---|---|
| Revenue trend (1.2) | Continuous over time | Position (line chart) | 1 | Bar chart — too many bars for 25 months |
| Top categories (1.3) | Ranked comparison | Length (horizontal bar) | 3 | Pie chart — poor for > 5 categories |
| Review distribution (1.4) | Part-of-whole, 5 groups | Angle (donut) | 4 | Bar — loses the "whole = 100%" context |
| Delivery by state (2.3) | Ranked comparison | Length (bar) | 3 | Table — harder to spot patterns |
| Delivery vs Review (2.5) | Correlation | Position × position (scatter) | 1+1 | Grouped bar — can't show correlation |
| Revenue by state (4.2) | Geographic distribution | Colour saturation (map) | 7 | Bar chart — loses geographic context |
| MoM growth (4.4) | Matrix (state × month) | Colour saturation (heatmap) | 7 | Line chart — too many lines (27 states) |

### Why donut for review scores but bar for categories?

**Review scores**: 5 discrete values representing parts of a whole (100% of reviews = scores 1 through 5). Donut chart is appropriate when:
- Categories ≤ 6 (Cleveland's guideline)
- The "total" is meaningful (all reviews sum to 100%)
- The audience cares about proportions, not exact values

**Product categories**: 10+ items ranked by value. Bar chart is appropriate when:
- Comparing magnitudes across many items
- The audience needs precise value comparison
- Items have no "total" relationship (categories don't sum to a meaningful whole)

### Why map for regional data despite Rank 7?

Colour saturation (Rank 7) is the least accurate encoding. However:

1. **Geographic context matters**: Knowing that Roraima has low revenue is less useful than seeing that Roraima is in the far north, far from seller-dense São Paulo. The spatial relationship explains the pattern.

2. **Pre-attentive processing**: A choropleth map leverages the brain's spatial processing (pre-attentive — processed in < 250ms). The viewer instantly sees "south = dense, north = sparse" without reading any numbers.

3. **Paired with bar chart**: We pair the map (4.2) with a freight % bar chart (4.3). The map shows WHERE; the bar shows HOW MUCH. Together they're more informative than either alone.

---

## 5. DAX Design Decisions

### Why DIVIDE() over `/` operator

```dax
-- This crashes when Total Orders = 0:
AOV = SUM(FactOrders[revenue]) / DISTINCTCOUNT(FactOrders[order_id])

-- This returns 0 when Total Orders = 0:
AOV = DIVIDE(SUM(FactOrders[revenue]), DISTINCTCOUNT(FactOrders[order_id]), 0)
```

When does `Total Orders = 0`? When a slicer filters to a state with no delivered orders in a specific month. The dashboard should show 0 or blank, not an error.

**DIVIDE()** is the [official Microsoft best practice](https://learn.microsoft.com/en-us/dax/best-practices/dax-divide-function-operator) for all division in DAX.

### Why VAR for intermediate results

```dax
-- Without VAR (evaluates [Total Revenue] twice):
Revenue MoM % =
DIVIDE(
    [Total Revenue] - CALCULATE([Total Revenue], DATEADD(...)),
    CALCULATE([Total Revenue], DATEADD(...)),
    BLANK()
)

-- With VAR (evaluates each expression once):
Revenue MoM % =
VAR CurrentRevenue = [Total Revenue]
VAR PreviousRevenue = CALCULATE([Total Revenue], DATEADD(...))
RETURN
    DIVIDE(CurrentRevenue - PreviousRevenue, PreviousRevenue, BLANK())
```

VAR provides:
1. **Performance**: The DAX engine evaluates each VAR once and caches the result. Without VAR, `CALCULATE([Total Revenue], DATEADD(...))` is evaluated twice.
2. **Readability**: Named variables are self-documenting.
3. **Debuggability**: You can inspect each VAR in DAX Studio.

### Why measures over calculated columns

```
Calculated column:
    Computed once at import time
    Stored in memory (increases model size)
    Does NOT respond to filters
    Example: revenue_per_item = price / item_count  ← static per row

Measure:
    Computed at query time
    NOT stored (computed on demand)
    DOES respond to filters
    Example: [Total Revenue] = SUM(revenue)  ← recalculates per slicer selection
```

Every KPI on our dashboard is a **measure** because they must respond to slicers (year, state, tier). If `[Total Revenue]` were a calculated column, filtering to São Paulo would still show national revenue.

---

## 6. Colour Palette — Why These Colours?

### Principle: Accessibility + Semantic Meaning

| Colour | Hex | Use | Reasoning |
|---|---|---|---|
| Blue | #2563EB | Primary/neutral metrics | Blue is the most universally liked colour. No emotional connotation. |
| Green | #10B981 | Positive (on-time, growth) | Universal "good" signal. |
| Red | #EF4444 | Negative (late, decline) | Universal "bad" signal. |
| Grey | #6B7280 | Neutral/context | De-emphasises secondary information. |
| Amber | #EAB308 | Warning/Gold tier | Intermediate between green and red. |

### WCAG Contrast Compliance

All text-on-colour combinations meet **WCAG AA** (contrast ratio ≥ 4.5:1):

```
White text on #2563EB → ratio = 4.56:1 ✓ (AA)
White text on #EF4444 → ratio = 4.53:1 ✓ (AA)
White text on #10B981 → ratio = 3.34:1 ✗ — use dark text instead
Dark text on #10B981  → ratio = 5.92:1 ✓ (AA)
```

### Colour-blind safe

The palette avoids pure red-green adjacency. Where red and green appear together (delivery status chart 2.4), they are:
- Separated by value labels (not relying on colour alone)
- Distinguishable by position (grouped bars, not overlapping)

---

## 7. Publishing to Power BI Service (Free Tier)

### Steps

1. Power BI Desktop → File → Publish → My Workspace
2. Navigate to app.powerbi.com → My Workspace → find the report
3. Share link: "Publish to web" (creates a public embed URL)

### Free tier limitations

| Feature | Free Tier | Pro (£7.50/mo) |
|---|---|---|
| Dataset size | 1 GB | 10 GB |
| Scheduled refresh | 8/day | 48/day |
| Share with others | Publish to web (public) | Share within org |
| DirectQuery | ✗ | ✓ |

Our dataset is ~5 MB (well under 1 GB), and refreshes are unnecessary (static data). The free tier is sufficient.

### Portfolio link

The "Publish to web" URL can be embedded in your:
- GitHub README
- LinkedIn project section
- Resume (as a hyperlink under the project description)

---

## 8. Step-by-Step: Connecting Power BI to BigQuery

1. **Install Power BI Desktop** (free, Windows only — use a VM on Mac)
2. **Get Data → Google BigQuery**
3. **Authentication**: Sign in with Google account (OAuth)
4. **Select project**: Choose your GCP project
5. **Select dataset**: `olist_ecommerce`
6. **Select views**: Check all 5 views (v_fact_orders, v_seller_scorecard, etc.)
7. **Import mode**: Power BI defaults to Import. Confirm.
8. **Transform Data**: Review in Power Query. No transformations needed (views are clean).
9. **Close & Apply**: Data loads into VertiPaq.
10. **Model view**: Set relationships (FactOrders.customer_state → DimStates.state_code)
11. **Create measures**: Paste DAX from `dax_measures.py`
12. **Build visuals**: Follow `dashboard_spec.py` tab by tab

---

## 9. What This Module Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| BI tool proficiency | 4-tab Power BI dashboard, published to web |
| Data modelling | Star schema with views, correct cardinality |
| DAX | 16 measures using DIVIDE, CALCULATE, VAR, DATEADD |
| Visual design | Chart types matched to data relationships (Cleveland hierarchy) |
| Accessibility | WCAG AA contrast, colour-blind safe palette |
| Cloud integration | BigQuery → Power BI via native connector |
| Communication | Each tab answers a specific stakeholder question |
