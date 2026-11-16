from audit.db import read_sql
import numpy as np
EXCEPTION_COLUMNS = ['test_id','test_name','entity_type','entity_id','amount','risk_level','detail']


""" The pattern for every test is the same:
    1. SQL in read_sql(...)
    2. filter in pandas
    3. add the 7 standard columns
    4. return df[EXCEPTION_COLUMNS]
"""     
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
    
    
def t02_duplicate_payments():
    # control: each payment should be recorded once
    # risk: double charging, or a payment counted twice
    # rule: same order_id with the same payment_value appearing more than once
    query = """
    SELECT order_id,
           payment_value,
           COUNT(*) AS count,
           GROUP_CONCAT(DISTINCT payment_type) AS payment_types
    FROM order_payments
    GROUP BY order_id, payment_value
    HAVING COUNT(*) > 1
    """
    pd_df = read_sql(query)
    pd_df['test_id'] = 'T02'
    pd_df['test_name'] = 'Duplicate payments'
    pd_df['entity_type'] = 'order'
    pd_df['entity_id'] = pd_df['order_id']
    pd_df['amount'] = (pd_df['count'] - 1) * pd_df['payment_value']  # the duplicated money
    # risk-based rule: a repeated card charge is serious, several identical vouchers usually are not
    pd_df['risk_level'] = np.select(
        [pd_df['payment_types'].str.contains('credit_card|debit_card'),
         pd_df['payment_types'] == 'voucher'],
        ['High', 'Low'],
        default='Medium',
    )
    pd_df['detail'] = pd_df.apply(
        lambda x: f"{x['count']} identical payments of {x['payment_value']:.2f} BRL ({x['payment_types']})",
        axis=1,
    )
    return pd_df[EXCEPTION_COLUMNS]


def t03_excessive_vouchers():
    # control: limits on promotional vouchers
    # risk: voucher abuse or unauthorised discounts
    # rule: orders paid with 3 or more voucher payments
    query = """
    SELECT order_id,
           COUNT(*) AS voucher_count,
           SUM(payment_value) AS voucher_value
    FROM order_payments
    WHERE payment_type = 'voucher'
    GROUP BY order_id
    HAVING COUNT(*) >= 3
    """
    pd_df = read_sql(query)
    pd_df['test_id'] = 'T03'
    pd_df['test_name'] = 'Excessive vouchers'
    pd_df['entity_type'] = 'order'
    pd_df['entity_id'] = pd_df['order_id']
    pd_df['amount'] = pd_df['voucher_value']  # money paid with vouchers
    pd_df['risk_level'] = np.where(pd_df['voucher_count'] >= 5, 'High', 'Medium')  # risk = number of vouchers
    pd_df['detail'] = pd_df.apply(
        lambda x: f"{x['voucher_count']} vouchers used, total {x['voucher_value']:.2f} BRL",
        axis=1,
    )
    return pd_df[EXCEPTION_COLUMNS]


def t04_abnormal_freight():
    # control: shipping charges should be reasonable compared with the item
    # risk: overcharging, or value hidden in freight
    # rule: freight > 3 x item price. Threshold chosen from the distribution:
    #       >1x = 4,124 lines, >2x = 531, >3x = 146, >5x = 41 -> 3x keeps the list reviewable
    query = """
    SELECT order_id, order_item_id, price, freight_value
    FROM order_items
    WHERE freight_value > 3 * price
    """
    pd_df = read_sql(query)
    pd_df['test_id'] = 'T04'
    pd_df['test_name'] = 'Abnormal freight'
    pd_df['entity_type'] = 'order item'
    # order_item_id is a number: convert it to text before joining the strings
    pd_df['entity_id'] = pd_df['order_id'] + '-' + pd_df['order_item_id'].astype(str)
    pd_df['amount'] = pd_df['freight_value'] - pd_df['price']  # freight above the item price
    pd_df['risk_level'] = np.where(pd_df['freight_value'] > 5 * pd_df['price'], 'High', 'Medium')
    pd_df['detail'] = pd_df.apply(
        lambda x: f"Freight {x['freight_value']:.2f} BRL is {x['freight_value'] / x['price']:.1f}x "
                  f"the item price {x['price']:.2f} BRL",
        axis=1,
    )
    return pd_df[EXCEPTION_COLUMNS]


