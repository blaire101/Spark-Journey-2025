CREATE OR REPLACE TEMP VIEW dm_reservation_conversion AS
WITH deduplicated_reservation AS (
    SELECT
        reservation_id,
        mid,
        campaign_id,
        product_id,
        site,
        reserve_time,
        channel
    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY mid, campaign_id, product_id, site
                ORDER BY reserve_time, reservation_id
            ) AS reservation_rank
        FROM dwd_reservation_event
    ) ranked
    WHERE reservation_rank = 1
),
matched AS (
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
            ORDER BY o.order_time, o.order_id
        ) AS order_rank
    FROM deduplicated_reservation r
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
    CASE
        WHEN order_id IS NOT NULL THEN 'CONVERTED'
        ELSE 'RESERVED_NOT_PAID'
    END AS conversion_segment,
    order_id,
    order_time
FROM matched
WHERE order_rank = 1;
