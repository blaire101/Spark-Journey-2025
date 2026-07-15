-- Query 1: user-level result
SELECT
    mid,
    order_flag,
    tag_reserved_not_paid,
    order_id
FROM reservation_curated.fact_reservation_conversion
ORDER BY mid;

-- Query 2: campaign/channel metrics
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

-- Query 3: CRM audience
SELECT
    mid,
    campaign_id,
    product_id,
    site,
    channel
FROM reservation_curated.crm_reserved_not_paid
ORDER BY mid;
