from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    parser.add_argument(
        "--cron",
        default="cron(0 2 * * ? *)",
        help="Default: daily 02:00 UTC",
    )
    args = parser.parse_args()

    state = json.loads(Path("aws_state.json").read_text(encoding="utf-8"))
    session = boto3.Session(
        profile_name=args.profile,
        region_name=state["region"],
    )
    glue = session.client("glue")
    trigger_name = "reservation-analytics-daily-trigger"

    kwargs = {
        "Name": trigger_name,
        "Type": "SCHEDULED",
        "Schedule": args.cron,
        "StartOnCreation": True,
        "Actions": [{"JobName": state["job_name"]}],
    }

    try:
        glue.get_trigger(Name=trigger_name)
        glue.update_trigger(Name=trigger_name, TriggerUpdate={
            "Schedule": args.cron,
            "Actions": [{"JobName": state["job_name"]}],
        })
        glue.start_trigger(Name=trigger_name)
        print(f"Updated trigger: {trigger_name}")
    except glue.exceptions.EntityNotFoundException:
        glue.create_trigger(**kwargs)
        print(f"Created trigger: {trigger_name}")

    print(f"Schedule: {args.cron}")


if __name__ == "__main__":
    main()
