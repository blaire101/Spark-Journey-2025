CREATE OR REPLACE TEMP VIEW dm_user_campaign_profile AS
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    channel,
    reserve_time,
    order_flag,
    tag_reserved_not_paid,
    CASE
        WHEN order_flag = 1 THEN 'CONVERTED'
        ELSE 'RESERVED_NOT_PAID'
    END AS conversion_segment
FROM fact_reservation_conversion;
