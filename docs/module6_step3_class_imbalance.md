# Module 6, Step 3 — Class Imbalance Handling: Methodology

---

## 1. The Imbalance Problem

In the Olist dataset, ~87% of reviews are 3-5 stars (satisfied) and ~13% are 1-2 stars (unsatisfied):

```
Class distribution:
    Satisfied (0):    ~85,000 orders    87%    ████████████████████████████████████
    Unsatisfied (1):  ~13,000 orders    13%    █████
```

A model that predicts "satisfied" for every order achieves **87% accuracy** while catching **0%** of bad reviews. Accuracy is a misleading metric.

### Imbalance ratio

```
IR = N_majority / N_minority = 85,000 / 13,000 ≈ 6.5:1
```

This is **moderate** imbalance (not extreme like fraud detection at 1000:1, but enough to bias a naive model toward the majority class).

---

## 2. Method Comparison: `scale_pos_weight` vs SMOTE vs Focal Loss

### Option A: `scale_pos_weight` (Chosen)

**How it works:** Multiplies the loss for minority-class (positive) samples by a factor, making misclassification of unsatisfied orders more costly:

```
Standard loss:   L = -[y·log(p) + (1-y)·log(1-p)]

Weighted loss:   L = -[w·y·log(p) + (1-y)·log(1-p)]

Where w = scale_pos_weight = N_neg / N_pos ≈ 6.5
```

**Effect:** Each unsatisfied order contributes 6.5× more to the gradient update than a satisfied order. The model is penalised 6.5× more for missing an unsatisfied order than for a false alarm.

**Why it's best for XGBoost:**
- Zero data manipulation — no synthetic samples, no modified dataset
- Computationally free — just changes the loss function weights
- Works within the gradient boosting framework (modifies gradients directly)
- Recommended by the XGBoost documentation for imbalanced classification

### Option B: SMOTE (Rejected)

**How it works:** Generates synthetic minority samples by interpolating between existing minority samples in feature space.

```
For two minority samples x₁ and x₂:
    x_new = x₁ + λ·(x₂ - x₁),    λ ~ Uniform(0, 1)
```

**Why rejected for XGBoost:**

1. **Tree models don't benefit from interpolation.** Decision trees split on axis-aligned boundaries. SMOTE creates points between existing points, which don't change where the optimal split boundary falls for trees. The synthetic points are redundant — they reinforce existing splits rather than creating new ones.

2. **Inflates training set size.** To balance a 6.5:1 ratio, SMOTE would create ~72,000 synthetic samples (6.5× the minority class). Training set grows from ~70K to ~142K rows. Training time doubles for no performance gain.

3. **Leakage risk.** If SMOTE is applied before train/test split (a common mistake), synthetic samples in the test set are interpolated from training samples. Even if applied correctly (after split), the synthetic samples carry information from the training set's structure.

4. **Research consensus (2025).** Recent benchmarks show that for gradient boosting on tabular data, cost-sensitive learning (`scale_pos_weight`) matches or outperforms SMOTE while being simpler and faster. Tree models already split well without oversampling.

### Option C: Focal Loss (Rejected)

**How it works:** Down-weights easy (well-classified) examples and focuses on hard (misclassified) examples:

```
FL(p) = -α·(1-p)^γ · log(p)     for positive class
      = -(1-α)·p^γ · log(1-p)   for negative class

Where:
    α controls class balance (like scale_pos_weight)
    γ controls focus on hard examples (γ=0 → standard cross-entropy)
```

**Why rejected:**

1. **Adds two hyperparameters (α, γ)** to an already complex tuning space. scale_pos_weight adds one (and has a sensible default: N_neg/N_pos).

2. **Requires custom objective function** in XGBoost (implementing gradient and hessian). This adds code complexity and makes the pipeline harder to maintain.

3. **Diminishing returns at moderate imbalance.** Focal loss was designed for extreme imbalance (object detection: 100,000:1). At our 6.5:1 ratio, the standard weighted loss is sufficient — the "easy" examples aren't so overwhelming that they drown out the minority class gradient.

4. **Harder to explain in an interview.** scale_pos_weight has a one-sentence explanation. Focal loss requires explaining γ's focusing effect, which is tangential to the business problem.

---

## 3. Optimal `scale_pos_weight` Value

### Textbook formula

```
scale_pos_weight = N_negative / N_positive = (y == 0).sum() / (y == 1).sum()
```

