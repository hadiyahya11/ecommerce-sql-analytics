import numpy as np
import pandas as pd
from scipy import stats

from audit.db import read_sql

# Nigrini's MAD thresholds for the first-digit test (upper bound, label)
NIGRINI_FIRST_DIGIT = [(0.006, "Close conformity"), (0.012, "Acceptable conformity"),
                       (0.015, "Marginal conformity"), (float("inf"), "Nonconformity")]


def benford_analysis():
    """Compare the first digit of payment amounts with Benford's law.

    Returns (benford_results, summary):
      benford_results: 9 rows, one per digit, with observed vs expected %
      summary: dict with n, chi-square, p-value, MAD and the conformity level
    """
    # 1. amounts >= 1 BRL (smaller amounts have no meaningful first digit)
    query = """
    SELECT payment_value
    FROM order_payments
    WHERE payment_value >= 1"""
    df = read_sql(query)

    # 2. first digit: safe as text because every value is >= 1
    first_digits = df['payment_value'].astype(str).str[0].astype(int)

    # 3. observed counts and proportions per digit
    observed_counts = first_digits.value_counts().reindex(range(1, 10), fill_value=0)
    n = observed_counts.sum()
    observed_proportions = observed_counts / n

    # 4. Benford's expected proportions: log10(1 + 1/d)
    expected_proportions = np.log10(1 + 1 / np.arange(1, 10))

    # 5. chi-square goodness-of-fit: must compare COUNTS, not proportions
    chi2_stat, p_value = stats.chisquare(observed_counts, expected_proportions * n)

    # 6. MAD = average size of the deviation (robust to large n, unlike the p-value)
    mad = np.mean(np.abs(observed_proportions.values - expected_proportions))
    conformity = next(label for limit, label in NIGRINI_FIRST_DIGIT if mad < limit)

    benford_results = pd.DataFrame({
        'digit': range(1, 10),
        'count': observed_counts.values,
        'observed_pct': (observed_proportions.values * 100).round(2),
        'expected_pct': (expected_proportions * 100).round(2),
        'difference_pct': ((observed_proportions.values - expected_proportions) * 100).round(2),
    })
    summary = {
        "analysis": "Benford first-digit test on payment amounts",
        "n": int(n),
        "statistic": round(float(chi2_stat), 1),   # chi-square
        "p_value": float(p_value),
        "effect_size": round(float(mad), 4),       # MAD
        "conclusion": f"{conformity} (MAD {mad:.4f})",
    }
    return benford_results, summary


def late_delivery_review_test():
    """Mann-Whitney U test: do late deliveries get lower review scores?"""
    # compare DATES: the promised date has no time, so same-day delivery is on time
    query = """
    SELECT r.review_score,
           CASE WHEN date(o.order_delivered_customer_date) > date(o.order_estimated_delivery_date)
                THEN 'Late' ELSE 'On time' END AS delivery_status
    FROM order_reviews r
    JOIN orders o ON o.order_id = r.order_id
    WHERE o.order_delivered_customer_date IS NOT NULL
      AND r.review_score IS NOT NULL
    """
    df = read_sql(query)

    # split the review scores into two groups
    late = df.loc[df['delivery_status'] == 'Late', 'review_score']
    on_time = df.loc[df['delivery_status'] == 'On time', 'review_score']

    # two-sided test: "are the two groups different?" (no normality assumption)
    u_statistic, p_value = stats.mannwhitneyu(late, on_time, alternative='two-sided')

    # effect size: rank-biserial correlation (0.1 small, 0.3 medium, 0.5+ large)
    # positive here = late reviews tend to be lower
    effect = 1 - (2 * u_statistic) / (len(late) * len(on_time))
    size = "large" if abs(effect) >= 0.5 else "medium" if abs(effect) >= 0.3 else "small"

    return {
        "analysis": "Mann-Whitney U: review score, late vs on-time delivery",
        "n": int(len(late) + len(on_time)),
        "statistic": float(u_statistic),
        "p_value": float(p_value),
        "effect_size": round(float(effect), 3),
        "conclusion": (f"Late (n={len(late):,}) median {late.median():.0f}, mean {late.mean():.2f} vs "
                       f"on time (n={len(on_time):,}) median {on_time.median():.0f}, mean {on_time.mean():.2f}; "
                       f"{size} effect"),
    }
