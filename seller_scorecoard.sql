-- Business question: Which sellers are performing best across revenue, delivery, and customer satisfaction?
-- Approach: Build a composite scorecard joining orders, items, reviews, and sellers.
-- Each CTE isolates one metric dimension before combining into a final ranked score.
-- Parameters: $1 = start_date, $2 = end_date, $3 = seller_state ('' means no filter)

WITH date_filtered_orders AS (
    SELECT order_id, order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date
    FROM orders
    WHERE order_status = 'delivered'
      AND ($1 = '' OR order_purchase_timestamp >= $1::TIMESTAMP)
      AND ($2 = '' OR order_purchase_timestamp <= $2::TIMESTAMP)
),
seller_revenue AS (
    SELECT
        oi.seller_id,
        SUM(oi.price + oi.freight_value) AS total_revenue,
        COUNT(DISTINCT oi.order_id)      AS total_orders
    FROM order_items oi
    JOIN date_filtered_orders o ON oi.order_id = o.order_id
    GROUP BY oi.seller_id
),
seller_delivery AS (
    SELECT
        oi.seller_id,
        AVG(
            CASE
                WHEN o.order_delivered_customer_date IS NOT NULL
                     AND o.order_estimated_delivery_date IS NOT NULL
                THEN DATEDIFF('day', o.order_delivered_customer_date, o.order_estimated_delivery_date)
                ELSE NULL
            END
        ) AS avg_days_early,
        SUM(CASE WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 1 ELSE 0 END)::FLOAT
            / COUNT(*) AS on_time_rate
    FROM order_items oi
    JOIN date_filtered_orders o ON oi.order_id = o.order_id
    GROUP BY oi.seller_id
),
seller_reviews AS (
    SELECT
        oi.seller_id,
        AVG(r.review_score) AS avg_review_score
    FROM order_items oi
    JOIN date_filtered_orders o ON oi.order_id = o.order_id
    JOIN order_reviews r ON r.order_id = o.order_id
    GROUP BY oi.seller_id
),
combined AS (
    SELECT
        s.seller_id,
        s.seller_state,
        s.seller_city,
        COALESCE(sr.total_revenue, 0)     AS total_revenue,
        COALESCE(sr.total_orders, 0)      AS total_orders,
        COALESCE(sd.on_time_rate, 0)      AS on_time_rate,
        COALESCE(sd.avg_days_early, 0)    AS avg_days_early,
        COALESCE(rv.avg_review_score, 0)  AS avg_review_score
    FROM sellers s
    LEFT JOIN seller_revenue sr  ON s.seller_id = sr.seller_id
    LEFT JOIN seller_delivery sd ON s.seller_id = sd.seller_id
    LEFT JOIN seller_reviews  rv ON s.seller_id = rv.seller_id
    WHERE ($3 = '' OR s.seller_state = $3)
      AND COALESCE(sr.total_orders, 0) > 0
)
SELECT
    seller_id,
    seller_state,
    seller_city,
    total_revenue,
    total_orders,
    ROUND(on_time_rate * 100, 1)          AS on_time_pct,
    ROUND(avg_days_early, 1)              AS avg_days_early,
    ROUND(avg_review_score, 2)            AS avg_review_score,
    ROUND(
        (PERCENT_RANK() OVER (ORDER BY total_revenue)     * 0.40 +
         PERCENT_RANK() OVER (ORDER BY on_time_rate)      * 0.30 +
         PERCENT_RANK() OVER (ORDER BY avg_review_score)  * 0.30) * 100
    , 1) AS composite_score
FROM combined
ORDER BY composite_score DESC
