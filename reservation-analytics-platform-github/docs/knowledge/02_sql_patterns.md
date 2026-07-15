# SQL patterns

## Deduplication
Use `ROW_NUMBER` to retain the earliest event per business key.

## Non-equi time-window join
There is no reservation-order foreign key, so match by stable business attributes and campaign time bounds.

## Conditional distinct counts
Use `COUNT(DISTINCT CASE WHEN ... THEN mid END)` for user-level conversion metrics.

## Derived operational tag
Precompute `tag_reserved_not_paid` so CRM does not rebuild complex joins.
