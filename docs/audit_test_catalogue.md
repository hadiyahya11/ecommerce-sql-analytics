# Audit Test Catalogue

This catalogue documents every analytic in the toolkit: the control it checks, the risk it addresses, its logic and thresholds, its data sources, and its known limitations. Results are from the run of 2026-11-16 on `olist.db`, 99,441 orders from 2016–2018.

Run everything with `python run_audit.py`. Add `--publish` to refresh the dashboard.

---

## 1. Rule-based tests (`audit/tests.py`)

Each test checks **100% of the population**, not a sample. It returns its exceptions in one standard format, so all tests can be combined, reported and filtered the same way:

| Column | Meaning |
|---|---|
| `test_id` | Test code (T01–T06) |
| `test_name` | Readable name |
| `entity_type` | What was checked: `order` or `order item` |
| `entity_id` | Which order (or order item) |
| `amount` | Money involved, in BRL |
| `risk_level` | `High`, `Medium` or `Low` |
| `detail` | One-sentence explanation for the auditor |

Tests are registered in the `TESTS` list. Each entry has its function and a **population query** ("out of how many?"), which is used to compute the exception rate.

### Summary of results

| Test | Exceptions | High | Amount involved (BRL) | Population | Exception rate |
|---|---|---|---|---|---|
| T01 Payment reconciliation | 249 | 8 | 3,262 | 98,665 orders | 0.25% |
| T02 Duplicate payments | 308 | 13 | 17,869 | 99,440 orders | 0.31% |
| T03 Excessive vouchers | 364 | 137 | 43,406 | 3,866 voucher orders | 9.42% |
| T04 Abnormal freight | 146 | 41 | 2,813 | 112,650 order items | 0.13% |
| T05 Process sequence violation | 1,382 | 23 | 209,488 | 99,441 orders | 1.39% |
| T06 Missing approval or carrier date | 16 | 16 | 2,343 | 96,478 delivered orders | 0.02% |
| **Total** | **2,465** | **238** | **279,181** | | |

"Amount involved" is the value of the transactions concerned, **not a loss**. The amounts are of different kinds (a gap, a duplicate, a full order value), and one order can appear in several tests, so the total must not be read as money lost.

### T01: Payment reconciliation

| | |
|---|---|
| **Control** | The amount a customer pays must equal the amount invoiced (item prices + freight). |
| **Risk** | Money collected but not recorded, overcharging, or payment processing errors. |
| **Logic** | Per order: sum of `payment_value` vs sum of `price + freight_value`. Payments and items are aggregated per order **before** joining, to avoid duplicated rows. |
| **Threshold** | Exception if the gap is more than **1 BRL** (tolerance for rounding). **High** if the gap is more than 50 BRL, otherwise Medium. |
| **Data** | `order_payments`, `order_items` |
| **Result** | 249 exceptions (8 High). 232 overpaid (3,065 BRL), 17 underpaid (198 BRL). |
| **Limitations** | 97.2% of exceptions are credit-card payments averaging 6.3 instalments (vs 2.9 for other orders), so most gaps are probably **instalment interest**, i.e. explainable false positives. **Next step:** allow for interest in the rule and focus on the 17 underpayments (revenue never collected). |

### T02: Duplicate payments

| | |
|---|---|
| **Control** | Each payment is recorded once. |
| **Risk** | Double charging, or a payment counted twice. |
| **Logic** | Same `order_id` and same `payment_value` recorded more than once. The amount is the duplicated value: value × (count − 1). |
| **Threshold** | Risk-based on the payment type: **High** for a repeated card charge, **Low** for identical vouchers, otherwise Medium. |
| **Data** | `order_payments` |
| **Result** | 308 exceptions: 13 High (card), 295 Low (voucher). Example: one order with 14 identical vouchers of 50 BRL. |
| **Limitations** | Several identical vouchers on one order are usually legitimate (gift cards split into equal parts), hence Low. The test doesn't look for duplicates across **different** orders, e.g. the same customer charged twice for two orders. |

### T03: Excessive vouchers

