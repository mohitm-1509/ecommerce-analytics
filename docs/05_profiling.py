"""Generate PDF: Phase 4 — Segment Profiling & SHAP Explainability."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    Image, KeepTogether, PageBreak,
)

OUTPUT = "docs/05_profiling.pdf"
PLOT_DIR = "/private/tmp/claude-501/-Users-mohitmalhotra-PycharmProjects/phase4_plots"

ACCENT = HexColor("#0E8A7D")
DARK = HexColor("#1a1a2e")
GREY = HexColor("#444444")
LIGHT_BG = HexColor("#f0faf8")
WHITE = HexColor("#ffffff")
BORDER = HexColor("#cccccc")
WARN_BG = HexColor("#fff8e1")
WARN_BORDER = HexColor("#f9a825")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DT4", parent=styles["Title"], fontSize=22, leading=28,
                          textColor=DARK, spaceAfter=4, alignment=TA_CENTER))
styles.add(ParagraphStyle("DS4", parent=styles["Normal"], fontSize=11, leading=14,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle("H1p", parent=styles["Heading1"], fontSize=15, leading=20,
                          textColor=ACCENT, spaceBefore=22, spaceAfter=8))
styles.add(ParagraphStyle("H2p", parent=styles["Heading2"], fontSize=12, leading=16,
                          textColor=DARK, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("H3p", parent=styles["Heading3"], fontSize=10.5, leading=14,
                          textColor=HexColor("#065e55"), spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle("Bp", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("BLp", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, leftIndent=18, spaceAfter=4, bulletIndent=6))
styles.add(ParagraphStyle("BLSp", parent=styles["Normal"], fontSize=10, leading=14,
                          textColor=GREY, leftIndent=36, spaceAfter=3, bulletIndent=24))
styles.add(ParagraphStyle("CDp", parent=styles["Normal"], fontSize=9, leading=12,
                          fontName="Courier", textColor=HexColor("#333333"),
                          backColor=HexColor("#f5f5f5"), leftIndent=12, rightIndent=12,
                          spaceBefore=4, spaceAfter=8, borderPadding=6))
styles.add(ParagraphStyle("CAPp", parent=styles["Normal"], fontSize=9, leading=12,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=10, spaceBefore=4))
styles.add(ParagraphStyle("NTp", parent=styles["Normal"], fontSize=9.5, leading=13,
                          textColor=HexColor("#7a6c00"), leftIndent=10, rightIndent=10,
                          spaceBefore=6, spaceAfter=10, backColor=WARN_BG,
                          borderColor=WARN_BORDER, borderWidth=0.5, borderPadding=8))

def hr(): return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6, spaceBefore=2)
def h1(t): return Paragraph(t, styles["H1p"])
def h2(t): return Paragraph(t, styles["H2p"])
def h3(t): return Paragraph(t, styles["H3p"])
def p(t): return Paragraph(t, styles["Bp"])
def bl(t): return Paragraph(f"•  {t}", styles["BLp"])
def bls(t): return Paragraph(f"–  {t}", styles["BLSp"])
def code(t): return Paragraph(t, styles["CDp"])
def caption(t): return Paragraph(t, styles["CAPp"])
def note(t): return Paragraph(f"<b>Note:</b> {t}", styles["NTp"])

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

def img(name, w=480, ratio=0.75):
    return Image(f"{PLOT_DIR}/{name}", width=w, height=w*ratio)


def build():
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
                            leftMargin=22*mm, rightMargin=22*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    s = []

    # ── Title ──
    s.append(Paragraph("Phase 4: Segment Profiling", styles["DT4"]))
    s.append(Paragraph("& SHAP Explainability — Detailed Technical Report", styles["DS4"]))
    s.append(hr())
    s.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: What Is Segment Profiling?
    # ═══════════════════════════════════════════════════════════
    s.append(h1("1. What Is Segment Profiling?"))
    s.append(p("After K-Means assigned each of the 93,357 customers to one of 3 clusters (Phase 3), "
               "the clusters are just numbered labels — Cluster 0, 1, 2 — with no business meaning. "
               "Phase 4 transforms these numerical labels into actionable customer segments by:"))
    s.append(Spacer(1, 4))
    s.append(bl("<b>Building statistical profiles:</b> Computing the mean, median, and standard "
                "deviation of raw RFM values (Recency, Frequency, Monetary) per cluster — translating "
                "abstract cluster assignments back into interpretable business metrics."))
    s.append(bl("<b>Assigning human-readable labels:</b> Using normalised RFM thresholds to assign "
                "names like 'Champions', 'Potential Loyalists', and 'Hibernating' — making each "
                "cluster immediately understandable to a non-technical stakeholder."))
    s.append(bl("<b>Explaining with SHAP:</b> Using SHAP (SHapley Additive exPlanations) to quantify "
                "which RFM feature drives each cluster's identity — providing model-agnostic "
                "feature importance at the per-segment level."))
    s.append(Spacer(1, 6))

    s.append(h2("1.1  Why Is Profiling Necessary?"))
    s.append(p("Clustering algorithms optimise mathematical objectives (minimise WCSS, maximise "
               "silhouette) but do not assign meaning. A marketing team cannot act on 'Cluster 2' "
               "— they need to know that Cluster 2 represents 'customers who purchased once over "
               "a year ago and may have churned'. Profiling bridges the gap between unsupervised "
               "learning output and business-actionable intelligence."))
    s.append(Spacer(1, 4))

    s.append(h2("1.2  Pipeline Context"))
    s.append(p("Phase 4 receives two inputs:"))
    s.append(bl("<b>clustered_customers.csv:</b> 93,357 rows with customer_id, PC1, PC2, and cluster "
                "label (0, 1, or 2) — the output of K-Means from Phase 3."))
    s.append(bl("<b>rfm_raw.csv:</b> 93,357 rows with customer_id, recency (days since last purchase), "
                "frequency (order count), and monetary (total spend in BRL) — the raw RFM features "
                "from Phase 1, before any transformation or scaling."))
    s.append(Spacer(1, 4))
    s.append(p("By merging these on customer_id, we can compute raw RFM statistics per cluster and "
               "assign labels based on the actual business meaning of each cluster's customers."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: Profiling Methodology
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("2. Profiling Methodology"))

    s.append(h2("2.1  Building the Profile Table"))
    s.append(p("The profiling function merges clustered customers with raw RFM values and computes "
               "aggregate statistics per cluster:"))
    s.append(Spacer(1, 4))
    s.append(code(
        "merged = clustered.merge(rfm_raw, on='customer_id')<br/>"
        "profile = merged.groupby('cluster').agg(<br/>"
        "&nbsp;&nbsp;recency  = ('recency',  'mean'),<br/>"
        "&nbsp;&nbsp;frequency= ('frequency', 'mean'),<br/>"
        "&nbsp;&nbsp;monetary = ('monetary',  'mean'),<br/>"
        "&nbsp;&nbsp;count    = ('customer_id','count')<br/>"
        ")"
    ))
    s.append(Spacer(1, 4))
    s.append(p("This gives us the mean RFM values per cluster, which we use to understand each "
               "segment's behavioural profile:"))
    s.append(Spacer(1, 4))

    profile_data = [
        ["Cluster", "Recency\n(days)", "Frequency\n(orders)", "Monetary\n(BRL)", "Count", "% of\nTotal"],
        ["0", "155.0", "1.0", "153.7", "42,865", "45.9%"],
        ["1", "268.6", "2.0", "294.7", "2,801", "3.0%"],
        ["2", "405.0", "1.0", "156.0", "47,691", "51.1%"],
    ]
    s.append(make_table(profile_data, [50, 65, 65, 65, 55, 50]))
    s.append(Spacer(1, 6))

    s.append(h2("2.2  Interpreting the Raw Profiles"))
    s.append(bl("<b>Cluster 0 (42,865 customers):</b> Low recency (155 days = recent), single purchase "
                "(frequency 1.0), moderate spend (BRL 154). These are customers who bought recently "
                "but only once — potential repeat buyers."))
    s.append(bl("<b>Cluster 1 (2,801 customers):</b> Medium recency (269 days), the only cluster with "
                "repeat purchases (frequency 2.0), and the highest spend (BRL 295). These are the "
                "most valuable customers."))
    s.append(bl("<b>Cluster 2 (47,691 customers):</b> High recency (405 days = long time ago), single "
                "purchase (frequency 1.0), moderate spend (BRL 156). These are lapsed customers "
                "who may have churned."))
    s.append(Spacer(1, 6))

    s.append(h2("2.3  Segment Heatmap"))
    s.append(p("The heatmap below visualises the normalised RFM profiles with raw value annotations. "
               "Colour intensity represents the min-max normalised value (0 to 1) across clusters "
               "for each feature, while the text annotations show the actual raw means."))
    s.append(Spacer(1, 4))
    s.append(img("segment_heatmap.png", w=480, ratio=0.48))
    s.append(caption("Figure 1: Normalised segment heatmap. Champions stand out with the highest "
                     "frequency and monetary values (dark cells). Hibernating has the highest "
                     "recency (darkest cell in recency column)."))
    s.append(Spacer(1, 4))
    s.append(note("In the heatmap, 'higher' always means 'more extreme'. For recency, a higher "
                   "value means more days since last purchase (i.e., less recent). For frequency and "
                   "monetary, higher means more purchases and more spending — which is desirable."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: Segment Labelling with Normalised Thresholds
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("3. Segment Labelling — Normalised Threshold Approach"))
    s.append(p("Raw cluster numbers (0, 1, 2) are meaningless to business stakeholders. We assign "
               "human-readable labels using a normalised threshold system that evaluates each "
               "cluster on two dimensions: <b>recency</b> (how recently they purchased) and "
               "<b>value</b> (how much they purchase)."))
    s.append(Spacer(1, 6))

    s.append(h2("3.1  How Normalisation Works"))
    s.append(p("For each cluster, we compute two normalised scores between 0 and 1:"))
    s.append(Spacer(1, 4))

    s.append(h3("Recency Score (r_norm) — Inverted"))
    s.append(code(
        "r_norm = 1 − (mean_recency − min_recency) / (max_recency − min_recency)"
    ))
    s.append(p("Recency is <b>inverted</b> because lower recency (fewer days since last purchase) "
               "is better. After inversion, r_norm = 1 means the most recent cluster, r_norm = 0 "
               "means the least recent."))
    s.append(Spacer(1, 4))

    s.append(h3("Value Score (v_norm) — Direct"))
    s.append(code(
        "f_norm = (mean_frequency − min_freq) / (max_freq − min_freq)<br/>"
        "m_norm = (mean_monetary − min_mon) / (max_mon − min_mon)<br/>"
        "v_norm = (f_norm + m_norm) / 2"
    ))
    s.append(p("Value is the average of normalised frequency and normalised monetary. Higher = more "
               "valuable. This captures both purchase volume and spend amount in a single metric."))
    s.append(Spacer(1, 6))

    s.append(h2("3.2  Computed Scores"))
    scores_data = [
        ["Cluster", "Mean\nRecency", "r_norm\n(inverted)", "Mean\nFrequency", "f_norm", "Mean\nMonetary",
         "m_norm", "v_norm\n(avg F+M)"],
        ["0", "155.0", "1.00", "1.0", "0.00", "153.7", "0.00", "0.00"],
        ["1", "268.6", "0.55", "2.0", "1.00", "294.7", "1.00", "1.00"],
        ["2", "405.0", "0.00", "1.0", "0.00", "156.0", "0.02", "0.01"],
    ]
    s.append(make_table(scores_data, [40, 42, 48, 48, 38, 48, 42, 55]))
    s.append(Spacer(1, 6))

    s.append(h2("3.3  Label Assignment Rules"))
    s.append(p("A threshold of <b>0.5</b> is applied to both scores:"))
    s.append(Spacer(1, 4))

    rules_data = [
        ["Condition", "Label", "Meaning"],
        ["r_norm ≥ 0.5 AND\nv_norm ≥ 0.5", "Champions", "Recent AND high value\n— best customers"],
        ["r_norm ≥ 0.5 AND\nv_norm < 0.5", "Potential\nLoyalists", "Recent but low value\n— nurture opportunities"],
        ["r_norm < 0.5", "Hibernating", "Not recent\n— lapsed customers"],
    ]
    s.append(make_table(rules_data, [110, 80, 200]))
    s.append(Spacer(1, 6))

    s.append(h2("3.4  Applying Rules to Our Clusters"))
    s.append(bl("<b>Cluster 0:</b> r_norm = 1.00 (≥ 0.5 ✓), v_norm = 0.00 (< 0.5 ✗) → "
                "<b>Potential Loyalists</b>. These are the most recent buyers, but they've only "
                "purchased once with moderate spend. They have the potential to become Champions "
                "with the right re-engagement."))
    s.append(bl("<b>Cluster 1:</b> r_norm = 0.55 (≥ 0.5 ✓), v_norm = 1.00 (≥ 0.5 ✓) → "
                "<b>Champions</b>. Both recency and value are above threshold. These are the "
                "repeat buyers with the highest monetary value — the most valuable 3%."))
    s.append(bl("<b>Cluster 2:</b> r_norm = 0.00 (< 0.5 ✗) → <b>Hibernating</b>. Recency alone "
                "disqualifies them — regardless of value, a customer who last purchased 405 days "
                "ago is lapsed. (Their value score is also near zero at 0.01.)"))
    s.append(Spacer(1, 6))

    s.append(h2("3.5  Labelling Decision Chart"))
    s.append(img("labelling_scores.png", w=480, ratio=0.50))
    s.append(caption("Figure 2: Normalised recency and value scores per cluster. The dashed red "
                     "line at 0.5 is the threshold. Cluster 0 crosses the threshold on recency "
                     "only (→ Potential Loyalists). Cluster 1 crosses both (→ Champions). "
                     "Cluster 2 crosses neither (→ Hibernating)."))
    s.append(Spacer(1, 4))
    s.append(note("The threshold of 0.5 is a natural midpoint on the normalised [0, 1] scale. It "
                   "divides clusters into 'above average' and 'below average' relative to the "
                   "cluster population. This approach is robust: it does not depend on rank ordering "
                   "(which can break with ties) or absolute thresholds (which vary across datasets)."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: SHAP Explainability
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("4. SHAP Explainability"))
    s.append(p("Cluster labels tell us <i>what</i> each segment looks like. SHAP (SHapley Additive "
               "exPlanations) tells us <i>why</i> — which RFM features are most important for "
               "distinguishing each segment from the others."))
    s.append(Spacer(1, 6))

    s.append(h2("4.1  Why SHAP?"))
    s.append(p("K-Means itself has no built-in feature importance measure. Unlike supervised models "
               "(e.g., Random Forest), unsupervised algorithms do not have a direct concept of "
               "'this feature matters more'. We need an external method to explain the clusters."))
    s.append(Spacer(1, 4))
    s.append(p("SHAP is based on Shapley values from cooperative game theory — a principled way to "
               "distribute a prediction among its input features. For each prediction, SHAP assigns "
               "a value to each feature representing how much that feature contributed to pushing "
               "the prediction away from the baseline (average prediction)."))
    s.append(Spacer(1, 4))

    shap_props = [
        ["Property", "Description"],
        ["Local accuracy", "SHAP values for a prediction sum to the\ndifference between prediction and baseline"],
        ["Consistency", "If a feature's contribution increases in a\nnew model, its SHAP value won't decrease"],
        ["Missingness", "Missing features get SHAP value = 0"],
        ["Additivity", "f(x) = base_value + Σ SHAP_i(x)"],
    ]
    s.append(make_table(shap_props, [100, 330]))
    s.append(Spacer(1, 6))

    s.append(h2("4.2  The Proxy Model Approach"))
    s.append(p("Since SHAP cannot be applied directly to K-Means, we train a <b>proxy classifier</b> "
               "that learns to predict the K-Means cluster labels from the raw RFM features. If the "
               "proxy is accurate, its SHAP values faithfully represent which features drive the "
               "clustering."))
    s.append(Spacer(1, 4))

    s.append(h3("Proxy Model: Random Forest Classifier"))
    s.append(bl("<b>Model:</b> RandomForestClassifier from scikit-learn"))
    s.append(bl("<b>n_estimators = 200</b> (200 decision trees in the ensemble)"))
    s.append(bl("<b>max_depth = 10</b> (each tree can be up to 10 levels deep)"))
    s.append(bl("<b>random_state = 42</b> (reproducibility)"))
    s.append(bl("<b>Input features:</b> recency, frequency, monetary (raw, unscaled values)"))
    s.append(bl("<b>Target:</b> K-Means cluster label (0, 1, or 2)"))
    s.append(Spacer(1, 4))

    s.append(h3("Why Random Forest?"))
    s.append(bl("Non-linear decision boundaries — captures complex RFM interactions"))
    s.append(bl("Compatible with SHAP's TreeExplainer — exact (not approximate) SHAP values"))
    s.append(bl("Robust to feature scale — raw RFM values can be used without standardisation"))
    s.append(bl("Fast training — 200 trees on 93K samples takes < 2 seconds"))
    s.append(Spacer(1, 6))

    s.append(h2("4.3  Proxy Model Validation"))
    s.append(p("The proxy is only useful if it faithfully reproduces the K-Means assignments. We "
               "validate with 5-fold stratified cross-validation:"))
    s.append(Spacer(1, 4))

    cv_data = [
        ["Fold", "Accuracy"],
        ["1", "0.9999"],
        ["2", "0.9999"],
        ["3", "0.9999"],
        ["4", "1.0000"],
        ["5", "0.9998"],
        ["Mean ± Std", "0.9999 ± 0.0001"],
    ]
    s.append(make_table(cv_data, [120, 120]))
    s.append(Spacer(1, 4))
    s.append(p("<b>Accuracy = 99.99%</b> — the Random Forest nearly perfectly reproduces the K-Means "
               "cluster assignments from raw RFM features. This means the proxy model's SHAP values "
               "are a faithful representation of the original clustering's feature dependencies."))
    s.append(Spacer(1, 4))
    s.append(note("An accuracy this high is expected. K-Means assigns clusters based on distances "
                   "in PCA space, which is a linear transformation of the standardised RFM features. "
                   "A 200-tree Random Forest can easily learn these decision boundaries. The near-"
                   "perfect accuracy confirms that no information was lost — the proxy is a reliable "
                   "stand-in for the K-Means model."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: SHAP Feature Importance Results
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("5. SHAP Feature Importance — Results"))

    s.append(h2("5.1  How SHAP Values Were Computed"))
    s.append(p("After training the proxy Random Forest on all 93,357 customers, we use SHAP's "
               "<b>TreeExplainer</b> — an exact algorithm for tree-based models that computes "
               "SHAP values in polynomial time (not the exponential cost of brute-force Shapley "
               "computation)."))
    s.append(Spacer(1, 4))
    s.append(code(
        "explainer = shap.TreeExplainer(rf_model)<br/>"
        "shap_values = explainer.shap_values(X_rfm)  # shape: (93357, 3, 3)<br/>"
        "# → 93,357 customers × 3 features × 3 classes"
    ))
    s.append(Spacer(1, 4))
    s.append(p("For each customer, TreeExplainer produces a 3×3 matrix: one SHAP value per feature "
               "per class. The mean absolute SHAP value per feature per class gives the global "
               "feature importance for each segment."))
    s.append(Spacer(1, 6))

    s.append(h2("5.2  SHAP Importance Table"))
    shap_data = [
        ["Segment", "Recency\n|SHAP|", "Frequency\n|SHAP|", "Monetary\n|SHAP|", "Dominant\nFeature"],
        ["Potential\nLoyalists", "0.4777", "0.0279", "0.0107", "Recency\n(92.6%)"],
        ["Champions", "0.0008", "0.0567", "0.0056", "Frequency\n(89.9%)"],
        ["Hibernating", "0.4784", "0.0288", "0.0076", "Recency\n(92.9%)"],
    ]
    s.append(make_table(shap_data, [70, 70, 70, 70, 70]))
    s.append(Spacer(1, 6))

    s.append(h2("5.3  Interpreting the SHAP Results"))

    s.append(h3("Recency Dominates Potential Loyalists and Hibernating"))
    s.append(p("The two largest segments — Potential Loyalists (45.9%) and Hibernating (51.1%) — "
               "are distinguished almost entirely by recency (SHAP = 0.478 for both). This makes "
               "sense: both segments have frequency = 1.0 and similar monetary values (BRL 154 vs "
               "156), so the only axis separating them is when they last purchased."))
    s.append(bl("<b>Potential Loyalists</b> have a mean recency of 155 days — they bought within "
                "the last ~5 months."))
    s.append(bl("<b>Hibernating</b> have a mean recency of 405 days — they bought over a year ago."))
    s.append(bl("Recency's SHAP value of ~0.48 means it shifts the prediction probability by "
                "48 percentage points toward these segments."))
    s.append(Spacer(1, 4))

    s.append(h3("Frequency Dominates Champions"))
    s.append(p("Champions are the only repeat buyers (frequency = 2.0 vs 1.0 for the other segments). "
               "Frequency has a SHAP value of 0.0567 for Champions — apparently small in absolute "
               "terms, but it accounts for 89.9% of the total importance for this segment. "
               "Recency's SHAP for Champions is almost zero (0.0008) because Champions span a wide "
               "range of recency values (mean 269 days with high variance)."))
    s.append(Spacer(1, 4))

    s.append(h3("Monetary Has Minimal Impact"))
    s.append(p("Monetary value contributes < 2% of SHAP importance for every segment. This does "
               "not mean monetary doesn't matter — it means that after controlling for recency "
               "and frequency, monetary adds little <i>additional</i> discriminative power. In this "
               "dataset, monetary is highly correlated with frequency (repeat buyers spend more), "
               "so frequency already captures most of the monetary signal."))
    s.append(Spacer(1, 6))

    s.append(h2("5.4  SHAP Heatmap"))
    s.append(img("shap_heatmap.png", w=440, ratio=0.52))
    s.append(caption("Figure 3: SHAP feature importance per segment. Recency (rightmost column) "
                     "dominates Potential Loyalists and Hibernating with deep purple cells. "
                     "Frequency dominates Champions (lighter purple in left column)."))
    s.append(Spacer(1, 6))

    s.append(h2("5.5  SHAP Bar Chart"))
    s.append(img("shap_bars.png", w=460, ratio=0.50))
    s.append(caption("Figure 4: Grouped bar chart of SHAP importance. The recency bars for "
                     "Potential Loyalists and Hibernating tower over all other values, confirming "
                     "recency is the primary clustering axis."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 6: RFM Distributions per Segment
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("6. RFM Distributions per Segment"))
    s.append(p("The box plots below show the distribution of raw RFM values within each segment. "
               "Outliers are hidden for clarity (they were capped at the 1st/99th percentiles in "
               "Phase 1, so extreme values are bounded)."))
    s.append(Spacer(1, 6))
    s.append(img("rfm_boxplots.png", w=500, ratio=0.32))
    s.append(caption("Figure 5: Box plots of raw Recency, Frequency, and Monetary per segment. "
                     "Outliers suppressed. Whiskers extend to the 1st/99th percentile values."))
    s.append(Spacer(1, 6))

    s.append(h2("6.1  Recency Distribution"))
    s.append(bl("<b>Potential Loyalists:</b> Tight distribution between ~55 and ~280 days (median ~155). "
                "All members purchased within the last 9 months."))
    s.append(bl("<b>Champions:</b> Wide spread from ~50 to ~640 days (median ~245). Champions are "
                "defined by repeat purchases, not by recency — some Champions last bought recently, "
                "others long ago."))
    s.append(bl("<b>Hibernating:</b> Distribution starts above ~280 days and extends to ~640 days "
                "(median ~400). These are uniformly old purchasers."))
    s.append(bl("<b>Key insight:</b> The Potential Loyalists and Hibernating boxes do not overlap — "
                "there is a clean ~280-day cutoff. This confirms the sharp recency split visible "
                "in the PCA scatter."))
    s.append(Spacer(1, 6))

    s.append(h2("6.2  Frequency Distribution"))
    s.append(bl("<b>Potential Loyalists and Hibernating:</b> Both have frequency = 1.0 for all "
                "members (the box collapses to a single line). They are one-time buyers."))
    s.append(bl("<b>Champions:</b> Frequency = 2.0 for all members (also a single line). They are "
                "the only repeat buyers in the dataset."))
    s.append(bl("<b>Key insight:</b> Frequency is binary in this dataset (1 or 2), which explains "
                "why Champions form a cleanly separated cluster in PCA space (PC1 > 3)."))
    s.append(Spacer(1, 6))

    s.append(h2("6.3  Monetary Distribution"))
    s.append(bl("<b>Potential Loyalists:</b> Median ~100 BRL, IQR from ~50 to ~200. Moderate spenders."))
    s.append(bl("<b>Champions:</b> Widest distribution with median ~240 BRL, IQR from ~130 to ~370. "
                "Higher spending reflects their repeat-purchase behaviour."))
    s.append(bl("<b>Hibernating:</b> Nearly identical to Potential Loyalists (median ~100, similar IQR). "
                "This confirms that Potential Loyalists and Hibernating differ only on recency, "
                "not on spending behaviour."))
    s.append(Spacer(1, 4))
    s.append(note("The monetary distributions of Potential Loyalists and Hibernating overlap almost "
                   "completely. This is consistent with the SHAP analysis: monetary contributes < 2% "
                   "of discriminative power because it does not help separate these two groups."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 7: Segments in PCA Space
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("7. Customer Segments in PCA Space"))
    s.append(p("The scatter plot below shows the final segmented customers projected into PCA "
               "space. This is the culmination of all four phases — customers now have both "
               "their PCA coordinates (for geometric understanding) and their segment labels "
               "(for business understanding)."))
    s.append(Spacer(1, 4))
    s.append(img("cluster_scatter.png", w=440, ratio=0.75))
    s.append(caption("Figure 6: Customer segments in PCA space. Green = Potential Loyalists (bottom), "
                     "Orange = Hibernating (top), Purple = Champions (right). The recency axis "
                     "(PC2) separates the two large segments; the spending axis (PC1) separates "
                     "Champions from the rest."))
    s.append(Spacer(1, 6))

    s.append(h2("7.1  Segment Geometry"))
    s.append(bl("<b>Potential Loyalists (green):</b> Bottom half of the main cluster body. PC2 < 0 "
                "corresponds to lower-than-average recency (more recent purchases). Spread across "
                "PC1 ∈ [−2, 1.5] shows variation in spending."))
    s.append(bl("<b>Hibernating (orange):</b> Top half of the main body. PC2 > 0 corresponds to "
                "higher-than-average recency (older purchases). Same PC1 range as Potential Loyalists, "
                "confirming they differ only on the recency axis."))
    s.append(bl("<b>Champions (purple):</b> Isolated island at PC1 > 3. Separated from the main "
                "body along PC1 (spending behaviour), which is composed of 0.70 × frequency + "
                "0.70 × monetary in the PCA loading vector."))
    s.append(Spacer(1, 6))

    s.append(h2("7.2  Why the Segments Make Sense"))
    s.append(p("The PCA scatter confirms the SHAP findings visually:"))
    s.append(bl("<b>PC2 (recency — 33.2% variance)</b> is the primary axis separating the two large "
                "segments. SHAP assigns recency a dominance of 92–93% for these segments."))
    s.append(bl("<b>PC1 (spending — 38.7% variance)</b> separates Champions. SHAP assigns frequency "
                "a dominance of 90% for Champions, and frequency is the main component of PC1."))
    s.append(bl("The mathematical explanation (SHAP) and the geometric explanation (PCA scatter) "
                "are consistent — both point to recency as the primary differentiator."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 8: Business Recommendations
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("8. Business Recommendations per Segment"))
    s.append(p("The segment profiles and SHAP analysis translate directly into marketing strategy. "
               "Each segment has a distinct behavioural profile that suggests specific interventions."))
    s.append(Spacer(1, 6))

    s.append(h2("8.1  Potential Loyalists (45.9% — 42,865 Customers)"))
    s.append(p("<b>Profile:</b> Recent one-time buyers (155 days avg), moderate spend (BRL 154)."))
    s.append(p("<b>Opportunity:</b> These customers are the easiest to convert into repeat buyers. "
               "They purchased recently and are still engaged."))
    s.append(bl("Send personalised follow-up emails with complementary product recommendations"))
    s.append(bl("Offer a time-limited loyalty discount for their second purchase"))
    s.append(bl("Implement a first-purchase-anniversary reminder campaign"))
    s.append(bl("Track cohort conversion rate to Champions over 90/180/365 day windows"))
    s.append(Spacer(1, 6))

    s.append(h2("8.2  Champions (3.0% — 2,801 Customers)"))
    s.append(p("<b>Profile:</b> Repeat buyers (frequency 2.0), highest spend (BRL 295), moderate "
               "recency (269 days)."))
    s.append(p("<b>Opportunity:</b> The most valuable 3% — retention is the priority."))
    s.append(bl("Enrol in a VIP loyalty programme with exclusive early-access to deals"))
    s.append(bl("Provide priority customer service and dedicated support channels"))
    s.append(bl("Send personalised high-value product recommendations based on purchase history"))
    s.append(bl("Monitor for churn signals: if recency exceeds 365 days, trigger a win-back campaign"))
    s.append(bl("Calculate Customer Lifetime Value (CLV) for this segment to justify retention spend"))
    s.append(Spacer(1, 6))

    s.append(h2("8.3  Hibernating (51.1% — 47,691 Customers)"))
    s.append(p("<b>Profile:</b> Lapsed one-time buyers (405 days avg), moderate spend (BRL 156)."))
    s.append(p("<b>Opportunity:</b> The largest segment but hardest to re-engage. Cost-effectiveness "
               "is critical — not all Hibernating customers are worth pursuing."))
    s.append(bl("Segment further by recency: 280–365 days (warm) vs 365+ days (cold)"))
    s.append(bl("Send a 'We miss you' win-back email with a compelling discount"))
    s.append(bl("For cold customers (400+ days), consider a final re-engagement attempt "
                "before deprioritising"))
    s.append(bl("A/B test different win-back offers (discount % vs free shipping vs new product alert)"))
    s.append(bl("Track reactivation rate — if < 2%, the cost of outreach may exceed the revenue"))
    s.append(Spacer(1, 6))

    s.append(h2("8.4  Summary of Segment Strategy"))
    strategy_data = [
        ["Segment", "Size", "Priority", "Strategy", "KPI to Track"],
        ["Potential\nLoyalists", "45.9%", "High", "Convert to repeat\nbuyers with targeted\nfollow-ups",
         "2nd purchase\nconversion rate"],
        ["Champions", "3.0%", "Critical", "Retain with VIP\ntreatment and\nloyalty programmes",
         "Retention rate,\nCLV"],
        ["Hibernating", "51.1%", "Medium", "Cost-effective\nwin-back campaigns\n(sub-segment first)",
         "Reactivation rate,\nCAC vs revenue"],
    ]
    s.append(make_table(strategy_data, [70, 40, 50, 120, 90]))
    s.append(Spacer(1, 8))

    s.append(note("These recommendations assume the Olist marketplace context (Brazilian e-commerce). "
                   "Actual implementation should factor in: communication channel preferences (email, "
                   "WhatsApp, SMS), regional buying patterns, product category affinity per segment, "
                   "and the cost of each intervention vs expected uplift."))

    # ── Build ──
    doc.build(s)
    print(f"PDF saved: {OUTPUT}")


if __name__ == "__main__":
    build()
