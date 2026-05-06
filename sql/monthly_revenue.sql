-- Business question: How has monthly revenue trended over the dataset's time range?
-- Approach: Aggregate delivered order revenue by month, compute MoM growth rate.
-- Parameters: $1 = start_date, $2 = end_date, $3 = seller_state ('' means no filter)

WITH date_filtered_orders AS (
    SELECT o.order_id, o.order_purchase_timestamp
    FROM orders o
    WHERE o.order_status = 'delivered'
      AND ($1 = '' OR o.order_purchase_timestamp >= $1::TIMESTAMP)
      AND ($2 = '' OR o.order_purchase_timestamp <= $2::TIMESTAMP)
),
seller_filter AS (
    SELECT DISTINCT oi.order_id
    FROM order_items oi
    JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE ($3 = '' OR s.seller_state = $3)
),
monthly AS (
    SELECT
        DATE_TRUNC('month', o.order_purchase_timestamp) AS month,
        SUM(oi.price + oi.freight_value)                AS revenue,
        COUNT(DISTINCT o.order_id)                      AS order_count,
        COUNT(DISTINCT oi.seller_id)                    AS active_sellers
    FROM date_filtered_orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE ($3 = '' OR o.order_id IN (SELECT order_id FROM seller_filter))
    GROUP BY DATE_TRUNC('month', o.order_purchase_timestamp)
)
SELECT
    month,
    ROUND(revenue, 2)       AS revenue,
    order_count,
    active_sellers,
    ROUND(
        (revenue - LAG(revenue) OVER (ORDER BY month))
        / NULLIF(LAG(revenue) OVER (ORDER BY month), 0) * 100
    , 1)                    AS mom_growth_pct
FROM monthly
ORDER BY month
