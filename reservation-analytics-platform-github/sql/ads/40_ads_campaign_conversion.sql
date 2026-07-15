CREATE OR REPLACE TEMP VIEW ads_campaign_conversion AS
SELECT
    campaign_id,
    site,
    channel,
    COUNT(DISTINCT mid) AS reserved_users,
    COUNT(DISTINCT CASE WHEN order_flag = 1 THEN mid END) AS paid_users,
    COUNT(DISTINCT CASE WHEN tag_reserved_not_paid = 1 THEN mid END) AS unconverted_users,
    ROUND(
        COUNT(DISTINCT CASE WHEN order_flag = 1 THEN mid END) * 1.0
        / NULLIF(COUNT(DISTINCT mid), 0),
        4
    ) AS conversion_rate
FROM fact_reservation_conversion
GROUP BY campaign_id, site, channel;
