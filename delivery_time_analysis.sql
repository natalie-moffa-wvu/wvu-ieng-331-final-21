-- Business question: Which geographic corridors consistently over- or under-deliver vs. estimate?
-- Approach: Join orders with customer geolocation, compute actual vs. estimated delta, aggregate by state.
-- Parameters: $1 = start_date, $2 = end_date, $3 = seller_state ('' means no filter)

WITH date_filtered_orders AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_purchase_timestamp,
        o.order_delivered_customer_date,
        o.order_estimated_delivery_date,
        DATEDIFF('day', o.order_purchase_timestamp, o.order_delivered_customer_date)   AS actual_days,
        DATEDIFF('day', o.order_purchase_timestamp, o.order_estimated_delivery_date)   AS estimated_days,
        DATEDIFF('day', o.order_delivered_customer_date, o.order_estimated_delivery_date) AS days_early
    FROM orders o
    WHERE o.order_status = 'delivered'
      AND o.order_delivered_customer_date IS NOT NULL
      AND o.order_estimated_delivery_date IS NOT NULL
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
geo_orders AS (
    SELECT
        fo.*,
        c.customer_state
    FROM filtered_orders fo
    JOIN customers c ON fo.customer_id = c.customer_id
)
SELECT
    customer_state                                      AS state,
    COUNT(*)                                            AS order_count,
    ROUND(AVG(actual_days), 1)                          AS avg_actual_days,
    ROUND(AVG(estimated_days), 1)                       AS avg_estimated_days,
    ROUND(AVG(days_early), 1)                           AS avg_days_early,
    ROUND(STDDEV(actual_days), 1)                       AS stddev_actual_days,
    SUM(CASE WHEN days_early >= 0 THEN 1 ELSE 0 END)::FLOAT / COUNT(*) * 100
                                                        AS on_time_pct,
    MIN(actual_days)                                    AS min_actual_days,
    MAX(actual_days)                                    AS max_actual_days
FROM geo_orders
GROUP BY customer_state
HAVING COUNT(*) >= 10
ORDER BY avg_days_early DESC
