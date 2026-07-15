CREATE OR REPLACE TEMP VIEW dwd_reservation AS
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
            ORDER BY reserve_time
        ) AS rn
    FROM ods_reservation_event
)
WHERE rn = 1;
