# Data layers

| Layer | Purpose | Example |
|---|---|---|
| ODS | Standardized upstream data | `ods_reservation_event` |
| DWD | Cleaned atomic detail | `dwd_reservation` |
| FACT | Business process at declared grain | `fact_reservation_conversion` |
| DM | Reusable subject-oriented model | `dm_user_campaign_profile` |
| ADS | Final reporting or operational output | `ads_campaign_conversion` |

Focus on **grain first**. Here the fact grain is `user × campaign × product × site`.
