# Module 6, Step 4 — Model Training: Methodology

---

## 1. Model Selection: XGBoost

### Candidates evaluated

| Model | Type | Strengths | Weaknesses |
|---|---|---|---|
| Logistic Regression | Linear baseline | Fast, interpretable, coefficients have meaning | Cannot capture non-linear interactions (e.g., "heavy item + far state = bad") |
| Random Forest | Bagged ensemble | Robust to overfitting, minimal tuning | Slower than boosted methods, no native cost-sensitivity |
| **XGBoost** (chosen) | Gradient boosted trees | State-of-art tabular performance, built-in `scale_pos_weight`, best SHAP integration | More hyperparameters to tune |
| LightGBM | Gradient boosted trees | Faster training, leaf-wise growth | Slightly less recognized in UK entry-level job specs |
| CatBoost | Gradient boosted trees | Best categorical handling | Slower on small datasets, less SHAP documentation |

### Why XGBoost over LightGBM and CatBoost

All three gradient boosting frameworks deliver comparable predictive performance on tabular data (confirmed by 2025-2026 benchmarks). We chose XGBoost because:

1. **SHAP integration**: `shap.TreeExplainer` was originally built for XGBoost. The integration is the most mature and best documented.

2. **Interview recognition**: XGBoost appears in ~80% of UK data scientist job descriptions that mention ML. LightGBM and CatBoost appear in ~40% and ~20% respectively. For an entry-level portfolio, use what interviewers know.

3. **Scale appropriateness**: LightGBM's speed advantage materialises on datasets >1M rows. At 96K rows, XGBoost trains in seconds — there's no speed problem to solve.

4. **Categorical handling**: CatBoost handles categoricals natively. But our categoricals (27 states, 5 payment types, 73 categories) work perfectly with label encoding + XGBoost. CatBoost's advantage is for high-cardinality categoricals (>1000 levels), which we don't have.

### Why logistic regression as baseline

Every ML project needs a baseline to contextualise model performance. "XGBoost achieves AUC-PR = 0.45" means nothing without knowing that logistic regression achieves AUC-PR = 0.35 on the same data.

Logistic regression with `class_weight='balanced'` is the correct baseline because:
1. It handles imbalance (via balanced weights)
2. It's linear — any improvement from XGBoost proves non-linear patterns exist
3. It trains in <1 second — zero computational cost for a meaningful comparison

---

## 2. Hyperparameter Tuning Strategy

### Why curated parameter combinations, not random search?

| Strategy | Combinations | Time | Interpretability |
|---|---|---|---|
| Grid Search | 3⁸ = 6,561 | Hours | Cannot explain each point |
| Random Search | ~100 | ~30 min | Some points are wasteful |
| Bayesian (Optuna) | ~50 | ~15 min | Requires extra dependency |
| **Curated Search** (chosen) | **6** | **~2 min** | **Every combo has a story** |

Our 6 curated combinations cover distinct modelling strategies:

| Combo | Strategy | Key Params |
|---|---|---|
| 1 | Fast & simple | depth=3, lr=0.1, n=200 |
| 2 | Balanced | depth=5, lr=0.05, n=300 |
| 3 | Complex & cautious | depth=7, lr=0.01, n=500, high reg |
| 4 | High regularisation | depth=5, lr=0.05, reg_alpha=1, reg_lambda=5 |
| 5 | Conservative | depth=3, lr=0.05, high subsample |
| 6 | Aggressive | depth=7, lr=0.1 |

Each combo explores a different bias-variance trade-off. An interviewer can ask "why these 6?" and each has a one-sentence answer.

### XGBoost hyperparameter reference

| Parameter | What it controls | Low value | High value |
|---|---|---|---|
| `max_depth` | Tree complexity | Underfitting (shallow, linear-like) | Overfitting (deep, memorises) |
| `learning_rate` (η) | Step size per tree | Slower convergence, needs more trees | Faster but may overshoot |
| `n_estimators` | Number of boosting rounds | Underfitting | Overfitting (if lr is high) |
| `min_child_weight` | Minimum samples per leaf | More splits (complex) | Fewer splits (conservative) |
| `subsample` | Row sampling per tree | More variance | Less variance (regularisation) |
| `colsample_bytree` | Feature sampling per tree | Less diverse trees | More diverse (regularisation) |
| `reg_alpha` (L1) | Sparsity regularisation | No regularisation | Drives irrelevant feature weights to 0 |
| `reg_lambda` (L2) | Ridge regularisation | No regularisation | Shrinks weights toward 0 |

