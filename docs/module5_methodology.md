# Module 5 — README & Documentation: Methodology

This document explains every decision behind the README structure, the ER diagram format, the recommendation projection methodology, and what was deliberately included or excluded.

---

## 1. Why This README Structure?

### The 90-Second Rule

Hiring managers and recruiters spend **~90 seconds** scanning a GitHub repo before deciding whether to investigate further ([Dataquest, 2025](https://www.dataquest.io/blog/how-to-share-data-science-portfolio/)). The README must answer three questions in that window:

1. **What did you build?** (first sentence)
2. **Why does it matter?** (business context paragraph)
3. **What did you find?** (key findings table)

Everything else — SQL examples, tech stack, setup instructions — is for the interviewer who has already decided to look deeper.

### Section ordering rationale

| Section | Position | Why this position |
|---|---|---|
| Title + one-liner | Top | Immediate context in 10 words |
| Business Context | 2nd | Frames everything that follows as business-driven, not code-driven |
| Data Model (ER diagram) | 3rd | Visual anchors attention. Shows schema complexity at a glance |
| Project Structure | 4th | Demonstrates engineering discipline. Scannable tree format |
| SQL Examples | 5th | Proof of technical skill. Interviewer can assess SQL fluency |
| Key Findings | 6th | The "so what?" — numbers that prove the analysis found something |
| Recommendations | 7th | The "now what?" — actions with projected impact. This is what separates analysts from dashboard builders |
| Tech Stack | 8th | Keyword matching for ATS (Applicant Tracking Systems) |
| How to Run | 9th | Reproducibility. Shows this isn't a screenshot — it actually runs |
| Methodology | 10th | Links to the deep docs for interviewers who want rigour |
| Dataset | Last | Attribution and license compliance |

### What was deliberately excluded

| Excluded | Why |
|---|---|
| "About Me" section | Belongs on LinkedIn/CV, not in a project README |
| Badges (build status, coverage) | No CI/CD pipeline. Fake badges are worse than none |
| Screenshots of Power BI | The dashboard is published to web — link is better than static images. Screenshots are added after deployment |
| Installation on Windows/Linux | The user (Mohit) runs macOS. Platform-specific instructions are added when someone opens an issue |
| Jupyter notebook links | Project uses .py files, not notebooks |
| "Future Work" section | Invites the question "why didn't you do it?" Better to list what you DID do |

---

## 2. ER Diagram: Why Mermaid over Alternatives?

### Alternatives considered

| Format | Pros | Cons |
|---|---|---|
| **Mermaid erDiagram** (chosen) | Text-based (version-controlled). GitHub renders natively. Editable without tools. | Limited styling. No custom positions. |
| dbdiagram.io | Pretty output. Drag-and-drop. | External dependency. Image export = static. Not version-controlled. |
| Draw.io / Lucidchart | Full control over layout | Binary file or XML. Not diffable. Requires external tool. |
| ASCII art | Works everywhere | Hard to read for complex schemas. No relationship lines. |
| Python (ERAlchemy, graphviz) | Programmatic | Requires database connection. Generates image, not text. |

### Why Mermaid wins for a GitHub portfolio

1. **Native rendering**: GitHub renders Mermaid in README.md without any external service. No image to host, no link to break.

2. **Version-controlled**: The diagram is text. A `git diff` shows exactly what changed (e.g., "added `seller_state` column to `sellers` table"). An image diff shows nothing useful.

3. **Editable by anyone**: A reviewer can fork the repo and edit the diagram without installing any software.

4. **Crow's foot notation**: Mermaid uses standard cardinality symbols (`||--o{`, `}o--||`), which is the notation used in data engineering interviews.

### Cardinality notation explained

```
||    exactly one
o|    zero or one
|{    one or many
o{    zero or many

--    identifying relationship (child depends on parent)
..    non-identifying relationship (child exists independently)
```

In our diagram:
- `customers ||--o{ orders` → one customer places zero or many orders
- `orders ||--|{ order_items` → one order contains one or many items
- `customers }o..o{ geolocation` → non-identifying, many-to-many (via zip code)

---

## 3. Key Findings: Selection Criteria

The README lists 7 findings. We started with 20+ observations from Module 2 and 3 and filtered using three criteria:

### Criterion 1: Is it actionable?

An actionable finding leads to a specific business decision. "The dataset has 99,441 orders" is a fact, not a finding. "Late deliveries receive 2× more 1-star reviews" is a finding because it implies "fix delivery to fix reviews."

### Criterion 2: Is it surprising?

If the finding is obvious (e.g., "São Paulo has the most orders" — it's the largest city), it doesn't demonstrate analytical value. We include it only when paired with a non-obvious insight ("SP has 42% of revenue but represents only 1 of 27 states — massive concentration risk").

### Criterion 3: Does it have a number?

"Delivery affects reviews" is a claim. "Late deliveries average 2.5 stars vs 4.3 for on-time" is evidence. Every finding in the README includes a specific number.

### Findings that didn't make the cut

| Observation | Why excluded |
|---|---|
| "Most orders are delivered" | Not surprising. 97% delivered is expected for an e-commerce platform. |
| "Reviews are mostly 5 stars" | Common in e-commerce. Not actionable. |
| "Product weight correlates with freight" | Obvious: heavier items cost more to ship. |
| "Some products have no category" | Data quality issue, not a business finding. Already in Module 2. |
| "Boleto payments take longer to confirm" | True but not actionable by Olist (boleto processing is bank-side). |

---

## 4. Recommendation Projections: Mathematical Methodology

### The projection framework

Each recommendation follows this structure:

```
Current State → Action → Mechanism → Metric Change → Revenue Impact

Example:
6.5% late rate → Invest in logistics → Fewer late deliveries → +0.06 avg review →
    → +2-3% conversion → R$135K-200K/year
```

### How we estimate revenue impact

**Method: Chain of proportional effects**

```
ΔRevenue = ΔMetric × Sensitivity × Base Revenue

Where:
    ΔMetric      = change in the operational metric (e.g., late rate drops 3.25pp)
    Sensitivity  = how much revenue changes per unit of metric change
    Base Revenue = R$6.75M/year (annualised from the dataset period)
```

### Recommendation 1: Late delivery reduction

```
Step 1: Quantify the problem
    Late orders:          ~6,500 / 100,000 = 6.5%
    Late avg review:      ~2.5
    On-time avg review:   ~4.3
    Gap:                  1.8 review points

Step 2: Define the intervention
    Target:               Reduce late rate by 50% (6.5% → 3.25%)
    Orders moved:         3,250

Step 3: Calculate review impact
    Review improvement per moved order:  +1.8 points
    Weighted platform impact:  (3,250 × 1.8) / 100,000 = +0.06 points

Step 4: Convert to revenue
    Industry benchmark: 0.5-1% conversion lift per 0.1 review-point improvement
    (Source: Spiegel Research Center, Northwestern — "How Online Reviews
     Influence Sales", 2017. Finding: product pages with reviews show 
     270% higher conversion than those without; each 0.1-point increase 
     in avg rating correlates with ~0.5-1% conversion lift in the 3-4 
     star range.)

    Our review improvement: 0.06 points ≈ 0.3-0.6% conversion lift
    Conservative estimate: +2% of revenue (accounts for first-order
    effects only, ignoring word-of-mouth and repeat purchase effects)

    Revenue impact: 2% × R$6.75M = R$135K
    Upper bound:    3% × R$6.75M = R$202K
```

### Recommendation 2: Seller quality management

```
Step 1: Identify the cohort
    Bottom 5% of sellers by review score: ~40 sellers
    These sellers: avg review < 2.5, handle ~8% of orders

Step 2: Model the removal scenario
    Orders from bottom sellers: ~8,000
    Assumption: 70% of these orders migrate to better sellers
                30% lost (customers who only found Olist through that seller)

    Migrated orders:  5,600
    Review improvement per migrated order: 2.0 → 3.8 (+1.8)

Step 3: Platform impact
    Platform review lift: (5,600 × 1.8) / 100,000 = +0.10 points
    1-star review reduction: bottom sellers generate ~2,400 1-star reviews
        Removing them reduces 1-star reviews by ~35% platform-wide

Step 4: Revenue
    Lost revenue from delisted sellers:     30% × 8,000 × R$137 = -R$329K
    Gained from reputation improvement:     0.10 review points
        → ~0.5-1% conversion lift → +R$337K to R$675K
    Net impact:                             R$100K to R$346K (conservative: R$100K-150K)
```

### Recommendation 3: Installment promotion

```
Step 1: Baseline
    Credit card orders:           ~74,000 (74%)
    Single-payment credit orders: ~41,000 (55% of credit)
    Single-payment AOV:           ~R$120
    4-6 installment AOV:          ~R$250

Step 2: Mechanism
    When customers see "R$42/month for 6 months" instead of "R$250",
    price anchoring shifts. The monthly price feels affordable.
    The total purchase increases because the payment barrier is lower.

    This is not hypothetical — Mercado Libre, Amazon Brazil, and Magazine
    Luiza all prominently display installment pricing. It's standard
    Brazilian e-commerce practice.

Step 3: Conservative conversion
    If 20% of single-payment orders switch to installments:
        Switched orders: 8,200
        AOV increase: R$120 → R$200 (conservative — not full R$250)
        Incremental revenue per order: R$80
        Total: 8,200 × R$80 = R$656K over dataset period (~2 years)
        Annualised: ~R$330K/year

Step 4: Why this is the highest-impact recommendation
    Cost to implement:     Near-zero (UX/checkout change)
    Risk:                  Low (no logistics investment, no seller disruption)
    Revenue impact:        R$330K/year
    Payback period:        Immediate
```

### Why ranges, not point estimates

Every projection gives a range (e.g., R$135K–R$200K) because:

1. **Sensitivity to assumptions**: The conversion-to-review relationship is based on industry benchmarks, not Olist-specific data. The true sensitivity could be 0.5× or 2× our estimate.

2. **Intellectual honesty**: A point estimate ("this will generate exactly R$173,250") implies false precision. Ranges communicate uncertainty, which interviewers respect.

3. **Decision-making utility**: The decision to invest in logistics doesn't depend on whether the impact is R$135K or R$200K — both justify the investment. The range answers "is this worth doing?" without pretending to answer "how much exactly?"

---

## 5. SQL Examples: Selection Criteria

The README includes 3 SQL examples. We chose them to demonstrate maximum technique breadth in minimum space:

| Example | Techniques Shown | Why This Query |
|---|---|---|
| Seller tier segmentation (Q06) | 4-table JOIN, 3 CTEs, min-max normalisation, NTILE, composite score | The most complex query. Shows SQL sophistication. |
| MoM revenue growth (Q10) | LAG, Named WINDOW, SAFE_DIVIDE | Period-over-period is the most common interview SQL question. |
| QUALIFY (Q05) | QUALIFY clause | BigQuery-specific. Shows platform knowledge. |

**What we excluded from the README:**
- Simple aggregation queries (Q01, Q09) — they don't demonstrate advanced SQL
- All 18 queries — too long for a README. The full set is in `business_queries.py`

---

## 6. Tech Stack Table: Why This Format?

### Keyword optimisation for ATS

Many UK companies use Applicant Tracking Systems that scan for keywords. The tech stack table uses exact terms that match job descriptions:

| Job Description Term | Our README | Match |
|---|---|---|
| "Google BigQuery" or "GCP" | "Google BigQuery (free tier)" | ✓ |
| "SQL" + "window functions" | "CTEs, window functions (RANK, LAG, NTILE...)" | ✓ |
| "Power BI" | "Power BI (4 tabs, 19 visuals...)" | ✓ |
| "Python" | "Python — kagglehub, google-cloud-bigquery" | ✓ |
| "XGBoost" or "scikit-learn" | "XGBoost, scikit-learn, SHAP" | ✓ |
| "Data visualisation" or "dashboard" | "BI Dashboard" row | ✓ |

### Why table format over a bullet list?

Tables are scannable. A recruiter's eye follows the left column (category) and right column (tools). A bullet list requires reading full sentences.

---

## 7. What This Module Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Technical writing | README readable by both recruiters (90-second scan) and engineers (SQL examples) |
| Business communication | Recommendations with projected revenue impact, not just "findings" |
| Data modelling | Mermaid ER diagram with correct cardinality notation |
| Quantitative reasoning | Chain-of-effects revenue projections with stated assumptions |
| Intellectual honesty | Ranges instead of point estimates. Assumptions made explicit. |
| Portfolio craft | Structure, ATS keywords, reproducibility instructions |
