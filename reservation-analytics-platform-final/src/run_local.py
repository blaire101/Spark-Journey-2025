from __future__ import annotations

import json
from pathlib import Path

import duckdb


def load_config() -> dict:
    return json.loads(Path("config/pipeline.json").read_text(encoding="utf-8"))


def main() -> None:
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    db_path = output_dir / "reservation_analytics.duckdb"

    con = duckdb.connect(str(db_path))
    con.execute(Path("sql/local/00_mock_ods.sql").read_text(encoding="utf-8"))

    config = load_config()
    for sql_path in config["sql_files"]:
        con.execute(Path(sql_path).read_text(encoding="utf-8"))

    for table in config["output_tables"]:
        persisted = f"p_{table}"
        con.execute(f"CREATE OR REPLACE TABLE {persisted} AS SELECT * FROM {table}")
        con.execute(
            f"COPY {persisted} TO ? (FORMAT CSV, HEADER TRUE)",
            [str(output_dir / f"{table}.csv")],
        )

    print("\n=== DWD reservation events ===")
    print(con.execute("SELECT * FROM p_dwd_reservation_event ORDER BY reservation_id").df().to_string(index=False))

    print("\n=== DM reservation conversion ===")
    print(con.execute("""
        SELECT mid, campaign_id, order_flag, tag_reserved_not_paid,
               conversion_segment, order_id
        FROM p_dm_reservation_conversion
        ORDER BY mid
    """).df().to_string(index=False))

    print("\n=== ADS campaign conversion ===")
    print(con.execute("SELECT * FROM p_ads_campaign_conversion ORDER BY channel").df().to_string(index=False))

    print("\n=== ADS CRM audience ===")
    print(con.execute("SELECT * FROM p_ads_crm_reserved_not_paid ORDER BY mid").df().to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
