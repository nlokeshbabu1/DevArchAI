"""CloudFormation template generator for AWS onboarding.

Generates a self-contained CloudFormation template that creates:
- IAM Role with read-only access
- Trust relationship for DevArchAI OIDC provider
- SecurityAudit + ReadOnlyAccess policies
- Cost Explorer + CloudWatch permissions
"""

from __future__ import annotations

import json
from typing import Any

# DevArchAI OIDC Provider ARN (production)
DEVARCHAI_OIDC_ARN = "arn:aws:iam::012345678901:oidc-provider/token.actions.githubusercontent.com"
DEVARCHAI_OIDC_URL = "https://token.actions.githubusercontent.com"
DEVARCHAI_AUDIENCE = "sts.amazonaws.com"

# DevArchAI AWS Account (where the OIDC provider lives)
DEVARCHAI_ACCOUNT_ID = "012345678901"


def generate_cloudformation_template(
    account_id: str,
    external_id: str,
    role_name: str = "DevArchAI-ReadOnly",
) -> str:
    """Generate a CloudFormation template JSON string.

    The template creates an IAM role that DevArchAI can assume via OIDC federation.
    The user's AWS account trusts DevArchAI's OIDC provider with the external ID
    as a condition to prevent confused deputy attacks.
    """
    template: dict[str, Any] = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "DevArchAI Cloud Security Platform - Read-Only Access Role",
        "Parameters": {
            "ExternalId": {
                "Type": "String",
                "Default": external_id,
                "Description": "Unique external ID for DevArchAI AssumeRole",
                "MinLength": 1,
            },
            "RoleName": {
                "Type": "String",
                "Default": role_name,
                "Description": "Name for the IAM role",
                "MinLength": 1,
                "MaxLength": 64,
            },
        },
        "Resources": {
            "DevArchAIRole": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "RoleName": {"Ref": "RoleName"},
                    "Description": "Read-only role for DevArchAI cloud security scanning",
                    "AssumeRolePolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {
                                    "Federated": f"arn:aws:iam::{DEVARCHAI_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com"
                                },
                                "Action": "sts:AssumeRoleWithWebIdentity",
                                "Condition": {
                                    "StringEquals": {
                                        "token.actions.githubusercontent.com:aud": DEVARCHAI_AUDIENCE,
                                    },
                        "StringLike": {
                            "token.actions.githubusercontent.com:sub": "repo:devarchai/*:ref:refs/heads/*",
                        },
                                },
                            },
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "cloudformation.amazonaws.com"},
                                "Action": "sts:AssumeRole",
                                "Condition": {
                                    "StringEquals": {
                                        "aws:SourceAccount": {"Ref": "AWS::AccountId"},
                                    }
                                },
                            },
                        ],
                    },
                    "ManagedPolicyArns": [
                        "arn:aws:iam::aws:policy/ReadOnlyAccess",
                        "arn:aws:iam::aws:policy/SecurityAudit",
                    ],
                    "Policies": [
                        {
                            "PolicyName": "DevArchAI-CostExplorer",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "ce:GetCostAndUsage",
                                            "ce:GetCostForecast",
                                            "ce:GetDimensionValues",
                                            "ce:GetReservationCoverage",
                                            "ce:GetReservationPurchaseRecommendation",
                                            "ce:GetReservationUtilization",
                                            "ce:GetUsageForecast",
                                            "ce:ListCostCategoryDefinitions",
                                        ],
                                        "Resource": "*",
                                    },
                                ],
                            },
                        },
                        {
                            "PolicyName": "DevArchAI-CloudWatch",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "cloudwatch:GetMetricData",
                                            "cloudwatch:GetMetricStatistics",
                                            "cloudwatch:ListMetrics",
                                            "logs:DescribeLogGroups",
                                            "logs:DescribeLogStreams",
                                            "logs:GetLogEvents",
                                            "logs:FilterLogEvents",
                                        ],
                                        "Resource": "*",
                                    },
                                ],
                            },
                        },
                        {
                            "PolicyName": "DevArchAI-Organizations",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "organizations:ListAccounts",
                                            "organizations:ListAccountsForParent",
                                            "organizations:ListOrganizationalUnitsForParent",
                                            "organizations:ListRoots",
                                            "organizations:DescribeOrganization",
                                        ],
                                        "Resource": "*",
                                    },
                                ],
                            },
                        },
                        {
                            "PolicyName": "DevArchAI-Support",
                            "PolicyDocument": {
                                "Version": "2012-10-17",
                                "Statement": [
                                    {
                                        "Effect": "Allow",
                                        "Action": [
                                            "support:DescribeTrustedAdvisorChecks",
                                            "support:DescribeTrustedAdvisorCheckResult",
                                            "support:DescribeTrustedAdvisorCheckSummaries",
                                        ],
                                        "Resource": "*",
                                    },
                                ],
                            },
                        },
                    ],
                    "Tags": [
                        {"Key": "ManagedBy", "Value": "DevArchAI"},
                        {"Key": "Purpose", "Value": "CloudSecurityScanning"},
                    ],
                },
            },
        },
        "Outputs": {
            "RoleArn": {
                "Description": "ARN of the DevArchAI IAM Role",
                "Value": {"Fn::GetAtt": ["DevArchAIRole", "Arn"]},
                "Export": {
                    "Name": {"Fn::Sub": "${AWS::StackName}-RoleArn"},
                },
            },
            "RoleName": {
                "Description": "Name of the DevArchAI IAM Role",
                "Value": {"Ref": "RoleName"},
            },
            "StackName": {
                "Description": "Name of this CloudFormation stack",
                "Value": {"Ref": "AWS::StackName"},
            },
        },
    }

    return json.dumps(template, indent=2)


def build_cloudformation_url(
    template_url: str,
    stack_name: str,
    external_id: str,
    role_name: str = "DevArchAI-ReadOnly",
) -> str:
    """Build a CloudFormation Quick Create URL.

    This URL opens AWS Console with the template pre-loaded and parameters pre-filled.
    The user only needs to click 'Create stack' to deploy everything.
    """
    from urllib.parse import urlencode

    params = {
        "templateURL": template_url,
        "stackName": stack_name,
        "param_ExternalId": external_id,
        "param_RoleName": role_name,
    }

    return (
        "https://console.aws.amazon.com/cloudformation/home"
        f"#/stacks/create/review?{urlencode(params)}"
    )
