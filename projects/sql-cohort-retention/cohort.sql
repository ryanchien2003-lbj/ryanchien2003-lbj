-- A customer joins a cohort in their first completed purchase month.
-- Activity is any completed purchase in a calendar month.
-- Populate calendar cells up to the observation month. Future cells stay absent.
WITH RECURSIVE
qualifying AS (
    SELECT customer_id, date(order_date, 'start of month') AS activity_month
    FROM orders
    WHERE status = 'completed' AND amount > 0
),
first_purchase AS (
    SELECT customer_id, MIN(activity_month) AS cohort_month
    FROM qualifying
    GROUP BY customer_id
),
sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM first_purchase
    GROUP BY cohort_month
),
active AS (
    SELECT DISTINCT f.cohort_month, q.activity_month, q.customer_id
    FROM first_purchase f
    JOIN qualifying q ON q.customer_id = f.customer_id
),
ages(month_index) AS (
    SELECT 0
    UNION ALL
    SELECT month_index + 1 FROM ages
    WHERE month_index < (
        SELECT MAX((CAST(strftime('%Y', :observation_month) AS INTEGER) -
                    CAST(strftime('%Y', cohort_month) AS INTEGER)) * 12 +
                    CAST(strftime('%m', :observation_month) AS INTEGER) -
                    CAST(strftime('%m', cohort_month) AS INTEGER))
        FROM sizes
    )
)
SELECT
    s.cohort_month,
    ages.month_index,
    s.cohort_size,
    COUNT(DISTINCT a.customer_id) AS active_customers,
    1.0 * COUNT(DISTINCT a.customer_id) / s.cohort_size AS retention
FROM sizes s
CROSS JOIN ages
LEFT JOIN active a
    ON a.cohort_month = s.cohort_month
    AND a.activity_month = date(s.cohort_month, '+' || ages.month_index || ' months')
WHERE date(s.cohort_month, '+' || ages.month_index || ' months') <= :observation_month
GROUP BY s.cohort_month, ages.month_index, s.cohort_size
ORDER BY s.cohort_month, ages.month_index;
