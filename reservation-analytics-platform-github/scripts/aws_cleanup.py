from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default=None)
    parser.add_argument("--delete-bucket", action="store_true")
    args = parser.parse_args()

    state = json.loads(Path("aws_state.json").read_text(encoding="utf-8"))
    session = boto3.Session(
        profile_name=args.profile,
        region_name=state["region"],
    )
    glue = session.client("glue")
    iam = session.client("iam")
    s3 = session.resource("s3")

    for trigger in ["reservation-analytics-daily-trigger"]:
        try:
            glue.delete_trigger(Name=trigger)
            print(f"Deleted trigger: {trigger}")
        except glue.exceptions.EntityNotFoundException:
            pass

    try:
        glue.delete_job(JobName=state["job_name"])
        print(f"Deleted Glue job: {state['job_name']}")
    except glue.exceptions.EntityNotFoundException:
        pass

    for db in ["reservation_curated", "reservation_ods"]:
        try:
            glue.delete_database(Name=db)
            print(f"Deleted Glue database: {db}")
        except glue.exceptions.EntityNotFoundException:
            pass

    role = state["role_name"]
    try:
        iam.delete_role_policy(
            RoleName=role,
            PolicyName="ReservationDemoDataAccess",
        )
    except ClientError:
        pass
    try:
        iam.detach_role_policy(
            RoleName=role,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole",
        )
    except ClientError:
        pass
    try:
        iam.delete_role(RoleName=role)
        print(f"Deleted IAM role: {role}")
    except ClientError as exc:
        print(f"IAM role not deleted: {exc}")

    if args.delete_bucket:
        bucket = s3.Bucket(state["bucket"])
        bucket.objects.all().delete()
        bucket.delete()
        print(f"Deleted bucket: {state['bucket']}")
    else:
        print(
            f"Bucket retained: {state['bucket']}. "
            "Use --delete-bucket to remove it and all demo files."
        )


if __name__ == "__main__":
    main()
