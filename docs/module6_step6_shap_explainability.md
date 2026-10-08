# Module 6, Step 6 — SHAP Explainability: Methodology

---

## 1. Why Explainability Matters for This Model

The model's output ("78% chance of bad review") is useless without knowing **why**. An operations team can't act on a probability — they need to know:

```
Model says: "High risk"
Team asks:  "What should we do about it?"

Without SHAP:  "¯\_(ツ)_/¯ — the model said so."
With SHAP:     "The seller has a 2.1 avg review and estimated delivery is 25 days.
                Options: reroute to faster courier, or assign to a better seller."
```

SHAP transforms the model from a **black-box classifier** into an **actionable decision support tool**.

---

## 2. SHAP vs LIME: Why SHAP?

### SHAP (SHapley Additive exPlanations)

Based on Shapley values from cooperative game theory (1953). For each prediction, SHAP computes the marginal contribution of each feature to the prediction.

### LIME (Local Interpretable Model-agnostic Explanations)

Fits a linear model on perturbed samples around the instance to explain.

| Criterion | SHAP TreeExplainer | LIME |
|---|---|---|
| **Theoretical basis** | Shapley values — axiomatically unique fair allocation | Local linear approximation — no uniqueness guarantee |
| **Consistency** | If a feature's contribution increases, its SHAP value increases | Not guaranteed — LIME can assign contradictory importances |
| **Global + Local** | Both (summary plot = global, waterfall = local) | Local only — no native global view |
| **Speed (tree models)** | O(TLD²) per sample (TreeExplainer) | O(n_perturbations × model_inference) — typically slower |
| **Deterministic** | Yes (exact Shapley computation for trees) | No — depends on random perturbations |
| **Feature interactions** | SHAP interaction values available | Not available |

### Why SHAP wins for our use case

1. **We need both global and local explanations.** Global: "which features drive dissatisfaction across all orders?" Local: "why was this specific order flagged?" LIME can only do local.

2. **TreeExplainer is exact and fast.** For tree-based models, SHAP computes exact Shapley values in polynomial time (no sampling, no approximation). LIME always approximates.

3. **Consistency guarantees.** SHAP satisfies three axioms:
   - **Local accuracy**: SHAP values sum to the prediction (base_value + Σφᵢ = f(x))
   - **Missingness**: features absent from the model get φ = 0
   - **Consistency**: if a feature's contribution increases, its SHAP value increases

   LIME satisfies none of these axiomatically.

4. **Industry standard.** SHAP is the default explainability tool for tabular ML in production. The EU AI Act's explainability requirements further cement SHAP's role.

---

## 3. Shapley Values: The Mathematics

### The intuition

Imagine each feature as a "player" in a cooperative game. The "payout" is the model's prediction. Shapley values fairly distribute the payout among players based on their marginal contributions.

### The formula

For a feature i, the Shapley value is:

```
φᵢ = Σ   |S|! · (|N| - |S| - 1)!   · [f(S ∪ {i}) - f(S)]
    S⊆N\{i}       |N|!

Where:
    N   = set of all features
    S   = a subset of features (excluding i)
    f(S) = model prediction using only features in S
    |S|! · (|N|-|S|-1)! / |N|! = weight for each subset
```

### Why this formula is "fair"

Shapley values are the **unique** allocation satisfying:

1. **Efficiency**: φ₁ + φ₂ + ... + φₙ = f(x) - E[f(x)]
   (SHAP values sum to the difference between this prediction and the average prediction)

2. **Symmetry**: If features i and j contribute equally in all subsets, φᵢ = φⱼ

3. **Null player**: If feature i adds nothing to any subset, φᵢ = 0

4. **Linearity**: For combined models, SHAP values of each model add up

No other method satisfies all four simultaneously (Shapley, 1953; proved unique by Young, 1985).

### Why exact computation is feasible for trees

Computing Shapley values naively requires evaluating 2ⁿ subsets (exponential). For n = 26 features, that's 67 million subsets per sample — infeasible.

**TreeExplainer** (Lundberg et al., 2020) exploits the tree structure:

```
A tree with T trees, each of depth D with L leaves:
    Naive Shapley:    O(2ⁿ) per sample
    TreeExplainer:    O(T · L · D²) per sample

For our model (T ≈ 300 trees, D ≈ 5, L ≈ 32):
    O(300 × 32 × 25) = O(240,000) per sample
    vs naive: O(67,000,000) per sample

Speedup: ~280×
```

