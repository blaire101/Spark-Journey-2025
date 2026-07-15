from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3


QUERIES = {
    "dm": """
        SELECT mid, order_flag, tag_reserved_not_paid, conversion_segment, order_id
        FROM reservation_curated.dm_reservation_conversion
        ORDER BY mid
    """,
    "ads": """
        SELECT campaign_id, site, channel, reserved_users, paid_users,
               unconverted_users, conversion_rate
        FROM reservation_curated.ads_campaign_conversion
        ORDER BY channel
    """,
    "crm": """
        SELECT mid, campaign_id, product_id, site, channel
        FROM reservation_curated.ads_crm_reserved_not_paid
        ORDER BY mid
    """,
}


def execute(athena, query: str, output: str) -> str:
    qid = athena.start_query_execution(
        QueryString=query,
        ResultConfiguration={"OutputLocation": output},
    )["QueryExecutionId"]
    while True:
        status = athena.get_query_execution(
            QueryExecutionId=qid
        )["QueryExecution"]["Status"]
        state = status["State"]
        if state in {"SUCCEEDED", "FAILED", "CANCELLED"}:
            if state != "SUCCEEDED":
                raise RuntimeError(status.get("StateChangeReason", state))
            return qid
        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    state = json.loads(Path("aws_state.json").read_text(encoding="utf-8"))
    session = boto3.Session(
        profile_name=args.profile,
        region_name=state["region"],
    )
    athena = session.client("athena")
    output = f"s3://{state['bucket']}/athena-results/"

    for name, query in QUERIES.items():
        qid = execute(athena, query, output)
        result = athena.get_query_results(QueryExecutionId=qid)
        rows = result["ResultSet"]["Rows"]
        print(f"\n=== {name.upper()} ===")
        for row in rows:
            print(" | ".join(x.get("VarCharValue", "NULL") for x in row["Data"]))


if __name__ == "__main__":
    main()
