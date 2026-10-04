export interface DocPage {
  slug: string
  title: string
  subtitle: string
  icon: string
  section: string
  headings: { id: string; label: string; level: number }[]
}

export interface DocSection {
  label: string
  pages: DocPage[]
}

export interface SearchResult {
  slug: string
  title: string
  subtitle: string
  match: string
}

const HEADING = (id: string, label: string, level: number = 2) => ({ id, label, level })

export const DOC_SECTIONS: DocSection[] = [
  {
    label: 'Getting Started',
    pages: [
      {
        slug: 'getting-started',
        title: 'Getting Started',
        subtitle: 'Set up your account and run your first security scan in minutes',
        icon: 'Rocket',
        section: 'Getting Started',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('step-1-create-account', 'Step 1: Create an Account'),
          HEADING('step-2-connect-repository', 'Step 2: Connect a Repository'),
          HEADING('step-3-run-scan', 'Step 3: Run a Scan'),
          HEADING('step-4-review-findings', 'Step 4: Review Findings'),
          HEADING('step-5-generate-report', 'Step 5: Generate a PDF Report'),
          HEADING('step-6-create-fix-pr', 'Step 6: Create a Fix PR'),
        ],
      },
    ],
  },
  {
    label: 'Integrations',
    pages: [
      {
        slug: 'github-integration',
        title: 'GitHub',
        subtitle: 'Connect GitHub repositories for automated scanning and PR comments',
        icon: 'Github',
        section: 'Integrations',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('oauth-login', 'OAuth Login'),
          HEADING('repository-access', 'Repository Access'),
          HEADING('pull-request-creation', 'Pull Request Creation'),
          HEADING('scan-triggers', 'Scan Triggers'),
          HEADING('webhooks', 'Webhooks'),
        ],
      },
      {
        slug: 'gitlab-integration',
        title: 'GitLab',
        subtitle: 'Connect GitLab repositories for MR scanning and pipeline analysis',
        icon: 'Gitlab',
        section: 'Integrations',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('oauth-login', 'OAuth Login'),
          HEADING('merge-requests', 'Merge Requests'),
          HEADING('pipeline-analysis', 'Pipeline Analysis'),
          HEADING('repository-scanning', 'Repository Scanning'),
        ],
      },
      {
        slug: 'aws-integration',
        title: 'AWS',
        subtitle: 'Connect your AWS account for comprehensive infrastructure scanning',
        icon: 'Cloud',
        section: 'Integrations',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-services', 'Supported Services'),
          HEADING('connection-methods', 'Connection Methods'),
          HEADING('method-1-iam-role', 'Method 1: IAM Role + External ID'),
          HEADING('method-2-oidc', 'Method 2: OIDC (Recommended)'),
          HEADING('required-fields', 'Required Fields'),
          HEADING('validation', 'Validation & Testing'),
          HEADING('common-errors', 'Common Errors'),
        ],
      },
      {
        slug: 'kubernetes-integration',
        title: 'Kubernetes',
        subtitle: 'Connect live clusters via Web UI or CLI — local, on-prem, EKS, and more',
        icon: 'Container',
        section: 'Integrations',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('architecture', 'Architecture & Data Flow'),
          HEADING('prerequisites', 'Prerequisites'),
          HEADING('web-ui-connect', 'Web UI: Connect a Cluster'),
          HEADING('web-ui-step-1', 'Step 1: Open Integrations'),
          HEADING('web-ui-step-2', 'Step 2: Connect Kubernetes'),
          HEADING('web-ui-step-3', 'Step 3: View Cluster Dashboard'),
          HEADING('web-ui-step-4', 'Step 4: Run Analysis'),
          HEADING('cli-connect', 'CLI: Connect a Cluster'),
          HEADING('cli-step-1', 'Step 1: Install & Authenticate'),
          HEADING('cli-step-2', 'Step 2: Connect via Kubeconfig'),
          HEADING('cli-step-3', 'Step 3: Verify Connection'),
          HEADING('cli-step-4', 'Step 4: Inspect & Analyze'),
          HEADING('cli-commands', 'CLI Commands Reference'),
          HEADING('eks-integration', 'Amazon EKS'),
          HEADING('aks-gke', 'Azure AKS & Google GKE'),
          HEADING('cli-web-sync', 'CLI ↔ Web UI Synchronization'),
          HEADING('api-endpoints', 'API Endpoints'),
          HEADING('security', 'Security'),
          HEADING('troubleshooting', 'Troubleshooting'),
        ],
      },
      {
        slug: 'azure-integration',
        title: 'Azure',
        subtitle: 'Connect your Azure subscription for cloud infrastructure scanning',
        icon: 'Server',
        section: 'Integrations',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('prerequisites', 'Prerequisites'),
          HEADING('connection-methods', 'Connection Methods'),
          HEADING('method-1-service-principal', 'Method 1: Service Principal'),
          HEADING('method-2-entra-id', 'Method 2: Entra ID (Recommended)'),
          HEADING('permissions-required', 'Permissions Required'),
          HEADING('validation', 'Validation & Testing'),
        ],
      },
    ],
  },
  {
    label: 'Scanning',
    pages: [
      {
        slug: 'repository-scanning',
        title: 'Repository Scan',
        subtitle: 'Understanding how DevArchAI scans your infrastructure code',
        icon: 'FolderGit2',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-formats', 'Supported Formats'),
          HEADING('scan-triggers', 'Scan Triggers'),
          HEADING('scan-results', 'Understanding Scan Results'),
        ],
      },
      {
        slug: 'secret-scanning',
        title: 'Secret Scan',
        subtitle: 'Detect exposed secrets, tokens, and credentials in your codebase',
        icon: 'Shield',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-secrets', 'Supported Secret Types'),
          HEADING('detection-methods', 'Detection Methods'),
          HEADING('remediation', 'Remediation'),
        ],
      },
      {
        slug: 'dependency-scanning',
        title: 'Dependency Scan',
        subtitle: 'Scan dependencies and packages for known vulnerabilities',
        icon: 'FileCode',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-ecosystems', 'Supported Ecosystems'),
          HEADING('vulnerability-detection', 'Vulnerability Detection'),
          HEADING('supply-chain-security', 'Supply Chain Security'),
        ],
      },
      {
        slug: 'docker-security',
        title: 'Docker Security',
        subtitle: 'Scan Dockerfiles and container configurations for security risks',
        icon: 'Container',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('checks-performed', 'Checks Performed'),
          HEADING('dockerfile-best-practices', 'Dockerfile Best Practices'),
        ],
      },
      {
        slug: 'kubernetes-security',
        title: 'Kubernetes Security',
        subtitle: 'Scan Kubernetes manifests, Helm charts, and cluster configurations',
        icon: 'Container',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-resources', 'Supported Resources'),
          HEADING('checks-performed', 'Checks Performed'),
          HEADING('best-practices', 'Best Practices'),
        ],
      },
      {
        slug: 'terraform-security',
        title: 'Terraform Security',
        subtitle: 'Scan Terraform configurations for misconfigurations and compliance issues',
        icon: 'FileCode',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-resources', 'Supported Resources'),
          HEADING('checks-performed', 'Checks Performed'),
          HEADING('compliance-frameworks', 'Compliance Frameworks'),
        ],
      },
      {
        slug: 'cicd-security',
        title: 'CI/CD Security',
        subtitle: 'Analyze CI/CD pipeline configurations for security vulnerabilities',
        icon: 'Zap',
        section: 'Scanning',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('supported-platforms', 'Supported Platforms'),
          HEADING('checks-performed', 'Checks Performed'),
        ],
      },
    ],
  },
  {
    label: 'AI Features',
    pages: [
      {
        slug: 'ai-recommendations',
        title: 'AI Recommendations',
        subtitle: 'Understand how AI-powered fix recommendations work',
        icon: 'Brain',
        section: 'AI Features',
        headings: [
          HEADING('overview', 'What is an AI Recommendation?'),
          HEADING('scoring-methodology', 'Scoring Methodology'),
          HEADING('risk-reduction', 'Risk Reduction Calculation'),
          HEADING('confidence-scoring', 'Confidence Scoring'),
          HEADING('effort-estimation', 'Estimated Effort'),
          HEADING('fix-pr-generation', 'Fix PR Generation'),
        ],
      },
      {
        slug: 'ai-fix-generation',
        title: 'AI Fix Generation',
        subtitle: 'Automatically generate fixes for security findings',
        icon: 'Brain',
        section: 'AI Features',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('how-it-works', 'How It Works'),
          HEADING('fix-quality', 'Fix Quality'),
          HEADING('supported-languages', 'Supported Languages'),
          HEADING('manual-review', 'Manual Review Process'),
        ],
      },
      {
        slug: 'pull-request-creation',
        title: 'Pull Request Creation',
        subtitle: 'Create automated pull requests to fix security issues',
        icon: 'Zap',
        section: 'AI Features',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('pr-workflow', 'PR Workflow'),
          HEADING('configuration', 'Configuration'),
          HEADING('branch-protection', 'Branch Protection'),
          HEADING('pr-templates', 'PR Templates'),
        ],
      },
    ],
  },
  {
    label: 'Reports',
    pages: [
      {
        slug: 'security-findings',
        title: 'Security Findings',
        subtitle: 'Understanding severity levels and remediation workflow',
        icon: 'AlertTriangle',
        section: 'Reports',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('severity-levels', 'Severity Levels'),
          HEADING('scoring-methodology', 'Scoring Methodology'),
          HEADING('remediation-workflow', 'Remediation Workflow'),
        ],
      },
      {
        slug: 'pdf-reports',
        title: 'PDF Reports',
        subtitle: 'Generate and export professional security audit reports',
        icon: 'FileText',
        section: 'Reports',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('report-contents', 'Report Contents'),
          HEADING('export-formats', 'Export Formats'),
          HEADING('scheduling', 'Scheduled Reports'),
        ],
      },
      {
        slug: 'excel-reports',
        title: 'Excel Reports',
        subtitle: 'Export findings and metrics to spreadsheet format',
        icon: 'FileText',
        section: 'Reports',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('exporting', 'Exporting to Excel'),
          HEADING('data-included', 'Data Included'),
          HEADING('customization', 'Customization'),
        ],
      },
    ],
  },
  {
    label: 'CLI',
    pages: [
      {
        slug: 'cli',
        title: 'CLI (devsec)',
        subtitle: 'Install the production CLI, authenticate, create projects, and run scans from your terminal',
        icon: 'Terminal',
        section: 'CLI',
        headings: [
          HEADING('overview', 'Overview'),
          HEADING('production-quickstart', 'Production quickstart'),
          HEADING('prerequisites', 'Prerequisites'),
          HEADING('step-1-install', 'Step 1: Install the production CLI'),
          HEADING('step-2-configure-api', 'Step 2: Configure for production'),
          HEADING('step-3-authenticate', 'Step 3: Authenticate'),
          HEADING('step-4-select-project', 'Step 4: Create and manage projects'),
          HEADING('step-5-run-scan', 'Step 5: Run a scan'),
          HEADING('step-6-view-results', 'Step 6: View results in the web app'),
          HEADING('step-7-scan-lifecycle', 'Step 7: Scan lifecycle'),
          HEADING('step-8-ci-pipeline', 'Step 8: Use in CI/CD'),
          HEADING('configuration-reference', 'Configuration Reference'),
          HEADING('commands-reference', 'Commands Reference'),
          HEADING('k8s-commands', 'Kubernetes (k8s) Commands'),
          HEADING('exit-codes', 'Exit Codes'),
          HEADING('troubleshooting', 'Troubleshooting'),
        ],
      },
    ],
  },
  {
    label: 'Support',
    pages: [
      {
        slug: 'faq',
        title: 'FAQ',
        subtitle: 'Frequently asked questions about DevArchAI',
        icon: 'HelpCircle',
        section: 'Support',
        headings: [
          HEADING('general', 'General'),
          HEADING('scanning', 'Scanning'),
          HEADING('integrations', 'Integrations'),
          HEADING('security', 'Security'),
          HEADING('billing', 'Billing'),
        ],
      },
      {
        slug: 'troubleshooting',
        title: 'Troubleshooting',
        subtitle: 'Common issues and how to resolve them',
        icon: 'Bug',
        section: 'Support',
        headings: [
          HEADING('aws-connection-failed', 'AWS Connection Failed'),
          HEADING('github-oauth-failed', 'GitHub OAuth Failed'),
          HEADING('gitlab-oauth-failed', 'GitLab OAuth Failed'),
          HEADING('repository-scan-stuck', 'Repository Scan Stuck'),
          HEADING('no-findings-generated', 'No Findings Generated'),
          HEADING('pdf-report-missing', 'PDF Report Missing'),
          HEADING('fix-pr-failed', 'Fix PR Failed'),
          HEADING('kubernetes-connection-failed', 'Kubernetes Connection Failed'),
          HEADING('kubernetes-ai-stuck', 'Kubernetes AI Analysis Stuck'),
        ],
      },
    ],
  },
]