def t05_process_sequence_violation():
    # control: an order follows purchase -> approval -> shipping -> delivery
    # risk: a step skipped or backdated (control bypass), or bad data
    # dates are text 'YYYY-MM-DD HH:MM:SS', which sorts correctly, so < works on text
    query = """
    WITH paid AS (
        SELECT order_id, SUM(payment_value) AS order_value
        FROM order_payments
        GROUP BY order_id
    )
    SELECT o.order_id,
           COALESCE(p.order_value, 0) AS order_value,
           CASE
               WHEN o.order_delivered_customer_date < o.order_delivered_carrier_date THEN 'Delivered before shipped'
               ELSE 'Shipped before payment approval'
           END AS violation
    FROM orders o
    LEFT JOIN paid p USING (order_id)
    WHERE o.order_delivered_carrier_date < o.order_approved_at
       OR o.order_delivered_customer_date < o.order_delivered_carrier_date
    """
    pd_df = read_sql(query)
    pd_df['test_id'] = 'T05'
    pd_df['test_name'] = 'Process sequence violation'
    pd_df['entity_type'] = 'order'
    pd_df['entity_id'] = pd_df['order_id']
    pd_df['amount'] = pd_df['order_value']  # value of the order affected
    # delivered before shipped is physically impossible -> data integrity issue -> High
    pd_df['risk_level'] = np.where(pd_df['violation'] == 'Delivered before shipped', 'High', 'Medium')
    pd_df['detail'] = pd_df['violation']
    return pd_df[EXCEPTION_COLUMNS]


def t06_missing_approval():
    # control: a delivered order must have an approval date and a carrier date
    # risk: delivery without approval, incomplete audit trail
    query = """
    WITH paid AS (
        SELECT order_id, SUM(payment_value) AS order_value
        FROM order_payments
        GROUP BY order_id
    )
    SELECT o.order_id,
           COALESCE(p.order_value, 0) AS order_value,
           o.order_approved_at,
           o.order_delivered_carrier_date
    FROM orders o
    LEFT JOIN paid p USING (order_id)
    WHERE o.order_status = 'delivered'
      AND (o.order_approved_at IS NULL OR o.order_delivered_carrier_date IS NULL)
    """
    pd_df = read_sql(query)
    pd_df['test_id'] = 'T06'
    pd_df['test_name'] = 'Missing approval or carrier date'
    pd_df['entity_type'] = 'order'
    pd_df['entity_id'] = pd_df['order_id']
    pd_df['amount'] = pd_df['order_value']
    pd_df['risk_level'] = 'High'  # few cases, and a missing approval is serious
    pd_df['detail'] = np.where(pd_df['order_approved_at'].isna(),
                               'Delivered without payment approval date',
                               'Delivered without carrier hand-over date')
    return pd_df[EXCEPTION_COLUMNS]


# Registry of all tests. population_sql = how many items each test checked
# (auditors always ask "out of how many?").
TESTS = [
    {"test_id": "T01", "function": t01_payment_reconciliation,
     "population_sql": """SELECT COUNT(*) AS n
                          FROM (SELECT DISTINCT order_id FROM order_payments)
                          JOIN (SELECT DISTINCT order_id FROM order_items) USING (order_id)"""},
    {"test_id": "T02", "function": t02_duplicate_payments,
     "population_sql": "SELECT COUNT(DISTINCT order_id) AS n FROM order_payments"},
    {"test_id": "T03", "function": t03_excessive_vouchers,
     "population_sql": "SELECT COUNT(DISTINCT order_id) AS n FROM order_payments WHERE payment_type = 'voucher'"},
    {"test_id": "T04", "function": t04_abnormal_freight,
     "population_sql": "SELECT COUNT(*) AS n FROM order_items"},
    {"test_id": "T05", "function": t05_process_sequence_violation,
     "population_sql": "SELECT COUNT(*) AS n FROM orders"},
    {"test_id": "T06", "function": t06_missing_approval,
     "population_sql": "SELECT COUNT(*) AS n FROM orders WHERE order_status = 'delivered'"},
]


