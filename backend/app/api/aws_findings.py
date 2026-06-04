"""AWS finding explanation routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.aws import AWSAccount, AWSFinding
from app.models.user import User

router = APIRouter(prefix="/aws/findings", tags=["AWS"])


def _normalize(value: str | None) -> str:
    return (value or "").lower().replace(" ", "_")


def _cli_commands(finding: AWSFinding) -> list[str]:
    resource_id = finding.resource_id or ""
    resource_type = _normalize(finding.resource_type)
    title = _normalize(finding.title)

    if "root" in title or "mfa" in title:
        return ["aws iam get-account-summary"]
    if "security_group" in resource_type:
        return [f"aws ec2 describe-security-groups --group-ids {resource_id}".strip()]
    if "s3" in resource_type:
        return [f"aws s3api get-public-access-block --bucket {resource_id}".strip(), f"aws s3api get-bucket-policy-status --bucket {resource_id}".strip()]
    if "rds" in resource_type:
        return [f"aws rds describe-db-instances --db-instance-identifier {resource_id}".strip()]
    if "ebs" in resource_type:
        return [f"aws ec2 describe-volumes --volume-ids {resource_id}".strip()]
    if "iam" in resource_type:
        return [f"aws iam get-user --user-name {resource_id}".strip(), f"aws iam list-attached-user-policies --user-name {resource_id}".strip()]
    if "lambda" in resource_type:
        return [f"aws lambda get-function --function-name {resource_id}".strip()]
    if "eks" in resource_type:
        return [f"aws eks describe-cluster --name {resource_id}".strip()]
    return ["aws sts get-caller-identity"]


def _terraform_example(finding: AWSFinding) -> str:
    resource_type = _normalize(finding.resource_type)
    title = _normalize(finding.title)

    if "security_group" in resource_type:
        return """resource "aws_security_group_rule" "restricted_ingress" {
  type              = "ingress"
  security_group_id = aws_security_group.app.id
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  cidr_blocks       = ["10.0.0.0/8"]
}"""
    if "s3" in resource_type:
        return """resource "aws_s3_bucket_public_access_block" "secure" {
  bucket                  = aws_s3_bucket.app.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}"""
    if "rds" in resource_type:
        return """resource "aws_db_instance" "private" {
  publicly_accessible = false
  storage_encrypted   = true
}"""
    if "ebs" in resource_type:
        return """resource "aws_ebs_volume" "encrypted" {
  availability_zone = "us-east-1a"
  encrypted         = true
  kms_key_id        = aws_kms_key.ebs.arn
}"""
    if "iam" in resource_type or "mfa" in title or "root" in title:
        return """resource "aws_iam_account_password_policy" "secure" {
  minimum_password_length        = 14
  require_lowercase_characters   = true
  require_uppercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  allow_users_to_change_password = true
}"""
    return "# Review this finding in AWS and codify the remediation in Terraform after validation."


def _fix_steps(finding: AWSFinding) -> list[str]:
    recommendation = finding.recommendation or "Apply the least-privilege and private-by-default remediation for this resource."
    return [
        "Confirm the affected AWS account and region.",
        "Open the affected resource in the AWS Console.",
        "Validate current configuration and business ownership.",
        recommendation,
        "Re-run the AWS scan and confirm the finding is resolved.",
    ]


@router.get("/{finding_id}/explain")
async def explain_aws_finding(
    finding_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return actionable remediation guidance for a user-owned AWS finding."""
    result = await db.execute(
        select(AWSFinding, AWSAccount)
        .join(AWSAccount, AWSFinding.account_id == AWSAccount.id)
        .where(AWSFinding.id == finding_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AWS finding not found")

    finding, account = row
    if account.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AWS finding access denied")

    return {
        "id": str(finding.id),
        "title": finding.title,
        "severity": finding.severity,
        "summary": finding.description,
        "risk": f"{finding.severity.capitalize()} risk affecting {finding.resource_type or 'the AWS account'}.",
        "attack_scenario": "An attacker or misconfigured workload could use this weakness to increase exposure, bypass least privilege, or access sensitive cloud resources.",
        "fix_steps": _fix_steps(finding),
        "cli_commands": _cli_commands(finding),
        "terraform_example": _terraform_example(finding),
        "best_practices": [
            "Prefer least privilege access and private network boundaries.",
            "Validate remediation in a non-production account when possible.",
            "Use infrastructure as code so the fix remains auditable.",
            "Re-scan after remediation and retain evidence for compliance.",
        ],
    }