export const ALL_PAGES = DOC_SECTIONS.flatMap((s) => s.pages)

export function getAllPages(): DocPage[] {
  return ALL_PAGES
}

export function getPage(slug: string): DocPage | undefined {
  return ALL_PAGES.find((p) => p.slug === slug)
}

export function getPrevNext(slug: string): { prev: DocPage | null; next: DocPage | null } {
  const flat = ALL_PAGES
  const idx = flat.findIndex((p) => p.slug === slug)
  return {
    prev: idx > 0 ? flat[idx - 1] : null,
    next: idx < flat.length - 1 ? flat[idx + 1] : null,
  }
}

// Build flat search index: each heading is a search entry
export function buildSearchIndex(): SearchResult[] {
  const results: SearchResult[] = []
  for (const page of ALL_PAGES) {
    results.push({
      slug: page.slug,
      title: page.title,
      subtitle: page.subtitle,
      match: page.title,
    })
    for (const h of page.headings) {
      results.push({
        slug: page.slug,
        title: page.title,
        subtitle: page.subtitle,
        match: h.label,
      })
    }
  }
  return results
}

export function searchDocs(query: string): SearchResult[] {
  const q = query.toLowerCase()
  return buildSearchIndex().filter(
    (r) =>
      r.title.toLowerCase().includes(q) ||
      r.subtitle.toLowerCase().includes(q) ||
      r.match.toLowerCase().includes(q)
  )
}
