#!/usr/bin/env python3
"""Analyze the AWS-S3 repository with the fixed parser."""
import sys
sys.path.insert(0, '/home/lokesh/AI-Engine/DevArchAI/backend')

from app.parsers.terraform import TerraformParser
from app.rule_engine.rules.terraform_rules import (
    TerraformStateLockingRule,
    TerraformBackendEncryptionRule,
    TerraformS3EncryptionRule,
    TerraformRequiredTagsRule,
)
from pathlib import Path
import os

repo_path = Path('/tmp/test-repo')
tf_files = list(repo_path.rglob('*.tf'))

print("=" * 70)
print(f"Analyzing repository: {repo_path}")
print(f"Terraform files found: {len(tf_files)}")
print("=" * 70)

parser = TerraformParser()
all_findings = []

for tf_file in tf_files:
    content = tf_file.read_text()
    result = parser.parse(tf_file, content)
    resources = parser.extract_resources(result.parsed_data)
    
    # Run rules
    locking_rule = TerraformStateLockingRule()
    encryption_rule = TerraformBackendEncryptionRule()
    s3_encryption_rule = TerraformS3EncryptionRule()
    tags_rule = TerraformRequiredTagsRule()
    
    findings = []
    findings.extend(locking_rule.evaluate(resources, str(tf_file)))
    findings.extend(encryption_rule.evaluate(resources, str(tf_file)))
    findings.extend(s3_encryption_rule.evaluate(resources, str(tf_file)))
    findings.extend(tags_rule.evaluate(resources, str(tf_file)))
    
    if findings:
        print(f"\n📁 {tf_file.relative_to(repo_path)}")
        for f in findings:
            print(f"  [{f.severity.value.upper()}] {f.rule_id}: {f.description[:80]}")
        all_findings.extend(findings)

print("\n" + "=" * 70)
print(f"TOTAL FINDINGS: {len(all_findings)}")
print("=" * 70)

# Summary by severity
from collections import Counter
severity_counts = Counter(f.severity.value for f in all_findings)
for sev in ['critical', 'high', 'medium', 'low']:
    count = severity_counts.get(sev, 0)
    if count > 0:
        print(f"  {sev.upper()}: {count}")

# Check specifically for locking findings
locking_findings = [f for f in all_findings if 'lock' in f.rule_id.lower() or 'locking' in f.description.lower()]
print(f"\n🔒 State Locking Findings: {len(locking_findings)}")
for f in locking_findings:
    print(f"  - {f.file_path}: {f.description[:60]}...")

if len(locking_findings) == 0:
    print("\n✅ SUCCESS: All backend.tf files have proper locking configured!")
