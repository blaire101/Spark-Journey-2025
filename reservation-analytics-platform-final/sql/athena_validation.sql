-- DM: user-level reservation conversion
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    order_flag,
    tag_reserved_not_paid,
    conversion_segment,
    order_id
FROM reservation_curated.dm_reservation_conversion
ORDER BY mid;

-- ADS: campaign/channel metrics
SELECT
    campaign_id,
    site,
    channel,
    reserved_users,
    paid_users,
    unconverted_users,
    conversion_rate
FROM reservation_curated.ads_campaign_conversion
ORDER BY channel;

-- ADS: CRM audience
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    channel
FROM reservation_curated.ads_crm_reserved_not_paid
ORDER BY mid;
