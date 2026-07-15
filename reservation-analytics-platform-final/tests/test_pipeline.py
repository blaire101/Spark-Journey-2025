import subprocess
import sys

import duckdb


def test_pipeline() -> None:
    subprocess.run([sys.executable, "-m", "src.run_local"], check=True)
    db = duckdb.connect("output/reservation_analytics.duckdb")

    assert db.execute("SELECT COUNT(*) FROM p_dwd_reservation_event").fetchone()[0] == 4

    rows = db.execute("""
        SELECT mid, order_flag, tag_reserved_not_paid
        FROM p_dm_reservation_conversion
        ORDER BY mid
    """).fetchall()

    assert rows == [
        ("U001", 1, 0),
        ("U002", 0, 1),
        ("U003", 0, 1),
    ]
    assert db.execute("SELECT COUNT(*) FROM p_ads_crm_reserved_not_paid").fetchone()[0] == 2
