from audit.db import read_sql
import numpy as np
EXCEPTION_COLUMNS = ['test_id','test_name','entity_type','entity_id','amount','risk_level','detail']

def t01_payment_reconciliation():
    #1 SQL: paid vs invoiced per order
    #2 pandas: difference, keep rows above tolerance
   
    
    query = """
    WITH paid AS (
        SELECT order_id, SUM(payment_value) AS paid
        FROM order_payments
        GROUP BY order_id
    ),
    invoiced AS ( 
    SELECT order_id, SUM(price+freight_value) AS invoiced
    FROM order_items
    GROUP BY order_id
    )
    SELECT order_id, paid, invoiced
    FROM paid
    JOIN invoiced USING (order_id)"""
    
    pd_df = read_sql(query)
    pd_df['difference'] = pd_df['paid'] - pd_df['invoiced']
    pd_df = pd_df[pd_df['difference'].abs() > 1].copy()  # tolerance: ignore rounding gaps up to 1 BRL
    pd_df['test_id'] = 'T01'
    pd_df['test_name'] = 'Payment reconciliation'
    pd_df['entity_type'] = 'order'
    pd_df['entity_id'] = pd_df['order_id']
    pd_df['amount'] = pd_df['difference'].abs()
    pd_df['risk_level'] = np.where(pd_df['amount'] > 50, 'High', 'Medium')  # risk = size of the gap
    pd_df['detail'] = pd_df.apply(
        lambda x: f"{'Overpaid' if x['difference'] > 0 else 'Underpaid'} by {x['amount']:.2f} BRL "
                  f"(paid {x['paid']:.2f}, invoiced {x['invoiced']:.2f})",
        axis=1,
    )
    pd_df = pd_df[EXCEPTION_COLUMNS]
    return pd_df
    