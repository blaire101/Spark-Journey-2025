# Development and Deployment Model

## Is SQL written in PyCharm instead of Glue Studio?

Yes. For code-based Glue jobs, a normal engineering workflow is:

```text
IDE → Git branch → local/unit tests → pull request → CI/CD → S3 job artifacts → Glue job → CloudWatch/Athena validation
```

PyCharm is only the editor. Git is the source of truth, and AWS Glue is the managed execution environment.

Glue Studio can also edit or upload scripts and integrate with Git. It is useful for prototyping, interactive sessions and debugging, but teams commonly avoid making production-only changes directly in the console because those changes are harder to review, reproduce and promote across environments.

## Two deployment modes in this repository

### Learning mode

The included Python commands create resources directly from your laptop:

```bash
python scripts/aws_setup.py
python scripts/aws_run.py
```

This is deliberately simple and suitable for a personal sandbox.

### Team/enterprise mode

A larger organization normally adds:

```text
GitHub/GitLab
→ CI checks
→ artifact upload
→ Terraform/CloudFormation/CDK deployment
→ dev environment test
→ approval
→ production deployment
```

Developers still write SQL in an IDE. The important difference is that deployment credentials and promotion are handled by CI/CD rather than each engineer deploying production from a laptop.

## What to say in an interview

> I develop Spark SQL and the Glue job wrapper locally in an IDE, keep them in Git, and test them against controlled mock data. In a personal sandbox I can deploy with AWS CLI or Boto3. In a production team, the same artifacts should be deployed through CI/CD and infrastructure as code, with environment-specific parameters, review and post-deployment validation. Glue Studio is useful for investigation and monitoring, but Git remains the source of truth.
