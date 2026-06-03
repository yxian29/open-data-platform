SELECT
    id,
    customer_id,
    product_id,
    quantity,
    total_amount,
    status,
    order_date
FROM {{ source('raw', 'analytics_orders') }}
WHERE status != ''
