# Module 6, Step 2 — Data Preparation: Methodology

---

## 1. Time-Based Split vs Random Split

### The problem with random splitting

Random splitting (e.g., `train_test_split(X, y, test_size=0.25, random_state=42)`) shuffles all rows. A training order from October 2018 sits next to a test order from January 2017. The model trains on "future" data and predicts "past" data.

```
Random split (WRONG for temporal prediction):
    Train: [Jan17, Mar18, Oct18, Feb17, Jul18, ...]  ← time is mixed
    Test:  [Nov17, Apr18, Sep16, Jun18, ...]          ← time is mixed
    
    Model sees Oct 2018 data during training,
    then predicts a Sep 2016 order in the test set.
    That's not prediction — it's hindsight.
```

### Time-based split (correct)

```
Time-based split:
    Train: [Sep16, Oct16, ..., Feb18, Mar18]    ← all BEFORE cutoff
    Test:  [Apr18, May18, ..., Sep18, Oct18]    ← all AFTER cutoff

    Model trains on the past, predicts the future.
    This mirrors production: you deploy the model and it scores NEW orders.
```

### Why 2018-04-01 as the cutoff?

The dataset spans September 2016 to October 2018 (~25 months).

```
Train: Sep 2016 – Mar 2018  ≈ 18 months ≈ ~72% of orders
Test:  Apr 2018 – Oct 2018  ≈  7 months ≈ ~28% of orders
```

This gives:
1. Enough training data for the model to learn patterns (18 months covers seasonal variation)
2. A test period long enough to evaluate robustness across multiple months
3. A realistic production scenario (train on historical data, deploy for future orders)

### Why not a 3-way split (train/validation/test)?

A 3-way time split (train / val / test) would reduce training data and complicate the pipeline. Instead, we use TimeSeriesSplit cross-validation within the training set for hyperparameter selection (see Step 4), and the test set only for final evaluation. This maximises training data while maintaining temporal integrity.

---

## 2. Categorical Encoding: Label Encoding

### The three options for tree-based models

| Method | How it works | Suitable for XGBoost? |
|---|---|---|
| **Label Encoding** (chosen) | Maps categories to integers (SP→0, RJ→1, ...) | Yes — trees split on any threshold |
| One-Hot Encoding | Creates binary columns per category | Poor — 73 categories → 73 sparse columns |
| Target Encoding | Maps category to mean of target | Risk of overfitting, needs careful regularisation |

### Why Label Encoding is correct for tree models

A decision tree splits on `feature < threshold`. For a label-encoded `customer_state`:

```
SP = 0, RJ = 1, MG = 2, BA = 3, ...

The tree can learn:
    IF customer_state < 2 → left (SP, RJ)
    ELSE → right (MG, BA, ...)

This is equivalent to grouping states — the tree figures out
which groupings matter, regardless of the numeric assignment.
```

One-hot encoding creates 27 binary columns for 27 states. Each split can only isolate one state at a time, requiring 27× more splits to achieve the same partition. This is both slower and less expressive.

### Why not Target Encoding?

Target encoding maps each category to its mean target value. For `customer_state`:

```
SP → mean(is_unsatisfied where state=SP) = 0.12
RJ → mean(is_unsatisfied where state=RJ) = 0.14
...
```

The problem: this leaks the target into features. Even with leave-one-out regularisation, target encoding creates a direct relationship between features and target that inflates apparent model performance. For 27 states, the regularisation is manageable, but for 73 product categories (some with few samples), overfitting is a real risk.

Label encoding avoids this entirely — the encoded values carry no target information.

---

## 3. Null Handling: Training-Set Median Imputation

### Strategy

```
1. Compute median of each column from the TRAINING set only
2. Fill NULLs in training set with these medians
3. Fill NULLs in test set with the SAME training medians
```

### Why training-set median, not overall median?

Using the overall median (train + test) leaks test-set statistics into training. The test-set median for a column might differ from the training-set median (e.g., if a feature trends over time). Using training-only medians mirrors production, where you don't have future data.

### Why median, not mean?

Median is robust to outliers:

```
Example: seller_prior_avg_delivery_days has outliers (some orders take 60+ days)

    Mean imputation:  12.3 days  (pulled up by outliers)
    Median imputation: 9.0 days  (resistant to outliers)

For tree models, the imputed value determines which side of a split
the null row falls on. Median places it at the "typical" value, which
is the safest assumption for missing data.
```

### Which columns have NULLs?

The primary source of NULLs is seller historical metrics (first orders have no prior data):

| Column | % NULL | Reason |
|---|---|---|
| `seller_prior_order_count` | ~30% | First order for this seller |
| `seller_prior_avg_review` | ~30% | Same |
| `seller_prior_avg_delivery_days` | ~30% | Same |
| `seller_prior_unsatisfied_rate` | ~30% | Same |
| `seller_prior_late_rate` | ~30% | Same |
| `avg_weight_g` | <1% | Missing product data |
| `avg_volume_cm3` | ~2% | Missing product dimensions |

### XGBoost's native missing-value handling

XGBoost can handle NaN natively (it learns a default direction for missing values at each split). However, we still impute because:
1. The logistic regression baseline cannot handle NaN
2. SHAP values are more interpretable on imputed data
3. Explicit imputation makes the pipeline's decisions visible

---

## 4. Feature Column Selection

The feature table has 31 columns. We exclude 4 metadata columns:

| Column | Why excluded |
|---|---|
| `order_id` | Identifier, not a feature |
| `order_purchase_timestamp` | Used for splitting, not as a feature (would leak temporal position) |
| `review_score` | The raw target — would cause perfect prediction |
| `is_unsatisfied` | The binary target variable |

The remaining 27 columns are features.

### Why not include `order_purchase_timestamp` as a feature?

Including time directly as a feature would let the model learn "orders placed after month X are more/less likely to be unsatisfied." This captures temporal trends but:

1. **Not actionable**: You can't change when an order was placed
2. **Fragile**: The trend in the dataset period may not continue
3. **Partially captured**: `order_month` captures seasonality without the trend component

We include cyclical time features (`order_dow`, `order_month`, `order_hour`) which capture repeating patterns, not linear time trends.

---

## 5. What This Step Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Train/test methodology | Time-based split, not random, with justification |
| Leakage awareness | Training-set medians only, timestamp excluded from features |
| Encoding knowledge | Label encoding for trees, with comparison to alternatives |
| Production mindset | Imputation fitted on training data, applied to test |
| Data pipeline design | `prepare_data()` is reusable across training, explanation, and evaluation |
