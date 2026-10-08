"""Generate PDF: Problem Statement & Approach."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

OUTPUT = "docs/01_problem_statement.pdf"

ACCENT = HexColor("#1D9E75")
DARK = HexColor("#1a1a2e")
GREY = HexColor("#444444")
LIGHT_BG = HexColor("#f0f7f4")
WHITE = HexColor("#ffffff")
BORDER = HexColor("#cccccc")

styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    "DocTitle", parent=styles["Title"], fontSize=22, leading=28,
    textColor=DARK, spaceAfter=4, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    "DocSubtitle", parent=styles["Normal"], fontSize=11, leading=14,
    textColor=GREY, alignment=TA_CENTER, spaceAfter=20,
))
styles.add(ParagraphStyle(
    "SectionHead", parent=styles["Heading1"], fontSize=15, leading=20,
    textColor=ACCENT, spaceBefore=22, spaceAfter=8,
    borderPadding=(0, 0, 2, 0),
))
styles.add(ParagraphStyle(
    "SubHead", parent=styles["Heading2"], fontSize=12, leading=16,
    textColor=DARK, spaceBefore=14, spaceAfter=6,
))
styles.add(ParagraphStyle(
    "Body", parent=styles["Normal"], fontSize=10.5, leading=15,
    textColor=GREY, alignment=TA_JUSTIFY, spaceAfter=8,
))
styles.add(ParagraphStyle(
    "BulletItem", parent=styles["Normal"], fontSize=10.5, leading=15,
    textColor=GREY, leftIndent=18, spaceAfter=4,
    bulletIndent=6, bulletFontSize=10,
))
styles.add(ParagraphStyle(
    "BulletSubItem", parent=styles["Normal"], fontSize=10, leading=14,
    textColor=GREY, leftIndent=36, spaceAfter=3,
    bulletIndent=24, bulletFontSize=9,
))

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6, spaceBefore=2)

def heading(text):
    return Paragraph(text, styles["SectionHead"])

def subheading(text):
    return Paragraph(text, styles["SubHead"])

def body(text):
    return Paragraph(text, styles["Body"])

def bullet(text):
    return Paragraph(f"•  {text}", styles["BulletItem"])

def sub_bullet(text):
    return Paragraph(f"–  {text}", styles["BulletSubItem"])


def build():
    doc = SimpleDocTemplate(
        OUTPUT, pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    story = []

    # ── Title ──
    story.append(Paragraph(
        "RFM Customer Segmentation Using<br/>Unsupervised Machine Learning",
        styles["DocTitle"],
    ))
    story.append(Paragraph(
        "Problem Statement &amp; Solution Approach",
        styles["DocSubtitle"],
    ))
    story.append(hr())
    story.append(Spacer(1, 6))

    # ── SECTION 1: Problem Statement ──
    story.append(heading("1. Problem Statement"))
    story.append(body(
        "In e-commerce, businesses accumulate millions of transactional records daily, yet most "
        "marketing strategies treat the entire customer base as a single homogeneous group. This "
        "one-size-fits-all approach leads to wasted marketing spend, poor customer retention, and "
        "missed revenue opportunities. Without a data-driven understanding of customer behaviour "
        "patterns, businesses cannot identify which customers are their most valuable, which are "
        "at risk of churning, and which have already become dormant."
    ))
    story.append(Spacer(1, 4))
    story.append(body(
        "<b>Formal Problem Statement:</b> Given a transactional dataset of 100,000+ e-commerce "
        "orders from the Olist Brazilian marketplace, develop an end-to-end unsupervised machine "
        "learning pipeline that (1) engineers Recency, Frequency, and Monetary (RFM) behavioural "
        "features from raw transaction logs, (2) reduces dimensionality via Principal Component "
        "Analysis to produce an orthogonal, visualisable feature space, (3) discovers natural "
        "customer segments through K-Means clustering with rigorous hyperparameter optimisation, "
        "and (4) profiles each segment with interpretable business labels and SHAP-based "
        "explainability, enabling targeted marketing strategies."
    ))

    # ── SECTION 2: What Problem Are We Trying to Solve? ──
    story.append(heading("2. What Problem Are We Trying to Solve?"))
    story.append(body(
        "The project addresses three interconnected challenges that e-commerce businesses face "
        "when trying to understand and act on customer behaviour:"
    ))
    story.append(Spacer(1, 4))

    story.append(subheading("2.1  Customer Heterogeneity Is Invisible in Raw Data"))
    story.append(body(
        "Raw transactional tables contain order timestamps, payment amounts, and product IDs, "
        "but they do not reveal behavioural patterns. A customer who placed one large order six "
        "months ago looks identical in a flat table to a customer who places small orders every "
        "week. Without engineered behavioural features, there is no axis along which to compare "
        "customers meaningfully."
    ))
    story.append(bullet(
        "<b>Recency</b> — How many days since the customer's last purchase? A proxy for "
        "engagement. Customers who bought recently are more likely to buy again."
    ))
    story.append(bullet(
        "<b>Frequency</b> — How many distinct orders has the customer placed? Measures "
        "loyalty and repeat-purchase behaviour."
    ))
    story.append(bullet(
        "<b>Monetary</b> — What is the customer's total lifetime spend? Captures "
        "economic value to the business."
    ))
    story.append(Spacer(1, 2))
    story.append(body(
        "These three metrics together capture the full spectrum of customer value: when they buy, "
        "how often they buy, and how much they spend."
    ))

    story.append(subheading("2.2  High-Dimensional, Skewed Features Resist Direct Clustering"))
    story.append(body(
        "Raw RFM distributions are heavily right-skewed (e.g., monetary skewness = 3.17 in this "
        "dataset) and contain extreme outliers (max monetary = €13,664 vs median = €108). "
        "Clustering algorithms like K-Means rely on Euclidean distance, which is distorted by "
        "skewed scales — a single high-spend outlier can pull an entire cluster centroid. "
        "Additionally, correlated features (frequency and monetary, r = 0.16) introduce "
        "redundant dimensions that dilute cluster separation."
    ))
    story.append(bullet(
        "<b>Skewness</b> must be reduced through power transforms (Box-Cox / Yeo-Johnson) "
        "before standardisation."
    ))
    story.append(bullet(
        "<b>Outliers</b> must be capped (not dropped) to preserve sample size while bounding "
        "extreme values."
    ))
    story.append(bullet(
        "<b>Correlation</b> between features must be resolved through PCA to produce orthogonal "
        "axes that maximise variance in fewer dimensions."
    ))

    story.append(subheading("2.3  The Number of Segments Is Unknown"))
    story.append(body(
        "Unlike supervised learning where labels are given, customer segmentation is an "
        "unsupervised problem — we do not know in advance how many natural groups exist. "
        "Choosing too few clusters merges distinct behaviours; too many creates "
        "unactionable micro-segments. The optimal K must be determined empirically using "
        "multiple validation metrics (Silhouette Score, Calinski-Harabasz Index, "
        "Davies-Bouldin Index) and compared against density-based alternatives (DBSCAN) "
        "to ensure the chosen algorithm fits the data's geometry."
    ))

    story.append(subheading("2.4  Clusters Must Be Interpretable, Not Just Statistical"))
    story.append(body(
        "A cluster label like \"Cluster 0\" is meaningless to a marketing team. Each discovered "
        "segment needs a human-readable business label (Champions, Potential Loyalists, "
        "At-Risk Spenders, Hibernating) and quantitative profiles showing what drives "
        "membership. SHAP explainability via a proxy Random Forest classifier reveals which "
        "RFM features most influence each segment's identity, turning statistical clusters "
        "into actionable business intelligence."
    ))

    # ── SECTION 3: How Are We Trying to Solve It? ──
    story.append(heading("3. How Are We Trying to Solve It?"))
    story.append(body(
        "The solution is a four-phase production Python pipeline, where each phase addresses "
        "one of the challenges above. The phases execute sequentially, with each phase's "
        "output feeding directly into the next:"
    ))
    story.append(Spacer(1, 4))

    # Phase 1
    story.append(subheading("Phase 1: RFM Feature Engineering"))
    story.append(body("<b>Goal:</b> Transform 100K raw transaction records into 93,357 "
                      "customer-level behavioural profiles."))
    story.append(Spacer(1, 2))

    story.append(bullet("<b>Data loading &amp; joining</b> — Three CSV files "
                        "(orders, customers, payments) are joined on order_id and customer_id. "
                        "Only delivered orders are retained (96,478 of 99,441)."))
    story.append(bullet("<b>RFM aggregation</b> — For each unique customer: "
                        "Recency = days since last purchase (relative to 18 Oct 2018), "
                        "Frequency = count of distinct orders, "
                        "Monetary = sum of all payment values."))
    story.append(bullet("<b>Outlier capping</b> — Values beyond the 1st and 99th "
                        "percentiles are clipped (not dropped), preserving all 93,357 customers "
                        "while bounding extremes."))
    story.append(bullet("<b>Power transforms</b> — Box-Cox is applied to recency "
                        "(λ=0.45, skew 0.42→0.09) and monetary (λ=−0.19, "
                        "skew 3.17→0.02). Frequency is skipped (only 2 unique values after "
                        "capping — 97% of customers are one-time buyers)."))
    story.append(bullet("<b>Z-score standardisation</b> — StandardScaler centres all "
                        "features to mean=0, std=1, ensuring equal contribution to distance-based "
                        "algorithms."))

    story.append(Spacer(1, 2))
    story.append(body("<b>Output:</b> rfm_raw.csv (original-scale profiles for later interpretation) "
                      "and rfm_scaled.csv (transformed + standardised features for PCA/clustering)."))

    # Phase 2
    story.append(subheading("Phase 2: PCA Dimensionality Reduction"))
    story.append(body("<b>Goal:</b> Decorrelate features and project into a 2D space for "
                      "clustering and visualisation."))
    story.append(Spacer(1, 2))

    story.append(bullet("<b>Correlation analysis</b> — Post-transform correlation matrix "
                        "confirms features are weakly correlated (max |r| = 0.16), meaning "
                        "variance is spread across all 3 components."))
    story.append(bullet("<b>Full PCA decomposition</b> — PCA is fit once on all 3 "
                        "components, then sliced to 2. This avoids redundant refitting while "
                        "providing the complete scree plot for documentation."))
    story.append(bullet("<b>Variance retention</b> — 2 components capture 72% of total "
                        "variance. While below the conventional 90% threshold, this is because "
                        "the features are genuinely weakly correlated after transforms — not "
                        "a sign of information loss. The 72% is sufficient for cluster separation "
                        "(silhouette = 0.41)."))
    story.append(bullet("<b>Component interpretation</b> — PC1 = spending behaviour "
                        "(frequency + monetary loadings ≈ 0.70 each), PC2 = recency "
                        "(loading = 0.99). This gives the scatter plot meaningful axes."))

    story.append(Spacer(1, 2))
    story.append(body("<b>Output:</b> pca_transformed.csv (93,357 customers × 2 principal "
                      "components), pca_loadings.csv, pca_variance.csv."))

    # Phase 3
    story.append(subheading("Phase 3: K-Means Clustering with DBSCAN Benchmark"))
    story.append(body("<b>Goal:</b> Discover the optimal number of customer segments and "
                      "assign every customer to a cluster."))
    story.append(Spacer(1, 2))

    story.append(bullet("<b>Multi-metric elbow analysis</b> — K-Means is run for "
                        "K=2 through K=10. Four metrics are computed at each K: Inertia (WCSS), "
                        "Silhouette Score, Calinski-Harabasz Index, Davies-Bouldin Index."))
    story.append(bullet("<b>Optimal K selection</b> — K=3 is selected as the silhouette-optimal "
                        "value (score = 0.41). Silhouette is used as the primary metric because it "
                        "directly measures cluster cohesion vs separation without requiring "
                        "ground-truth labels."))
    story.append(bullet("<b>Final K-Means fit</b> — K-Means with K=3, n_init=20 "
                        "(20 random initialisations to avoid local minima), deterministic seed. "
                        "Cluster sizes: 42,865 / 2,801 / 47,691 customers."))
    story.append(bullet("<b>DBSCAN comparison</b> — A density-based benchmark is run "
                        "with multi-eps grid search across the 75th–95th percentiles of "
                        "k-NN distances. Best DBSCAN result: 5 clusters, silhouette = 0.20. "
                        "K-Means clearly outperforms (0.41 vs 0.20), confirming the data has "
                        "roughly spherical cluster geometry that suits centroid-based methods."))

    story.append(Spacer(1, 2))
    story.append(body("<b>Output:</b> clustered_customers.csv (each customer's cluster label), "
                      "clustering_metrics.csv, cluster_centroids.csv, algorithm_comparison.csv."))

    # Phase 4
    story.append(subheading("Phase 4: Segment Profiling & SHAP Explainability"))
    story.append(body("<b>Goal:</b> Translate statistical clusters into actionable business "
                      "segments with interpretable labels and feature-importance explanations."))
    story.append(Spacer(1, 2))

    story.append(bullet("<b>Profile table</b> — Cluster labels are merged back to "
                        "original-scale RFM values (not transformed/scaled) so that profiles "
                        "are in human-readable units (days, order count, currency)."))
    story.append(bullet("<b>Segment labelling</b> — Each cluster's RFM means are normalised "
                        "to [0, 1] across clusters. A recency score (inverted: lower recency = "
                        "higher score) and a value score (average of normalised frequency + "
                        "monetary) determine the label:"))
    story.append(sub_bullet("<b>Champions</b> — Recent + high value (R ≥ 0.5, V ≥ 0.5)"))
    story.append(sub_bullet("<b>Potential Loyalists</b> — Recent + low value (R ≥ 0.5, V &lt; 0.5)"))
    story.append(sub_bullet("<b>At-Risk Spenders</b> — Not recent + high value (R &lt; 0.5, V ≥ 0.5)"))
    story.append(sub_bullet("<b>Hibernating</b> — Not recent + low value (R &lt; 0.5, V &lt; 0.5)"))
    story.append(Spacer(1, 2))
    story.append(bullet("<b>SHAP explainability</b> — A Random Forest proxy classifier is "
                        "trained on original RFM features to predict cluster membership "
                        "(5-fold CV accuracy: 99.99%). SHAP TreeExplainer then quantifies each "
                        "feature's contribution to each cluster's identity. Key finding: "
                        "recency is the dominant driver (SHAP = 0.478) for separating "
                        "Potential Loyalists from Hibernating, while frequency distinguishes "
                        "Champions (SHAP = 0.057)."))

    story.append(Spacer(1, 2))
    story.append(body("<b>Output:</b> segment_profiles.csv, shap_importance.csv, plus 8 diagnostic "
                      "and presentation plots."))

    # ── Results summary table ──
    story.append(heading("4. Discovered Segments"))
    story.append(body("The pipeline identifies three distinct customer segments:"))
    story.append(Spacer(1, 6))

    table_data = [
        ["Segment", "Count", "%", "Recency\n(days)", "Frequency\n(orders)", "Monetary\n(€)"],
        ["Potential Loyalists", "42,865", "45.9%", "155", "1.0", "154"],
        ["Champions", "2,801", "3.0%", "269", "2.0", "295"],
        ["Hibernating", "47,691", "51.1%", "405", "1.0", "156"],
    ]

    col_widths = [95, 52, 38, 55, 62, 58]
    t = Table(table_data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    story.append(Spacer(1, 10))
    story.append(body(
        "<b>Key insight:</b> 97% of Olist customers are one-time buyers (frequency = 1), "
        "making recency the primary differentiator between segments. The 3% who return "
        "(Champions) spend nearly 2× more per visit and represent the highest lifetime value. "
        "This directly informs strategy: retention campaigns for Potential Loyalists, "
        "win-back campaigns for Hibernating, and loyalty rewards for Champions."
    ))

    # ── Tech Stack ──
    story.append(heading("5. Technology Stack"))
    story.append(Spacer(1, 4))

    tech_data = [
        ["Layer", "Tools"],
        ["Data Processing", "pandas, NumPy"],
        ["Statistical Transforms", "SciPy (Box-Cox, Yeo-Johnson)"],
        ["Machine Learning", "scikit-learn (PCA, K-Means, DBSCAN, StandardScaler, RandomForest)"],
        ["Explainability", "SHAP (TreeExplainer)"],
        ["Visualisation", "Matplotlib, Seaborn"],
        ["Runtime", "Python 3.9+, modular CLI pipeline"],
    ]

    t2 = Table(tech_data, colWidths=[110, 250], repeatRows=1)
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_BG]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)

    doc.build(story)
    print(f"PDF saved: {OUTPUT}")


if __name__ == "__main__":
    build()
