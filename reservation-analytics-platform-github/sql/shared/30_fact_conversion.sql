CREATE OR REPLACE TEMP VIEW fact_reservation_conversion AS
WITH matched AS (
    SELECT
        r.reservation_id,
        r.mid,
        r.campaign_id,
        r.product_id,
        r.site,
        r.reserve_time,
        r.channel,
        o.order_id,
        o.order_time,
        ROW_NUMBER() OVER (
            PARTITION BY r.reservation_id
            ORDER BY o.order_time
        ) AS order_rank
    FROM dwd_reservation r
    JOIN dim_campaign c
      ON r.campaign_id = c.campaign_id
     AND r.product_id = c.product_id
     AND r.site = c.site
    LEFT JOIN dwd_paid_order o
      ON r.mid = o.mid
     AND r.product_id = o.product_id
     AND r.site = o.site
     AND o.order_time BETWEEN c.launch_start AND c.launch_end
)
SELECT
    reservation_id,
    mid,
    campaign_id,
    product_id,
    site,
    reserve_time,
    channel,
    1 AS reserve_flag,
    CASE WHEN order_id IS NOT NULL THEN 1 ELSE 0 END AS order_flag,
    CASE WHEN order_id IS NULL THEN 1 ELSE 0 END AS tag_reserved_not_paid,
    order_id,
    order_time
FROM matched
WHERE order_rank = 1;
