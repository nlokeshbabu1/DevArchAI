# Rule Engine Accuracy Report

**Generated:** 2026-03-12 19:43:52

## Summary

- **Repositories tested:** 46
- **Total files scanned:** 91
- **Total findings:** 45
- **Scan duration:** 0.09s

## Accuracy Metrics

| Metric | Value |
|--------|-------|
| True Positives | 0 |
| False Positives | 45 |
| False Negatives | 52 |
| **Accuracy** | **0.0%** |
| Precision | 0.0% |
| Recall | 0.0% |
| F1 Score | 0.0% |
| False Positive Rate | 100.0% |
| False Negative Rate | 100.0% |

## Per Repository Results

| Repository | Files | Findings | TP | FP | FN | Duration |
|------------|-------|----------|----|----|----|---------|
| cicd-no-security-scan | 1 | 0 | 0 | 0 | 1 | 0.00s |
| docker-add-root | 2 | 2 | 0 | 2 | 2 | 0.00s |
| docker-alpine | 2 | 0 | 0 | 0 | 0 | 0.00s |
| docker-apt-no-clean | 2 | 3 | 0 | 3 | 1 | 0.00s |
| docker-complete-secure | 2 | 0 | 0 | 0 | 0 | 0.00s |
| docker-curl-pipe | 2 | 3 | 0 | 3 | 1 | 0.00s |
| docker-expose-all | 2 | 3 | 0 | 3 | 1 | 0.00s |
| docker-latest-base | 2 | 1 | 0 | 1 | 1 | 0.00s |
| docker-mixed-issues | 2 | 3 | 0 | 3 | 3 | 0.00s |
| docker-multi-stage | 2 | 0 | 0 | 0 | 0 | 0.00s |
| docker-no-healthcheck | 2 | 1 | 0 | 1 | 1 | 0.00s |
| docker-no-user | 2 | 2 | 0 | 2 | 1 | 0.00s |
| docker-node-root | 2 | 2 | 0 | 2 | 2 | 0.00s |
| docker-python-insecure | 2 | 2 | 0 | 2 | 2 | 0.00s |
| docker-root-user | 2 | 1 | 0 | 1 | 1 | 0.00s |
| docker-secure | 2 | 0 | 0 | 0 | 0 | 0.00s |
| k8s-complete-secure | 2 | 1 | 0 | 1 | 0 | 0.01s |
| k8s-default-ns | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-host-network | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-latest-tag | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-mixed-issues | 2 | 1 | 0 | 1 | 2 | 0.00s |
| k8s-multiple-issues | 2 | 1 | 0 | 1 | 3 | 0.00s |
| k8s-no-hpa | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-no-limits | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-no-network-policy | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-no-pdb | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-no-probes | 2 | 1 | 0 | 1 | 2 | 0.00s |
| k8s-no-security-context | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-privileged | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-root-container | 2 | 1 | 0 | 1 | 1 | 0.00s |
| k8s-secure | 2 | 1 | 0 | 1 | 0 | 0.01s |
| tf-complete-secure | 2 | 0 | 0 | 0 | 0 | 0.01s |
| tf-ec2-unencrypted | 2 | 0 | 0 | 0 | 1 | 0.00s |
| tf-hardcoded-secrets | 2 | 0 | 0 | 0 | 1 | 0.00s |
| tf-iam-wildcard | 2 | 0 | 0 | 0 | 1 | 0.00s |
| tf-local-backend | 2 | 1 | 0 | 1 | 1 | 0.00s |
| tf-mixed-bad | 2 | 1 | 0 | 1 | 3 | 0.00s |
| tf-mixed-good | 2 | 2 | 0 | 2 | 2 | 0.00s |
| tf-no-backend | 2 | 1 | 0 | 1 | 1 | 0.00s |
| tf-no-locking | 2 | 2 | 0 | 2 | 1 | 0.00s |
| tf-no-tags | 2 | 0 | 0 | 0 | 1 | 0.00s |
| tf-rds-public | 2 | 0 | 0 | 0 | 2 | 0.00s |
| tf-s3-public | 2 | 0 | 0 | 0 | 2 | 0.00s |
| tf-s3-secure | 2 | 0 | 0 | 0 | 0 | 0.00s |
| tf-security-group-open | 2 | 0 | 0 | 0 | 1 | 0.00s |
| tf-unpinned-providers | 2 | 0 | 0 | 0 | 1 | 0.00s |

## Rule Performance

| Rule ID | Triggered | Correct | Incorrect |
|---------|-----------|---------|-----------|
| DKR-COST-001 | 4 | 0 | 4 |
| DKR-REL-001 | 7 | 0 | 7 |
| DKR-SCALE-001 | 3 | 0 | 3 |
| DKR-SEC-001 | 9 | 0 | 9 |
| K8S-OBS-001 | 15 | 0 | 15 |
| TF-STATE-001 | 3 | 0 | 3 |
| TF-STATE-003 | 2 | 0 | 2 |
| TF-STATE-004 | 2 | 0 | 2 |

## Observations

### Rules with High False Positive Rate

- **DKR-SEC-001**: 9 false positives out of 9 triggers
- **DKR-COST-001**: 4 false positives out of 4 triggers
- **DKR-REL-001**: 7 false positives out of 7 triggers
- **DKR-SCALE-001**: 3 false positives out of 3 triggers
- **K8S-OBS-001**: 15 false positives out of 15 triggers
- **TF-STATE-001**: 3 false positives out of 3 triggers
- **TF-STATE-003**: 2 false positives out of 2 triggers
- **TF-STATE-004**: 2 false positives out of 2 triggers

### Repositories with Missed Detections

- **cicd-no-security-scan**: 1 findings missed
- **docker-add-root**: 2 findings missed
- **docker-apt-no-clean**: 1 findings missed
- **docker-curl-pipe**: 1 findings missed
- **docker-expose-all**: 1 findings missed
- **docker-latest-base**: 1 findings missed
- **docker-mixed-issues**: 3 findings missed
- **docker-no-healthcheck**: 1 findings missed
- **docker-no-user**: 1 findings missed
- **docker-node-root**: 2 findings missed

## Recommendations

1. **Review high false-positive rules:**
   - Refine detection logic for `DKR-SEC-001`
   - Refine detection logic for `DKR-COST-001`
   - Refine detection logic for `DKR-REL-001`
   - Refine detection logic for `DKR-SCALE-001`
   - Refine detection logic for `K8S-OBS-001`

2. **Improve detection coverage:**
   - Add more test cases for edge cases
   - Review parser extraction logic

3. **General improvements:**
   - Add semantic analysis for context-aware detection
   - Implement rule confidence scoring
   - Add automated rule testing in CI/CD

## Performance Metrics

- **Average files per repo:** 2.0
- **Average findings per repo:** 1.0
- **Average scan time per repo:** 0.00s
- **Files scanned per second:** 1008.9
