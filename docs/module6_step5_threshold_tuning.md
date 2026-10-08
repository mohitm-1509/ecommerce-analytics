# Module 6, Step 5 — Threshold Tuning: Methodology

---

## 1. The Default Threshold Problem

Binary classifiers output a **probability** (0 to 1). To make a decision, we apply a threshold:

```
If P(unsatisfied) ≥ threshold → flag for intervention
If P(unsatisfied) <  threshold → no action
```

The default threshold is **0.5**: flag if the model is more confident in "unsatisfied" than "satisfied." This seems intuitive but is wrong when:
1. Classes are imbalanced (unsatisfied is only 13%)
2. Misclassification costs are asymmetric (missing a bad review costs 9× more than a false alarm)

### Why 0.5 is suboptimal

```
At threshold = 0.5:
    Model flags ONLY orders it's very confident about (prob > 50%)
    This gives HIGH precision (few false alarms)
    But LOW recall (misses many bad reviews with prob = 30-49%)

The missed orders (30-49% probability) are exactly the ones where
intervention would be most valuable — moderate risk, easy to fix.
```

---

## 2. The Precision-Recall Trade-off

Lowering the threshold catches more bad reviews (higher recall) but also flags more good orders (lower precision):

```
Threshold    Precision    Recall    F1     Flagged Orders
─────────    ─────────    ──────    ────   ──────────────
0.50         0.45         0.25     0.32   ~550
0.40         0.35         0.45     0.39   ~1,300
0.30         0.28         0.60     0.37   ~2,200
0.20         0.20         0.75     0.31   ~3,800
0.10         0.15         0.90     0.25   ~6,000
```

(Illustrative — actual values depend on model output.)

**There is no "correct" threshold — only a threshold that optimises a chosen objective.**

---

## 3. F1 vs F2: Which Objective to Optimise?

### F1: Equal weight to precision and recall

```
F1 = 2 · P · R / (P + R)

F1 is maximised when P ≈ R (the threshold where precision and recall
are closest to each other).
```

### F2: Recall matters 2× more than precision

```
F2 = 5 · P · R / (4·P + R)

F2 is maximised at a LOWER threshold than F1 — it tolerates more
false alarms to catch more bad reviews.
```

### Why we choose F2

The business cost structure:

```
Cost of a false negative (missed bad review):  R$75
Cost of a false positive (unnecessary upgrade): R$8

Ratio: 75 / 8 = 9.4

Recall should matter ~9× more than precision.
F2 (β = 2) weights recall 2× more than precision.

Why not β = √9.4 ≈ 3?
    F3 makes the score ≈ recall alone, losing the precision constraint.
    F2 is the standard "recall-favoring" choice that still penalises
    excessive false alarms.
```

### Mathematical justification for the threshold

At the F2-optimal threshold, the marginal cost of lowering the threshold further equals the marginal benefit:

```
Marginal benefit of lowering threshold by Δ:
    Δ_TP additional bad reviews caught → save Δ_TP × R$75

Marginal cost:
    Δ_FP additional false alarms → spend Δ_FP × R$8

Optimal when:  Δ_TP × 75 = Δ_FP × 8
    →  Δ_TP / Δ_FP = 8 / 75 ≈ 0.107

So we should keep lowering the threshold as long as each additional
false alarm "buys" at least 0.107 additional true positives.
```

---

## 4. How Threshold Tuning Works in Our Code

```python
precisions, recalls, thresholds = precision_recall_curve(y_test, y_prob)

# F2 at each threshold
beta = 2.0
f2_scores = (1 + beta**2) * P * R / (beta**2 * P + R)

# Best F2 threshold
best_f2_idx = argmax(f2_scores)
optimal_threshold = thresholds[best_f2_idx]
```

`precision_recall_curve` computes precision and recall at every unique probability value in the test predictions. We compute F2 at each point and pick the threshold that maximises it.

### Visualisation (saved to `outputs/precision_recall_curve.png`)

The plot shows two panels:
1. **Left: PR curve** — precision (y) vs recall (x). The area under this curve = AUC-PR.
2. **Right: F1/F2 vs threshold** — the F1 and F2 curves, with vertical lines marking the optimal threshold for each.

The gap between F1-optimal and F2-optimal thresholds shows the effect of cost asymmetry:

```
F1-optimal threshold: ~0.35 (higher — conservative)
F2-optimal threshold: ~0.25 (lower — favours catching bad reviews)
```

---

## 5. Comparison: Default vs Tuned Threshold

```
                    Default (0.50)              Tuned (F2-optimal)
─────────────       ──────────────              ──────────────────
Recall              ~25%                        ~60-70%
Precision           ~45%                        ~25-30%
F1                  ~0.32                       ~0.35-0.40
F2                  ~0.27                       ~0.50-0.55
Orders flagged      ~550                        ~2,200
Bad reviews caught  ~300 / 1,200                ~750 / 1,200
Missed              ~900                        ~450
```

The tuned threshold catches **2.5× more bad reviews** at the cost of ~5× more interventions. Since interventions cost R$8 each and prevented bad reviews save R$75 each, this trade-off is highly profitable:

```
Extra interventions: 1,650 × R$8 = R$13,200
Extra bad reviews caught: 450 × R$75 = R$33,750
Net benefit of threshold tuning: R$20,550 (test period)
```

---

## 6. Production Considerations

### Monitoring threshold drift

In production, the optimal threshold should be recalibrated periodically because:
1. **Class distribution shifts**: if the unsatisfied rate changes, the optimal threshold changes
2. **Feature distribution shifts**: new sellers, new product categories, seasonal effects
3. **Cost changes**: if intervention cost changes (e.g., new shipping contract), the cost ratio changes

A production system would recalibrate monthly using the most recent 3 months of data.

### Threshold as a business lever

The operations team can adjust the threshold based on capacity:

```
During holiday season (capacity constrained):
    Raise threshold to 0.35 → fewer flags, only high-confidence cases

During slow periods (excess capacity):
    Lower threshold to 0.20 → flag more orders, prevent more bad reviews
```

This makes the model a tunable tool, not a fixed predictor.

---

## 7. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Threshold selection | F1 vs F2 comparison with cost-ratio justification |
| Business-ML translation | Threshold mapped to operational costs |
| Mathematical reasoning | Marginal cost = marginal benefit derivation |
| Production thinking | Threshold as a tunable business lever, monitoring for drift |
| Visualisation | PR curve with annotated optimal thresholds |