### The relationship: learning_rate × n_estimators

```
These two parameters are inversely related:

High lr (0.1) + few trees (200):
    Total learning = 0.1 × 200 = 20 "units"
    Fast training, risk of overshoot

Low lr (0.01) + many trees (500):
    Total learning = 0.01 × 500 = 5 "units"
    Slow, stable, better generalisation (usually)

Rule of thumb: if lr ↓, then n_estimators ↑
```

---

## 3. Cross-Validation: TimeSeriesSplit

### Why TimeSeriesSplit, not KFold?

```
KFold (WRONG for temporal data):
    Fold 1: Train on [2,3,4,5], Test on [1]  ← training on future!
    Fold 2: Train on [1,3,4,5], Test on [2]  ← training on future!
    ...

TimeSeriesSplit (CORRECT):
    Fold 1: Train on [1],       Test on [2]
    Fold 2: Train on [1,2],     Test on [3]
    Fold 3: Train on [1,2,3],   Test on [4]
    Fold 4: Train on [1,2,3,4], Test on [5]
```

Each fold trains on a growing window of past data and tests on the next period. This mirrors how the model would be retrained in production (accumulate more historical data, predict the next period).

### Why 5 splits?

```
With n_splits=5 on our training data (~72K orders, 18 months):

    Fold 1: Train ≈ 3 months,  Test ≈ 3 months
    Fold 2: Train ≈ 6 months,  Test ≈ 3 months
    Fold 3: Train ≈ 9 months,  Test ≈ 3 months
    Fold 4: Train ≈ 12 months, Test ≈ 3 months
    Fold 5: Train ≈ 15 months, Test ≈ 3 months

Each test fold covers ~3 months, which is enough to smooth out
monthly variation. The final fold's training set (15 months)
is close to the full training set (18 months).
```

---

## 4. Scoring Metric: `average_precision`

We use `average_precision` (area under the precision-recall curve) as the CV scoring metric because:

```
average_precision = Σ (R_n - R_{n-1}) · P_n

Where:
    R_n = recall at threshold n
    P_n = precision at threshold n
```

This is the area under the precision-recall curve, computed as a weighted sum of precisions at each recall threshold. It evaluates the model across ALL thresholds simultaneously, unlike F1 (which evaluates at a single threshold).

Since we tune the threshold separately (Step 5), we want the CV to select parameters that give the best PR curve overall, not just at one operating point.

---

## 5. Final Model Training

After selecting the best hyperparameters via CV, we train the final model on **all training data** (not just the last CV fold):

```
CV selects best_params (from 6 combos)
    ↓
Train final model on ALL training rows (Sep 2016 – Mar 2018)
    ↓
Evaluate on test set (Apr 2018 – Oct 2018)
```

### Why no early stopping?

Early stopping requires a held-out evaluation set. Using the test set for early stopping would be data leakage (the test set influences when training stops, which affects the model).

Instead, `n_estimators` is part of the hyperparameter search — the CV already selected the right number of trees. The final model trains for exactly that many rounds.

---

## 6. `tree_method="hist"`

XGBoost offers three tree construction methods:

| Method | How | Speed | Accuracy |
|---|---|---|---|
| `exact` | Evaluates all possible split points | Slow | Marginally better |
| `approx` | Uses quantile sketch for split candidates | Moderate | Near-exact |
| **`hist`** (chosen) | Bins features into ~256 buckets | **Fast** | **Near-exact** |

`hist` is the default in XGBoost 2.0+. It bins continuous features into discrete histograms, reducing the number of split candidates from O(n) to O(256). For 96K rows, this provides a ~5× speedup with negligible accuracy loss.

---

## 7. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Model selection | Comparison of 5 candidates with specific reasoning |
| Hyperparameter understanding | Each parameter explained, trade-offs documented |
| CV methodology | TimeSeriesSplit with reasoning, not default KFold |
| ML engineering | Curated search over grid/random, early stopping reasoning |
| XGBoost depth | tree_method, learning_rate × n_estimators relationship |
