DROP TABLE IF EXISTS ods_reservation_event;
DROP TABLE IF EXISTS ods_order;
DROP TABLE IF EXISTS dim_campaign;

CREATE TABLE ods_reservation_event (
    reservation_id VARCHAR,
    mid VARCHAR,
    campaign_id VARCHAR,
    product_id VARCHAR,
    site VARCHAR,
    reserve_time TIMESTAMP,
    channel VARCHAR
);

INSERT INTO ods_reservation_event VALUES
('R001','U001','CAMP100','SKU-PHONE-15','SG','2026-06-28 10:00:00','Google'),
('R002','U001','CAMP100','SKU-PHONE-15','SG','2026-06-28 10:05:00','Google'),
('R003','U002','CAMP100','SKU-PHONE-15','SG','2026-06-29 11:30:00','Facebook'),
('R004','U003','CAMP100','SKU-PHONE-15','SG','2026-06-30 09:00:00','Direct');

CREATE TABLE ods_order (
    order_id VARCHAR,
    mid VARCHAR,
    product_id VARCHAR,
    site VARCHAR,
    order_time TIMESTAMP,
    order_status VARCHAR
);

INSERT INTO ods_order VALUES
('O001','U001','SKU-PHONE-15','SG','2026-07-02 12:00:00','PAID'),
('O002','U002','SKU-PHONE-15','SG','2026-07-08 09:00:00','PAID'),
('O003','U003','SKU-PHONE-15','SG','2026-07-06 18:00:00','CANCELLED');

CREATE TABLE dim_campaign (
    campaign_id VARCHAR,
    product_id VARCHAR,
    site VARCHAR,
    launch_start TIMESTAMP,
    launch_end TIMESTAMP
);

INSERT INTO dim_campaign VALUES
('CAMP100','SKU-PHONE-15','SG','2026-07-01 00:00:00','2026-07-07 23:59:59');