For our dataset: `scale_pos_weight ≈ 6.5`

### Is the textbook ratio always optimal?

No. The optimal value depends on the business cost asymmetry. Research shows that sweeping several values around the ratio often finds a better trade-off.

However, for our use case:
- The textbook ratio is a strong starting point
- We tune the **threshold** separately (Step 5), which controls the precision-recall trade-off more precisely than adjusting scale_pos_weight
- Tuning both scale_pos_weight AND threshold creates a confounded search space

Our approach: **fix scale_pos_weight at the textbook ratio, tune the threshold.**

---

## 4. Evaluation Metrics: Why Not Accuracy?

### The accuracy trap

```
Model A: Predicts "satisfied" for everything
    Accuracy: 87%    (looks great!)
    Recall:   0%     (catches zero bad reviews)
    Business value: ZERO

Model B: Our XGBoost with tuned threshold
    Accuracy: 75%    (looks worse!)
    Recall:   65%    (catches 65% of bad reviews)
    Business value: R$100K+ annual savings
```

### Metrics we use

| Metric | Formula | Why |
|---|---|---|
| **Precision** | TP / (TP + FP) | Of the orders we flag, how many truly needed intervention? |
| **Recall** | TP / (TP + FN) | Of all bad reviews, how many did we catch? |
| **F1 Score** | 2·P·R / (P+R) | Harmonic mean of precision and recall |
| **F2 Score** | 5·P·R / (4P+R) | Weighs recall 2× more than precision |
| **AUC-PR** | Area under PR curve | Threshold-independent performance across all operating points |
| **MCC** | (TP·TN - FP·FN) / √((TP+FP)(TP+FN)(TN+FP)(TN+FN)) | Balanced metric that accounts for all four confusion matrix cells |

### Why AUC-PR over AUC-ROC?

```
AUC-ROC uses FPR = FP / (FP + TN)

When TN is large (87% of data is negative), FPR stays low even
when FP is substantial. A model with 1,000 false positives has:
    FPR = 1,000 / 85,000 = 1.2%   ← looks great!
    But that's 1,000 unnecessary shipping upgrades.

AUC-PR uses Precision = TP / (TP + FP)
    Same 1,000 false positives:
    Precision = 500 / (500 + 1,000) = 33%   ← reveals the problem.
```

AUC-PR is more informative than AUC-ROC when the positive class is rare.

### Why MCC?

Matthews Correlation Coefficient is the only metric that produces a high score **only if the model does well on all four confusion matrix cells** (TP, TN, FP, FN). It ranges from -1 (total disagreement) to +1 (perfect prediction), with 0 meaning no better than random. It's considered the most reliable single metric for imbalanced binary classification.

---

## 5. Mathematical Derivation: F-beta Score

The F-beta score generalises the F1 score by weighting precision and recall differently:

```
F_β = (1 + β²) · (Precision · Recall) / (β² · Precision + Recall)
```

**Derivation from weighted harmonic mean:**

```
The F1 score is the harmonic mean of P and R:
    1/F1 = (1/2) · (1/P + 1/R)

The F-beta score is the WEIGHTED harmonic mean:
    1/F_β = 1/(1+β²) · (β²/P + 1/R)

Solving for F_β:
    F_β = (1 + β²) · P · R / (β² · P + R)
```

**Interpretation of β:**
- β = 1: F1 — equal weight to precision and recall
- β = 2: F2 — recall is 2× as important as precision
- β = 0.5: F0.5 — precision is 2× as important as recall

**Why F2 for our use case:**

```
False negative (miss a bad review):  costs R$75 (bad review posted)
False positive (unnecessary upgrade): costs R$8  (wasted shipping cost)

Cost ratio: 75/8 ≈ 9.4

Recall matters ~9× more than precision. F2 (β=2) weights recall
2× more — a conservative step toward the true cost ratio.
We don't use β=9.4 because extreme β values make the F-score
almost identical to recall alone, losing the precision constraint.
```

---

## 6. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Class imbalance expertise | Comparison of 3 methods with mathematical reasoning |
| Metric selection | AUC-PR over AUC-ROC with worked example |
| Cost-sensitive thinking | F2 score derived from business cost asymmetry |
| Research awareness | SMOTE rejection backed by 2025 benchmark findings |
| Mathematical rigour | F-beta derivation from weighted harmonic mean |
