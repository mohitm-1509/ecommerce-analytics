"""
DAX measures for Power BI.

This file is NOT executed — it's a reference document containing all DAX
formulas to paste into Power BI Desktop. Organised by dashboard tab.

Why DAX measures over calculated columns:
- Measures evaluate at query time, respecting slicer/filter context.
  A "Total Revenue" measure recalculates when you filter to one state.
- Calculated columns compute once at import and consume storage.
- Rule of thumb: if it should respond to filters → measure.

Why DIVIDE() over `/`:
- DIVIDE(a, b, 0) returns 0 when b is zero or blank.
- a / b returns Infinity or error.
- Standard DAX best practice since 2020.
"""

# All measures reference the v_fact_orders view imported into Power BI.
# Table name in Power BI model: FactOrders

DAX_MEASURES = {

    # =================================================================
    # TAB 1: EXECUTIVE SUMMARY
    # =================================================================

    "Total Revenue": """
Total Revenue =
SUM(FactOrders[revenue])
""",

    "Total Orders": """
Total Orders =
DISTINCTCOUNT(FactOrders[order_id])
""",

    "Average Order Value": """
AOV =
DIVIDE(
    [Total Revenue],
    [Total Orders],
    0
)
""",

    "Avg Review Score": """
Avg Review Score =
AVERAGE(FactOrders[review_score])
""",

    "Total Customers": """
Total Customers =
DISTINCTCOUNT(FactOrders[customer_unique_id])
""",

    "Revenue MoM Growth %": """
Revenue MoM Growth % =
VAR CurrentRevenue = [Total Revenue]
VAR PreviousRevenue =
    CALCULATE(
        [Total Revenue],
        DATEADD(FactOrders[order_date], -1, MONTH)
    )
RETURN
    DIVIDE(
        CurrentRevenue - PreviousRevenue,
        PreviousRevenue,
        BLANK()
    )
""",

    # =================================================================
    # TAB 2: DELIVERY SLA PERFORMANCE
    # =================================================================

    "On-Time Delivery %": """
On-Time Delivery % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactOrders),
        FactOrders[delivery_status] = "On-Time"
    ),
    CALCULATE(
        COUNTROWS(FactOrders),
        FactOrders[delivery_status] <> "Not Delivered"
    ),
    0
)
""",

    "Late Delivery %": """
Late Delivery % =
DIVIDE(
    CALCULATE(
        COUNTROWS(FactOrders),
        FactOrders[delivery_status] = "Late"
    ),
    CALCULATE(
        COUNTROWS(FactOrders),
        FactOrders[delivery_status] <> "Not Delivered"
    ),
    0
)
""",

    "Avg Delivery Days": """
Avg Delivery Days =
AVERAGE(FactOrders[delivery_days])
""",

    "Late Orders Count": """
Late Orders =
CALCULATE(
    COUNTROWS(FactOrders),
    FactOrders[delivery_status] = "Late"
)
""",

    "Avg Delay Days (Late Only)": """
Avg Delay Days (Late Only) =
CALCULATE(
    AVERAGE(FactOrders[delay_days]),
    FactOrders[delivery_status] = "Late"
)
""",

    # =================================================================
    # TAB 3: SELLER SCORECARD
    # =================================================================
    # These use the v_seller_scorecard view (table: SellerScorecard)

    "Gold Seller Count": """
Gold Sellers =
CALCULATE(
    COUNTROWS(SellerScorecard),
    SellerScorecard[tier] = "Gold"
)
""",

    "Silver Seller Count": """
Silver Sellers =
CALCULATE(
    COUNTROWS(SellerScorecard),
    SellerScorecard[tier] = "Silver"
)
""",

    "Bronze Seller Count": """
Bronze Sellers =
CALCULATE(
    COUNTROWS(SellerScorecard),
    SellerScorecard[tier] = "Bronze"
)
""",

    "Gold Tier Revenue Share": """
Gold Revenue Share =
DIVIDE(
    CALCULATE(
        SUM(SellerScorecard[total_revenue]),
        SellerScorecard[tier] = "Gold"
    ),
    SUM(SellerScorecard[total_revenue]),
    0
)
""",

    # =================================================================
    # TAB 4: REGIONAL BREAKDOWN
    # =================================================================

    "Freight % of Revenue": """
Freight % of Revenue =
DIVIDE(
    SUM(FactOrders[freight]),
    SUM(FactOrders[revenue]),
    0
)
""",

    "Revenue Market Share": """
Revenue Market Share =
DIVIDE(
    [Total Revenue],
    CALCULATE(
        [Total Revenue],
        ALL(FactOrders[customer_state])
    ),
    0
)
""",

    "Customer Concentration": """
Customer Concentration =
DIVIDE(
    [Total Customers],
    CALCULATE(
        [Total Customers],
        ALL(FactOrders[customer_state])
    ),
    0
)
""",
}


def print_all_measures() -> None:
    """Print all DAX measures formatted for copy-paste into Power BI."""
    print("=" * 60)
    print("  DAX MEASURES — Copy into Power BI Desktop")
    print("=" * 60)
    for name, formula in DAX_MEASURES.items():
        print(f"\n--- {name} ---")
        print(formula.strip())
    print(f"\n{'=' * 60}")
    print(f"  Total: {len(DAX_MEASURES)} measures")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    print_all_measures()
