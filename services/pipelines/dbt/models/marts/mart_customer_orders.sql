SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    c.email,
    c.country,
    count(o.id) AS total_orders,
    sum(o.total_amount) AS total_revenue,
    max(o.order_date) AS last_order_date
FROM {{ ref('stg_customers') }} c
LEFT JOIN {{ ref('stg_orders') }} o ON c.id = o.customer_id
GROUP BY c.id, c.name, c.email, c.country
