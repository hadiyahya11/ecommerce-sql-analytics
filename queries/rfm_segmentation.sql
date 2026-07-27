WITH raw_metrics(customer_unique_id,frequency,recency,monetary) AS (
    SELECT  c.customer_unique_id,COUNT(DISTINCT o.order_id),MAX(o.order_purchase_timestamp),SUM(p.payment_value)
    FROM orders o
    JOIN order_payments p
    ON o.order_id = p.order_id
    JOIN customers c
    ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
    ),
anchor_date(last_date) AS (
    SELECT MAX(o.order_purchase_timestamp)
    FROM orders o
    
),
customer_metrics (customer_unique_id,frequency,monetary,recency_days) AS (  
SELECT r.customer_unique_id,r.frequency,r.monetary, CAST(julianday(d.last_date) - julianday(r.recency) AS INTEGER) AS recency_days
FROM raw_metrics r, anchor_date d
),

customer_scores (customer_unique_id,frequency,monetary,recency_days,f_score,m_score,r_score) AS (
    SELECT *,
    NTILE(5) OVER (ORDER BY frequency ASC) f_score,
    NTILE(5) OVER (ORDER BY monetary ASC) m_score,
    NTILE(5) OVER (ORDER BY recency_days DESC) r_score
    FROM customer_metrics
),
customers_labels(unique_id,label) AS (
SELECT customer_unique_id, 
CASE
    WHEN s.f_score>=4 AND s.m_score>=4 AND s.r_score>=4 THEN 'Champion'
    WHEN s.f_score>=4 AND s.m_score>=3 AND s.r_score>=3 THEN 'Loyal'
    WHEN s.f_score<=2  AND s.r_score>=4 THEN 'Recent customer'
    WHEN s.f_score>=3 AND s.m_score>=3 AND s.r_score<=2 THEN 'At risk'
    WHEN s.f_score<=2 AND s.m_score<=2 AND s.r_score<=2 THEN 'Lost'
    ELSE 'Other'
    END as customer_label
FROM customer_scores s
)

SELECT label, COUNT(label) as total_customers
FROM customers_labels
GROUP BY label
