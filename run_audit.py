from contextlib import closing

from audit.db import get_connection
from audit.tests import t01_payment_reconciliation

if __name__ == "__main__":
    df = t01_payment_reconciliation()
    print(f"T01: Found {len(df)} exceptions")
    # closing(...) closes the connection at the end of the block;
    # "with connection" saves (commits) the new table.
    with closing(get_connection()) as connection, connection:
        df.to_sql("audit_exceptions", connection, if_exists="replace", index=False)
