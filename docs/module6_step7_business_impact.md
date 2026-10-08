# Module 6, Step 7 — Business Impact Estimation: Methodology

---

## 1. The Cost-Benefit Framework

Every model prediction falls into one of four outcomes. Each has a known cost:

```
                        Predicted
                   Flagged    Not Flagged
              ┌───────────┬───────────────┐
Actual   Bad  │    TP     │      FN       │
Review        │ Intervene │ Bad review    │
              │ Cost: R$8 │ posted        │
              │ Save: R$75│ Cost: R$75    │
              ├───────────┼───────────────┤
         Good │    FP     │      TN       │
Review        │ Intervene │ No action     │
              │ Cost: R$8 │ Cost: R$0     │
              │ Waste     │ Correct       │
              └───────────┴───────────────┘
```

| Outcome | Cost/Benefit | Formula |
|---|---|---|
| True Positive | Save R$75 (prevented bad review) – R$8 (intervention) = **+R$67 net** | TP × (75 - 8) |
| False Positive | Waste R$8 (unnecessary intervention) = **-R$8** | FP × 8 |
| False Negative | Lose R$75 (bad review posted) = **-R$75** | FN × 75 |
| True Negative | R$0 (nothing happens) | 0 |

### Net value of the model

```
Net Value = TP × R$67 - FP × R$8 - FN × R$75
```

### Net value without any model (status quo)

```
All bad reviews get posted (no intervention):
    Cost = (TP + FN) × R$75
```

### Savings from deploying the model

```
Savings = Cost_without_model - Cost_with_model
        = (TP + FN) × 75 - [FN × 75 + (TP + FP) × 8]
        = TP × 75 - TP × 8 - FP × 8
        = TP × 67 - FP × 8
```

---

## 2. Cost Assumptions

### R$8 per intervention

This is the marginal cost of upgrading shipping for one order:

```
Standard shipping (Correios SEDEX):     R$15-25
Express shipping (Correios SEDEX 12):   R$23-33
Difference:                              R$8-10

We use R$8 (conservative lower bound).
```

Alternative interventions (proactive email, customer service pre-contact) cost less (~R$2) but have smaller effect. We model the most impactful intervention.

### R$75 per bad review

This is the estimated lifetime cost of a 1-2 star review on a marketplace:

```
A bad review reduces conversion rate for ALL future visitors who see it.

Calculation:
    Monthly visitors to a product page:    ~200
    Base conversion rate:                   3%
    Conversion rate with a bad review:      2.5%  (0.5pp drop)
    Orders lost per month:                  200 × 0.5% = 1 order
    Average order value:                    R$137
    Review visible for ~6 months:           6 × R$137 × 0.5% × 200 ≈ R$82

    Conservative estimate: R$75
```

This is a lower bound. Industry research (Spiegel Research Center, 2017) suggests the impact can be 2-3× higher for prominent negative reviews.

### Why not use exact costs?

Olist doesn't publish shipping costs or conversion data. Our estimates are **order-of-magnitude correct** — the analysis shows the model is profitable as long as:

```
Cost per intervention < Cost per bad review × (TP / (TP + FP))
R$8 < R$75 × precision
R$8 < R$75 × 0.28
R$8 < R$21  ✓

The model is profitable at ANY intervention cost below ~R$21,
which is a wide margin of safety.
```

---

## 3. Annualisation

The test set covers ~7 months (Apr–Oct 2018). To project annual impact:

```
Annualised Savings = Test Period Savings × (Annual Orders / Test Orders)

Where:
    Test Orders ≈ 28,000  (28% of 96K delivered orders)
    Annual Orders ≈ 50,000  (annualised from the ~25-month dataset)
```

### Why not multiply by 12/7?

Simply scaling by months assumes uniform order volume. The Olist dataset shows significant monthly variation (November–December have 2× the volume of January–February). Using order counts instead of months accounts for this variation.

---

## 4. Sensitivity Analysis

### What if our cost assumptions are wrong?

| Scenario | Intervention Cost | Bad Review Cost | Net Annual Savings |
|---|---|---|---|
| Base case | R$8 | R$75 | R$X (computed at runtime) |
| Cheap intervention | R$2 | R$75 | Higher — proactive email instead of shipping upgrade |
| Expensive intervention | R$15 | R$75 | Lower — but still profitable if precision > 20% |
| Low review impact | R$8 | R$40 | Lower — breakeven at precision > 20% |
| High review impact | R$8 | R$150 | 2× base case savings |

### Break-even analysis

```
The model is profitable when:
    TP × (Bad_Review_Cost - Intervention_Cost) > FP × Intervention_Cost

    TP × (C_review - C_intervene) > FP × C_intervene

    TP / FP > C_intervene / (C_review - C_intervene)

For base case:
    TP / FP > 8 / (75 - 8) = 0.119

    This means: for every 1 false positive, we need at least 0.119
    true positives. Equivalently: precision > 0.119 / (1 + 0.119) = 10.6%

    Our model's precision: ~28%  >>  10.6%  ✓ (comfortable margin)
```

---

## 5. What the Confusion Matrix Tells the Business

```
                        Predicted Unsatisfied    Predicted Satisfied
                        ───────────────────────  ─────────────────────
Actual Unsatisfied      TP = X orders caught     FN = X orders missed
                        → intervened, prevented  → bad review posted
                        
Actual Satisfied        FP = X orders flagged    TN = X orders correct
                        → unnecessarily upgraded → no action needed
```

**For the operations team:**
- "We flagged X orders per month for intervention"
- "Of those, Y% actually needed it (precision)"
- "We caught Z% of all bad reviews before they happened (recall)"
- "Net cost: R$A per month in interventions, saving R$B per month in prevented bad reviews"

---

## 6. ROI Metric

```
ROI = Net Annual Savings / Annual Intervention Cost

Where:
    Annual Intervention Cost = (TP + FP) × R$8 × annualisation_factor
    Net Annual Savings = computed above

Expected ROI: 3-5× (for every R$1 spent on interventions,
              we save R$3-5 in prevented bad reviews)
```

This is the number that justifies deployment to management. A 3× ROI with a R$8 marginal cost per order is a low-risk, high-return investment.

---

## 7. Limitations and Honest Caveats

| Limitation | Impact | Mitigation |
|---|---|---|
| Cost estimates are approximations | Actual savings may differ by ±50% | Break-even analysis shows wide margin |
| Model trained on 2016-2018 data | Customer behaviour may have shifted | Retrain on recent data before deployment |
| Assumes intervention prevents the bad review | Some customers will still be unhappy | Model only claims to reduce, not eliminate bad reviews |
| Test set evaluation, not A/B test | True causal effect unknown | Recommend A/B test before full rollout |

### The right next step

This analysis proves the model is **worth testing**, not that it **will work**. The correct deployment strategy:

```
1. Deploy to 10% of flagged orders (A/B test)
2. Measure: do intervened orders actually get better reviews?
3. If yes → scale to 100%
4. If no → investigate why (intervention type, timing, etc.)
```

---

## 8. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Business-ML translation | Confusion matrix → dollar impact |
| Financial modelling | Cost-benefit framework, break-even analysis, ROI |
| Intellectual honesty | Sensitivity analysis, stated limitations, A/B test recommendation |
| Communication | Numbers a non-technical stakeholder can act on |
| Production thinking | A/B test deployment strategy, retraining recommendation |
