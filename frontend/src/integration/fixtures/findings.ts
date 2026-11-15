export const sampleFindings = [
  {
    id: 'f1111111-2222-3333-4444-555555555551',
    scan_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    rule_id: 'DOCKER-001',
    rule_name: 'Container Runs as Root',
    severity: 'high',
    category: 'security',
    file_path: 'Dockerfile',
    description: 'Container runs as root user',
    processing_metadata: {
      remediation: {
        explanation: 'Add a non-root USER instruction in the Dockerfile',
        patch_status: 'ready',
      },
    },
  },
  {
    id: 'f1111111-2222-3333-4444-555555555552',
    scan_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    rule_id: 'K8S-002',
    rule_name: 'Missing Resource Limits',
    severity: 'medium',
    category: 'reliability',
    file_path: 'k8s/deployment.yaml',
    description: 'No CPU/memory limits defined',
  },
]
