from contextlib import closing

import pandas as pd

from audit.db import get_connection, read_sql
from audit.report import write_excel_report
from audit.seller_risk import build_seller_features, score_sellers
from audit.statistics import benford_analysis, late_delivery_review_test
from audit.tests import TESTS

if __name__ == "__main__":
    all_exceptions = []
    summary_rows = []

    for test in TESTS:
        df = test["function"]()                              # run the test
        population = read_sql(test["population_sql"])["n"][0]  # how many items were checked
        print(f"{test['test_id']}: Found {len(df)} exceptions out of {population:,}")

        all_exceptions.append(df)
        summary_rows.append({
            "test_id": test["test_id"],
            "test_name": df["test_name"].iloc[0] if len(df) else "",
            "exceptions": len(df),
            "high_risk": int((df["risk_level"] == "High").sum()),
            "amount_at_risk": round(df["amount"].sum(), 2),
            "population": population,
            "exception_rate": round(len(df) / population, 4),
        })

    exceptions = pd.concat(all_exceptions, ignore_index=True)  # one table for all tests
    summary = pd.DataFrame(summary_rows)

    # statistical analyses (M3)
    benford_results, benford_summary = benford_analysis()
    review_test = late_delivery_review_test()
    statistical_tests = pd.DataFrame([benford_summary, review_test])
    def p_text(p):
        return "p<0.001" if p < 0.001 else f"p={p:.3f}"

    print(f"\nBenford: {benford_summary['conclusion']}, chi2 {benford_summary['statistic']:,.0f}, "
          f"{p_text(benford_summary['p_value'])}")
    print(f"Mann-Whitney: effect size {review_test['effect_size']}, {p_text(review_test['p_value'])}")

    # ML seller risk scoring (M4): uses this run's exceptions as one of the features
    seller_risk = score_sellers(build_seller_features(exceptions))
    print(f"\nSeller risk: {len(seller_risk)} sellers scored, "
          f"{seller_risk['is_outlier'].sum()} flagged as outliers. Top 10:")
    print(seller_risk.head(10)[['risk_rank', 'seller_id', 'seller_state', 'n_orders',
                                 'risk_score', 'top_reasons']].to_string(index=False))

    # closing(...) closes the connection at the end of the block;
    # "with connection" saves (commits) the new tables.
    with closing(get_connection()) as connection, connection:
        exceptions.to_sql("audit_exceptions", connection, if_exists="replace", index=False)
        summary.to_sql("audit_test_summary", connection, if_exists="replace", index=False)
        benford_results.to_sql("benford_results", connection, if_exists="replace", index=False)
        statistical_tests.to_sql("statistical_tests", connection, if_exists="replace", index=False)
        seller_risk.to_sql("seller_risk", connection, if_exists="replace", index=False)

    print()
    print(summary.to_string(index=False))

    # automated Excel report for auditors (M5)
    report_path = write_excel_report(summary, exceptions, seller_risk, benford_results, statistical_tests)
    print(f"\nExcel report: {report_path}")
