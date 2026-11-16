from contextlib import closing

import pandas as pd

from audit.db import get_connection, read_sql
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

    # closing(...) closes the connection at the end of the block;
    # "with connection" saves (commits) the new tables.
    with closing(get_connection()) as connection, connection:
        exceptions.to_sql("audit_exceptions", connection, if_exists="replace", index=False)
        summary.to_sql("audit_test_summary", connection, if_exists="replace", index=False)

    print()
    print(summary.to_string(index=False))
