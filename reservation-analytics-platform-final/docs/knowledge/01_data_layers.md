# Data Layers

This project uses:

```text
ODS → DWD + DIM → DM → ADS
```

There is **no separate FACT layer**.

| Layer | Responsibility | Example |
|---|---|---|
| ODS | Source-aligned landing tables | `ods_reservation_event`, `ods_order` |
| DWD | Clean atomic fact detail, close to source grain | `dwd_reservation_event`, `dwd_paid_order` |
| DIM | Reusable descriptive dimensions | `dim_campaign` |
| DM | Subject-oriented joins and business rules | `dm_reservation_conversion` |
| ADS | Final reporting or application output | `ads_campaign_conversion`, `ads_crm_reserved_not_paid` |

## Grain

- `dwd_reservation_event`: one reservation event per row.
- `dwd_paid_order`: one paid order per row.
- `dim_campaign`: one campaign-product-site definition per row.
- `dm_reservation_conversion`: one user × campaign × product × site per row.

The reservation deduplication and order-window matching happen in DM, not DWD.
