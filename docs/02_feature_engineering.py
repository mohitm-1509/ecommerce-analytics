"""Generate PDF: Phase 1 — Feature Engineering Deep Dive."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    Image, KeepTogether, PageBreak,
)

OUTPUT = "docs/02_feature_engineering.pdf"
PLOT_DIR = "/private/tmp/claude-501/-Users-mohitmalhotra-PycharmProjects/phase1_plots"

ACCENT = HexColor("#1D9E75")
DARK = HexColor("#1a1a2e")
GREY = HexColor("#444444")
LIGHT_BG = HexColor("#f0f7f4")
WHITE = HexColor("#ffffff")
BORDER = HexColor("#cccccc")
WARN_BG = HexColor("#fff8e1")
WARN_BORDER = HexColor("#f9a825")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DocTitle", parent=styles["Title"], fontSize=22, leading=28,
                          textColor=DARK, spaceAfter=4, alignment=TA_CENTER))
styles.add(ParagraphStyle("DocSub", parent=styles["Normal"], fontSize=11, leading=14,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle("S1", parent=styles["Heading1"], fontSize=15, leading=20,
                          textColor=ACCENT, spaceBefore=22, spaceAfter=8))
styles.add(ParagraphStyle("S2", parent=styles["Heading2"], fontSize=12, leading=16,
                          textColor=DARK, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("S3", parent=styles["Heading3"], fontSize=10.5, leading=14,
                          textColor=HexColor("#2a6e50"), spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle("B", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("Blt", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, leftIndent=18, spaceAfter=4, bulletIndent=6))
styles.add(ParagraphStyle("BltSub", parent=styles["Normal"], fontSize=10, leading=14,
                          textColor=GREY, leftIndent=36, spaceAfter=3, bulletIndent=24))
styles.add(ParagraphStyle("CodeBlock", parent=styles["Normal"], fontSize=9, leading=12,
                          fontName="Courier", textColor=HexColor("#333333"),
                          backColor=HexColor("#f5f5f5"), leftIndent=12, rightIndent=12,
                          spaceBefore=4, spaceAfter=8, borderPadding=6))
styles.add(ParagraphStyle("Caption", parent=styles["Normal"], fontSize=9, leading=12,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=10, spaceBefore=4))
styles.add(ParagraphStyle("Note", parent=styles["Normal"], fontSize=9.5, leading=13,
                          textColor=HexColor("#7a6c00"), leftIndent=10, rightIndent=10,
                          spaceBefore=6, spaceAfter=10, backColor=WARN_BG,
                          borderColor=WARN_BORDER, borderWidth=0.5, borderPadding=8))

def hr(): return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6, spaceBefore=2)
def h1(t): return Paragraph(t, styles["S1"])
def h2(t): return Paragraph(t, styles["S2"])
def h3(t): return Paragraph(t, styles["S3"])
def p(t): return Paragraph(t, styles["B"])
def bl(t): return Paragraph(f"•  {t}", styles["Blt"])
def bls(t): return Paragraph(f"–  {t}", styles["BltSub"])
def code(t): return Paragraph(t, styles["CodeBlock"])
def caption(t): return Paragraph(t, styles["Caption"])
def note(t): return Paragraph(f"<b>Note:</b> {t}", styles["Note"])

def make_table(data, col_widths, header_bg=ACCENT):
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), header_bg),
        ("TEXTCOLOR", (0,0), (-1,0), WHITE),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 9),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("ALIGN", (0,0), (0,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("GRID", (0,0), (-1,-1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    return t

def img(name, w=480):
    return Image(f"{PLOT_DIR}/{name}", width=w, height=w*0.3)


def build():
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                            leftMargin=22*mm, rightMargin=22*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = []

    # ── Title ──
    s.append(Paragraph("Phase 1: Feature Engineering", styles["DocTitle"]))
    s.append(Paragraph("RFM Customer Segmentation Pipeline — Detailed Technical Report", styles["DocSub"]))
    s.append(hr())
    s.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: Individual Table Schemas
    # ═══════════════════════════════════════════════════════════
    s.append(h1("1. Individual Table Schemas"))
    s.append(p("The Olist Brazilian E-Commerce dataset consists of three CSV files that together "
               "describe the full customer purchase journey. Below is the schema of each table, "
               "including data types and purpose of each column."))

    # Orders
    s.append(h2("1.1  olist_orders_dataset.csv"))
    s.append(p("<b>Rows:</b> 99,441  |  <b>Purpose:</b> One row per order placed on the marketplace."))
    s.append(Spacer(1, 4))
    orders_data = [
        ["Column", "Dtype", "Nulls", "Description"],
        ["order_id", "object (UUID)", "0", "Primary key — unique order identifier"],
        ["customer_id", "object (UUID)", "0", "FK to customers table (one per order)"],
        ["order_status", "object", "0", "delivered, shipped, canceled, etc. (8 values)"],
        ["order_purchase_timestamp", "object → datetime", "0", "When the customer placed the order"],
        ["order_approved_at", "object → datetime", "160", "When payment was approved"],
        ["order_delivered_carrier_date", "object → datetime", "1,783", "When carrier picked up the order"],
        ["order_delivered_customer_date", "object → datetime", "2,965", "When customer received delivery"],
        ["order_estimated_delivery_date", "object → datetime", "0", "Estimated delivery date shown at checkout"],
    ]
    s.append(make_table(orders_data, [135, 85, 35, 215]))
    s.append(Spacer(1, 4))
    s.append(note("Missing values in delivery dates are expected — they correspond to orders that were "
                   "canceled, still in transit, or not yet picked up. We filter to <b>delivered</b> orders only, "
                   "which eliminates most nulls."))

    # Customers
    s.append(h2("1.2  olist_customers_dataset.csv"))
    s.append(p("<b>Rows:</b> 99,441  |  <b>Purpose:</b> Maps each order's customer_id to a "
               "customer_unique_id (a single person can have multiple customer_ids across orders)."))
    s.append(Spacer(1, 4))
    cust_data = [
        ["Column", "Dtype", "Nulls", "Description"],
        ["customer_id", "object (UUID)", "0", "FK matching orders table (one per order)"],
        ["customer_unique_id", "object (UUID)", "0", "De-duplicated customer identifier"],
        ["customer_zip_code_prefix", "int64", "0", "First 5 digits of customer ZIP"],
        ["customer_city", "object", "0", "Customer city name"],
        ["customer_state", "object", "0", "Customer state (2-letter code)"],
    ]
    s.append(make_table(cust_data, [135, 85, 35, 215]))
    s.append(Spacer(1, 4))
    s.append(p("<b>Key distinction:</b> <i>customer_id</i> is per-order (99,441 values), while "
               "<i>customer_unique_id</i> represents a real person (96,096 unique). A returning "
               "customer gets a new customer_id each order but keeps the same customer_unique_id. "
               "RFM aggregation must group by customer_unique_id."))

    # Payments
    s.append(h2("1.3  olist_order_payments_dataset.csv"))
    s.append(p("<b>Rows:</b> 103,886  |  <b>Purpose:</b> Payment details per order. An order "
               "can have multiple payment rows (e.g., credit card + voucher)."))
    s.append(Spacer(1, 4))
    pay_data = [
        ["Column", "Dtype", "Nulls", "Description"],
        ["order_id", "object (UUID)", "0", "FK to orders table"],
        ["payment_sequential", "int64", "0", "Sequence number for multi-payment orders"],
        ["payment_type", "object", "0", "credit_card, boleto, voucher, debit_card"],
        ["payment_installments", "int64", "0", "Number of installments chosen"],
        ["payment_value", "float64", "0", "Amount paid in this payment row (BRL)"],
    ]
    s.append(make_table(pay_data, [120, 75, 35, 240]))
    s.append(Spacer(1, 4))
    s.append(note("103,886 payment rows vs 99,441 orders means ~4,445 orders used split payments. "
                   "We aggregate payment_value per order_id before joining, so each order has a "
                   "single total monetary value."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: Joined Schema
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("2. Joined Table Schema"))
    s.append(p("The three tables are joined in two steps to produce a single denormalised transaction table:"))
    s.append(Spacer(1, 4))

    s.append(h3("Step 1: Orders × Customers (INNER JOIN on customer_id)"))
    s.append(p("This attaches the <i>customer_unique_id</i> to each order. We first filter orders "
               "to <b>order_status = 'delivered'</b> (96,478 of 99,441 orders), discarding canceled, "
               "unavailable, and in-transit orders that would distort RFM metrics."))

    s.append(h3("Step 2: Result × Payments (INNER JOIN on order_id)"))
    s.append(p("Before joining, payments are pre-aggregated: <i>payments.groupby('order_id')['payment_value'].sum()</i>. "
               "This collapses split-payment rows into a single total per order. The inner join drops 1 delivered order "
               "that has no payment record (96,478 → 96,477 rows)."))
    s.append(Spacer(1, 6))

    s.append(h3("Resulting Schema"))
    joined_data = [
        ["Column", "Source Table", "Used in RFM?"],
        ["order_id", "orders", "Yes — frequency (nunique)"],
        ["customer_id", "orders", "No — join key only"],
        ["order_status", "orders", "No — already filtered to 'delivered'"],
        ["order_purchase_timestamp", "orders", "Yes — recency (max per customer)"],
        ["customer_unique_id", "customers", "Yes — groupby key"],
        ["payment_value", "payments (aggregated)", "Yes — monetary (sum)"],
        ["5 other columns", "orders + customers", "No — location/delivery metadata"],
    ]
    s.append(make_table(joined_data, [130, 120, 220]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Final joined table:</b> 96,477 rows × 13 columns, representing 93,357 unique "
               "customers (some customers have multiple delivered orders)."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: Why Join These Tables?
    # ═══════════════════════════════════════════════════════════
    s.append(h1("3. Why Join These Three Tables?"))
    s.append(p("No single table contains all the information needed for RFM analysis:"))
    s.append(Spacer(1, 2))
    s.append(bl("<b>Orders table</b> provides <i>when</i> each purchase happened (order_purchase_timestamp "
                "→ Recency) and a countable order_id (→ Frequency), but has no payment amounts."))
    s.append(bl("<b>Payments table</b> provides <i>how much</i> was spent (payment_value → Monetary), "
                "but has no timestamps or customer identifiers."))
    s.append(bl("<b>Customers table</b> provides the <i>customer_unique_id</i> needed to group orders "
                "by real person. Without it, a returning customer would appear as two separate customers "
                "(each order generates a different customer_id)."))
    s.append(Spacer(1, 4))
    s.append(p("The join is the minimum necessary linkage: orders ↔ customers (via customer_id) gives "
               "us the person, and orders ↔ payments (via order_id) gives us the spend. Omitting any "
               "table would leave a gap in the R, F, or M calculation."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: RFM Aggregation
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("4. RFM Aggregation"))
    s.append(p("RFM aggregation collapses the 96,477-row transaction table into a single row per customer "
               "(93,357 rows), computing three behavioural metrics:"))
    s.append(Spacer(1, 4))

    s.append(code(
        "rfm = transactions.groupby('customer_unique_id').agg(<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;recency = ('order_purchase_timestamp', λx: (ref_date − x.max()).days),<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;frequency = ('order_id', 'nunique'),<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;monetary = ('payment_value', 'sum'),<br/>"
        ")"
    ))
    s.append(Spacer(1, 4))

    rfm_def = [
        ["Metric", "Aggregation", "Interpretation", "Range"],
        ["Recency", "(reference_date − max\n(purchase_date)).days",
         "Days since last purchase.\nLower = more recent = better.", "49 – 744\ndays"],
        ["Frequency", "nunique(order_id)", "Count of distinct orders.\nHigher = more loyal.", "1 – 15\norders"],
        ["Monetary", "sum(payment_value)", "Total lifetime spend.\nHigher = more valuable.", "9.59 – 13,664\nBRL"],
    ]
    s.append(make_table(rfm_def, [70, 120, 155, 65]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Reference date:</b> 18 October 2018 — chosen as one day after the latest order "
               "in the dataset, ensuring all recency values are positive (required for Box-Cox)."))
    s.append(Spacer(1, 4))

    s.append(h2("4.1  What Do We Gain from RFM?"))
    s.append(bl("<b>Dimensionality reduction:</b> 96,477 transaction rows with 13 columns collapse "
                "to 93,357 customer rows with 3 meaningful features."))
    s.append(bl("<b>Behavioural encoding:</b> Raw timestamps and amounts become actionable metrics. "
                "Recency captures engagement decay, frequency captures loyalty, monetary captures value."))
    s.append(bl("<b>Clustering readiness:</b> Each customer is now a point in 3D RFM space, "
                "where distance between points represents behavioural similarity — exactly what "
                "K-Means optimises."))
    s.append(bl("<b>Business interpretability:</b> Unlike latent features from autoencoders or "
                "embeddings, RFM metrics have direct business meaning, making cluster profiles "
                "actionable by non-technical stakeholders."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: Raw Distributions
    # ═══════════════════════════════════════════════════════════
    s.append(h1("5. Raw Feature Distributions"))
    s.append(p("Before any cleaning or transformation, the three RFM features exhibit very "
               "different distributional characteristics:"))
    s.append(Spacer(1, 4))
    s.append(img("raw_distributions.png", w=470))
    s.append(caption("Figure 1: Raw RFM distributions before any processing."))
    s.append(Spacer(1, 4))

    raw_stats = [
        ["Statistic", "Recency", "Frequency", "Monetary"],
        ["Mean", "286.5 days", "1.03 orders", "€165.20"],
        ["Median", "267.0 days", "1.00 orders", "€107.78"],
        ["Std Dev", "152.6", "0.21", "226.3"],
        ["Skewness", "0.4473", "11.0951", "9.2110"],
        ["Kurtosis", "−0.6615", "323.55", "237.15"],
        ["Min / Max", "49 / 744", "1 / 15", "9.59 / 13,664"],
    ]
    s.append(make_table(raw_stats, [75, 105, 105, 105]))
    s.append(Spacer(1, 6))

    s.append(bl("<b>Recency</b> is roughly uniform with mild right skew (0.45). Relatively well-behaved."))
    s.append(bl("<b>Frequency</b> is extremely right-skewed (11.09) because 97% of customers ordered "
                "exactly once. It is effectively a binary variable (1 vs 2+), not a continuous distribution."))
    s.append(bl("<b>Monetary</b> is heavily right-skewed (9.21) with a very long tail — the maximum "
                "(€13,664) is 127× the median (€108). A handful of high-spenders dominate."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 6: Missing Values
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("6. Missing Values"))

    s.append(h2("6.1  In Source Tables"))
    miss_data = [
        ["Table", "Column", "Missing", "Cause", "Impact on RFM"],
        ["orders", "order_approved_at", "160", "Unapproved orders", "None — not used"],
        ["orders", "order_delivered_carrier_date", "1,783", "Unshipped orders", "None — not used"],
        ["orders", "order_delivered_customer_date", "2,965", "Undelivered orders", "None — not used"],
        ["customers", "(all columns)", "0", "—", "—"],
        ["payments", "(all columns)", "0", "—", "—"],
    ]
    s.append(make_table(miss_data, [55, 130, 45, 105, 105]))
    s.append(Spacer(1, 6))

    s.append(h2("6.2  After Filtering and Joining"))
    s.append(p("After filtering to <b>delivered</b> orders and joining, the three RFM-relevant "
               "columns have <b>zero missing values</b>:"))
    s.append(bl("<b>order_purchase_timestamp:</b> 0 nulls (always recorded at order placement)"))
    s.append(bl("<b>order_id:</b> 0 nulls (primary key)"))
    s.append(bl("<b>payment_value:</b> 0 nulls (aggregated from payments; 1 order dropped by inner join)"))
    s.append(Spacer(1, 4))
    s.append(p("<b>Why no imputation was needed:</b> The missing values in source tables exist in columns "
               "we do not use for RFM (delivery dates, approval timestamps). By filtering to delivered "
               "orders first, we remove the root cause of missingness (non-delivered orders). The inner "
               "join naturally excludes the single delivered order with no payment record. No synthetic "
               "imputation (mean, median, KNN) was necessary because the columns feeding R, F, and M "
               "are structurally complete for delivered orders."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 7: Outlier Handling
    # ═══════════════════════════════════════════════════════════
    s.append(h1("7. Outlier Handling"))
    s.append(p("Outliers distort both power transforms (Box-Cox is sensitive to extreme values) "
               "and K-Means (centroid positions are pulled by outliers). We use <b>percentile-based "
               "capping</b> (Winsorisation) at the 1st and 99th percentiles."))
    s.append(Spacer(1, 4))

    s.append(h2("7.1  Why Capping Instead of Dropping (IQR)?"))
    s.append(p("The standard IQR method (drop rows outside Q1 − 1.5×IQR to Q3 + 1.5×IQR) was "
               "considered but rejected for two reasons:"))
    s.append(bl("<b>Frequency's IQR = 0</b> — Because Q1 = Q3 = 1, the IQR is zero, making the "
                "bounds [1, 1]. This would drop all 2,801 repeat customers (3% of the dataset), "
                "removing the very customers who make segmentation interesting."))
    s.append(bl("<b>Monetary's IQR drops 7.9%</b> — The IQR bounds [−116, 362] would remove 7,402 "
                "customers, a significant loss of high-value segment data."))
    s.append(Spacer(1, 4))
    s.append(p("Percentile capping preserves <b>all 93,357 customers</b> while bounding extreme values. "
               "The 1st/99th percentile thresholds remove influence from the most extreme 2% of each tail "
               "without deleting any rows."))
    s.append(Spacer(1, 6))

    s.append(h2("7.2  Per-Feature Capping Details"))

    cap_data = [
        ["Feature", "1st Pctl", "99th Pctl", "Rows\nClipped", "Effect"],
        ["Recency", "58 days", "624 days", "1,798\n(1.9%)",
         "Trims ultra-recent (< 2 months) and\nvery old (> 20 months) extremes"],
        ["Frequency", "1 order", "2 orders", "228\n(0.2%)",
         "Caps rare 3–15 order customers to 2;\npreserves the binary split"],
        ["Monetary", "€22.80", "€1,097", "1,862\n(2.0%)",
         "Bounds the €13,664 max to €1,097;\nreduces skew from 9.21 to 3.17"],
    ]
    s.append(make_table(cap_data, [60, 55, 55, 55, 195]))
    s.append(Spacer(1, 6))

    s.append(h3("Recency"))
    s.append(p("Recency has very few outliers (IQR method finds only 6). Percentile capping clips "
               "1,798 values at both tails. The distribution shape barely changes (skew 0.4473 → 0.4155) "
               "because recency is already roughly uniform. Capping here is a precaution for Box-Cox stability."))

    s.append(h3("Frequency"))
    s.append(p("After capping at the 99th percentile (= 2), the 228 customers with 3–15 orders are capped "
               "to 2. This leaves exactly 2 unique values: {1, 2}. The near-binary nature of frequency "
               "(97% = 1, 3% = 2) is a fundamental characteristic of this marketplace — most customers "
               "are one-time buyers — not an artifact of the capping."))

    s.append(h3("Monetary"))
    s.append(p("This feature benefits most from capping. The raw max (€13,664) is 127× the median, "
               "creating a tail that dominates Euclidean distance. After capping to €1,097, the skew "
               "drops from 9.21 to 3.17 — still heavy, but now manageable for Box-Cox."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 8: Power Transforms
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("8. Power Transforms"))
    s.append(p("K-Means assumes roughly spherical clusters, which requires features to be approximately "
               "symmetric (low skewness). Power transforms reduce skewness by applying a monotonic "
               "nonlinear function y = f(x) that compresses the long tail."))
    s.append(Spacer(1, 4))

    s.append(h2("8.1  Box-Cox Transform"))
    s.append(p("The Box-Cox transform is defined as:"))
    s.append(code(
        "y = (x<sup>λ</sup> − 1) / λ &nbsp;&nbsp;&nbsp; if λ ≠ 0<br/>"
        "y = ln(x) &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; if λ = 0"
    ))
    s.append(p("<b>Requirement:</b> All values must be strictly positive (x &gt; 0). This holds for "
               "recency (min = 58 days) and monetary (min = €22.80) after capping."))
    s.append(p("<b>How λ is chosen:</b> SciPy's <i>boxcox()</i> uses Maximum Likelihood Estimation (MLE) — "
               "it searches over λ values to find the one that makes the transformed distribution closest "
               "to Gaussian. This is not a manual choice; the algorithm optimises λ analytically."))
    s.append(Spacer(1, 8))

    # ── RECENCY ──
    s.append(h2("8.2  Recency: Box-Cox (λ = 0.4510)"))
    s.append(Spacer(1, 4))
    s.append(img("recency_pipeline.png", w=470))
    s.append(caption("Figure 2: Recency transformation pipeline — capped → Box-Cox → Z-score."))
    s.append(Spacer(1, 4))

    rec_data = [
        ["Stage", "Skewness", "Min", "Max", "Notes"],
        ["After capping", "0.4155", "58.0", "624.0", "Mild right skew, already decent"],
        ["After Box-Cox (λ=0.45)", "−0.0879", "7.28", "24.31",
         "Near-zero skew; λ≈0.5 is close to √x"],
        ["After Z-score", "−0.0879", "−1.93", "1.99", "Centred at 0, unit variance"],
    ]
    s.append(make_table(rec_data, [80, 60, 45, 50, 205]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Why Box-Cox works well here:</b> Recency was only mildly skewed (0.42), so Box-Cox "
               "with λ = 0.45 (approximately a square-root transform) gently compresses the right tail. "
               "The result is nearly perfectly symmetric (skew = −0.09)."))

    # ── MONETARY ──
    s.append(h2("8.3  Monetary: Box-Cox (λ = −0.1915)"))
    s.append(Spacer(1, 4))
    s.append(img("monetary_pipeline.png", w=470))
    s.append(caption("Figure 3: Monetary transformation pipeline — capped → Box-Cox → Z-score."))
    s.append(Spacer(1, 4))

    mon_data = [
        ["Stage", "Skewness", "Min", "Max", "Notes"],
        ["After capping", "3.1677", "22.80", "1,097.10", "Heavy right skew, long tail"],
        ["After Box-Cox (λ=−0.19)", "0.0171", "−1.58", "−0.63",
         "Near-zero skew; negative λ → reciprocal-like"],
        ["After Z-score", "0.0171", "−2.98", "3.85", "Centred at 0, unit variance"],
    ]
    s.append(make_table(mon_data, [80, 60, 50, 55, 195]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Why Box-Cox works well here:</b> Monetary had severe skew (3.17). The MLE-optimal "
               "λ = −0.19 applies a transform close to −1/x<sup>0.19</sup>, aggressively compressing "
               "the long tail of high-spend values. The result is near-perfectly symmetric (skew = 0.02)."))
    s.append(p("<b>Why not log transform?</b> Log (λ=0) was considered but λ = −0.19 achieves lower "
               "skew. Box-Cox with MLE finds the globally optimal λ rather than restricting to the "
               "special case of log. Since all values are positive, Box-Cox is strictly more general."))

    # ── FREQUENCY ──
    s.append(PageBreak())
    s.append(h2("8.4  Frequency: Transform SKIPPED"))
    s.append(Spacer(1, 4))
    s.append(img("frequency_pipeline.png", w=400))
    s.append(caption("Figure 4: Frequency pipeline — no power transform applied."))
    s.append(Spacer(1, 4))

    s.append(p("<b>Why skipped:</b> After capping, frequency has only <b>2 unique values</b> "
               "(1 and 2). Applying Box-Cox to a near-binary feature is mathematically degenerate:"))
    s.append(bl("The MLE optimiser finds an extreme λ (e.g., λ = −52) because the likelihood "
                "surface is flat — there is no meaningful 'shape' to normalise in a two-point distribution."))
    s.append(bl("The transformed skewness remains unchanged (5.51) because no monotonic transform "
                "can reshape a 97%/3% binary split into a symmetric distribution."))
    s.append(bl("The pipeline guards against this with a <b>MIN_UNIQUE_FOR_TRANSFORM = 10</b> "
                "threshold: any feature with fewer than 10 unique values after capping is passed "
                "through to StandardScaler unchanged."))
    s.append(Spacer(1, 4))
    s.append(note("This is not a limitation of the pipeline — it reflects a genuine data "
                   "characteristic: 97% of Olist customers are one-time buyers. Frequency acts as a "
                   "near-binary indicator (bought once vs bought again), and StandardScaler handles "
                   "binary features correctly by centring and scaling."))

    freq_data = [
        ["Value", "Count", "Percentage", "After Z-score"],
        ["1 (one-time)", "90,556", "97.0%", "−0.171"],
        ["2 (repeat)", "2,801", "3.0%", "+5.68"],
    ]
    s.append(make_table(freq_data, [85, 70, 75, 85]))

    # ═══════════════════════════════════════════════════════════
    # SECTION 9: Z-Score Standardisation
    # ═══════════════════════════════════════════════════════════
    s.append(h1("9. Z-Score Standardisation"))
    s.append(p("After power transforms, each feature has a different scale and unit. Z-score "
               "standardisation (StandardScaler) centres each feature to mean = 0 and scales to "
               "standard deviation = 1:"))
    s.append(Spacer(1, 2))
    s.append(code("z = (x − μ) / σ"))
    s.append(Spacer(1, 4))

    s.append(h2("9.1  Why Z-Score After Power Transforms?"))
    s.append(bl("<b>K-Means uses Euclidean distance</b> — If features have different scales, the "
                "feature with the largest variance dominates distance calculations. A 100-unit "
                "difference in monetary would overwhelm a 1-unit difference in frequency, making "
                "K-Means cluster almost entirely on monetary."))
    s.append(bl("<b>Power transforms fix shape, not scale</b> — Box-Cox makes distributions "
                "symmetric but doesn't equalise their variances. Recency after Box-Cox ranges "
                "[7.28, 24.31] while monetary ranges [−1.58, −0.63]. Without standardisation, "
                "recency would dominate by 25:1."))
    s.append(bl("<b>PCA requires centred data</b> — PCA computes the covariance matrix, which "
                "assumes features are centred at zero. Without centring, the first principal "
                "component would capture the mean offset rather than the direction of maximum variance."))
    s.append(Spacer(1, 4))

    s.append(h2("9.2  Why Z-Score Over Other Scalers?"))
    std_comp = [
        ["Method", "When to Use", "Why Not Here"],
        ["Z-score\n(StandardScaler)", "When features are\napprox. Gaussian after\ntransform", "USED — features are\nnear-Gaussian after\nBox-Cox"],
        ["Min-Max\n[0, 1]", "When you need bounded\noutputs (e.g., neural nets)", "Sensitive to outliers;\ncompresses bulk of data\ninto narrow range"],
        ["Robust Scaler\n(IQR-based)", "When outliers remain\nafter cleaning", "Outliers already capped;\nZ-score is more natural\nfor Gaussian data"],
    ]
    s.append(make_table(std_comp, [85, 120, 140]))
    s.append(Spacer(1, 6))

    s.append(h2("9.3  Per-Feature After Standardisation"))
    std_data = [
        ["Feature", "Mean", "Std", "Min", "Max", "Pre-Z Shape"],
        ["Recency", "0.0000", "1.0000", "−1.93", "1.99", "Symmetric (Box-Cox, λ=0.45)"],
        ["Frequency", "0.0000", "1.0000", "−0.17", "5.68", "Binary (97%/3% split, no transform)"],
        ["Monetary", "0.0000", "1.0000", "−2.98", "3.85", "Symmetric (Box-Cox, λ=−0.19)"],
    ]
    s.append(make_table(std_data, [60, 50, 45, 40, 40, 175]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Verification:</b> All three features now have mean ≈ 0 and std ≈ 1, confirming "
               "equal contribution to Euclidean distance in K-Means and equal weight in PCA's "
               "covariance matrix."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 10: Interaction Terms
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("10. Interaction Terms — Why Not Used"))
    s.append(p("Interaction terms (e.g., frequency × monetary, recency × frequency) were considered "
               "but deliberately not included. Here is the reasoning:"))
    s.append(Spacer(1, 4))

    s.append(h2("10.1  K-Means Cannot Exploit Interactions"))
    s.append(p("K-Means partitions data based on Euclidean distance to centroids. It draws linear "
               "decision boundaries in feature space. Adding interaction terms would increase "
               "dimensionality from 3 to 6+ features (R, F, M, R×F, R×M, F×M) without enabling "
               "K-Means to discover more complex boundaries — it would still draw hyperplanes, "
               "just in a higher-dimensional space. The extra dimensions would dilute cluster "
               "separation (curse of dimensionality) and make the results harder to interpret."))

    s.append(h2("10.2  PCA Already Captures Linear Combinations"))
    s.append(p("PCA decomposes the feature space into orthogonal linear combinations of R, F, and M. "
               "The principal components <i>are</i> weighted combinations of the original features — "
               "PC1 = 0.70×frequency + 0.70×monetary − 0.13×recency already captures the "
               "frequency-monetary interaction. Adding explicit interaction terms before PCA would "
               "introduce multicollinearity (F×M is correlated with both F and M), inflating the "
               "covariance matrix without adding independent information."))

    s.append(h2("10.3  Only 3 Original Features"))
    s.append(p("With only 3 input features, the feature space is already low-dimensional. Interaction "
               "terms are most valuable when the feature space is rich enough to hide nonlinear "
               "relationships (e.g., 50+ features in a tabular ML model). In a 3-feature RFM space, "
               "the relationships are transparent and well-captured by PCA's linear combinations."))

    s.append(h2("10.4  Interpretability Would Suffer"))
    s.append(p("One of the project's goals is that segment profiles are interpretable by non-technical "
               "stakeholders. A cluster described as 'high recency, low frequency, medium monetary' "
               "is actionable. A cluster described as 'high recency×frequency interaction' is not. "
               "Adding interaction terms would obscure the SHAP explanations and make the segment "
               "heatmap unreadable."))
    s.append(Spacer(1, 6))

    s.append(note("If the clustering algorithm were a kernel-based method (e.g., Spectral Clustering) "
                   "or a tree-based model (e.g., using cluster labels as a supervised target), interaction "
                   "terms would be handled implicitly by the algorithm. For K-Means + PCA, they add noise "
                   "rather than signal."))

    # ── Build ──
    doc.build(s)
    print(f"PDF saved: {OUTPUT}")


if __name__ == "__main__":
    build()