| | |
|---|---|
| **Control** | Promotional vouchers are limited per order. |
| **Risk** | Voucher abuse or unauthorised discounts. |
| **Logic** | Orders paid with **3 or more** voucher payments. The amount is the total voucher value. |
| **Threshold** | **High** at 5 or more vouchers, otherwise Medium. |
| **Data** | `order_payments` (where `payment_type = 'voucher'`) |
| **Result** | 364 exceptions (137 High). The maximum is 29 vouchers on one order. |
| **Limitations** | The thresholds (3 and 5) are assumptions; the real voucher policy would set them. The high rate (9.42%) reflects a **small population** (only orders paid by voucher). It overlaps with T02, since identical vouchers appear in both. |

### T04: Abnormal freight

| | |
|---|---|
| **Control** | Shipping charges are reasonable compared with the item. |
| **Risk** | Overcharging, or value hidden in freight. |
| **Logic** | Order lines where `freight_value > 3 × price`. The amount is the excess (freight − price). |
| **Threshold** | **3×**, chosen from the distribution to keep the list reviewable: >1× = 4,124 lines, >2× = 531, **>3× = 146**, >5× = 41. **High** above 5×. |
| **Data** | `order_items` |
| **Result** | 146 exceptions (41 High). Worst case: freight of 121.22 BRL on a 9.90 BRL item (12.2×). |
| **Limitations** | Cheap, heavy or remote-delivery items can legitimately have high freight. Weight and distance aren't used yet; the `products` table has weight and size, which would refine the test. |

### T05: Process sequence violation (control bypass)

| | |
|---|---|
| **Control** | An order follows purchase → payment approval → handed to carrier → delivered. |
| **Risk** | A step skipped or backdated (shipping before payment is approved), or bad data. |
| **Logic** | `order_delivered_carrier_date < order_approved_at` **or** `order_delivered_customer_date < order_delivered_carrier_date`. The amount is the order value. |
| **Threshold** | **High** for "delivered before shipped" (physically impossible, so a data-integrity issue). **Medium** for "shipped before payment approval". |
| **Data** | `orders`, `order_payments` |
| **Result** | 1,382 exceptions: 1,359 shipped before approval, 23 delivered before shipped. |
| **Limitations** | Timestamps may be recorded late, or in different time zones by different systems. The 209k BRL is the value **exposed**, not lost. |

### T06: Missing approval or carrier date

| | |
|---|---|
| **Control** | A delivered order has a payment-approval date and a carrier hand-over date. |
| **Risk** | Delivery without approval, or an incomplete audit trail. |
| **Logic** | `order_status = 'delivered'` and (`order_approved_at` is empty **or** `order_delivered_carrier_date` is empty). |
| **Threshold** | All **High**: there are few cases, and a missing approval is serious. |
| **Data** | `orders`, `order_payments` |
| **Result** | 16 exceptions: 14 without an approval date, 2 without a carrier date. |
| **Limitations** | It can't tell a skipped approval from a date that simply wasn't recorded. Both need follow-up with the data owner. |

---

## 2. Statistical analyses (`audit/statistics.py`)

### S01: Benford's law on payment amounts

| | |
|---|---|
| **Objective** | Screen payment amounts for signs of invented or manipulated values. |
| **Method** | In many natural financial datasets, the first digit d appears with probability log10(1 + 1/d): about 30.1% of amounts start with 1, and only 4.6% with 9. Compare the observed first-digit distribution with this. |
| **Tests** | **Chi-square goodness-of-fit** on the counts, plus the **MAD** (mean absolute deviation), interpreted with Nigrini's first-digit thresholds: < 0.006 close, < 0.012 acceptable, < 0.015 marginal, otherwise nonconformity. |
| **Data** | `order_payments`, payments ≥ 1 BRL (103,720) |
| **Result** | Chi² = 2,013, p < 0.001; **MAD = 0.0142, marginal conformity**. Digit 1: 33.25% vs 30.10% expected; digit 2: 13.89% vs 17.61%. |
| **Interpretation** | With 100,000+ rows, chi-square rejects even tiny differences, which is why MAD measures the size of the deviation. The deviation is plausibly explained by price points chosen by sellers (19.90, 69.90 BRL). |
| **Limitations / next step** | Benford is a **screening** test, not proof. Next step: run it **per seller** or per payment type, and investigate the groups that deviate most. |

