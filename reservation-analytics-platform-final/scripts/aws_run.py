from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import boto3


TERMINAL = {"SUCCEEDED", "FAILED", "STOPPED", "TIMEOUT", "ERROR"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    args = parser.parse_args()

    state = json.loads(Path("aws_state.json").read_text(encoding="utf-8"))
    session = boto3.Session(
        profile_name=args.profile,
        region_name=state["region"],
    )
    glue = session.client("glue")
    run_id = glue.start_job_run(JobName=state["job_name"])["JobRunId"]
    print(f"Started Glue job run: {run_id}")

    while True:
        run = glue.get_job_run(
            JobName=state["job_name"],
            RunId=run_id,
            PredecessorsIncluded=False,
        )["JobRun"]
        status = run["JobRunState"]
        print(f"Status: {status}")
        if status in TERMINAL:
            break
        time.sleep(15)

    if status != "SUCCEEDED":
        message = run.get("ErrorMessage", "No error message")
        raise SystemExit(f"Glue job failed: {message}")

    print("\nGlue job succeeded.")
    print("Open Athena and run sql/athena_validation.sql")
    print(f"Database: {state['output_database']}")


if __name__ == "__main__":
    main()
