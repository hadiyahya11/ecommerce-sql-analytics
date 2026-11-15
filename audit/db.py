import os
import sqlite3
from contextlib import closing

import pandas as pd

# Absolute path to olist.db (one folder above this file), so the code works
# no matter which folder you run it from.
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "olist.db")


def get_connection():
    """Open a new connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def read_sql(query):
    """Run a SQL query and return the result as a pandas DataFrame."""
    # closing(...) makes sure the connection is closed when the block ends.
    # (A plain "with sqlite3 connection" only commits; it does NOT close it.)
    with closing(get_connection()) as connection:
        return pd.read_sql_query(query, connection)