### S02: Late delivery vs review score (Mann-Whitney U)

| | |
|---|---|
| **Objective** | Measure whether late deliveries are linked to worse customer satisfaction. |
| **Method** | **Mann-Whitney U** test, two-sided: it compares two groups by ranks, with no assumption of normality, which suits 1–5 star scores. **Effect size:** rank-biserial correlation (0.1 small, 0.3 medium, 0.5 or more large). |
| **Definition** | Late = delivery **date** after the promised date. Same-day delivery counts as on time, because the promised date has no time of day. |
| **Data** | `orders`, `order_reviews` (delivered orders with a review: 96,359) |
| **Result** | Late: n = 6,410, median 1★, mean 2.27. On time: n = 89,949, median 5★, mean 4.29. p < 0.001, **effect size 0.64 (large)**. |
| **Interpretation** | The difference is significant **and** large, so it matters in practice. Delivery performance is a key driver of satisfaction, and logistics controls belong in the audit plan. |
| **Limitations** | This is a correlation, not proof of causation. |

---

## 3. Machine-learning model (`audit/seller_risk.py`)

### M01: Seller risk scoring (Isolation Forest)

| | |
|---|---|
| **Objective** | Risk-based audit planning: rank sellers so auditors know which ones to review first. |
| **Why unsupervised** | No seller is labelled as fraudulent, so a supervised model can't be trained. **Anomaly detection** finds sellers whose behaviour differs from their peers. |
| **Population** | Sellers with **30 or more orders** (634): fewer orders give unreliable averages. |
| **Features** | Built at the (order, seller) level, then averaged per seller:<br>• `late_rate`: share of delivered orders that arrived late<br>• `avg_review`: average review score<br>• `cancel_rate`: share of orders canceled or unavailable<br>• `freight_ratio`: total freight ÷ total price<br>• `exception_rate`: share of the seller's orders flagged by the order-level tests (T01–T03, T05, T06) **in the same run**, which links the rules to the model<br>• `avg_order_value`: average (price + freight) per order |
| **Model** | `StandardScaler` (puts features on the same scale), then `IsolationForest(n_estimators=200, contamination=0.05, random_state=42)`. Risk score = the anomaly score rescaled to 0–100, plus a rank and an outlier flag. `random_state` makes runs reproducible. |
| **Explainability** | `top_reasons` lists the 2 features more than 1 standard deviation (z > 1) in the **risky** direction (for reviews, low is risky). **"Unusual is not the same as risky":** Isolation Forest also flags harmless extremes, such as perfect reviews, so those are not shown as reasons. |
| **Result** | 32 outliers (5%). Main drivers: cancellations (10), late deliveries (6), audit-test exceptions (5), order value (5), freight (3), reviews (3). Rank 1: late on 31.6% of orders (typical: 5.5%), reviews 3.07. Rank 6: **15.8% of its orders flagged by the audit tests**, so the rules and the model agree. |
| **Limitations** | `contamination = 5%` is a choice, not a finding. The score shows how **unusual** a seller is, not that they did anything wrong, and a human review is always required. States with very few sellers (e.g. MA, 1 seller) shouldn't be over-interpreted on the map. The model should be re-run and monitored as data changes. |

---

## 4. Outputs

| Output | Content | Audience |
|---|---|---|
| SQLite tables | `audit_exceptions`, `audit_test_summary`, `benford_results`, `statistical_tests`, `seller_risk` (replaced on each run) | Analysts |
| Excel report | `reports/audit_report_<date>.xlsx`: Summary, T01–T06 (High first), Seller risk (top 50), Statistics. Frozen headers, filters. | Auditors (fieldwork) |
| BigQuery and Looker Studio | The same 5 tables in dataset `olist`, refreshed with `--publish`. Two dashboard pages: exceptions, and seller risk & statistics. | Audit management |
