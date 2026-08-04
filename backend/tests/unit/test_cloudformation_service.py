"""Unit tests for CloudFormation template services.

Tests cover:
- Template loading from disk
- Template variable replacement
- S3 upload (mocked)
- CloudFormation URL generation
- Full prepare_template workflow
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.cloudformation.template_service import (
    CloudFormationTemplateError,
    load_template,
    render_template,
)
from app.services.cloudformation.s3_service import (
    S3UploadError,
    get_template_url,
    upload_template,
    validate_bucket,
)
from app.services.cloudformation.cloudformation_service import (
    CloudFormationServiceError,
    get_launch_url,
    get_template_object_key,
    prepare_template,
)


# ── Template Service Tests ─────────────────────────────────


class TestLoadTemplate:
    """Tests for load_template()."""

    def test_load_existing_template(self):
        """Should load the aws-role-v1.yaml template successfully."""
        content = load_template("aws-role-v1.yaml")
        assert isinstance(content, str)
        assert len(content) > 100
        assert "AWSTemplateFormatVersion" in content
        assert "DevarchaiReadOnlyRole" in content

    def test_load_nonexistent_template_raises(self):
        """Should raise CloudFormationTemplateError for missing template."""
        with pytest.raises(CloudFormationTemplateError, match="Template not found"):
            load_template("nonexistent-template-v99.yaml")

    def test_template_contains_placeholders(self):
        """Template should contain the expected placeholder variables."""
        content = load_template("aws-role-v1.yaml")
        assert "{{EXTERNAL_ID}}" in content
        assert "{{ROLE_NAME}}" in content
        assert "{{ACCOUNT_ID}}" in content
        assert "{{SCANNER_ROLE_ARN}}" in content


class TestRenderTemplate:
    """Tests for render_template()."""

    def test_render_basic(self):
        """Should replace all placeholders with provided values."""
        template = "Hello {{NAME}}, your account is {{ACCOUNT_ID}}."
        result = render_template(template, {"NAME": "Alice", "ACCOUNT_ID": "123456789012"})
        assert result == "Hello Alice, your account is 123456789012."

    def test_render_all_placeholders(self):
        """Should replace all placeholders in the actual template."""
        content = load_template("aws-role-v1.yaml")
        rendered = render_template(content, {
            "ACCOUNT_ID": "123456789012",
            "EXTERNAL_ID": "abc123",
            "ROLE_NAME": "TestRole",
            "SCANNER_ROLE_ARN": "arn:aws:iam::999888777666:role/TestScannerRole",
        })
        assert "{{ACCOUNT_ID}}" not in rendered
        assert "{{EXTERNAL_ID}}" not in rendered
        assert "{{ROLE_NAME}}" not in rendered
        assert "{{SCANNER_ROLE_ARN}}" not in rendered
        assert "123456789012" in rendered
        assert "abc123" in rendered
        assert "TestRole" in rendered
        assert "arn:aws:iam::999888777666:role/TestScannerRole" in rendered

    def test_render_missing_variable_raises(self):
        """Should raise error when required variable is missing."""
        template = "Hello {{NAME}}, your role is {{ROLE_NAME}}."
        with pytest.raises(CloudFormationTemplateError, match="Missing required template variables"):
            render_template(template, {"NAME": "Alice"})

    def test_render_no_placeholders(self):
        """Should return template unchanged when no placeholders exist."""
        template = "No placeholders here."
        result = render_template(template, {"UNUSED": "value"})
        assert result == "No placeholders here."


# ── S3 Service Tests ───────────────────────────────────────


class TestGetTemplateUrl:
    """Tests for get_template_url()."""

    def test_default_bucket(self):
        """Should generate correct public URL with default bucket."""
        url = get_template_url("cloudformation/aws-role-v1.yaml")
        assert url.startswith("https://")
        assert "devarchai-assets" in url
        assert "cloudformation/aws-role-v1.yaml" in url

    def test_custom_bucket(self):
        """Should generate correct URL with custom bucket."""
        url = get_template_url("cloudformation/aws-role-v1.yaml", "my-bucket")
        assert "my-bucket" in url


class TestGetTemplateObjectKey:
    """Tests for get_template_object_key()."""

    def test_object_key_format(self):
        """Should return prefix/filename format."""
        key = get_template_object_key()
        assert key.startswith("cloudformation/")
        assert key.endswith(".yaml")


class TestValidateBucket:
    """Tests for validate_bucket() with mocked S3."""

    @patch("app.services.cloudformation.s3_service._get_s3_client")
    def test_valid_bucket(self, mock_get_client):
        """Should return True for accessible bucket."""
        mock_client = MagicMock()
        mock_client.head_bucket.return_value = {}
        mock_get_client.return_value = mock_client

        result = validate_bucket("test-bucket")
        assert result is True
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")

    @patch("app.services.cloudformation.s3_service._get_s3_client")
    def test_missing_bucket_raises(self, mock_get_client):
        """Should raise S3UploadError for non-existent bucket."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        error_response = {"Error": {"Code": "404"}}
        mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")
        mock_get_client.return_value = mock_client

        with pytest.raises(S3UploadError, match="Bucket not found"):
            validate_bucket("missing-bucket")

    @patch("app.services.cloudformation.s3_service._get_s3_client")
    def test_access_denied_raises(self, mock_get_client):
        """Should raise S3UploadError for access denied."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        error_response = {"Error": {"Code": "403"}}
        mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")
        mock_get_client.return_value = mock_client

        with pytest.raises(S3UploadError, match="Access denied"):
            validate_bucket("restricted-bucket")


class TestUploadTemplate:
    """Tests for upload_template() with mocked S3."""

    @patch("app.services.cloudformation.s3_service._get_s3_client")
    def test_upload_success(self, mock_get_client):
        """Should upload template and return public URL."""
        mock_client = MagicMock()
        mock_client.put_object.return_value = {}
        mock_get_client.return_value = mock_client

        url = upload_template("template content", "cloudformation/test.yaml", "test-bucket")

        assert url.startswith("https://")
        assert "test-bucket" in url
        assert "cloudformation/test.yaml" in url
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "cloudformation/test.yaml"
        assert call_kwargs["ContentType"] == "application/x-yaml"

    @patch("app.services.cloudformation.s3_service._get_s3_client")
    def test_upload_failure_raises(self, mock_get_client):
        """Should raise S3UploadError on upload failure."""
        from botocore.exceptions import ClientError

        mock_client = MagicMock()
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
        mock_client.put_object.side_effect = ClientError(error_response, "PutObject")
        mock_get_client.return_value = mock_client

        with pytest.raises(S3UploadError, match="Failed to upload"):
            upload_template("content", "key.yaml")


# ── CloudFormation Service Tests ───────────────────────────


class TestGetLaunchUrl:
    """Tests for get_launch_url()."""

    def test_launch_url_contains_template_and_stack(self):
        """Should generate URL with template URL and stack name."""
        url = get_launch_url(
            template_url="https://bucket.s3.amazonaws.com/tpl.yaml",
            stack_name="MyStack",
        )
        assert url.startswith("https://console.aws.amazon.com/cloudformation/home")
        assert "templateURL=" in url
        assert "stackName=MyStack" in url

    def test_launch_url_no多余_parameters(self):
        """Pre-rendered templates should not include CloudFormation parameters."""
        url = get_launch_url(
            template_url="https://bucket.s3.amazonaws.com/tpl.yaml",
            stack_name="Stack",
        )
        assert "param_ExternalId" not in url
        assert "param_RoleName" not in url


class TestPrepareTemplate:
    """Tests for prepare_template() with mocked S3."""

    @patch("app.services.cloudformation.cloudformation_service.upload_template")
    def test_prepare_template_success(self, mock_upload):
        """Should load, render, upload, and return public URLs."""
        mock_upload.return_value = (
            "https://devarchai-assets.s3.ap-south-1.amazonaws.com/cloudformation/aws-role-v1.yaml"
        )

        result = prepare_template(
            account_id="123456789012",
            external_id="test-external-id",
            role_name="TestRole",
        )

        assert "template_url" in result
        assert "object_key" in result
        assert "template_content" in result
        assert result["template_url"].startswith("https://")
        assert "aws-role-v1.yaml" in result["object_key"]

        # Verify upload was called with rendered content
        mock_upload.assert_called_once()
        call_args = mock_upload.call_args
        rendered_content = call_args[0][0]
        assert "123456789012" in rendered_content
        assert "test-external-id" in rendered_content
        assert "TestRole" in rendered_content

    @patch("app.services.cloudformation.cloudformation_service.upload_template")
    def test_prepare_template_default_role_name(self, mock_upload):
        """Should use default role name when not specified."""
        mock_upload.return_value = "https://bucket.s3.amazonaws.com/cloudformation/aws-role-v1.yaml"

        result = prepare_template(
            account_id="123456789012",
            external_id="ext-id",
        )

        rendered_content = mock_upload.call_args[0][0]
        assert "DevarchaiReadOnlyRole" in rendered_content

    @patch("app.services.cloudformation.cloudformation_service.upload_template")
    def test_prepare_template_s3_failure(self, mock_upload):
        """Should raise CloudFormationServiceError on S3 upload failure."""
        mock_upload.side_effect = S3UploadError("Upload failed")

        with pytest.raises(CloudFormationServiceError, match="Failed to upload template"):
            prepare_template(
                account_id="123456789012",
                external_id="ext-id",
            )


# ── Integration-style Tests ────────────────────────────────


class TestTemplateIntegration:
    """Integration tests that verify the full template pipeline without mocking S3."""

    def test_template_load_render_roundtrip(self):
        """Should load, render, and validate the template structure."""
        content = load_template("aws-role-v1.yaml")

        rendered = render_template(content, {
            "ACCOUNT_ID": "123456789012",
            "EXTERNAL_ID": "test-external-id-abc",
            "ROLE_NAME": "TestRole",
            "SCANNER_ROLE_ARN": "arn:aws:iam::999888777666:role/TestScannerRole",
        })

        # Verify no unreplaced placeholders
        assert "{{" not in rendered

        # Verify critical template elements
        assert "AWSTemplateFormatVersion" in rendered
        assert "DevarchaiReadOnlyRole" in rendered or "TestRole" in rendered
        assert "123456789012" in rendered
        assert "test-external-id-abc" in rendered
        assert "ReadOnlyAccess" in rendered
        assert "SecurityAudit" in rendered
        assert "CostExplorer" in rendered or "ce:GetCostAndUsage" in rendered

    def test_template_has_required_sections(self):
        """Template should have all required CloudFormation sections."""
        content = load_template("aws-role-v1.yaml")
        assert "AWSTemplateFormatVersion:" in content
        assert "Description:" in content
        assert "Resources:" in content
        assert "Outputs:" in content
        # Pre-rendered template — no Parameters section (values baked in)
        assert "Parameters:" not in content

    def test_template_creates_iam_role(self):
        """Template should create an IAM Role with correct type."""
        content = load_template("aws-role-v1.yaml")
        assert "AWS::IAM::Role" in content
        assert "AssumeRolePolicyDocument" in content

    def test_template_has_managed_policies(self):
        """Template should attach ReadOnlyAccess and SecurityAudit policies."""
        content = load_template("aws-role-v1.yaml")
        assert "ReadOnlyAccess" in content
        assert "SecurityAudit" in content

    def test_template_render_produces_valid_structure(self):
        """Rendered template should still be valid YAML structure."""
        import yaml

        class CloudFormationLoader(yaml.SafeLoader):
            """YAML loader that handles CloudFormation intrinsic function tags."""

        def _cf_constructor(loader, tag_suffix, node):
            if isinstance(node, yaml.ScalarNode):
                return loader.construct_scalar(node)
            if isinstance(node, yaml.SequenceNode):
                return loader.construct_sequence(node)
            if isinstance(node, yaml.MappingNode):
                return loader.construct_mapping(node)
            return None

        CloudFormationLoader.add_multi_constructor("!", _cf_constructor)

        content = load_template("aws-role-v1.yaml")
        rendered = render_template(content, {
            "ACCOUNT_ID": "123456789012",
            "EXTERNAL_ID": "ext-123",
            "ROLE_NAME": "TestRole",
            "SCANNER_ROLE_ARN": "arn:aws:iam::999888777666:role/TestScannerRole",
        })
        parsed = yaml.load(rendered, Loader=CloudFormationLoader)
        assert parsed["AWSTemplateFormatVersion"] == "2010-09-09"
        assert "DevarchaiReadOnlyRole" in parsed["Resources"]
        role = parsed["Resources"]["DevarchaiReadOnlyRole"]
        assert role["Type"] == "AWS::IAM::Role"
        assert role["Properties"]["RoleName"] == "TestRole"
