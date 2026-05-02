-- Business question: Which products drive the most revenue (Pareto classification)?
-- Approach: Compute cumulative revenue share using window functions, then assign A/B/C tiers.
-- A = top 80% of revenue, B = next 15%, C = remaining 5%.
-- Parameters: $1 = start_date, $2 = end_date, $3 = seller_state ('' means no filter)

WITH date_filtered_orders AS (
    SELECT order_id
    FROM orders
    WHERE order_status = 'delivered'
      AND ($1 = '' OR order_purchase_timestamp >= $1::TIMESTAMP)
      AND ($2 = '' OR order_purchase_timestamp <= $2::TIMESTAMP)
),
product_revenue AS (
    SELECT
        oi.product_id,
        SUM(oi.price) AS revenue,
        COUNT(*)      AS units_sold
    FROM order_items oi
    JOIN date_filtered_orders o ON oi.order_id = o.order_id
    LEFT JOIN order_items oi2 ON oi.order_id = oi2.order_id
    LEFT JOIN sellers s ON oi.seller_id = s.seller_id
    WHERE ($3 = '' OR s.seller_state = $3)
    GROUP BY oi.product_id
),
total AS (
    SELECT SUM(revenue) AS grand_total FROM product_revenue
),
ranked AS (
    SELECT
        pr.product_id,
        COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
        pr.revenue,
        pr.units_sold,
        pr.revenue / t.grand_total                                          AS revenue_share,
        SUM(pr.revenue) OVER (ORDER BY pr.revenue DESC) / t.grand_total     AS cumulative_share
    FROM product_revenue pr
    JOIN total t ON TRUE
    LEFT JOIN products p ON pr.product_id = p.product_id
    LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
)
SELECT
    product_id,
    category,
    ROUND(revenue, 2)                    AS revenue,
    units_sold,
    ROUND(revenue_share * 100, 4)        AS revenue_share_pct,
    ROUND(cumulative_share * 100, 2)     AS cumulative_share_pct,
    CASE
        WHEN cumulative_share <= 0.80 THEN 'A'
        WHEN cumulative_share <= 0.95 THEN 'B'
        ELSE 'C'
    END AS abc_class
FROM ranked
ORDER BY revenue DESC
