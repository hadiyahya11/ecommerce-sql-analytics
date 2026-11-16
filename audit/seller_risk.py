import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from audit.db import read_sql

MIN_ORDERS = 30  # fewer orders -> averages too unreliable to compare sellers

FEATURE_COLUMNS = ['late_rate', 'avg_review', 'cancel_rate', 'freight_ratio',
                   'exception_rate', 'avg_order_value']

# For explanations: +1 = a HIGH value is risky, -1 = a LOW value is risky
RISKY_DIRECTION = {'late_rate': 1, 'avg_review': -1, 'cancel_rate': 1,
                   'freight_ratio': 1, 'exception_rate': 1, 'avg_order_value': 1}


def build_seller_features(exceptions):
    """One row per seller (with >= MIN_ORDERS orders) and the 6 risk features.

    `exceptions` is the DataFrame produced by the audit tests in this same run,
    so the model always uses the current exceptions, not last run's table.
    """
    # Grain = one row per (order, seller): an order can contain items from several
    # sellers, so price/freight are summed per seller BEFORE joining (no fan-out).
    query = """
    WITH seller_items AS (
        SELECT order_id, seller_id,
               SUM(price) AS price,
               SUM(freight_value) AS freight
        FROM order_items
        GROUP BY order_id, seller_id
    ),
    reviews AS (
        SELECT order_id, AVG(review_score) AS review_score  -- some orders have 2 reviews
        FROM order_reviews
        GROUP BY order_id
    )
    SELECT si.seller_id,
           s.seller_state,
           si.order_id,
           CASE WHEN o.order_delivered_customer_date IS NULL THEN NULL  -- not delivered: ignore
                WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date) THEN 1.0
                ELSE 0.0 END AS is_late,
           r.review_score,
           CASE WHEN o.order_status IN ('canceled', 'unavailable') THEN 1.0 ELSE 0.0 END AS is_canceled,
           si.price,
           si.freight
    FROM seller_items si
    JOIN orders o USING (order_id)
    JOIN sellers s USING (seller_id)
    LEFT JOIN reviews r USING (order_id)
    """
    orders = read_sql(query)

    # Link the rule-based tests to the ML: was this order flagged by any order-level test?
    flagged_orders = set(exceptions.loc[exceptions['entity_type'] == 'order', 'entity_id'])
    orders['is_flagged'] = orders['order_id'].isin(flagged_orders).astype(float)

    # Aggregate to one row per seller (groupby keeps seller_id aligned with its values)
    features = orders.groupby(['seller_id', 'seller_state']).agg(
        n_orders=('order_id', 'nunique'),
        late_rate=('is_late', 'mean'),        # mean ignores NaN (undelivered orders)
        avg_review=('review_score', 'mean'),
        cancel_rate=('is_canceled', 'mean'),
        total_freight=('freight', 'sum'),
        total_price=('price', 'sum'),
        exception_rate=('is_flagged', 'mean'),
    ).reset_index()
    features['freight_ratio'] = features['total_freight'] / features['total_price']
    features['avg_order_value'] = (features['total_price'] + features['total_freight']) / features['n_orders']

    features = features[features['n_orders'] >= MIN_ORDERS].reset_index(drop=True)
    return features[['seller_id', 'seller_state', 'n_orders'] + FEATURE_COLUMNS]


def explain(z_row):
    """Top 2 features pushing this seller in the RISKY direction, as readable text.

    Only features more than 1 standard deviation in the risky direction count
    (z > 1): "unusual" is not the same as "risky" (e.g. perfect reviews are unusual).
    """
    risky = {f: z_row[f] * RISKY_DIRECTION[f] for f in FEATURE_COLUMNS}
    top = [f for f in sorted(risky, key=risky.get, reverse=True) if risky[f] > 1][:2]
    if not top:
        return 'Unusual combination, no single risky driver'
    return ', '.join(f"{f} (z={z_row[f]:+.1f})" for f in top)


def score_sellers(features):
    """Isolation Forest anomaly score (0-100), rank, outlier flag and reasons."""
    # 1. scale: otherwise avg_order_value (hundreds of BRL) would dominate rates (0-1)
    X = StandardScaler().fit_transform(features[FEATURE_COLUMNS])

    # 2. unsupervised anomaly detection: no fraud labels exist, so no supervised model
    model = IsolationForest(n_estimators=200, contamination=0.05, random_state=42).fit(X)

    # 3. score_samples: lower = more abnormal -> flip the sign, rescale to 0-100
    raw = -model.score_samples(X)
    scored = features.copy()
    scored['risk_score'] = ((raw - raw.min()) / (raw.max() - raw.min()) * 100).round(1)
    scored['is_outlier'] = model.predict(X) == -1      # -1 = outlier (about 5% of sellers)
    scored['risk_rank'] = scored['risk_score'].rank(ascending=False, method='first').astype(int)

    # 4. explainability: z-scores are the scaled values, one column per feature
    z = pd.DataFrame(X, columns=FEATURE_COLUMNS)
    scored['top_reasons'] = z.apply(explain, axis=1)

    return scored.sort_values('risk_rank').reset_index(drop=True)
