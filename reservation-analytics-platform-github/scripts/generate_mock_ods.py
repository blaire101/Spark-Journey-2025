from __future__ import annotations

from pathlib import Path
import duckdb


def main() -> None:
    output = Path("aws/mock_ods")
    output.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(Path("sql/local/00_mock_ods.sql").read_text(encoding="utf-8"))

    for table in ["ods_reservation_event", "ods_order", "dim_campaign"]:
        folder = output / table
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "part-00000.parquet"
        con.execute(
            f"COPY {table} TO ? (FORMAT PARQUET)",
            [str(path)],
        )
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows -> {path}")


if __name__ == "__main__":
    main()
