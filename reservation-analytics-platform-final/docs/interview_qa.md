# Interview Q&A

## 1. What was the business problem?

Users reserved products before launch, but the business could not tell whether they purchased during the campaign window or identify users who should receive CRM reminders.

## 2. What was the grain?

```text
User × Campaign × Product × Site
```

## 3. Why deduplicate?

A user may click the reservation button more than once. I kept the earliest reservation using `ROW_NUMBER`.

## 4. Why was the join difficult?

Reservation and order tables had no direct foreign key. I matched by user, product and site, and required the paid order time to fall inside the campaign launch window.

## 5. Why create `tag_reserved_not_paid`?

CRM could consume the audience directly without rebuilding the reservation-to-order join.

## 6. What did you do every day?

I checked the scheduled Glue run and CloudWatch logs, validated metrics in Athena, discussed new business requirements, updated Spark SQL in PyCharm, tested locally with mock ODS tables, submitted the change through Git review, and deployed the SQL through CI/CD.

## 7. Did you manually run ETL every day?

No. The Glue job was scheduled. I used the AWS Console mainly for monitoring, validation and incident reruns.

## 8. Why SQL-first?

The main complexity was data modeling, deduplication, time-window matching and aggregation. SQL made the logic easy to review and consistent with my Spark SQL experience.

## 9. How would you improve this for production?

- write curated tables as Iceberg;
- use incremental partitions instead of full overwrite;
- add DQ alerts;
- add job bookmarks or watermark logic;
- monitor SLA and cost;
- use Athena/QuickSight and CRM exports downstream.
