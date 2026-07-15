CREATE OR REPLACE TEMP VIEW crm_reserved_not_paid AS
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    channel,
    reserve_time
FROM fact_reservation_conversion
WHERE tag_reserved_not_paid = 1;
