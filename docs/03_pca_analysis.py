"""Generate PDF: Phase 2 — PCA Dimensionality Reduction Deep Dive."""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    Image, KeepTogether, PageBreak,
)

OUTPUT = "docs/03_pca_analysis.pdf"
PLOT_DIR = "/private/tmp/claude-501/-Users-mohitmalhotra-PycharmProjects/phase2_plots"

ACCENT = HexColor("#534AB7")
DARK = HexColor("#1a1a2e")
GREY = HexColor("#444444")
LIGHT_BG = HexColor("#f0f0fa")
WHITE = HexColor("#ffffff")
BORDER = HexColor("#cccccc")
WARN_BG = HexColor("#fff8e1")
WARN_BORDER = HexColor("#f9a825")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle("DocTitle2", parent=styles["Title"], fontSize=22, leading=28,
                          textColor=DARK, spaceAfter=4, alignment=TA_CENTER))
styles.add(ParagraphStyle("DocSub2", parent=styles["Normal"], fontSize=11, leading=14,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=20))
styles.add(ParagraphStyle("S1p", parent=styles["Heading1"], fontSize=15, leading=20,
                          textColor=ACCENT, spaceBefore=22, spaceAfter=8))
styles.add(ParagraphStyle("S2p", parent=styles["Heading2"], fontSize=12, leading=16,
                          textColor=DARK, spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle("S3p", parent=styles["Heading3"], fontSize=10.5, leading=14,
                          textColor=HexColor("#3a2e8a"), spaceBefore=10, spaceAfter=4))
styles.add(ParagraphStyle("Bp", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle("Bltp", parent=styles["Normal"], fontSize=10.5, leading=15,
                          textColor=GREY, leftIndent=18, spaceAfter=4, bulletIndent=6))
styles.add(ParagraphStyle("BltSubp", parent=styles["Normal"], fontSize=10, leading=14,
                          textColor=GREY, leftIndent=36, spaceAfter=3, bulletIndent=24))
styles.add(ParagraphStyle("CodeP", parent=styles["Normal"], fontSize=9, leading=12,
                          fontName="Courier", textColor=HexColor("#333333"),
                          backColor=HexColor("#f5f5f5"), leftIndent=12, rightIndent=12,
                          spaceBefore=4, spaceAfter=8, borderPadding=6))
styles.add(ParagraphStyle("CaptionP", parent=styles["Normal"], fontSize=9, leading=12,
                          textColor=GREY, alignment=TA_CENTER, spaceAfter=10, spaceBefore=4))
styles.add(ParagraphStyle("NoteP", parent=styles["Normal"], fontSize=9.5, leading=13,
                          textColor=HexColor("#7a6c00"), leftIndent=10, rightIndent=10,
                          spaceBefore=6, spaceAfter=10, backColor=WARN_BG,
                          borderColor=WARN_BORDER, borderWidth=0.5, borderPadding=8))

def hr(): return HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6, spaceBefore=2)
def h1(t): return Paragraph(t, styles["S1p"])
def h2(t): return Paragraph(t, styles["S2p"])
def h3(t): return Paragraph(t, styles["S3p"])
def p(t): return Paragraph(t, styles["Bp"])
def bl(t): return Paragraph(f"•  {t}", styles["Bltp"])
def bls(t): return Paragraph(f"–  {t}", styles["BltSubp"])
def code(t): return Paragraph(t, styles["CodeP"])
def caption(t): return Paragraph(t, styles["CaptionP"])
def note(t): return Paragraph(f"<b>Note:</b> {t}", styles["NoteP"])

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
    s.append(Paragraph("Phase 2: PCA Dimensionality Reduction", styles["DocTitle2"]))
    s.append(Paragraph("RFM Customer Segmentation Pipeline — Detailed Technical Report", styles["DocSub2"]))
    s.append(hr())
    s.append(Spacer(1, 6))

    # ═══════════════════════════════════════════════════════════
    # SECTION 1: How PCA Was Performed
    # ═══════════════════════════════════════════════════════════
    s.append(h1("1. How PCA Was Performed"))
    s.append(p("Principal Component Analysis (PCA) was applied to the 3-dimensional standardised "
               "RFM feature space (recency, frequency, monetary — all with mean = 0, std = 1 after "
               "Phase 1's Box-Cox + Z-score pipeline). The goal is to reduce the 3 correlated features "
               "into 2 uncorrelated principal components that capture the maximum possible variance, "
               "making the data easier to cluster and visualise."))
    s.append(Spacer(1, 4))

    s.append(h2("1.1  Implementation"))
    s.append(code(
        "from sklearn.decomposition import PCA<br/><br/>"
        "pca = PCA(n_components=3, random_state=42)<br/>"
        "pc_all = pca.fit_transform(rfm_scaled[['recency','frequency','monetary']])<br/><br/>"
        "# Retain first 2 components for clustering<br/>"
        "pca_df = pd.DataFrame(pc_all[:, :2], columns=['PC1','PC2'])"
    ))
    s.append(Spacer(1, 4))

    s.append(h2("1.2  Key Design Decisions"))
    s.append(bl("<b>Fit on all 3 components first</b> — We fit PCA with n_components=3 (the full rank) "
                "to inspect all eigenvalues and variance ratios before deciding how many to keep. "
                "Then we slice to 2 components."))
    s.append(bl("<b>Standardised input</b> — PCA is applied to Z-scored features (not raw RFM values). "
                "This ensures the covariance matrix equals the correlation matrix, giving each feature "
                "equal weight regardless of original scale."))
    s.append(bl("<b>Deterministic</b> — random_state=42 ensures reproducible sign orientation of "
                "eigenvectors across runs."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 2: Complete Mathematics
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("2. Complete PCA Mathematics — End to End"))
    s.append(p("PCA proceeds through four mathematical steps, each of which we will trace with the "
               "actual numbers from this project."))
    s.append(Spacer(1, 4))

    s.append(h2("Step 1: Compute the Covariance Matrix"))
    s.append(p("Given an <i>n × p</i> data matrix <b>X</b> (n = 93,357 customers, p = 3 features), "
               "the covariance matrix is:"))
    s.append(code("C = (1 / (n − 1)) × X<sup>T</sup>X"))
    s.append(p("Because the features are standardised (μ = 0, σ = 1), the covariance matrix is "
               "<b>numerically identical</b> to the correlation matrix. We verified this: the maximum "
               "absolute difference between the correlation and covariance matrices is 0.000011 — "
               "floating-point rounding only."))
    s.append(Spacer(1, 6))

    s.append(h2("Step 2: Eigenvalue Decomposition"))
    s.append(p("Decompose the covariance matrix into eigenvalues and eigenvectors:"))
    s.append(code("C × v = λ × v"))
    s.append(p("where λ is a scalar eigenvalue and <b>v</b> is the corresponding unit eigenvector. "
               "Each eigenvalue represents the amount of variance captured along that eigenvector's "
               "direction. The eigenvectors are orthogonal (perpendicular to each other), forming "
               "a new coordinate system."))
    s.append(Spacer(1, 6))

    s.append(h2("Step 3: Sort by Eigenvalue (Descending)"))
    s.append(p("Arrange eigenpairs (λ, v) in descending order of λ. The eigenvector with the largest "
               "eigenvalue defines the direction of maximum variance — this becomes PC1. The next "
               "eigenvector (orthogonal to PC1) becomes PC2, and so on."))
    s.append(Spacer(1, 6))

    s.append(h2("Step 4: Project Data onto New Axes"))
    s.append(p("Transform each customer's feature vector <b>x</b> = [recency, frequency, monetary] "
               "into the new coordinate system by multiplying with the eigenvector matrix:"))
    s.append(code(
        "PC<sub>i</sub> = v<sub>i1</sub> × recency + v<sub>i2</sub> × frequency + "
        "v<sub>i3</sub> × monetary"
    ))
    s.append(p("This produces new uncorrelated variables (PC1, PC2, PC3) that are linear combinations "
               "of the original features. Each customer is now a point in PC-space instead of RFM-space."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 3: Correlation Analysis
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("3. Correlation Analysis"))
    s.append(p("Before PCA, we examine the correlation structure of the standardised RFM features "
               "to understand what relationships PCA will exploit."))
    s.append(Spacer(1, 4))
    s.append(img("correlation_heatmap.png", w=340, ratio=0.85))
    s.append(caption("Figure 1: Pearson correlation matrix of standardised RFM features."))
    s.append(Spacer(1, 6))

    corr_data = [
        ["", "Recency", "Frequency", "Monetary"],
        ["Recency", "1.0000", "−0.0483", "−0.0365"],
        ["Frequency", "−0.0483", "1.0000", "0.1608"],
        ["Monetary", "−0.0365", "0.1608", "1.0000"],
    ]
    s.append(make_table(corr_data, [80, 100, 100, 100]))
    s.append(Spacer(1, 6))

    s.append(h2("3.1  Interpretation"))
    s.append(bl("<b>Frequency ↔ Monetary (r = 0.16):</b> Weak positive correlation. Customers who buy "
                "more often tend to spend slightly more overall. This is the strongest pairwise "
                "relationship and the one PCA will capture in PC1."))
    s.append(bl("<b>Recency ↔ Frequency (r = −0.05):</b> Nearly zero. How recently a customer bought "
                "is almost independent of how many times they bought."))
    s.append(bl("<b>Recency ↔ Monetary (r = −0.04):</b> Nearly zero. Recent customers do not "
                "systematically spend more or less."))
    s.append(Spacer(1, 4))

    s.append(h2("3.2  Implications for PCA"))
    s.append(p("The weak correlations (max |r| = 0.16) mean the features are already nearly independent. "
               "This has two consequences:"))
    s.append(bl("<b>No single component can dominate</b> — With near-independent features, variance is "
                "spread roughly equally across all directions. No PC will capture 90%+ variance."))
    s.append(bl("<b>PCA still helps</b> — Even with weak correlations, PCA rotates the coordinate "
                "system to align with the directions of maximum variance. The frequency-monetary "
                "correlation (0.16), while weak, creates a direction of joint variation that PCA "
                "captures as PC1, improving cluster separation."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 4: Covariance Matrix & PCA Decomposition
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("4. Covariance Matrix & Full PCA Decomposition"))

    s.append(h2("4.1  Covariance Matrix"))
    s.append(p("For standardised features, the covariance matrix equals the correlation matrix "
               "(proven by: Cov(z<sub>i</sub>, z<sub>j</sub>) = Cor(x<sub>i</sub>, x<sub>j</sub>) "
               "when both features have σ = 1)."))
    s.append(Spacer(1, 4))
    s.append(img("covariance_heatmap.png", w=340, ratio=0.85))
    s.append(caption("Figure 2: Covariance matrix (numerically equal to correlation for standardised data)."))
    s.append(Spacer(1, 6))

    s.append(h2("4.2  Eigenvalue Decomposition"))
    s.append(p("The covariance matrix C is decomposed as C = VΛV<sup>T</sup>, where V is the matrix "
               "of eigenvectors (columns) and Λ is the diagonal matrix of eigenvalues."))
    s.append(Spacer(1, 4))

    s.append(h3("Eigenvalues (Λ)"))
    eigen_data = [
        ["Component", "Eigenvalue (λ)", "Variance Explained", "Cumulative"],
        ["PC1", "1.1619", "38.73%", "38.73%"],
        ["PC2", "0.9973", "33.24%", "71.97%"],
        ["PC3", "0.8408", "28.03%", "100.00%"],
    ]
    s.append(make_table(eigen_data, [70, 100, 100, 100]))
    s.append(Spacer(1, 4))
    s.append(p("<b>Verification:</b> λ<sub>1</sub> + λ<sub>2</sub> + λ<sub>3</sub> = 1.1619 + 0.9973 "
               "+ 0.8408 = <b>3.0000</b> = number of features. The total variance is preserved — PCA "
               "only rotates, it never discards or creates variance."))
    s.append(Spacer(1, 6))

    s.append(h3("Eigenvectors (V) — The Loading Matrix"))
    s.append(p("Each eigenvector defines a direction in original feature space. The components of an "
               "eigenvector are called <b>loadings</b> — they tell us how much each original feature "
               "contributes to that principal component."))
    s.append(Spacer(1, 4))

    load_data = [
        ["", "Recency", "Frequency", "Monetary"],
        ["PC1 (λ=1.16)", "−0.1312", "0.7025", "0.6995"],
        ["PC2 (λ=1.00)", "0.9908", "0.0700", "0.1156"],
        ["PC3 (λ=0.84)", "0.0323", "0.7083", "−0.7052"],
    ]
    s.append(make_table(load_data, [90, 100, 100, 100]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Verification of orthonormality:</b> Each eigenvector has unit length "
               "(||v|| = 1) and each pair is orthogonal (v<sub>i</sub> · v<sub>j</sub> = 0). "
               "For example: ||v<sub>1</sub>|| = √(0.1312² + 0.7025² + 0.6995²) = √(0.0172 + "
               "0.4935 + 0.4893) = √1.0000 = 1."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 5: Loading Vectors & PCA Equations
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("5. Loading Vectors & PCA Equations"))
    s.append(p("The loading vectors show which original features drive each principal component. "
               "A loading close to 0 means that feature contributes little; a loading near ±1 means "
               "it dominates that component."))
    s.append(Spacer(1, 4))

    s.append(h2("5.1  PC1: Spending Behaviour (38.7% variance)"))
    s.append(code(
        "PC1 = −0.1312 × recency + 0.7025 × frequency + 0.6995 × monetary"
    ))
    s.append(bl("<b>Frequency (0.70) and Monetary (0.70)</b> load equally and heavily. PC1 is essentially "
                "an <i>average of spending intensity</i> — customers with high PC1 bought frequently "
                "and spent a lot."))
    s.append(bl("<b>Recency (−0.13)</b> loads weakly negative. A customer's recency barely affects their "
                "PC1 score, but all else equal, a more recent customer (lower recency value) gets a "
                "slightly higher PC1."))
    s.append(bl("<b>Business meaning:</b> PC1 separates <i>high-value customers</i> (positive PC1) "
                "from <i>low-value customers</i> (negative PC1). The Champions cluster sits at the "
                "positive extreme."))
    s.append(Spacer(1, 6))

    s.append(h2("5.2  PC2: Recency (33.2% variance)"))
    s.append(code(
        "PC2 = 0.9908 × recency + 0.0700 × frequency + 0.1156 × monetary"
    ))
    s.append(bl("<b>Recency (0.99)</b> dominates completely. PC2 is almost a pure copy of the recency "
                "feature — 99% of its variance comes from recency alone."))
    s.append(bl("<b>Frequency (0.07) and Monetary (0.12)</b> contribute negligibly. Spending behaviour "
                "is almost entirely orthogonal to recency in this dataset."))
    s.append(bl("<b>Business meaning:</b> PC2 separates <i>active customers</i> (low recency → low PC2) "
                "from <i>lapsed customers</i> (high recency → high PC2). The Hibernating cluster sits "
                "at the positive extreme of PC2."))
    s.append(Spacer(1, 6))

    s.append(h2("5.3  PC3: Frequency vs Monetary (28.0% variance)"))
    s.append(code(
        "PC3 = 0.0323 × recency + 0.7083 × frequency − 0.7052 × monetary"
    ))
    s.append(bl("<b>Frequency (+0.71) and Monetary (−0.71)</b> load equally but with opposite signs. "
                "PC3 captures the <i>contrast</i> between buying often (high frequency) and spending "
                "a lot per order (high monetary)."))
    s.append(bl("<b>Recency (0.03)</b> is negligible — this component is purely about the "
                "frequency/monetary trade-off."))
    s.append(bl("<b>Business meaning:</b> PC3 distinguishes customers who buy many cheap items from "
                "those who buy few expensive items. This component is <b>dropped</b> in the final model "
                "to reduce dimensionality."))
    s.append(Spacer(1, 6))

    s.append(h2("5.4  Biplot: Loadings + Cluster Scatter"))
    s.append(Spacer(1, 4))
    s.append(img("biplot.png", w=420, ratio=0.85))
    s.append(caption("Figure 3: Biplot showing feature loading arrows overlaid on the PC1-PC2 customer scatter. "
                     "Frequency and monetary point right (PC1 direction); recency points up (PC2 direction)."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 6: Why 2 Components?
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("6. Why 2 Components? Design Choice"))
    s.append(p("The decision to retain 2 out of 3 components (PC1 + PC2, dropping PC3) is based on "
               "four considerations:"))
    s.append(Spacer(1, 4))

    s.append(h2("6.1  Variance Retention"))
    s.append(Spacer(1, 4))
    s.append(img("scree_plot.png", w=440, ratio=0.62))
    s.append(caption("Figure 4: Scree plot with cumulative variance. 2 components retain 72%."))
    s.append(Spacer(1, 6))

    var_data = [
        ["Components\nRetained", "Variance\nExplained", "Variance\nLost", "Dimensions\nReduced"],
        ["1 (PC1 only)", "38.7%", "61.3%", "3 → 1"],
        ["2 (PC1 + PC2)", "72.0%", "28.0%", "3 → 2"],
        ["3 (all)", "100.0%", "0.0%", "3 → 3 (no reduction)"],
    ]
    s.append(make_table(var_data, [75, 85, 75, 85]))
    s.append(Spacer(1, 6))

    s.append(p("72% is below the common 90% threshold often cited in textbooks. However, this "
               "threshold assumes high-dimensional data where most features are redundant. With "
               "only 3 nearly-independent features, 72% is the maximum achievable with 2 components. "
               "The alternative — keeping all 3 — defeats the purpose of PCA entirely."))
    s.append(Spacer(1, 4))

    s.append(h2("6.2  What Does PC3 Capture?"))
    s.append(p("PC3 = 0.71 × frequency − 0.71 × monetary. This is the contrast between buying often "
               "and spending a lot. In this dataset, this distinction adds little clustering value:"))
    s.append(bl("Frequency is near-binary (97% = 1, 3% = 2), so the frequency-monetary contrast "
                "is largely determined by monetary alone."))
    s.append(bl("The 28% variance in PC3 is primarily noise from the binary frequency split, "
                "not meaningful behavioural variation."))
    s.append(bl("Keeping PC3 would add a 3rd dimension to K-Means without improving cluster "
                "separation, since the meaningful structure (spending vs recency) is already "
                "captured in PC1 and PC2."))
    s.append(Spacer(1, 4))

    s.append(h2("6.3  Practical Benefits of 2D"))
    s.append(bl("<b>Visualisation:</b> 2D scatter plots allow direct inspection of cluster boundaries. "
                "3D plots lose information when projected onto a screen and are harder to interpret."))
    s.append(bl("<b>K-Means performance:</b> K-Means in 2D is faster and less susceptible to the "
                "curse of dimensionality. With 93,357 customers, the difference in runtime is modest, "
                "but the improvement in cluster interpretability is significant."))
    s.append(bl("<b>Cluster validation:</b> Silhouette scores, which measure cluster separation, tend "
                "to be higher in lower dimensions because random noise dimensions dilute separation."))
    s.append(Spacer(1, 4))

    s.append(h2("6.4  Empirical Validation"))
    s.append(p("The final K-Means model (K=3) achieves a <b>silhouette score of 0.41</b> on the "
               "2-component space. This indicates moderate-to-good cluster separation — clusters are "
               "meaningfully distinct. Adding PC3 would likely reduce this score by introducing noise "
               "that blurs cluster boundaries."))
    s.append(Spacer(1, 4))
    s.append(note("The 72% vs 100% variance trade-off is a deliberate signal-noise decomposition. "
                   "PC1 and PC2 capture the signal (spending behaviour + recency); PC3 captures the "
                   "remaining 28%, which is dominated by the binary frequency artefact. Dropping it "
                   "is analogous to denoising."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 7: Variance Retention Detail
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("7. Variance Retention — Per-Component Detail"))

    s.append(h2("7.1  Eigenvalue Interpretation"))
    s.append(p("Each eigenvalue λ represents the variance of the data when projected onto the "
               "corresponding eigenvector. The variance explained ratio is λ / Σλ:"))
    s.append(Spacer(1, 4))

    detail_data = [
        ["Component", "Eigenvalue", "Var. Ratio", "Interpretation"],
        ["PC1", "1.1619", "38.73%", "Slightly above average (1.0) → captures\nthe frequency-monetary correlation"],
        ["PC2", "0.9973", "33.24%", "Almost exactly 1.0 → captures roughly\none feature's worth of variance (recency)"],
        ["PC3", "0.8408", "28.03%", "Below average → captures the residual\nfrequency vs monetary contrast"],
    ]
    s.append(make_table(detail_data, [65, 65, 65, 230]))
    s.append(Spacer(1, 6))

    s.append(h2("7.2  Why Eigenvalues Are Close to 1.0"))
    s.append(p("With standardised features, each original feature contributes exactly 1.0 to the "
               "total variance (Σλ = 3.0). If the features were perfectly independent (zero correlation), "
               "all three eigenvalues would be exactly 1.0 and PCA would achieve nothing — no direction "
               "would have more variance than any other."))
    s.append(Spacer(1, 4))
    s.append(p("Our eigenvalues (1.16, 1.00, 0.84) are <i>close</i> to 1.0 because the features "
               "are weakly correlated (max |r| = 0.16). The slight spread is caused by the "
               "frequency-monetary correlation: it pushes variance slightly toward PC1 (1.16 > 1.0) "
               "and away from PC3 (0.84 < 1.0)."))
    s.append(Spacer(1, 4))
    s.append(p("This is why PCA achieves only 72% with 2 components rather than the 90%+ often seen "
               "in high-dimensional datasets with many redundant features. The data's near-independence "
               "is a property of the business domain, not a failure of the method."))

    # ═══════════════════════════════════════════════════════════
    # SECTION 8: 3D Visualisation
    # ═══════════════════════════════════════════════════════════
    s.append(PageBreak())
    s.append(h1("8. 3D Visualisation: Before & After PCA"))
    s.append(p("Below are 3D scatter plots of 6,000 sampled customers, coloured by their final "
               "cluster assignment (determined in Phase 3). Both plots show the same customers — "
               "only the coordinate system changes."))
    s.append(Spacer(1, 6))

    s.append(h2("8.1  Before PCA: Standardised RFM Space"))
    s.append(Spacer(1, 4))
    s.append(img("3d_before_pca.png", w=420, ratio=0.85))
    s.append(caption("Figure 5: Customers in the original 3-axis (recency, frequency, monetary) space. "
                     "Clusters overlap significantly because frequency is near-binary, collapsing the "
                     "data into two 'sheets' at frequency ≈ −0.17 and frequency ≈ 5.68."))
    s.append(Spacer(1, 6))

    s.append(h3("Observations"))
    s.append(bl("<b>Frequency axis is nearly discrete:</b> 97% of points lie on the frequency = −0.17 "
                "plane (one-time buyers). The 3% repeat buyers form a sparse parallel plane at "
                "frequency = 5.68. This 'sheet' structure makes 3D RFM space a poor input for K-Means."))
    s.append(bl("<b>Recency spreads evenly:</b> The roughly uniform original distribution is visible as "
                "an even spread along the recency axis."))
    s.append(bl("<b>Cluster boundaries are unclear:</b> In original RFM coordinates, the clusters "
                "(colours) overlap heavily because the axes are not aligned with the natural cluster "
                "separations."))

    s.append(PageBreak())
    s.append(h2("8.2  After PCA: Principal Component Space"))
    s.append(Spacer(1, 4))
    s.append(img("3d_after_pca.png", w=420, ratio=0.85))
    s.append(caption("Figure 6: Customers in PC space (PC1 = spending, PC2 = recency, PC3 = freq vs "
                     "monetary). Champions (purple) separate clearly along the PC1 axis."))
    s.append(Spacer(1, 6))

    s.append(h3("Observations"))
    s.append(bl("<b>Champions (purple) are clearly separated</b> along the PC1 axis at high values "
                "(PC1 > 3). These are the high-frequency, high-monetary customers that PC1 was "
                "designed to capture."))
    s.append(bl("<b>Potential Loyalists (green) vs Hibernating (orange)</b> separate primarily along "
                "the PC2 axis. Potential loyalists have lower PC2 (more recent purchases); hibernating "
                "customers have higher PC2 (older purchases)."))
    s.append(bl("<b>PC3 adds little separation:</b> The green and orange clusters overlap heavily along "
                "the PC3 axis, confirming that dropping PC3 loses little clustering information."))
    s.append(Spacer(1, 6))

    s.append(h2("8.3  What PCA Changed"))
    change_data = [
        ["Property", "Before PCA (RFM)", "After PCA (PC)"],
        ["Axes", "recency, frequency, monetary", "PC1 (spending), PC2 (recency),\nPC3 (freq vs monetary)"],
        ["Correlation\nbetween axes", "Weak (max |r| = 0.16)", "Zero (guaranteed by PCA)"],
        ["Feature scale", "All standardised (σ = 1)", "Varies: σ = 1.08, 1.00, 0.92\n(= √eigenvalue)"],
        ["Cluster\nseparation", "Overlapping, unclear\nboundaries", "Visually separated, especially\nChampions on PC1"],
        ["Dimensionality\nused", "3 (all needed)", "2 (PC3 dropped, 72% retained)"],
    ]
    s.append(make_table(change_data, [75, 155, 195]))
    s.append(Spacer(1, 6))

    s.append(p("<b>Key takeaway:</b> PCA did not invent the clusters — it rotated the coordinate system "
               "so that the existing cluster structure became visible and separable. The transformation "
               "from 3D RFM to 2D PC-space is a projection onto the plane of maximum variance, "
               "discarding the direction (PC3) that contributes noise rather than structure."))

    # ── Build ──
    doc.build(s)
    print(f"PDF saved: {OUTPUT}")


if __name__ == "__main__":
    build()
