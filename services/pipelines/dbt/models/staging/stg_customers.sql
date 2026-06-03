SELECT
    id,
    name,
    email,
    country,
    created_at
FROM {{ source('raw', 'analytics_customers') }}
WHERE name != ''