TreeExplainer walks each tree from root to leaf, tracking which features were used in splits and their contributions, then aggregates across all trees. The result is exact (not an approximation).

---

## 4. Global Explanations: Summary Plot

### What the beeswarm plot shows

```
            ← pushes toward "satisfied"    pushes toward "unsatisfied" →
                                    |
seller_prior_avg_review       ●●●●●|●●●●●●●●●
estimated_delivery_days       ●●●●●|●●●●●●
freight_ratio                 ●●●●●|●●●●●
seller_prior_unsatisfied_rate ●●●●●|●●●●
total_price                   ●●●●●|●●●
seller_prior_order_count      ●●●●●|●●
...                                |
```

Each dot is one order. Colour = feature value (red = high, blue = low). Position = SHAP value (left = reduces risk, right = increases risk).

**How to read it:** If high values of `seller_prior_avg_review` are on the left (blue dots right, red dots left), then higher seller reviews reduce dissatisfaction risk. If high values of `estimated_delivery_days` are on the right, long delivery estimates increase risk.

### Why we cap at 5,000 samples

Computing SHAP for 25,000 test orders would take several minutes and produce an unreadable plot. 5,000 samples are sufficient for stable importance rankings (law of large numbers — feature importance converges well before 5,000).

---

## 5. Local Explanations: Waterfall Plot

### What a waterfall plot shows

For a single order:

```
Base value (average prediction): 0.13
    + seller_prior_avg_review = 2.1          → +0.15
    + estimated_delivery_days = 28           → +0.08
    + freight_ratio = 0.35                   → +0.04
    + seller_prior_order_count = 3           → +0.03
    - total_price = 45.0                     → -0.02
    - is_same_state = 1                      → -0.03
    ...
    ────────────────────────────────────────────
    = Model output: 0.38  (unsatisfied probability)
```

Starting from the base value (the average prediction across all training data), each feature pushes the prediction up or down. The final sum equals the model's output for this order.

### Why two waterfall plots (high-risk + low-risk)?

We generate two examples:
1. **True Positive** (model correctly flagged an unsatisfied order): shows what drives a high-risk prediction
2. **True Negative** (model correctly did NOT flag): shows what a low-risk order looks like

Together, they tell a complete story:
- "Bad reviews are driven by: poor seller history, long delivery, high freight"
- "Good reviews come from: experienced seller, short delivery, same-state shipping"

An interviewer can look at these two plots and understand the model's decision logic without reading any code.

---

## 6. Feature Importance: SHAP vs XGBoost Built-in

We generate both:

| Method | Metric | Interpretation |
|---|---|---|
| XGBoost `feature_importances_` (gain) | Total gain when a feature is used for splitting | "How useful was this feature for the trees?" |
| SHAP mean |SHAP value| | Average absolute SHAP value across all samples | "How much does this feature move predictions?" |

### Why they can disagree

```
Scenario: A feature is used in many tree splits (high gain)
    but the splits rarely change the prediction (low SHAP).

Example: order_month appears in many splits (gain = high)
    but the splits are close to 50/50, so the net effect on
    any single prediction is small (SHAP = low).
```

SHAP importance is more reliable because it measures the feature's effect on the **output**, not on the internal tree structure. We report SHAP importance as the primary ranking.

---

## 7. Subsampling Strategy

```python
if len(X_test) > 5000:
    idx = np.random.RandomState(42).choice(len(X_test), 5000, replace=False)
    X_shap = X_test.iloc[idx]
```

- **RandomState(42)**: deterministic subsampling — same results every run
- **5,000 samples**: sufficient for stable mean |SHAP| (Central Limit Theorem: with n=5000, the standard error of mean |SHAP| is σ/√5000 ≈ 0.014σ — negligible)
- **replace=False**: no duplicate rows

---

## 8. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Explainability expertise | SHAP vs LIME comparison with Shapley axioms |
| Mathematical depth | Shapley value formula, TreeExplainer complexity analysis |
| Communication | Global (summary) + local (waterfall) = complete explanation |
| Production thinking | Subsampling for speed, deterministic random state |
| ML ethics/regulation | Reference to EU AI Act explainability requirements |
