CREATE OR REPLACE TEMP VIEW dwd_paid_order AS
SELECT
    order_id,
    mid,
    product_id,
    site,
    order_time
FROM ods_order
WHERE order_status = 'PAID';
