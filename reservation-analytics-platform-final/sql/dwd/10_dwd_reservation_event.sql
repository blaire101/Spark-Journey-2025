CREATE OR REPLACE TEMP VIEW dwd_reservation_event AS
SELECT
    reservation_id,
    mid,
    campaign_id,
    product_id,
    site,
    reserve_time,
    channel
FROM ods_reservation_event;
