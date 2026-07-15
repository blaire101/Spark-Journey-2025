CREATE OR REPLACE TEMP VIEW ads_crm_reserved_not_paid AS
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    channel,
    reserve_time
FROM dm_reservation_conversion
WHERE tag_reserved_not_paid = 1;
