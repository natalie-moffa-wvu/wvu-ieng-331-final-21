-- Business question: What percentage of customers return within 30, 60, and 90 days of their first purchase?
-- Approach: Assign customers to cohorts by first-purchase month, then calculate repeat purchase rates.
-- Parameters: $1 = start_date, $2 = end_date, $3 = seller_state ('' means no filter)

WITH date_filtered_orders AS (
    SELECT o.order_id, o.customer_id, o.order_purchase_timestamp
    FROM orders o
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
      AND ($1 = '' OR o.order_purchase_timestamp >= $1::TIMESTAMP)
      AND ($2 = '' OR o.order_purchase_timestamp <= $2::TIMESTAMP)
),
seller_filter AS (
    SELECT DISTINCT oi.order_id
    FROM order_items oi
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE ($3 = '' OR s.seller_state = $3)
),
filtered_orders AS (
    SELECT dfo.*
    FROM date_filtered_orders dfo
    WHERE ($3 = '' OR dfo.order_id IN (SELECT order_id FROM seller_filter))
),
customer_first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(o.order_purchase_timestamp)                             AS first_purchase_ts,
        DATE_TRUNC('month', MIN(o.order_purchase_timestamp))        AS cohort_month
    FROM filtered_orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
),
all_purchases AS (
    SELECT
        c.customer_unique_id,
        o.order_purchase_timestamp
    FROM filtered_orders o
    JOIN customers c ON o.customer_id = c.customer_id
),
cohort_activity AS (
    SELECT
        fp.cohort_month,
        fp.customer_unique_id,
        MIN(ap.order_purchase_timestamp) FILTER (
            WHERE ap.order_purchase_timestamp > fp.first_purchase_ts
        ) AS second_purchase_ts
    FROM customer_first_purchase fp
    LEFT JOIN all_purchases ap ON fp.customer_unique_id = ap.customer_unique_id
    GROUP BY fp.cohort_month, fp.customer_unique_id, fp.first_purchase_ts
)
SELECT
    cohort_month,
    COUNT(*)                                                                        AS cohort_size,
    SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 30 DAY
             THEN 1 ELSE 0 END)                                                     AS returned_30d,
    SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 60 DAY
             THEN 1 ELSE 0 END)                                                     AS returned_60d,
    SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 90 DAY
             THEN 1 ELSE 0 END)                                                     AS returned_90d,
    ROUND(SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 30 DAY
                   THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100, 2)                  AS retention_30d_pct,
    ROUND(SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 60 DAY
                   THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100, 2)                  AS retention_60d_pct,
    ROUND(SUM(CASE WHEN second_purchase_ts <= first_purchase_ts + INTERVAL 90 DAY
                   THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100, 2)                  AS retention_90d_pct
FROM cohort_activity
JOIN customer_first_purchase USING (cohort_month, customer_unique_id)
GROUP BY cohort_month
ORDER BY cohort_month
