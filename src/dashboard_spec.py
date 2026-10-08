"""
Module 4: Power BI Dashboard Specification.

This file defines the exact layout, chart types, and data mappings for all
4 dashboard tabs. It serves as a blueprint — print it and follow step-by-step
in Power BI Desktop.

Print the spec:  python -m src.dashboard_spec
"""

SPEC = """
# ============================================================================
#  OLIST E-COMMERCE — POWER BI DASHBOARD SPECIFICATION
# ============================================================================
#
#  Data source: BigQuery views (Import mode, scheduled daily refresh)
#  Tables in model:
#     FactOrders       ← v_fact_orders
#     SellerScorecard  ← v_seller_scorecard
#     CategoryMetrics  ← v_category_metrics
#     DeliverySLA      ← v_delivery_sla
#     DimStates        ← v_dim_states
#
#  Relationships (star schema):
#     FactOrders[customer_state]  →  DimStates[state_code]   (many:1)
#     DeliverySLA[state]          →  DimStates[state_code]   (many:1)
#
#  Theme: Use a neutral corporate palette.
#     Primary:    #2563EB (blue)
#     Secondary:  #10B981 (green)
#     Negative:   #EF4444 (red)
#     Neutral:    #6B7280 (grey)
#     Background: #F9FAFB (light grey)
# ============================================================================


# ============================================================================
# TAB 1: EXECUTIVE SUMMARY
# ============================================================================
# Purpose: CEO-level overview. Answers "How is the business doing?"
# Layout: 12-column grid, 4 KPI cards across the top, charts below.
# ============================================================================

VISUAL 1.1 — KPI Card Row (top, spanning full width)
    ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
    │  Total   │ │  Total   │ │   AOV    │ │ Avg Review│
    │ Revenue  │ │  Orders  │ │ (R$)     │ │  Score    │
    │ R$13.5M  │ │  99,441  │ │ R$137    │ │   4.09    │
    └──────────┘ └──────────┘ └──────────┘ └──────────┘
    Type:     New Card visual (2025+) with sparkline
    Measure:  [Total Revenue], [Total Orders], [AOV], [Avg Review Score]
    Sparkline: order_month on x-axis, respective measure on y-axis
    Format:   Revenue → R$ currency, 1 decimal. Orders → whole number.
              AOV → R$ 2 decimals. Review → 2 decimals.

VISUAL 1.2 — Revenue Trend (left, below KPIs, 8 columns wide)
    Type:     Line chart
    X-axis:   order_month (from FactOrders)
    Y-axis:   [Total Revenue]
    Secondary Y: [Total Orders] (dashed line)
    Why line: Shows trend over time. Bar chart would work but line
              better communicates continuous progression.

VISUAL 1.3 — Top 10 Categories by Revenue (right, 4 columns wide)
    Type:     Horizontal bar chart
    Y-axis:   category_english (from CategoryMetrics)
    X-axis:   SUM(revenue) from CategoryMetrics
    Sort:     Descending by revenue
    Limit:    Top N filter = 10
    Why horizontal bar: Category names are long. Horizontal bars let
              names display without rotation.

VISUAL 1.4 — Review Score Distribution (bottom-left, 4 columns)
    Type:     Donut chart
    Values:   COUNT of order_id
    Legend:   review_score (1-5)
    Colors:   1★ = #EF4444, 2★ = #F97316, 3★ = #EAB308,
              4★ = #22C55E, 5★ = #10B981
    Why donut: Part-of-whole relationship. 5 discrete categories.
              Pie/donut is appropriate when categories ≤ 6.

VISUAL 1.5 — Payment Type Split (bottom-right, 4 columns)
    Type:     Stacked bar chart (single bar, horizontal)
    Values:   SUM(total_payment) from FactOrders, split by payment_types
    Why stacked: Shows proportion within a fixed total.

SLICER: order_year (dropdown, top-right corner)


# ============================================================================
# TAB 2: DELIVERY SLA PERFORMANCE
# ============================================================================
# Purpose: Ops team. Answers "Is our logistics improving?"
# ============================================================================

VISUAL 2.1 — KPI Card Row
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │  On-Time %   │ │ Avg Delivery │ │ Late Orders  │
    │    93.4%     │ │   12.5 days  │ │   6,535      │
    └──────────────┘ └──────────────┘ └──────────────┘
    Measures:  [On-Time Delivery %], [Avg Delivery Days], [Late Orders]
    Conditional formatting:
        On-Time % ≥ 95% → green background
        On-Time % 90-95% → yellow
        On-Time % < 90% → red

VISUAL 2.2 — Late Delivery % Trend (8 columns, below KPIs)
    Type:     Combo chart (bars + line)
    X-axis:   order_month (from DeliverySLA)
    Bars:     total_orders (column)
    Line:     on_time_pct (line, secondary Y-axis)
    Why combo: Volume context prevents misreading a drop in late %
              that's actually just fewer orders.

VISUAL 2.3 — Avg Delivery Days by State (4 columns)
    Type:     Horizontal bar chart
    Y-axis:   state (from DeliverySLA), mapped via DimStates for full name
    X-axis:   avg_delivery_days
    Sort:     Descending (slowest state first)
    Conditional: Bars > 15 days → red. Bars ≤ 10 days → green.

VISUAL 2.4 — Delivery Status vs Review Score (bottom, 6 columns)
    Type:     Grouped bar chart
    X-axis:   delivery_status (On-Time / Late)
    Y-axis:   [Avg Review Score]
    Colors:   On-Time → #10B981, Late → #EF4444
    Annotation: Show the exact avg score on each bar.
    Why this chart: Directly proves BQ1 hypothesis visually.

VISUAL 2.5 — State-level Scatter (bottom, 6 columns)
    Type:     Scatter plot
    X-axis:   avg_delivery_days (from DeliverySLA)
    Y-axis:   avg_review_score (from DeliverySLA)
    Size:     total_orders
    Labels:   state
    Why scatter: Shows correlation between delivery speed and satisfaction.
              States in bottom-right (slow + bad reviews) need intervention.

SLICER: order_month (range slider)


# ============================================================================
# TAB 3: SELLER SCORECARD
# ============================================================================
# Purpose: Marketplace team. Answers "Which sellers to reward/remove?"
# ============================================================================

VISUAL 3.1 — Tier KPI Cards
    ┌──────────┐ ┌──────────┐ ┌──────────┐
    │   Gold   │ │  Silver  │ │  Bronze  │
    │   XXX    │ │   XXX    │ │   XXX    │
    │ sellers  │ │ sellers  │ │ sellers  │
    └──────────┘ └──────────┘ └──────────┘
    Colors:   Gold → #EAB308, Silver → #9CA3AF, Bronze → #B45309

VISUAL 3.2 — Tier Comparison (6 columns)
    Type:     Clustered bar chart
    X-axis:   tier (Gold / Silver / Bronze)
    Y-axis:   Three measures (use small multiples or clustered bars):
              - avg_review_score
              - avg_delivery_days
              - avg_item_price
    Why clustered: Side-by-side comparison of performance gaps between tiers.

VISUAL 3.3 — Revenue by Tier (6 columns)
    Type:     Treemap
    Category: tier
    Size:     total_revenue
    Color:    tier (Gold/Silver/Bronze palette)
    Why treemap: Shows that Gold sellers generate disproportionate revenue
              relative to their count.

VISUAL 3.4 — Seller Detail Table (bottom, full width)
    Type:     Table / Matrix visual
    Columns:  seller_id, seller_state, order_count, total_revenue,
              avg_review_score, avg_delivery_days, composite_score, tier
    Sort:     composite_score descending
    Conditional formatting: Review score < 3.0 → red cell background
    Drill-through: Click a seller → detail page (optional)
    Why table: Enables operational lookup. Dashboard charts show patterns;
              tables show individual records for action.

SLICER: tier (buttons: Gold / Silver / Bronze / All)
SLICER: seller_state (dropdown)


# ============================================================================
# TAB 4: REGIONAL BREAKDOWN
# ============================================================================
# Purpose: Growth team. Answers "Where to invest next?"
# ============================================================================

VISUAL 4.1 — Revenue KPI Cards
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Top State    │ │ # States     │ │ Avg Freight  │
    │   SP (42%)   │ │    27        │ │   % of Rev   │
    └──────────────┘ └──────────────┘ └──────────────┘

VISUAL 4.2 — Revenue by State Map (8 columns)
    Type:     Filled map (choropleth)
    Location: state_name (from DimStates)
    Color saturation: [Total Revenue]
    Tooltip:  state, revenue, order_count, avg_delivery_days
    Why map: Geographical distribution is instantly visible.
             SP/RJ dominance is obvious at a glance.
    Note:    Power BI uses Bing Maps. Use state_name (full name)
             not state_code for accurate geocoding of Brazilian states.

VISUAL 4.3 — Freight % by State (4 columns)
    Type:     Horizontal bar chart
    Y-axis:   state (via DimStates)
    X-axis:   [Freight % of Revenue]
    Sort:     Descending (highest freight % first)
    Reference line: National average freight %
    Conditional: Bars > 25% → red.
    Why bar: Direct comparison across states. The reference line
             instantly shows who's above/below average.

VISUAL 4.4 — MoM Growth Heatmap (bottom-left, 6 columns)
    Type:     Matrix visual
    Rows:     state (top 10 by revenue)
    Columns:  order_month
    Values:   [Total Revenue]
    Conditional formatting: Background colour scale (red-yellow-green)
    Why matrix: Shows temporal + geographic patterns simultaneously.
              Bright green cells = growth pockets. Red = decline.

VISUAL 4.5 — Customer vs Seller Concentration (bottom-right, 6 columns)
    Type:     Clustered bar chart
    X-axis:   state (top 10)
    Y-axis:   Two bars per state:
              - [Customer Concentration] (blue)
              - Seller concentration (calculated similarly, orange)
    Why this: If customers are in the North but sellers are in the South,
              that explains high freight and slow delivery. Mismatch = opportunity.

SLICER: order_year (dropdown)
SLICER: customer_state (multi-select dropdown)


# ============================================================================
# GLOBAL SETTINGS
# ============================================================================
# - Filter pane: Hidden (all filtering via slicers for cleaner UX)
# - Page navigation: Tab buttons at the bottom (standard Power BI tabs)
# - Mobile layout: Configure for each tab (Power BI auto-generates)
# - Tooltips: Enable hover tooltips on all chart visuals
# - Theme: Import custom JSON theme for consistent colours
# - Publish: Power BI Service (app.powerbi.com) → My Workspace → free tier
"""


def print_spec() -> None:
    print(SPEC)


if __name__ == "__main__":
    print_spec()
