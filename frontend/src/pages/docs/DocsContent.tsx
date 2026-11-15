import { motion } from 'framer-motion'
import {
  Check, Copy, ChevronDown, ChevronRight, AlertTriangle,
  Info, CheckCircle, BookOpen, ArrowRight,
} from 'lucide-react'
import { useState } from 'react'

import { cn, copyToClipboard } from '../../lib/utils'


/* ── Utility Components ── */

function CodeBlock({ code, lang = 'bash' }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false)
  const handleCopy = () => {
    copyToClipboard(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="relative group my-4 rounded-xl border border-white/10 bg-black/40 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-white/5 border-b border-white/10">
        <span className="text-[10px] font-mono text-muted-foreground uppercase">{lang}</span>
        <button onClick={handleCopy} className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          {copied ? <Check className="h-3.5 w-3.5 text-green-400" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm font-mono text-foreground leading-relaxed"><code>{code}</code></pre>
    </div>
  )
}

function Callout({ type = 'info', title, children }: { type?: 'info' | 'warning' | 'error' | 'success'; title?: string; children: React.ReactNode }) {
  const styles = {
    info: { bg: 'bg-blue-500/10 border-blue-500/30', icon: Info, color: 'text-blue-400' },
    warning: { bg: 'bg-yellow-500/10 border-yellow-500/30', icon: AlertTriangle, color: 'text-yellow-400' },
    error: { bg: 'bg-red-500/10 border-red-500/30', icon: AlertTriangle, color: 'text-red-400' },
    success: { bg: 'bg-green-500/10 border-green-500/30', icon: CheckCircle, color: 'text-green-400' },
  }
  const s = styles[type]
  const Icon = s.icon
  return (
    <div className={cn('flex items-start gap-3 p-4 rounded-xl border my-4', s.bg)}>
      <Icon className={cn('h-5 w-5 flex-shrink-0 mt-0.5', s.color)} />
      <div>
        {title && <p className="text-sm font-semibold text-foreground mb-0.5">{title}</p>}
        <div className="text-sm text-muted-foreground [&>p]:my-0">{children}</div>
      </div>
    </div>
  )
}

function Steps({ children }: { children: React.ReactNode }) {
  return <div className="space-y-6 my-6">{children}</div>
}

function Step({ number, title, children }: { number: string; title: string; children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      className="flex gap-4"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/15 border border-primary/30 flex items-center justify-center text-sm font-bold text-primary">
        {number}
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-base font-semibold text-foreground mb-1.5">{title}</h3>
        <div className="text-sm text-muted-foreground space-y-2 [&>p]:my-0">{children}</div>
      </div>
    </motion.div>
  )
}

function Expandable({ title, children }: { title: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-white/10 rounded-xl overflow-hidden my-3">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center justify-between w-full px-4 py-3 text-sm font-medium text-foreground hover:bg-white/5 transition-colors"
      >
        {title}
        {open ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
      </button>
      {open && <div className="px-4 pb-4 text-sm text-muted-foreground">{children}</div>}
    </div>
  )
}

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2 id={id} className="text-xl font-bold text-foreground mt-10 mb-4 scroll-mt-20">
      {children}
    </h2>
  )
}

function H3({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h3 id={id} className="text-lg font-semibold text-foreground mt-8 mb-3 scroll-mt-20">
      {children}
    </h3>
  )
}

function P({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-muted-foreground leading-relaxed mb-4">{children}</p>
}

function Ul({ children }: { children: React.ReactNode }) {
  return <ul className="list-disc pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">{children}</ul>
}

function Ol({ children }: { children: React.ReactNode }) {
  return <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">{children}</ol>
}

function Table({ headers, rows }: { headers: string[]; rows: (string | React.ReactNode)[][] }) {
  return (
    <div className="overflow-x-auto my-4 rounded-xl border border-white/10">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-white/5 border-b border-white/10">
            {headers.map((h) => (
              <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-white/5 last:border-0 hover:bg-white/5">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-sm text-foreground">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SeverityBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    Critical: 'bg-red-500/15 text-red-400 border-red-500/30',
    High: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    Medium: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    Low: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    Info: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
  }
  return (
    <span className={cn('inline-flex px-2 py-0.5 rounded text-[11px] font-medium border', colors[level] || colors.Info)}>
      {level}
    </span>
  )
}

function LinkCard({ href, title, desc }: { href: string; title: string; desc: string }) {
  return (
    <a
      href={href}
      className="flex items-center justify-between p-4 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors group my-2"
    >
      <div>
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
      </div>
      <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
    </a>
  )
}

/* ── Page Content ── */

export function GettingStartedContent() {
  return (
    <>
      <P>DevArchAI scans your infrastructure-as-code repositories, CI/CD pipelines, and cloud configurations for security vulnerabilities, misconfigurations, and compliance issues. Follow these steps to get started.</P>

      <Steps>
        <Step number="1" title="Create an Account">
          <P>Sign up for DevArchAI using your email, GitHub OAuth, or GitLab OAuth.</P>
          <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
            <li>Navigate to the <a href="/register" className="text-primary hover:underline">registration page</a>.</li>
            <li>Choose your sign-up method: Email + Password, GitHub, or GitLab.</li>
            <li>Verify your email address (if using email registration).</li>
            <li>Complete your profile with your name and organization details.</li>
          </ol>
          <Callout type="info" title="OAuth Benefits">
            Signing up with GitHub or GitLab automatically connects your repositories — no additional configuration needed.
          </Callout>
        </Step>

        <Step number="2" title="Connect a Repository">
          <P>Connect your repository to start scanning. DevArchAI supports GitHub, GitLab, and Bitbucket.</P>
          <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
            <li>Go to the <strong>Repositories</strong> page from the sidebar.</li>
            <li>Click <strong>Import Repository</strong>.</li>
            <li>Select your provider and authorize access.</li>
            <li>Choose the repositories you want to scan.</li>
          </ol>
        </Step>

        <Step number="3" title="Run a Scan">
          <P>Once your repository is connected, you can run a security scan.</P>
          <CodeBlock code={`# Trigger a scan via the dashboard\n1. Navigate to the repository you want to scan\n2. Click "Scan Now"\n3. Wait for the scan to complete (typically 30-120 seconds)`} />
          <P>You can also scan a public repository without an account by entering its URL on the scan page.</P>
        </Step>

        <Step number="4" title="Review Findings">
          <P>After the scan completes, review the findings in the <strong>Security Findings</strong> page. Each finding includes:</P>
          <Ul>
            <li><strong>Severity level</strong> — Critical, High, Medium, Low, or Info</li>
            <li><strong>Description</strong> — What the issue is and why it matters</li>
            <li><strong>Location</strong> — The exact file and line number</li>
            <li><strong>Remediation</strong> — How to fix the issue</li>
          </Ul>
        </Step>

        <Step number="5" title="Generate a PDF Report">
          <P>Export your scan results as a professional PDF report for compliance, auditing, or sharing with your team.</P>
          <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
            <li>Open a completed scan result.</li>
            <li>Click <strong>Export PDF</strong> in the top-right corner.</li>
            <li>The report includes executive summary, findings breakdown, severity distribution, and remediation recommendations.</li>
          </ol>
        </Step>

        <Step number="6" title="Create a Fix PR">
          <P>DevArchAI can automatically create pull requests with fixes for detected issues.</P>
          <ol className="list-decimal pl-5 space-y-1 text-sm text-muted-foreground">
            <li>Navigate to the <strong>AI Suggestions</strong> page.</li>
            <li>Review the suggested fixes for each finding.</li>
            <li>Click <strong>Create Fix PR</strong> to open a pull request with the proposed changes.</li>
            <li>Review the PR in your repository and merge it.</li>
          </ol>
          <Callout type="warning" title="Review Before Merging">
            Always review AI-generated fixes before merging. While the suggestions are designed to be accurate, they should be validated in your specific context.
          </Callout>
        </Step>
      </Steps>
    </>
  )
}

export function RepositoryScanningContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI scans your infrastructure-as-code repositories to detect security vulnerabilities, misconfigurations, and compliance violations. The scanner supports a wide range of file formats and infrastructure tools.</P>

      <H2 id="supported-formats">Supported Formats</H2>
      <P>DevArchAI can analyze the following file types and configurations:</P>
      <Table
        headers={['Format', 'File Types', 'What We Check']}
        rows={[
          ['Terraform', '*.tf, *.tfvars, *.tfstate', 'IAM policies, security groups, encryption, network ACLs'],
          ['Kubernetes', '*.yaml, *.yml', 'Pod security contexts, RBAC, network policies, secrets'],
          ['Docker', 'Dockerfile', 'Root user, exposed ports, secret injection, base images'],
          ['GitHub Actions', '.github/workflows/*.yml', 'Token exposure, script injection, permissions'],
          ['GitLab CI', '.gitlab-ci.yml', 'Secret exposure, runner security, job permissions'],
          ['Jenkins', 'Jenkinsfile', 'Credential usage, agent security, script approval'],
          ['CloudFormation', '*.json, *.yaml, *.yml', 'IAM policies, encryption, security groups'],
          ['Helm', 'Chart.yaml, templates/', 'Default credentials, RBAC, container security'],
        ]}
      />

      <H2 id="scan-triggers">Scan Triggers</H2>
      <P>Scans can be triggered in several ways:</P>
      <Ul>
        <li><strong>Manual</strong> — Click "Scan Now" on any connected repository</li>
        <li><strong>Webhook</strong> — Automatic scan on push or pull request (requires webhook configuration)</li>
        <li><strong>Scheduled</strong> — Recurring scans configured in repository settings</li>
      </Ul>

      <H2 id="scan-results">Understanding Scan Results</H2>
      <P>Each scan produces a comprehensive report including:</P>
      <Ul>
        <li><strong>Security Score</strong> — A numerical score (0-100) representing overall security posture</li>
        <li><strong>Findings</strong> — Individual issues grouped by severity</li>
        <li><strong>AI Recommendations</strong> — Automated fix suggestions with confidence scores</li>
        <li><strong>Category Breakdown</strong> — Issues categorized by type (IAM, Networking, Encryption, etc.)</li>
      </Ul>
    </>
  )
}

export function AwsIntegrationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>Connect your AWS account to DevArchAI for comprehensive scanning of your cloud infrastructure. The integration scans IAM policies, EC2 instances, EKS clusters, S3 buckets, Lambda functions, and more.</P>

      <Callout type="info" title="Prerequisites">
        You need an AWS account with permissions to create IAM roles. Admin or SecurityAudit access is recommended.
      </Callout>

      <H2 id="supported-services">Supported Services</H2>
      <P>DevArchAI scans the following AWS services:</P>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 my-4">
        {['IAM', 'EC2', 'EKS', 'S3', 'Lambda', 'RDS', 'VPC', 'CloudTrail', 'SecurityHub'].map((s) => (
          <div key={s} className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-foreground text-center">{s}</div>
        ))}
      </div>

      <H2 id="connection-methods">Connection Methods</H2>
      <P>There are two ways to connect your AWS account. OIDC is recommended for production environments.</P>

      <H3 id="method-1-iam-role">Method 1: IAM Role + External ID</H3>
      <P>This method uses cross-account IAM roles with an External ID for secure access.</P>
      <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">
        <li>Go to the <strong>Integrations</strong> page and click <strong>Connect AWS</strong>.</li>
        <li>Copy the provided <strong>External ID</strong> (unique to your integration).</li>
        <li>In your AWS account, create a new IAM role with the following trust policy:</li>
      </ol>
      <CodeBlock lang="json" code={`{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT_ID:root"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "YOUR_EXTERNAL_ID"
        }
      }
    }
  ]
}`} />
      <P>Attach the <strong>SecurityAudit</strong> and <strong>ReadOnlyAccess</strong> managed policies to the role.</P>

      <H3 id="method-2-oidc">Method 2: OIDC (Recommended)</H3>
      <P>OIDC provides more secure, temporary credentials without managing long-lived keys.</P>
      <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">
        <li>In your AWS account, create an OIDC identity provider pointing to DevArchAI's issuer URL.</li>
        <li>Create an IAM role with the OIDC provider as a trust entity.</li>
        <li>Attach the required permission policies to the role.</li>
        <li>Enter the IAM Role ARN in the DevArchAI integration form.</li>
      </ol>
      <Callout type="success" title="Why OIDC?">
        OIDC eliminates the need to manage static credentials. Tokens are short-lived and automatically rotated.
      </Callout>

      <H2 id="required-fields">Required Fields</H2>
      <Table
        headers={['Field', 'Description', 'Example']}
        rows={[
          ['AWS Account ID', 'Your 12-digit AWS account number', '123456789012'],
          ['IAM Role ARN', 'The ARN of the IAM role to assume', 'arn:aws:iam::123456789012:role/DevArchAI-Scanner'],
          ['External ID', 'Unique identifier for cross-account access', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'],
          ['Region', 'The AWS region to scan', 'us-east-1'],
        ]}
      />

      <H2 id="validation">Validation & Testing</H2>
      <P>After entering your credentials, DevArchAI validates the connection by:</P>
      <Ol>
        <li>Assuming the IAM role using the provided credentials</li>
        <li>Calling sts:GetCallerIdentity to verify the role</li>
        <li>Performing a test scan of your account's resources</li>
      </Ol>

      <H2 id="common-errors">Common Errors</H2>
      <Expandable title="Invalid IAM Role ARN">
        <P>Ensure the ARN format is correct: <code className="text-primary">arn:aws:iam::123456789012:role/DevArchAI-Scanner</code>. The account ID in the ARN must match the AWS Account ID field.</P>
      </Expandable>
      <Expandable title="Access Denied">
        <P>The IAM role must have a trust policy that allows DevArchAI's AWS account to assume it. Verify the External ID matches exactly.</P>
      </Expandable>
      <Expandable title="Region Not Supported">
        <P>DevArchAI supports all commercial AWS regions. Government regions (us-gov-*) and China regions (cn-*) are not supported.</P>
      </Expandable>
    </>
  )
}

export function KubernetesIntegrationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        DevArchAI connects to <strong>live Kubernetes clusters</strong> for health monitoring, security analysis,
        upgrade readiness analysis, version advisory, and AI copilot troubleshooting. Connect from the <a href="/integrations" className="text-primary hover:underline">Web UI Integrations</a> page
        or the <code className="text-primary">devsec k8s</code> CLI — both use the same backend connection records.
      </P>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-4">
        {['Local / On-Prem', 'Amazon EKS', 'Azure AKS*', 'Google GKE*'].map((s) => (
          <div key={s} className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-foreground text-center">{s}</div>
        ))}
      </div>
      <Callout type="info" title="* AKS / GKE">
        AKS and GKE managed-connect APIs are coming soon. You can connect AKS/GKE clusters today via kubeconfig
        (<code className="text-primary">devsec k8s config --kubeconfig</code>).
      </Callout>

      <H2 id="architecture">Architecture & Data Flow</H2>
      <P>All cluster access is <strong>backend-mediated</strong>. The CLI and Web UI never talk to the Kubernetes API directly.</P>
      <CodeBlock code={`┌─────────────┐     ┌─────────────┐
│  Web UI     │     │  devsec CLI │
│ /kubernetes │     │  devsec k8s │
└──────┬──────┘     └──────┬──────┘
       │                   │
       └─────────┬─────────┘
                 ▼
       ┌─────────────────────┐
       │  DevArchAI Backend   │
       │  /api/v1/kubernetes  │
       └──────────┬──────────┘
                  ▼
       ┌─────────────────────┐
       │  Kubernetes API      │
       │  (your cluster)      │
       └─────────────────────┘`} />
      <Ul>
        <li>Kubeconfigs are encrypted at rest — never returned to the browser or CLI</li>
        <li>Connections are stored per-user in the backend database (single source of truth)</li>
        <li>AI analysis runs via Celery/background workers — results sync to both CLI and Web UI</li>
      </Ul>

      <H2 id="prerequisites">Prerequisites</H2>
      <Ul>
        <li>A DevArchAI account with an API key (CLI) or web session (UI)</li>
        <li>A reachable Kubernetes cluster (kind, minikube, on-prem, or cloud-managed)</li>
        <li>A kubeconfig with read permissions (list nodes, pods, deployments, services, events)</li>
        <li>For EKS: an active <a href="/docs/aws-integration" className="text-primary hover:underline">AWS connection</a> in DevArchAI</li>
      </Ul>

      <H2 id="web-ui-connect">Web UI: Connect a Cluster</H2>

      <H3 id="web-ui-step-1">Step 1: Open Integrations</H3>
      <Ol>
        <li>Sign in at <a href="/login" className="text-primary hover:underline">devarchai.xyz</a></li>
        <li>Navigate to <a href="/integrations" className="text-primary hover:underline">Integrations</a> in the sidebar</li>
        <li>Find the <strong>Kubernetes</strong> card under the Containers category</li>
      </Ol>

      <H3 id="web-ui-step-2">Step 2: Connect Kubernetes</H3>
      <Ol>
        <li>Click <strong>Connect</strong> on the Kubernetes card</li>
        <li>Enter a connection name (e.g. <code className="text-primary">production-hyd</code>)</li>
        <li>Upload your kubeconfig file or paste the YAML contents</li>
        <li>Optionally specify a context name if your kubeconfig has multiple contexts</li>
        <li>Click <strong>Test Connection</strong> to validate before saving</li>
        <li>Click <strong>Connect</strong> to register the cluster</li>
      </Ol>
      <Callout type="warning" title="Security">
        DevArchAI never displays tokens, client keys, certificates, or kubeconfig secrets in the UI.
        Only cluster metadata (name, version, node count) is shown after connection.
      </Callout>

      <H3 id="web-ui-step-3">Step 3: View Cluster Dashboard</H3>
      <Ol>
        <li>Go to <a href="/kubernetes" className="text-primary hover:underline">Kubernetes</a> in the sidebar</li>
        <li>Click your connected cluster to open the detail page</li>
        <li>Explore tabs: Overview, Nodes, Pods, Events, Security, Version, AI Analysis</li>
      </Ol>

      <H3 id="web-ui-step-4">Step 4: Run Analysis</H3>
      <P>From the cluster detail page you can:</P>
      <Ul>
        <li><strong>Refresh</strong> — collect latest cluster snapshot</li>
        <li><strong>Health Check</strong> — re-validate API connectivity and permissions</li>
        <li><strong>Security Scan</strong> — run the Kubernetes security engine</li>
        <li><strong>Versions → Analyze Upgrade</strong> — full upgrade readiness analysis (API compatibility, CRDs, upgrade path, what could break)</li>
        <li><strong>AI Analysis → Run Copilot</strong> — evidence-based cluster health and recommendations (runs in background)</li>
        <li><strong>AI Analysis → Troubleshooting</strong> — ask natural-language questions (e.g. &quot;why is payment-api failing?&quot;)</li>
      </Ul>

      <H2 id="cli-connect">CLI: Connect a Cluster</H2>

      <H3 id="cli-step-1">Step 1: Install & Authenticate</H3>
      <CodeBlock lang="bash" code={`pip install devsec
devsec auth login --api-key sk-your-key-here
devsec auth status`} />

      <H3 id="cli-step-2">Step 2: Connect via Kubeconfig</H3>
      <CodeBlock lang="bash" code={`# Connect local or on-premises cluster
devsec k8s config --kubeconfig ~/.kube/config --name my-cluster

# Specify a context (optional)
devsec k8s config \\
  --kubeconfig ~/.kube/config \\
  --context production \\
  --name production-hyd`} />
      <P>Expected validation output:</P>
      <CodeBlock code={`✓ Kubeconfig detected
✓ Context validated
✓ Kubernetes API reachable
✓ Authentication successful
✓ Permissions validated
✓ Cluster discovered

Cluster: production-hyd
  Version: v1.30.0
  Nodes: 4`} />

      <H3 id="cli-step-3">Step 3: Verify Connection</H3>
      <CodeBlock lang="bash" code={`# List all connected clusters
devsec k8s list

# Check connection status
devsec k8s status

# Run diagnostics
devsec k8s doctor`} />

      <H3 id="cli-step-4">Step 4: Inspect & Analyze</H3>
      <CodeBlock lang="bash" code={`# Cluster overview
devsec k8s inspect

# Health score (from backend evidence engine)
devsec k8s health

# Security scan
devsec k8s security

# Version upgrade advisor (baseline)
devsec k8s version
devsec k8s advisor --target v1.34

# Full upgrade readiness analysis (background job)
devsec k8s upgrade analyze --target v1.34 --wait

# AI copilot analysis (background job)
devsec k8s troubleshoot --watch

# AI troubleshooting with a specific question
devsec k8s troubleshoot "why is payment-api failing?" --watch`} />

      <H2 id="cli-commands">CLI Commands Reference</H2>
      <Table
        headers={['Command', 'Description']}
        rows={[
          ['devsec k8s config --kubeconfig <path>', 'Connect via kubeconfig (local/on-prem)'],
          ['devsec k8s connect --type eks', 'Connect Amazon EKS cluster'],
          ['devsec k8s connect --type aks', 'AKS (not yet available — use kubeconfig)'],
          ['devsec k8s connect --type gke', 'GKE (not yet available — use kubeconfig)'],
          ['devsec k8s list', 'List connected clusters'],
          ['devsec k8s status [cluster]', 'Show connection status'],
          ['devsec k8s inspect [cluster]', 'Cluster overview dashboard'],
          ['devsec k8s health [cluster]', 'Health score from backend'],
          ['devsec k8s security [cluster]', 'Run security scan'],
          ['devsec k8s nodes [cluster]', 'List nodes'],
          ['devsec k8s pods [cluster] [-n ns]', 'List pods'],
          ['devsec k8s workloads [cluster]', 'List deployments'],
          ['devsec k8s services [cluster]', 'List services'],
          ['devsec k8s events [cluster]', 'List cluster events'],
          ['devsec k8s version [cluster] [--target v1.34]', 'Version upgrade advisor (baseline)'],
          ['devsec k8s advisor [cluster] [--target v1.34]', 'Alias for version; --target shows per-version impact'],
          ['devsec k8s upgrade analyze [--target v1.34] [--wait]', 'Full upgrade readiness analysis (async job)'],
          ['devsec k8s troubleshoot [question] [--watch]', 'AI copilot or troubleshooting with optional question'],
          ['devsec k8s analyze [--wait]', 'Alias for troubleshoot (copilot mode)'],
          ['devsec k8s doctor [--kubeconfig <path>]', 'Diagnostic checks'],
          ['devsec k8s disconnect <cluster>', 'Remove connection'],
        ]}
      />
      <Callout type="info" title="Alias">
        <code className="text-primary">devsec kubernetes</code> is an alias for <code className="text-primary">devsec k8s</code>.
        All commands support <code className="text-primary">--json</code> for scripting.
      </Callout>

      <H2 id="eks-integration">Amazon EKS</H2>
      <P>EKS uses your existing DevArchAI AWS connection — no additional AWS credentials needed.</P>
      <Steps>
        <Step number="1" title="Connect AWS (if not already)">
          <P>Follow the <a href="/docs/aws-integration" className="text-primary hover:underline">AWS Integration guide</a> to connect your AWS account via the Integrations page.</P>
        </Step>
        <Step number="2" title="Discover EKS clusters">
          <CodeBlock lang="bash" code={`# CLI: list available EKS clusters
devsec k8s connect --type eks --region us-east-1
# Shows available clusters if --cluster-name is omitted`} />
        </Step>
        <Step number="3" title="Connect EKS cluster">
          <CodeBlock lang="bash" code={`devsec k8s connect --type eks \\
  --region us-east-1 \\
  --cluster-name production-eks \\
  --name prod-eks`} />
          <P>Or use the Web UI: Integrations → EKS → select region and cluster.</P>
        </Step>
      </Steps>

      <H2 id="aks-gke">Azure AKS & Google GKE</H2>
      <Callout type="warning" title="Coming Soon">
        Managed AKS and GKE connect APIs are not yet available. Attempting{' '}
        <code className="text-primary">devsec k8s connect --type aks</code> or{' '}
        <code className="text-primary">--type gke</code> returns an honest &quot;not yet available&quot; message.
      </Callout>
      <P><strong>Workaround today:</strong> export your AKS/GKE kubeconfig and connect via kubeconfig:</P>
      <CodeBlock lang="bash" code={`# AKS
az aks get-credentials --resource-group myRG --name myAKSCluster
devsec k8s config --kubeconfig ~/.kube/config --name my-aks

# GKE
gcloud container clusters get-credentials my-gke --zone us-central1-a
devsec k8s config --kubeconfig ~/.kube/config --name my-gke`} />

      <H2 id="cli-web-sync">CLI ↔ Web UI Synchronization</H2>
      <P>Connections are stored in the <strong>backend database</strong> — not in local CLI files.</P>
      <Table
        headers={['Action', 'CLI', 'Web UI', 'Synced?']}
        rows={[
          ['Connect cluster', 'devsec k8s config', 'Integrations → Connect', '✓ Immediately'],
          ['List clusters', 'devsec k8s list', '/kubernetes page', '✓ Same data'],
          ['Security scan', 'devsec k8s security', 'Cluster → Security tab', '✓ Same engine'],
          ['Upgrade analysis', 'devsec k8s upgrade analyze --wait', 'Cluster → Versions → Analyze Upgrade', '✓ Same job'],
          ['AI copilot', 'devsec k8s troubleshoot --watch', 'Cluster → AI Analysis → Run Copilot', '✓ Same job'],
          ['AI troubleshoot', 'devsec k8s troubleshoot "question" --watch', 'Cluster → AI Analysis → Investigate', '✓ Same job'],
          ['Disconnect', 'devsec k8s disconnect', 'Integrations → Manage', '✓ Immediately'],
        ]}
      />
      <Callout type="success" title="Single source of truth">
        Connect a cluster via CLI → it appears in the Web UI instantly. Connect via Web UI → visible in{' '}
        <code className="text-primary">devsec k8s list</code> immediately.
      </Callout>

      <H2 id="api-endpoints">API Endpoints</H2>
      <P>All endpoints are under <code className="text-primary">/api/v1/kubernetes</code>. Authenticate with Bearer token or API key.</P>
      <Table
        headers={['Method', 'Endpoint', 'Purpose']}
        rows={[
          ['POST', '/kubernetes/connect', 'Connect via kubeconfig'],
          ['POST', '/kubernetes/test', 'Validate kubeconfig without saving'],
          ['GET', '/kubernetes/connections', 'List connections'],
          ['DELETE', '/kubernetes/connections/{id}', 'Disconnect'],
          ['POST', '/kubernetes/connections/{id}/validate', 'Re-validate connection'],
          ['POST', '/kubernetes/connections/{id}/refresh', 'Refresh cluster snapshot'],
          ['GET', '/kubernetes/connections/{id}/overview', 'Dashboard overview'],
          ['GET', '/kubernetes/connections/{id}/nodes', 'List nodes'],
          ['GET', '/kubernetes/connections/{id}/pods', 'List pods'],
          ['GET', '/kubernetes/connections/{id}/health-score', 'Health score'],
          ['POST', '/kubernetes/connections/{id}/security-scan', 'Security scan'],
          ['GET', '/kubernetes/connections/{id}/version-advisor?target_version=', 'Version advisor (optional per-version detail)'],
          ['POST', '/kubernetes/connections/{id}/upgrade-analysis', 'Start upgrade readiness analysis'],
          ['GET', '/kubernetes/connections/{id}/upgrade-analysis/{job_id}', 'Poll upgrade analysis job'],
          ['POST', '/kubernetes/connections/{id}/ai-analysis', 'Start AI copilot or troubleshoot ({ question, analysis_type })'],
          ['GET', '/kubernetes/connections/{id}/ai-analysis/latest', 'Latest AI analysis job'],
          ['GET', '/kubernetes/connections/{id}/ai-analysis/{job_id}', 'Poll AI analysis job'],
          ['GET', '/kubernetes/eks/aws-available', 'Check AWS connection for EKS'],
          ['GET', '/kubernetes/eks/clusters?region=', 'Discover EKS clusters'],
          ['POST', '/kubernetes/eks/connect', 'Connect EKS cluster'],
        ]}
      />

      <H2 id="security">Security</H2>
      <Ul>
        <li>Kubeconfigs are encrypted at rest using DevArchAI&apos;s encryption service</li>
        <li>Credentials are never logged, returned to the browser, or sent to the LLM</li>
        <li>Default cluster analysis is <strong>read-only</strong> (list/get permissions only)</li>
        <li>RBAC permissions are validated and reported during connection</li>
        <li>Kubernetes Secret values are never collected or exposed</li>
      </Ul>

      <H2 id="troubleshooting">Troubleshooting</H2>
      <Expandable title="Connection test fails">
        <P>Run <code className="text-primary">devsec k8s doctor --kubeconfig ~/.kube/config</code> to diagnose kubeconfig, API reachability, and permissions.</P>
      </Expandable>
      <Expandable title="Cluster not visible in Web UI after CLI connect">
        <P>Refresh the <a href="/kubernetes" className="text-primary hover:underline">Kubernetes</a> page. Connections are backend-stored and should appear immediately. Verify with <code className="text-primary">devsec k8s list --json</code>.</P>
      </Expandable>
      <Expandable title="AI or upgrade analysis stuck on 'queued'">
        <P>Analysis jobs run via background workers. In development, ensure the backend is running. Retry AI copilot with <code className="text-primary">devsec k8s troubleshoot --watch</code>, upgrade analysis with <code className="text-primary">devsec k8s upgrade analyze --target v1.34 --wait</code>, or click the action again in the Web UI.</P>
      </Expandable>
      <Expandable title="EKS: No AWS connection found">
        <P>Connect AWS first via the <a href="/integrations" className="text-primary hover:underline">Integrations</a> page before connecting EKS clusters.</P>
      </Expandable>
    </>
  )
}

export function AzureIntegrationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>Connect your Azure subscription to scan resources including virtual machines, storage accounts, databases, and identity configurations.</P>

      <H2 id="prerequisites">Prerequisites</H2>
      <Ul>
        <li>An Azure subscription with Contributor or Reader access</li>
        <li>Permission to create App Registrations (for Service Principal method)</li>
        <li>Azure Entra ID access (for Entra ID method)</li>
      </Ul>

      <H2 id="connection-methods">Connection Methods</H2>

      <H3 id="method-1-service-principal">Method 1: Service Principal</H3>
      <P>Create an Azure AD application and service principal for programmatic access.</P>
      <CodeBlock lang="bash" code={`# Create a service principal with Azure CLI
az ad sp create-for-rbac --name "DevArchAI-Scanner" --role Reader --scope /subscriptions/YOUR_SUBSCRIPTION_ID`} />
      <P>This outputs the Tenant ID, Client ID, and Client Secret you need to enter in DevArchAI.</P>

      <H3 id="method-2-entra-id">Method 2: Entra ID (Recommended)</H3>
      <P>Use Azure Entra ID for passwordless, managed identity-based authentication. This eliminates the need to manage client secrets.</P>
      <Callout type="info" title="Entra ID Availability">
        Entra ID integration is available for Azure tenants with managed identity support enabled.
      </Callout>

      <H2 id="permissions-required">Permissions Required</H2>
      <Ul>
        <li><strong>Reader</strong> role on the subscription (minimum)</li>
        <li><strong>Security Reader</strong> for security posture assessment</li>
        <li>Microsoft Graph <strong>User.Read</strong> for directory-level checks</li>
      </Ul>

      <H2 id="validation">Validation & Testing</H2>
      <P>After connecting, DevArchAI validates by listing resources in your subscription and scanning them against our security rules.</P>
    </>
  )
}

export function GithubIntegrationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI integrates with GitHub to scan repositories, create pull requests with fixes, and provide status checks on your commits.</P>

      <H2 id="oauth-login">OAuth Login</H2>
      <P>You can sign in to DevArchAI using your GitHub account. This automatically connects your GitHub profile and grants access to your repositories.</P>
      <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">
        <li>Click <strong>Sign in with GitHub</strong> on the login page.</li>
        <li>Authorize DevArchAI to access your GitHub account.</li>
        <li>You are redirected back to DevArchAI with your profile and repositories ready to scan.</li>
      </ol>
      <Callout type="warning" title="Required Permissions">
        DevArchAI requests read access to your repositories and write access to create pull requests. You can revoke access at any time from your GitHub settings.
      </Callout>

      <H2 id="repository-access">Repository Access</H2>
      <P>After authentication, you can import repositories for scanning:</P>
      <Ol>
        <li>Go to the <strong>Repositories</strong> page.</li>
        <li>Click <strong>Import Repository</strong> to browse your GitHub repositories.</li>
        <li>Select the repositories you want to scan and confirm.</li>
      </Ol>

      <H2 id="pull-request-creation">Pull Request Creation</H2>
      <P>DevArchAI can automatically create pull requests with security fixes. For each fixable finding, the AI generates:</P>
      <Ul>
        <li>The corrected code or configuration</li>
        <li>A descriptive PR title and body explaining the fix</li>
        <li>References to the original security finding</li>
      </Ul>

      <H2 id="scan-triggers">Scan Triggers</H2>
      <P>Configure automatic scans on GitHub events:</P>
      <Ul>
        <li><strong>Push events</strong> — Scan when code is pushed to specific branches</li>
        <li><strong>Pull request events</strong> — Scan new PRs for security issues before merging</li>
        <li><strong>Schedule</strong> — Run scans on a cron schedule</li>
      </Ul>

      <H2 id="webhooks">Webhooks</H2>
      <P>DevArchAI uses GitHub webhooks to receive real-time notifications about repository events. The webhook is automatically configured when you connect a repository.</P>
      <Table
        headers={['Event', 'Trigger', 'Action']}
        rows={[
          ['push', 'Code pushed to branch', 'Run scan on new commits'],
          ['pull_request', 'PR opened or updated', 'Run scan, add status check'],
          ['pull_request_review', 'PR reviewed', 'Update PR check status'],
        ]}
      />
    </>
  )
}

export function GitlabIntegrationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI integrates with GitLab to scan repositories, analyze CI/CD pipelines, and provide merge request comments with security findings.</P>

      <H2 id="oauth-login">OAuth Login</H2>
      <P>Sign in using your GitLab account to automatically connect your projects and pipelines.</P>
      <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">
        <li>Click <strong>Sign in with GitLab</strong> on the login page.</li>
        <li>Authorize DevArchAI to access your GitLab account.</li>
        <li>Your GitLab projects are available for scanning immediately.</li>
      </ol>

      <H2 id="merge-requests">Merge Requests</H2>
      <P>DevArchAI comments on merge requests with scan results, including:</P>
      <Ul>
        <li>Security score change summary</li>
        <li>New findings introduced by the merge request</li>
        <li>Inline code suggestions for fixing issues</li>
        <li>Pass/fail status for compliance policies</li>
      </Ul>

      <H2 id="pipeline-analysis">Pipeline Analysis</H2>
      <P>DevArchAI analyzes your <code className="text-primary">.gitlab-ci.yml</code> configuration for:</P>
      <Ul>
        <li>Secret exposure in CI/CD variables</li>
        <li>Insecure runner configurations</li>
        <li>Dependency scanning gaps</li>
        <li>Artifact security issues</li>
      </Ul>

      <H2 id="repository-scanning">Repository Scanning</H2>
      <P>Scan your GitLab repositories for infrastructure-as-code issues. DevArchAI detects Terraform, Kubernetes, Docker, and CloudFormation configurations within your projects.</P>
    </>
  )
}

export function KubernetesSecurityContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI scans Kubernetes manifests and Helm charts for security misconfigurations, privilege escalations, and compliance violations.</P>

      <H2 id="supported-resources">Supported Resources</H2>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 my-4">
        {['Pods', 'Deployments', 'StatefulSets', 'Services', 'Ingresses', 'NetworkPolicies', 'RBAC', 'Secrets', 'ConfigMaps'].map((r) => (
          <div key={r} className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-foreground text-center">{r}</div>
        ))}
      </div>

      <H2 id="checks-performed">Checks Performed</H2>
      <Table
        headers={['Category', 'Check', 'Severity']}
        rows={[
          ['Pod Security', 'Container running as root', <><SeverityBadge level="Critical" /></>],
          ['Pod Security', 'Privileged container allowed', <><SeverityBadge level="Critical" /></>],
          ['Network', 'Default deny network policy missing', <><SeverityBadge level="High" /></>],
          ['RBAC', 'Cluster-admin binding for service account', <><SeverityBadge level="Critical" /></>],
          ['Secrets', 'Environment variables with secrets', <><SeverityBadge level="High" /></>],
          ['Resources', 'Resource limits not configured', <><SeverityBadge level="Medium" /></>],
          ['Storage', 'HostPath volume mounted', <><SeverityBadge level="High" /></>],
          ['Security', 'Security context not defined', <><SeverityBadge level="Medium" /></>],
        ]}
      />

      <H2 id="best-practices">Best Practices</H2>
      <Ul>
        <li>Always set <code className="text-primary">securityContext</code> at pod and container level</li>
        <li>Use <code className="text-primary">readOnlyRootFilesystem: true</code> when possible</li>
        <li>Define <code className="text-primary">NetworkPolicy</code> to restrict ingress/egress</li>
        <li>Avoid <code className="text-primary">privileged: true</code> unless absolutely necessary</li>
        <li>Use <code className="text-primary">SeccompProfile</code> and <code className="text-primary">AppArmor</code> profiles</li>
      </Ul>
    </>
  )
}

export function TerraformSecurityContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI scans Terraform configurations for security misconfigurations, compliance violations, and infrastructure risks before deployment.</P>

      <H2 id="supported-resources">Supported Resources</H2>
      <P>DevArchAI analyzes over 100+ Terraform resource types across major providers:</P>
      <Ul>
        <li><strong>AWS Provider</strong> — S3, IAM, EC2, RDS, Lambda, VPC, KMS, WAF</li>
        <li><strong>Azure Provider</strong> — Storage, Network, Compute, SQL, Key Vault</li>
        <li><strong>GCP Provider</strong> — GCS, GKE, IAM, Cloud SQL, KMS</li>
        <li><strong>Kubernetes Provider</strong> — Pod, Service, Ingress, Namespace, RBAC</li>
      </Ul>

      <H2 id="checks-performed">Checks Performed</H2>
      <Ul>
        <li><strong>S3 bucket ACLs and policies</strong> — Public access, encryption, versioning</li>
        <li><strong>IAM policies</strong> — Wildcard actions, privilege escalation paths</li>
        <li><strong>Security groups</strong> — Open ports, 0.0.0.0/0 CIDR blocks</li>
        <li><strong>Encryption</strong> — Unencrypted EBS volumes, RDS instances, S3 buckets</li>
        <li><strong>Network ACLs</strong> — Overly permissive rules</li>
        <li><strong>State file security</strong> — Backend encryption, access controls</li>
      </Ul>

      <H2 id="compliance-frameworks">Compliance Frameworks</H2>
      <P>DevArchAI checks Terraform configurations against:</P>
      <Ul>
        <li>CIS AWS Foundations Benchmark</li>
        <li>CIS Azure Foundations Benchmark</li>
        <li>CIS Kubernetes Benchmark</li>
        <li>NIST 800-53</li>
        <li>PCI DSS</li>
        <li>SOC 2</li>
      </Ul>
    </>
  )
}

export function DockerSecurityContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI scans Dockerfiles and container configurations for security vulnerabilities and best practice violations.</P>

      <H2 id="checks-performed">Checks Performed</H2>
      <Ul>
        <li><strong>Root user</strong> — Container running as root instead of non-root user</li>
        <li><strong>Exposed ports</strong> — Unnecessary ports exposed to host network</li>
        <li><strong>Secret injection</strong> — Hardcoded secrets in build args or environment</li>
        <li><strong>Base images</strong> — Outdated or vulnerable base images</li>
        <li><strong>Layer caching</strong> — Inefficient layer ordering affecting cache</li>
        <li><strong>Privileged mode</strong> — Unnecessary Linux capabilities</li>
      </Ul>

      <H2 id="dockerfile-best-practices">Dockerfile Best Practices</H2>
      <CodeBlock lang="dockerfile" code={`# Good practice: non-root user, multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:18-alpine
RUN addgroup -g 1001 -S nodejs && \\
    adduser -S nodejs -u 1001
WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .
USER nodejs
EXPOSE 3000
CMD ["node", "server.js"]`} />
    </>
  )
}

export function CicdSecurityContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>DevArchAI analyzes CI/CD pipeline configurations across multiple platforms to detect security vulnerabilities in your automation workflows.</P>

      <H2 id="supported-platforms">Supported Platforms</H2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-4">
        {['GitHub Actions', 'GitLab CI', 'Jenkins', 'CircleCI'].map((p) => (
          <div key={p} className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm font-medium text-foreground text-center">{p}</div>
        ))}
      </div>

      <H2 id="checks-performed">Checks Performed</H2>
      <Ul>
        <li><strong>Token exposure</strong> — Hardcoded tokens in workflow files</li>
        <li><strong>Script injection</strong> — Unsanitized input in script steps</li>
        <li><strong>Permission sprawl</strong> — Overly permissive workflow permissions</li>
        <li><strong>Third-party actions</strong> — Unpinned action versions (security risk)</li>
        <li><strong>Secret leaking</strong> — Environment variables exposing secrets to logs</li>
      </Ul>
    </>
  )
}

export function AiRecommendationsContent() {
  return (
    <>
      <H2 id="overview">What is an AI Recommendation?</H2>
      <P>AI Recommendations are automatically generated fix suggestions for security findings detected during scans. Each recommendation uses a large language model trained on security best practices to propose precise, context-aware fixes.</P>

      <H2 id="scoring-methodology">Scoring Methodology</H2>
      <P>Each recommendation includes a <strong>Security Score</strong> from 0 to 100 that represents the overall security posture of the scanned infrastructure. The score is calculated based on:</P>
      <Ul>
        <li><strong>Severity distribution</strong> — Number and severity of findings</li>
        <li><strong>Risk weight</strong> — Each finding type has a predefined risk weight based on industry standards</li>
        <li><strong>Coverage</strong> — Percentage of infrastructure covered by security controls</li>
        <li><strong>Compliance</strong> — Adherence to compliance frameworks</li>
      </Ul>
      <Table
        headers={['Score Range', 'Grade', 'Meaning']}
        rows={[
          ['90-100', 'A', 'Excellent security posture'],
          ['80-89', 'B', 'Good, minor improvements needed'],
          ['70-79', 'C', 'Fair, moderate risk'],
          ['60-69', 'D', 'Poor, significant risk'],
          ['0-59', 'F', 'Critical, immediate action required'],
        ]}
      />

      <H2 id="risk-reduction">Risk Reduction Calculation</H2>
      <P>Risk reduction estimates the improvement in security score if a recommendation is applied. It is calculated by:</P>
      <Ol>
        <li>Identifying the severity of the finding being fixed</li>
        <li>Calculating the weight of the finding relative to total findings</li>
        <li>Projecting the score improvement based on historical data</li>
      </Ol>

      <H2 id="confidence-scoring">Confidence Scoring</H2>
      <P>Each recommendation has a <strong>confidence score</strong> (0.0 to 1.0) indicating how likely the fix is to be correct. Factors include:</P>
      <Ul>
        <li><strong>Pattern matching</strong> — How well the finding matches known fix patterns</li>
        <li><strong>Context similarity</strong> — Similarity to previously validated fixes</li>
        <li><strong>Code complexity</strong> — Simpler fixes have higher confidence</li>
      </Ul>

      <H2 id="effort-estimation">Estimated Effort</H2>
      <P>The estimated effort required to implement a fix is categorized as:</P>
      <Table
        headers={['Effort', 'Description', 'Typical Time']}
        rows={[
          ['Low', 'Simple configuration change', '5-15 minutes'],
          ['Medium', 'Multi-line change with verification', '15-60 minutes'],
          ['High', 'Complex refactoring required', '1-4 hours'],
        ]}
      />

      <H2 id="fix-pr-generation">Fix PR Generation</H2>
      <P>DevArchAI can automatically create a pull request with the recommended fix applied. The generation process:</P>
      <Ol>
        <li>Analyzes the finding location and context</li>
        <li>Generates the corrected code using the AI model</li>
        <li>Creates a new branch with the fix applied</li>
        <li>Opens a pull request with a descriptive title and body</li>
      </Ol>
      <Callout type="warning" title="Review Required">
        AI-generated fixes should always be reviewed by a human before merging. While DevArchAI strives for accuracy, automated fixes may not account for all edge cases in your specific infrastructure.
      </Callout>
    </>
  )
}

export function SecurityFindingsContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>Security findings are individual issues detected during scans. Each finding represents a security vulnerability, misconfiguration, or compliance violation in your infrastructure code.</P>

      <H2 id="severity-levels">Severity Levels</H2>
      <P>Findings are categorized by severity to help prioritize remediation:</P>
      <Table
        headers={['Severity', 'Color', 'Description', 'Example']}
        rows={[
          ['Critical', 'Red', 'Immediate risk, exploitable vulnerability', 'Publicly accessible S3 bucket with sensitive data'],
          ['High', 'Orange', 'Significant risk, likely exploitable', 'Container running as root'],
          ['Medium', 'Yellow', 'Moderate risk, should be addressed', 'Missing resource limits on pod'],
          ['Low', 'Blue', 'Minor risk, best practice violation', 'Missing tags on resources'],
          ['Info', 'Gray', 'Informational, no immediate risk', 'Deprecated API version in use'],
        ]}
      />

      <H2 id="scoring-methodology">Scoring Methodology</H2>
      <P>Each finding includes:</P>
      <Ul>
        <li><strong>CWE/CVE reference</strong> — Standard vulnerability identifier</li>
        <li><strong>Rule ID</strong> — DevArchAI-specific rule identifier</li>
        <li><strong>Location</strong> — File path and line number</li>
        <li><strong>Description</strong> — Human-readable explanation of the issue</li>
        <li><strong>Remediation</strong> — Step-by-step fix instructions</li>
      </Ul>

      <H2 id="remediation-workflow">Remediation Workflow</H2>
      <ol className="list-decimal pl-5 space-y-1.5 text-sm text-muted-foreground mb-4">
        <li><strong>Review</strong> — Examine the finding details to understand the issue</li>
        <li><strong>Prioritize</strong> — Focus on Critical and High severity findings first</li>
        <li><strong>Fix</strong> — Apply the recommended fix or create a Fix PR</li>
        <li><strong>Re-scan</strong> — Run a new scan to verify the fix</li>
        <li><strong>Verify</strong> — Confirm the finding no longer appears</li>
      </ol>
    </>
  )
}

export function PdfReportsContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>Generate professional PDF reports from your scan results for compliance, auditing, and stakeholder communication.</P>

      <H2 id="report-contents">Report Contents</H2>
      <P>Each PDF report includes:</P>
      <Ul>
        <li><strong>Executive Summary</strong> — High-level overview of findings</li>
        <li><strong>Security Score</strong> — Overall score with grade</li>
        <li><strong>Severity Distribution</strong> — Breakdown by severity level</li>
        <li><strong>Findings Details</strong> — Complete list of findings with descriptions</li>
        <li><strong>Remediation Recommendations</strong> — AI-generated fix suggestions</li>
        <li><strong>Compliance Mapping</strong> — Mapping to compliance frameworks</li>
      </Ul>

      <H2 id="export-formats">Export Formats</H2>
      <Ul>
        <li><strong>PDF</strong> — Professional report format (recommended)</li>
        <li><strong>JSON</strong> — Machine-readable data for integration</li>
        <li><strong>CSV</strong> — Spreadsheet-compatible format</li>
      </Ul>

      <H2 id="scheduling">Scheduled Reports</H2>
      <P>Scheduled reports are available on Pro and Enterprise plans. Configure automated weekly or monthly reports delivered via email.</P>
    </>
  )
}

export function CliContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        The <code className="text-primary">devsec</code> CLI is the production command-line client for DevArchAI.
        Install it with <code className="text-primary">pip install devsec</code>, authenticate against the hosted
        SaaS backend, register repositories as projects, and run scans from your terminal or CI — the same scans
        you see in the web app under <a href="/history" className="text-primary hover:underline">Scan History</a>.
      </P>
      <Callout type="info" title="Thin client">
        All scanning runs on <code className="text-primary">https://backend.devarchai.xyz</code>. The CLI sends API
        requests, streams backend-driven progress, and displays findings. It does not run scanners locally.
      </Callout>

      <H2 id="production-quickstart">Production quickstart</H2>
      <P>Complete setup from a fresh machine — no repository clone required:</P>
      <CodeBlock lang="bash" code={`# 1. Install (Python 3.11+)
pip install devsec
devsec --version

# 2. Confirm production defaults (no config file needed)
devsec config show

# 3. Authenticate — generate a key in the web app first (Settings → Security)
devsec auth login
devsec auth status

# 4. Register and select a project
devsec project create https://github.com/your-org/your-repo
devsec project list
devsec project select <project-id-prefix>
devsec project set-branch <project-id-prefix> main

# 5. Run a scan
devsec scan --project <project-id-prefix> --branch main

# 6. Open results in the web app (printed at the end of the scan)
#    https://www.devarchai.xyz/scans/<scan-id>
#    https://www.devarchai.xyz/history`} />

      <H2 id="prerequisites">Prerequisites</H2>
      <Ul>
        <li><strong>Python 3.11+</strong> on your machine or CI runner</li>
        <li>A DevArchAI account at <a href="https://www.devarchai.xyz" className="text-primary hover:underline">devarchai.xyz</a></li>
        <li>An API key from <a href="/settings" className="text-primary hover:underline">Settings → Security</a></li>
        <li>Network access to <code className="text-primary">https://backend.devarchai.xyz</code></li>
      </Ul>

      <Steps>
        <Step number="1" title="Install the production CLI">
          <P>Install from PyPI — works globally on any machine with Python 3.11+:</P>
          <CodeBlock lang="bash" code={`pip install devsec

# Verify installation (works from any directory)
devsec --version
devsec --help`} />
          <Callout type="success" title="Expected output">
            <code className="text-primary">devsec 0.1.2</code> (or newer) with API{' '}
            <code className="text-primary">https://backend.devarchai.xyz</code> and commands{' '}
            <code className="text-primary">auth</code>, <code className="text-primary">project</code>, and{' '}
            <code className="text-primary">scan</code>.
          </Callout>
          <P>
            Upgrade an existing install: <code className="text-primary">pip install --upgrade devsec</code>
          </P>
        </Step>

        <Step number="2" title="Configure for production">
          <P>
            Production URLs are built in — you do <strong>not</strong> need to create a config file for hosted SaaS.
            Run <code className="text-primary">devsec config show</code> to confirm:
          </P>
          <Table
            headers={['Setting', 'Production default']}
            rows={[
              ['API URL', 'https://backend.devarchai.xyz'],
              ['Frontend URL', 'https://www.devarchai.xyz'],
            ]}
          />
          <CodeBlock lang="bash" code={`devsec config show`} />
          <Callout type="warning" title="Use the backend API URL">
            The API URL must be <code className="text-primary">https://backend.devarchai.xyz</code> — not the
            marketing site (<code className="text-primary">www.devarchai.xyz</code>) and not a frontend dev port
            like <code className="text-primary">5174</code>. The CLI rejects misconfigured URLs automatically.
          </Callout>
          <P>Override only for local development or self-hosted deployments:</P>
          <CodeBlock lang="bash" code={`# Local backend + frontend (development only)
export DEVSEC_API_URL=http://localhost:8000
export DEVSEC_FRONTEND_URL=http://localhost:5174
export DEVSEC_ALLOW_HTTP=1

# Or persist in config
devsec config set api-url http://localhost:8000
devsec config set frontend-url http://localhost:5174`} />
          <P>Configuration precedence (highest wins):</P>
          <Ol>
            <li>Environment variables (<code className="text-primary">DEVSEC_API_URL</code>, <code className="text-primary">DEVSEC_API_KEY</code>)</li>
            <li>Config file at <code className="text-primary">~/.config/devsec/config.toml</code></li>
            <li>Built-in production defaults</li>
          </Ol>
        </Step>

        <Step number="3" title="Authenticate">
          <P>
            Generate an API key in the web app, then store it with the CLI. Keys start with{' '}
            <code className="text-primary">sk-</code> and are validated against the backend before being saved.
          </P>
          <Ol>
            <li>Sign in at <a href="/login" className="text-primary hover:underline">devarchai.xyz</a>.</li>
            <li>Open <a href="/settings" className="text-primary hover:underline">Settings → Security</a>.</li>
            <li>Create a new API key and copy it (shown once).</li>
            <li>Run <code className="text-primary">devsec auth login</code> and paste the key when prompted.</li>
          </Ol>
          <CodeBlock lang="bash" code={`# Interactive login (opens Settings in your browser)
devsec auth login

# Non-interactive login (CI / scripts)
devsec auth login --api-key sk-your-key-here

# Or set the key via environment variable (never commit this value)
export DEVSEC_API_KEY=sk-your-key-here

# Verify authentication
devsec auth status
devsec auth status --json`} />
          <Callout type="info" title="Credential storage">
            API keys are stored in your OS keyring when available, or in{' '}
            <code className="text-primary">~/.config/devsec/credentials.json</code> with restricted permissions.
            Tokens are never written to <code className="text-primary">config.toml</code> and are never printed in logs.
          </Callout>
        </Step>

        <Step number="4" title="Create and manage projects">
          <P>
            Projects map to repositories in the DevArchAI backend — the same records shown under{' '}
            <a href="/repositories" className="text-primary hover:underline">Repositories</a> in the web app.
            Register a repo from the CLI or select one you already connected in the UI.
          </P>
          <CodeBlock lang="bash" code={`# Register a new repository as a project
devsec project create https://github.com/your-org/your-repo

# List projects (table shows shortened IDs; use --json for full UUIDs)
devsec project list
devsec project list --json

# Show details for one project
devsec project show <project-id-prefix>

# Select the active project (stored locally in ~/.config/devsec/config.toml)
devsec project select <project-id-prefix>
devsec project current

# Set the default branch used when --branch is omitted
devsec project set-branch <project-id-prefix> main`} />
          <Callout type="warning" title="Branch is required">
            The CLI does not hardcode <code className="text-primary">main</code> or{' '}
            <code className="text-primary">master</code>. Pass <code className="text-primary">--branch</code> on each
            scan, or set a default with <code className="text-primary">devsec project set-branch</code>. When scanning
            from a local git repo, the current branch is used automatically.
          </Callout>
          <Callout type="info" title="Project ID format">
            The list table shows shortened UUIDs (e.g. <code className="text-primary">badb6f14</code>). Use that
            prefix or the full UUID from <code className="text-primary">devsec project list --json</code>.
          </Callout>
        </Step>

        <Step number="5" title="Run a scan">
          <P>
            Start a scan from a git repository, an explicit URL, or a selected project. The CLI calls{' '}
            <code className="text-primary">POST /api/v1/scan/start</code> and streams backend-driven progress.
            Completed scans appear in the web app immediately.
          </P>
          <CodeBlock lang="bash" code={`# From inside a git repo (uses origin/upstream + current branch)
cd your-repo
devsec scan

# Scan any repository URL (auto-registers if needed)
devsec scan --repo https://github.com/your-org/your-repo --branch main

# Explicit project + branch
devsec scan --project badb6f14 --branch main

# Selected project (after devsec project select)
devsec scan --branch main

# Start without waiting for completion
devsec scan --no-wait

# Inspect later
devsec scan status <scan-id>
devsec scan results <scan-id>`} />
          <P>Progress uses WebSocket (with API-key auth) and HTTP polling fallback. Technologies are detected dynamically by the backend.</P>
          <CodeBlock lang="bash" code={`# Policy gate for CI (default: --fail-on high)
devsec scan --fail-on high

# JSON output for scripting
devsec scan --json --quiet

# Skip waiting for AI recommendations
devsec scan --no-ai`} />
        </Step>

        <Step number="6" title="View results in the web app">
          <P>
            CLI scans use the same backend as the web UI. When a scan finishes, the CLI prints links to open results
            in your browser:
          </P>
          <Table
            headers={['Link', 'URL pattern', 'Description']}
            rows={[
              ['Scan detail', 'https://www.devarchai.xyz/scans/<scan-id>', 'Full results for this scan (findings, AI recommendations)'],
              ['Scan history', 'https://www.devarchai.xyz/history', 'All scans including CLI runs'],
              ['Repository results', 'https://www.devarchai.xyz/repositories/<project-id>/results', 'Latest completed scan for a project'],
            ]}
          />
          <Callout type="success" title="Same data as the UI">
            Scans started from the CLI are listed under <a href="/history" className="text-primary hover:underline">Scan History</a>{' '}
            and open on the same scan detail page as scans started from the dashboard.
          </Callout>
        </Step>

        <Step number="7" title="Scan lifecycle">
          <P>The CLI and web app share the same backend scan model. A typical flow:</P>
          <CodeBlock code={`Connect → Clone → Detect technologies → Scan → Findings → AI analysis → Results`} />
          <P>Stages and technologies come from the backend — never hardcoded in the CLI.</P>
        </Step>

        <Step number="8" title="Use in CI/CD">
          <P>Use environment variables so the pipeline never prompts for input:</P>
          <CodeBlock lang="bash" code={`export DEVSEC_API_URL=https://backend.devarchai.xyz
export DEVSEC_API_KEY=sk-your-ci-key

devsec auth status --json
devsec scan --repo https://github.com/your-org/your-repo --branch main --json --quiet --no-color --fail-on high`} />
          <P>Example GitHub Actions step:</P>
          <CodeBlock lang="yaml" code={`- name: DevArchAI security scan
  env:
    DEVSEC_API_URL: https://backend.devarchai.xyz
    DEVSEC_API_KEY: \${{ secrets.DEVSEC_API_KEY }}
  run: |
    pip install devsec
    devsec scan --repo \${{ github.server_url }}/\${{ github.repository }} --branch \${{ github.ref_name }} --json --quiet --no-color --fail-on high`} />
          <Callout type="info" title="CI detection">
            The CLI detects CI environments (<code className="text-primary">GITHUB_ACTIONS</code>,{' '}
            <code className="text-primary">GITLAB_CI</code>, <code className="text-primary">JENKINS_URL</code>, etc.)
            and avoids interactive prompts automatically.
          </Callout>
        </Step>
      </Steps>

      <H2 id="configuration-reference">Configuration Reference</H2>
      <Table
        headers={['Setting', 'Config command', 'Environment variable', 'Description']}
        rows={[
          ['API URL', 'devsec config set api-url <url>', 'DEVSEC_API_URL', 'Backend base URL (must be HTTPS in production)'],
          ['Frontend URL', 'devsec config set frontend-url <url>', 'DEVSEC_FRONTEND_URL', 'Web app URL for API key generation page'],
          ['API key', 'devsec auth login', 'DEVSEC_API_KEY', 'Authentication token (sk- prefix)'],
          ['Selected project', 'devsec project select <id>', '—', 'Stored locally in config.toml'],
          ['Allow HTTP', '—', 'DEVSEC_ALLOW_HTTP=1', 'Override HTTPS requirement for non-local URLs'],
        ]}
      />

      <H2 id="commands-reference">Commands Reference</H2>
      <Table
        headers={['Command', 'Description']}
        rows={[
          ['devsec auth login', 'Store an API key after validating with the backend'],
          ['devsec auth logout', 'Remove the locally stored credential'],
          ['devsec auth status', 'Show authentication state and current user'],
          ['devsec config show', 'Display non-secret configuration values'],
          ['devsec project create <url>', 'Register a repository URL as a project'],
          ['devsec project list', 'List registered repositories'],
          ['devsec project show <id>', 'Show project details'],
          ['devsec project select <id>', 'Set the current project (prefix or full UUID)'],
          ['devsec project set-branch <id> <branch>', 'Set default branch for scans'],
          ['devsec project current', 'Show the selected project'],
          ['devsec scan', 'Start a scan (git repo, --repo, or selected project)'],
          ['devsec scan --project <id> --branch <name>', 'Scan a specific project and branch'],
          ['devsec scan --repo <url>', 'Scan a repository URL directly'],
          ['devsec scan status <id>', 'Show scan progress'],
          ['devsec scan results <id>', 'Fetch findings for a completed scan'],
        ]}
      />

      <H2 id="k8s-commands">Kubernetes (k8s) Commands</H2>
      <P>
        Manage live Kubernetes clusters from the CLI. Connections sync with the Web UI instantly.
        See the full <a href="/docs/kubernetes-integration" className="text-primary hover:underline">Kubernetes Integration guide</a> for step-by-step setup.
      </P>
      <CodeBlock lang="bash" code={`# Connect a local cluster
devsec k8s config --kubeconfig ~/.kube/config --name my-cluster

# List, inspect, and analyze
devsec k8s list
devsec k8s inspect
devsec k8s health
devsec k8s security

# Version advisor and upgrade readiness
devsec k8s version
devsec k8s advisor --target v1.34
devsec k8s upgrade analyze --target v1.34 --wait

# AI copilot and troubleshooting
devsec k8s troubleshoot --watch
devsec k8s troubleshoot "why is payment-api failing?" --watch

# EKS (requires AWS connection in DevArchAI)
devsec k8s connect --type eks --region us-east-1 --cluster-name prod-eks`} />
      <Table
        headers={['Command', 'Description']}
        rows={[
          ['devsec k8s config --kubeconfig <path>', 'Connect via kubeconfig'],
          ['devsec k8s connect --type eks', 'Connect Amazon EKS'],
          ['devsec k8s list', 'List connected clusters'],
          ['devsec k8s status', 'Connection status'],
          ['devsec k8s inspect', 'Cluster overview'],
          ['devsec k8s health', 'Health score'],
          ['devsec k8s security', 'Security scan'],
          ['devsec k8s version [--target v1.34]', 'Version upgrade advisor'],
          ['devsec k8s advisor [--target v1.34]', 'Alias for version'],
          ['devsec k8s upgrade analyze [--target v1.34] [--wait]', 'Upgrade readiness analysis'],
          ['devsec k8s troubleshoot [question] [--watch]', 'AI copilot or troubleshooting'],
          ['devsec k8s analyze [--wait]', 'Alias for troubleshoot'],
          ['devsec k8s doctor', 'Diagnostic checks'],
          ['devsec k8s disconnect <name>', 'Remove connection'],
        ]}
      />

      <H2 id="exit-codes">Exit Codes</H2>
      <P>The CLI uses stable exit codes for CI pipelines:</P>
      <Table
        headers={['Code', 'Meaning']}
        rows={[
          ['0', 'Success — scan passed policy check'],
          ['1', 'Policy violation — findings at or above --fail-on threshold'],
          ['2', 'Usage error — invalid arguments or missing project'],
          ['3', 'Authentication error — missing or invalid API key'],
          ['4', 'API error — backend unreachable or returned an error'],
          ['5', 'Scan failure — scan did not complete successfully'],
        ]}
      />

      <H2 id="troubleshooting">Troubleshooting</H2>
      <Expandable title="No Git remote found">
        Run <code className="text-primary">devsec scan</code> inside a git repository with an origin/upstream remote, or use{' '}
        <code className="text-primary">devsec scan --repo &lt;repository-url&gt;</code>.
      </Expandable>
      <Expandable title="No project selected">
        Run <code className="text-primary">devsec project list</code>, then{' '}
        <code className="text-primary">devsec project select &lt;id-prefix&gt;</code> or{' '}
        <code className="text-primary">devsec scan --project &lt;id&gt;</code>.
        If you have only one project, <code className="text-primary">devsec scan</code> selects it automatically.
      </Expandable>
      <Expandable title="Invalid repository ID format / Expected UUID">
        The project table shows shortened IDs. Use the prefix from the table (e.g.{' '}
        <code className="text-primary">ae8f8620</code>) or the full UUID from{' '}
        <code className="text-primary">devsec project list --json</code>.
      </Expandable>
      <Expandable title="Unable to reach the API">
        Confirm the backend is running and <code className="text-primary">DEVSEC_API_URL</code> is correct.
        Test with: <code className="text-primary">curl $DEVSEC_API_URL/api/v1/health</code>
      </Expandable>
      <Expandable title="Branch not specified">
        Pass <code className="text-primary">--branch &lt;name&gt;</code> on the scan command, or run{' '}
        <code className="text-primary">devsec project set-branch &lt;id&gt; &lt;branch&gt;</code> to
        store a default. When scanning from a local git repo, the current branch is used automatically.
      </Expandable>
      <Expandable title="Could not validate credentials">
        Regenerate an API key in <a href="/settings" className="text-primary hover:underline">Settings → Security</a>{' '}
        and run <code className="text-primary">devsec auth login</code> again. Confirm{' '}
        <code className="text-primary">devsec config show</code> points to{' '}
        <code className="text-primary">https://backend.devarchai.xyz</code> (not the www frontend URL).
      </Expandable>
      <Expandable title="Scan not visible in the web app">
        CLI scans appear under <a href="/history" className="text-primary hover:underline">Scan History</a> and at{' '}
        <code className="text-primary">/scans/&lt;scan-id&gt;</code>. Ensure you are signed in with the same account
        used for <code className="text-primary">devsec auth login</code>.
      </Expandable>
      <Expandable title="Authentication failed">
        Regenerate an API key in Settings → Security and run <code className="text-primary">devsec auth login</code> again,
        or set <code className="text-primary">DEVSEC_API_KEY</code> in your environment.
      </Expandable>
      <Expandable title="API URL must use HTTPS">
        Use an <code className="text-primary">https://</code> URL for production, or set{' '}
        <code className="text-primary">DEVSEC_ALLOW_HTTP=1</code> for local development only.
      </Expandable>

      <LinkCard href="/docs/getting-started" title="Getting Started" desc="Set up your account and run your first scan in the web app" />
    </>
  )
}

export function ApiReferenceContent() {
  return (
    <>
      <H2 id="authentication">Authentication</H2>
      <P>All API requests require authentication using a Bearer token. Obtain your API key from the <LinkCard href="/settings" title="Settings → API Keys" desc="Generate and manage API keys" /></P>
      <H3 id="headers">Headers</H3>
      <CodeBlock lang="http" code={`Authorization: Bearer your_api_key_here
Content-Type: application/json`} />

      <H2 id="scans-api">Scans API</H2>
      <H3 id="trigger-scan">Trigger a Scan</H3>
      <CodeBlock lang="http" code={`POST /api/scans
Content-Type: application/json

{
  "repository_url": "https://github.com/org/repo",
  "branch": "main"
}`} />
      <CodeBlock lang="json" code={`{
  "scan_id": "scan_abc123",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z"
}`} />

      <H3 id="get-scan-results">Get Scan Results</H3>
      <CodeBlock lang="http" code={`GET /api/scans/{scan_id}`} />
      <CodeBlock lang="json" code={`{
  "scan_id": "scan_abc123",
  "status": "completed",
  "score": 72,
  "total_findings": 15,
  "findings": [
    {
      "id": "find_001",
      "severity": "critical",
      "rule_id": "TF-S3-001",
      "file_path": "modules/s3/main.tf",
      "line": 42,
      "description": "S3 bucket does not have encryption enabled"
    }
  ]
}`} />

      <H2 id="repositories-api">Repositories API</H2>
      <H3 id="list-repositories">List Repositories</H3>
      <CodeBlock lang="http" code={`GET /api/repositories`} />
      <H3 id="add-repository">Add Repository</H3>
      <CodeBlock lang="http" code={`POST /api/repositories
Content-Type: application/json

{
  "url": "https://github.com/org/repo",
  "provider": "github"
}`} />

      <H2 id="findings-api">Findings API</H2>
      <H3 id="list-findings">List Findings</H3>
      <CodeBlock lang="http" code={`GET /api/findings?scan_id=scan_abc123&severity=critical,high`} />
      <H3 id="update-finding-status">Update Finding Status</H3>
      <CodeBlock lang="http" code={`PATCH /api/findings/{finding_id}
Content-Type: application/json

{
  "status": "resolved"
}`} />

      <H2 id="reports-api">Reports API</H2>
      <H3 id="generate-report">Generate Report</H3>
      <CodeBlock lang="http" code={`POST /api/reports
Content-Type: application/json

{
  "scan_id": "scan_abc123",
  "format": "pdf"
}`} />

      <H2 id="integrations-api">Integrations API</H2>
      <H3 id="check-integration-status">Check Integration Status</H3>
      <CodeBlock lang="http" code={`GET /api/integrations/status`} />
      <H3 id="connect-aws">Connect AWS</H3>
      <CodeBlock lang="http" code={`POST /api/integrations/aws
Content-Type: application/json

{
  "account_id": "123456789012",
  "role_arn": "arn:aws:iam::123456789012:role/Scanner",
  "external_id": "your-external-id",
  "region": "us-east-1"
}`} />

      <H2 id="rate-limiting">Rate Limiting</H2>
      <P>API requests are rate-limited per API key:</P>
      <Table
        headers={['Plan', 'Rate Limit', 'Burst']}
        rows={[
          ['Free', '10 req/min', '20 req/min'],
          ['Plus', '60 req/min', '120 req/min'],
          ['Pro', '300 req/min', '600 req/min'],
          ['Enterprise', 'Custom', 'Custom'],
        ]}
      />
    </>
  )
}

export function FaqContent() {
  return (
    <>
      <H2 id="general">General</H2>
      <Expandable title="What is DevArchAI?">
        DevArchAI is a security scanning platform for infrastructure-as-code. It analyzes Terraform, Kubernetes, Docker, CI/CD pipelines, and cloud configurations to detect vulnerabilities, misconfigurations, and compliance violations.
      </Expandable>
      <Expandable title="How does the security score work?">
        The security score ranges from 0-100 and is calculated based on the number and severity of findings, coverage of security controls, and compliance with industry frameworks.
      </Expandable>

      <H2 id="scanning">Scanning</H2>
      <Expandable title="How long does a scan take?">
        Most scans complete within 30-120 seconds, depending on the repository size and number of files to analyze.
      </Expandable>
      <Expandable title="Can I scan private repositories?">
        Yes. Connect your GitHub, GitLab, or Bitbucket account and grant access to private repositories. Your credentials are securely stored.
      </Expandable>
      <Expandable title="How often should I scan?">
        We recommend scanning on every push to your default branch, or at minimum weekly. Scheduled scans are available on Pro and Enterprise plans.
      </Expandable>

      <H2 id="integrations">Integrations</H2>
      <Expandable title="Can I connect multiple AWS accounts?">
        Yes, you can connect multiple AWS accounts by adding each one individually in the Integrations page.
      </Expandable>
      <Expandable title="Does DevArchAI modify my infrastructure?">
        No. DevArchAI is read-only. It never modifies your infrastructure or code without explicit action (e.g., creating a Fix PR).
      </Expandable>

      <H2 id="security">Security</H2>
      <Expandable title="How is my data protected?">
        All data is encrypted in transit (TLS 1.3) and at rest (AES-256). API keys and secrets are stored using hardware security modules (HSM).
      </Expandable>
      <Expandable title="Can I self-host DevArchAI?">
        Enterprise plans include self-hosted deployment options. Contact sales for more information.
      </Expandable>

      <H2 id="billing">Billing</H2>
      <Expandable title="Is there a free tier?">
        Yes. The Free plan includes 3 scans per month for 1 repository. Upgrade to Plus or Pro for more capacity.
      </Expandable>
      <Expandable title="Can I cancel anytime?">
        Yes, you can cancel your subscription at any time. Your data will be retained for 30 days after cancellation.
      </Expandable>
    </>
  )
}

export function TroubleshootingContent() {
  return (
    <>
      <H2 id="aws-connection-failed">AWS Connection Failed</H2>
      <P>If AWS connection fails during setup:</P>
      <Ul>
        <li>Verify the <strong>AWS Account ID</strong> is exactly 12 digits</li>
        <li>Ensure the <strong>IAM Role ARN</strong> format is correct: <code className="text-primary">arn:aws:iam::ACCOUNT_ID:role/ROLE_NAME</code></li>
        <li>Check the IAM role trust policy includes the correct <strong>External ID</strong></li>
        <li>Verify the IAM role has <strong>SecurityAudit</strong> and <strong>ReadOnlyAccess</strong> policies attached</li>
      </Ul>
      <CodeBlock lang="bash" code={`# Test the role assumption manually
aws sts assume-role --role-arn "arn:aws:iam::123456789012:role/DevArchAI-Scanner" \\
  --role-session-name "DevArchAI-Test" \\
  --external-id "your-external-id"`} />

      <H2 id="github-oauth-failed">GitHub OAuth Failed</H2>
      <P>If GitHub login fails:</P>
      <Ul>
        <li>Clear your browser cache and cookies</li>
        <li>Ensure third-party cookies are not blocked</li>
        <li>Try a different browser (Chrome or Firefox recommended)</li>
        <li>Check that you have not revoked DevArchAI access in GitHub settings</li>
      </Ul>

      <H2 id="gitlab-oauth-failed">GitLab OAuth Failed</H2>
      <P>If GitLab login fails:</P>
      <Ul>
        <li>Verify your GitLab instance is reachable (self-managed instances may have network restrictions)</li>
        <li>Ensure DevArchAI is authorized in your GitLab applications settings</li>
        <li>Check that your GitLab account has the required permissions</li>
      </Ul>

      <H2 id="repository-scan-stuck">Repository Scan Stuck</H2>
      <P>If a scan appears stuck:</P>
      <Ul>
        <li>Try refreshing the page</li>
        <li>Cancel the scan and start a new one</li>
        <li>Check if the repository is accessible (not deleted or made private)</li>
        <li>For large repositories, scans may take several minutes</li>
      </Ul>

      <H2 id="no-findings-generated">No Findings Generated</H2>
      <P>If a scan completes with zero findings:</P>
      <Ul>
        <li>Verify the repository contains supported file types (Terraform, Kubernetes, Docker, etc.)</li>
        <li>Check that the repository has infrastructure-as-code configurations</li>
        <li>Try scanning a different branch</li>
        <li>Some configurations may genuinely have no security issues</li>
      </Ul>

      <H2 id="pdf-report-missing">PDF Report Missing</H2>
      <P>If the PDF report does not generate:</P>
      <Ul>
        <li>Ensure the scan completed successfully</li>
        <li>Try exporting in JSON or CSV format as an alternative</li>
        <li>Check your browser's download settings</li>
        <li>PDF generation may take up to 30 seconds for large scans</li>
      </Ul>

      <H2 id="fix-pr-failed">Fix PR Failed</H2>
      <P>If creating a Fix PR fails:</P>
      <Ul>
        <li>Verify the repository has been imported correctly</li>
        <li>Check that DevArchAI has write access to the repository</li>
        <li>Ensure the repository does not have branch protection rules blocking automated PRs</li>
        <li>Try creating the fix manually and pushing it</li>
      </Ul>

      <H2 id="kubernetes-connection-failed">Kubernetes Connection Failed</H2>
      <P>If connecting a Kubernetes cluster fails:</P>
      <Ul>
        <li>Run <code className="text-primary">devsec k8s doctor --kubeconfig ~/.kube/config</code> to diagnose</li>
        <li>Verify the kubeconfig has valid <code className="text-primary">clusters</code> and <code className="text-primary">contexts</code> sections</li>
        <li>Ensure the API server is reachable from the DevArchAI backend (not just your laptop)</li>
        <li>Check RBAC permissions — list nodes, pods, and namespaces are required</li>
        <li>For kind/minikube: the API server must be accessible at the address in kubeconfig</li>
      </Ul>
      <CodeBlock lang="bash" code={`# Test locally first
kubectl cluster-info
kubectl get nodes

# Then test via DevArchAI CLI
devsec k8s config --kubeconfig ~/.kube/config --name test`} />

      <H2 id="kubernetes-ai-stuck">Kubernetes AI Analysis Stuck</H2>
      <P>If AI analysis or upgrade analysis stays on &quot;queued&quot; in the Web UI or CLI:</P>
      <Ul>
        <li>Ensure the backend server is running (development) or Celery workers are active (production)</li>
        <li>Retry AI copilot: <code className="text-primary">devsec k8s troubleshoot --watch</code> or click Run Copilot again</li>
        <li>Retry upgrade analysis: <code className="text-primary">devsec k8s upgrade analyze --target v1.34 --wait</code></li>
        <li>Check backend logs for <code className="text-primary">CLUSTER_AI_JOB</code> messages</li>
        <li>Refresh the cluster page after 30–60 seconds — jobs run in background</li>
      </Ul>

      <Callout type="info" title="Need More Help?">
        Contact our support team at <strong>support@devarchai.com</strong> or use the in-app chat for real-time assistance.
      </Callout>
    </>
  )
}

export function SecretScanningContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        DevArchAI scans your repositories for hardcoded secrets, API keys, tokens, and credentials
        that should never be committed to source control. The secret scanner uses pattern matching
        and entropy analysis to detect potential secrets across your entire codebase.
      </P>

      <H2 id="supported-secrets">Supported Secret Types</H2>
      <Table
        headers={['Secret Type', 'Examples', 'Detection Method']}
        rows={[
          ['Cloud Provider Keys', 'AWS Access Key, GCP Service Account', 'Regex + Entropy'],
          ['API Tokens', 'GitHub Token, GitLab Token, Slack Token', 'Regex + Pattern'],
          ['Database Credentials', 'PostgreSQL, MySQL, MongoDB URLs', 'Pattern + Context'],
          ['Private Keys', 'SSH Keys, PGP Keys, JWT Secrets', 'Header + Entropy'],
          ['OAuth Secrets', 'Client Secret, Refresh Token', 'Regex + Pattern'],
          ['Encryption Keys', 'AES Keys, HMAC Secrets', 'Entropy + Length'],
        ]}
      />

      <H2 id="detection-methods">Detection Methods</H2>
      <P>The secret scanner uses multiple techniques to identify potential secrets:</P>
      <Ul>
        <li><strong>Regex Patterns:</strong> Predefined patterns for known secret formats (AWS, GCP, GitHub, etc.)</li>
        <li><strong>Entropy Analysis:</strong> High-entropy strings that resemble random keys or tokens</li>
        <li><strong>Context Analysis:</strong> File paths, variable names, and surrounding code to reduce false positives</li>
        <li><strong>History Scanning:</strong> Git history analysis to detect secrets in previous commits</li>
      </Ul>

      <H2 id="remediation">Remediation</H2>
      <P>When a secret is detected, DevArchAI recommends:</P>
      <Ol>
        <li>Revoke the exposed credential immediately</li>
        <li>Remove the secret from your repository history</li>
        <li>Rotate the credential and update any affected services</li>
        <li>Add a <code className="text-primary">.git-secrets</code> or <code className="text-primary">.gitleaks.toml</code> configuration to prevent future leaks</li>
      </Ol>
      <Callout type="warning" title="Important">
        Never commit secrets to source control. Use environment variables or a secret management service like AWS Secrets Manager or HashiCorp Vault.
      </Callout>
    </>
  )
}

export function DependencyScanningContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        The Dependency Scanner analyzes your project's dependencies and package manifests for
        known vulnerabilities (CVEs), outdated packages, and supply chain risks. It supports
        multiple package ecosystems and provides actionable remediation advice.
      </P>

      <H2 id="supported-ecosystems">Supported Ecosystems</H2>
      <Table
        headers={['Ecosystem', 'Files Scanned', 'Vulnerability Database']}
        rows={[
          ['npm', 'package.json, package-lock.json', 'npm Advisory + OSV'],
          ['Python', 'requirements.txt, Pipfile.lock, pyproject.toml', 'PyPI + OSV'],
          ['Go', 'go.mod, go.sum', 'Go Vulnerability DB'],
          ['Java/Maven', 'pom.xml, build.gradle', 'Maven Central + OSV'],
          ['Rust', 'Cargo.toml, Cargo.lock', 'RustSec Advisory'],
          ['Ruby', 'Gemfile, Gemfile.lock', 'Ruby Advisory'],
        ]}
      />

      <H2 id="vulnerability-detection">Vulnerability Detection</H2>
      <P>
        For each dependency, DevArchAI checks against multiple vulnerability databases to identify:
      </P>
      <Ul>
        <li><strong>Known CVEs:</strong> Publicly disclosed vulnerabilities with CVE identifiers</li>
        <li><strong>Malicious Packages:</strong> Packages identified as typosquatting or containing malware</li>
        <li><strong>Deprecated Packages:</strong> Packages that are no longer maintained or have been deprecated</li>
        <li><strong>License Violations:</strong> Packages with licenses incompatible with your project</li>
      </Ul>

      <H2 id="supply-chain-security">Supply Chain Security</H2>
      <P>
        Beyond direct dependencies, DevArchAI analyzes your transitive dependency tree to identify
        deep supply chain risks that traditional scanners might miss.
      </P>
      <Callout type="info" title="Proactive Security">
        Enable automated dependency scanning on every push to catch new vulnerabilities as soon as they are disclosed.
      </Callout>
    </>
  )
}

export function AiFixGenerationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        AI Fix Generation automatically creates remediation code for security findings detected
        during scans. Instead of manually researching and writing fixes, DevArchAI generates
        production-ready code changes that address the root cause of each finding.
      </P>

      <H2 id="how-it-works">How It Works</H2>
      <Steps>
        <Step number="1" title="Finding Detection">
          A security scan identifies a misconfiguration or vulnerability with a specific file and line number.
        </Step>
        <Step number="2" title="Context Analysis">
          The AI analyzes the finding in context — surrounding code, infrastructure type, and severity.
        </Step>
        <Step number="3" title="Fix Generation">
          Using a specialized security model, DevArchAI generates a targeted fix that resolves the issue without introducing new problems.
        </Step>
        <Step number="4" title="Review & Apply">
          Review the generated fix in the AI Suggestions panel, then apply it directly or create a Pull Request.
        </Step>
      </Steps>

      <H2 id="fix-quality">Fix Quality</H2>
      <P>Generated fixes are designed to be:</P>
      <Ul>
        <li><strong>Semantically Correct:</strong> Fixes preserve the intended behavior of your infrastructure</li>
        <li><strong>Context-Aware:</strong> Fixes adapt to your existing code style and patterns</li>
        <li><strong>Best Practice Aligned:</strong> Fixes follow industry security best practices</li>
        <li><strong>Non-Destructive:</strong> Fixes never remove functionality or break existing configurations</li>
      </Ul>

      <H2 id="supported-languages">Supported Languages</H2>
      <P>AI Fix Generation currently supports the following infrastructure types:</P>
      <Table
        headers={['Language', 'Fix Types', 'Example']}
        rows={[
          ['Terraform (HCL)', 'Security groups, encryption, logging', 'Enable S3 bucket encryption'],
          ['Kubernetes (YAML)', 'Pod security, network policies, resource limits', 'Add securityContext to pod spec'],
          ['Dockerfile', 'Base images, USER directives, HEALTHCHECK', 'Switch to distroless base image'],
          ['CloudFormation (JSON/YAML)', 'IAM policies, encryption, networking', 'Attach least-privilege IAM policy'],
          ['Helm Charts', 'Values, templates, RBAC', 'Set pod security context in values.yaml'],
        ]}
      />

      <H2 id="manual-review">Manual Review Process</H2>
      <P>
        Before applying any AI-generated fix, we recommend reviewing the change in the AI Suggestions
        panel. Each fix includes a before/after diff, an explanation of what changed and why, and
        the option to modify the fix before creating a Pull Request.
      </P>
      <Callout type="warning" title="Review Required">
        Always review AI-generated fixes before applying them to production environments. While the AI is highly accurate, infrastructure changes should always be validated.
      </Callout>
    </>
  )
}

export function PullRequestCreationContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        DevArchAI can automatically create Pull Requests (PRs) with fixes for detected security
        issues. This streamlines the remediation workflow, allowing your team to review and merge
        security fixes directly from version control.
      </P>

      <H2 id="pr-workflow">PR Workflow</H2>
      <Steps>
        <Step number="1" title="Select Findings">
          Choose the security findings you want to fix from the scan results or AI Suggestions panel.
        </Step>
        <Step number="2" title="Review Fixes">
          Review each AI-generated fix, including the before/after diff and explanation.
        </Step>
        <Step number="3" title="Create PR">
          Click "Create Fix PR" to open a Pull Request with all selected fixes.
        </Step>
        <Step number="4" title="Review & Merge">
          Your team reviews the PR in your repository and merges it when ready.
        </Step>
      </Steps>

      <H2 id="configuration">Configuration</H2>
      <P>You can configure how PRs are created in your integration settings:</P>
      <Ul>
        <li><strong>Branch Name:</strong> Customize the branch naming pattern (e.g., <code className="text-primary">devarchai/fix-{'{finding_id}'}</code>)</li>
        <li><strong>PR Title:</strong> Set a template for the PR title</li>
        <li><strong>Assignees:</strong> Automatically assign PRs to specific team members</li>
        <li><strong>Labels:</strong> Add labels like <code className="text-primary">security</code> or <code className="text-primary">automated-fix</code></li>
        <li><strong>Reviewers:</strong> Request reviews from specific users or teams</li>
      </Ul>

      <H2 id="branch-protection">Branch Protection</H2>
      <P>
        If your repository has branch protection rules, the PR may require specific checks to pass
        before it can be merged. DevArchAI will create the PR regardless, and you can work with
        your branch protection settings to allow automated fixes.
      </P>
      <Callout type="info" title="Best Practice">
        Create a dedicated <code className="text-primary">devarchai</code> team in your version control platform with write access to repositories for automated PRs.
      </Callout>

      <H2 id="pr-templates">PR Templates</H2>
      <P>Each automated PR includes a structured template with:</P>
      <Ul>
        <li>Summary of the security issue</li>
        <li>List of files changed and why</li>
        <li>Severity and impact of each finding</li>
        <li>Link back to the original scan in DevArchAI</li>
        <li>Testing instructions and rollback guidance</li>
      </Ul>
    </>
  )
}

export function ExcelReportsContent() {
  return (
    <>
      <H2 id="overview">Overview</H2>
      <P>
        In addition to PDF reports, DevArchAI can export scan results to Excel (.xlsx) format.
        Excel reports are ideal for further analysis, filtering, and integration with your existing
        reporting workflows and dashboards.
      </P>

      <H2 id="exporting">Exporting to Excel</H2>
      <P>To export an Excel report:</P>
      <Ol>
        <li>Navigate to the scan results page</li>
        <li>Click the <strong>Export</strong> button in the header</li>
        <li>Select <strong>Excel (.xlsx)</strong> from the dropdown</li>
        <li>The file will download automatically</li>
      </Ol>

      <H2 id="data-included">Data Included</H2>
      <P>The Excel report contains the following sheets:</P>
      <Table
        headers={['Sheet', 'Contents']}
        rows={[
          ['Summary', 'Overall score, grade, severity distribution, and repository info'],
          ['Findings', 'All findings with severity, category, file path, and description'],
          ['Categories', 'Score breakdown by category (security, scalability, reliability, etc.)'],
          ['Recommendations', 'AI recommendations with confidence scores and effort estimates'],
          ['DevOps Stack', 'Detected technologies and infrastructure types'],
        ]}
      />

      <H2 id="customization">Customization</H2>
      <P>
        Excel reports include all available data fields. If you need a customized report with
        specific columns or formatting, you can:
      </P>
      <Ul>
        <li>Filter and sort the Excel data using built-in spreadsheet tools</li>
        <li>Create pivot tables and charts from the raw data</li>
        <li>Use the JSON export for programmatic integration with BI tools</li>
        <li>Contact support for custom report templates on Enterprise plans</li>
      </Ul>
      <Callout type="info" title="Large Scans">
        For scans with more than 1,000 findings, the Excel report may be split into multiple sheets to maintain performance.
      </Callout>
    </>
  )
}

export const PAGE_CONTENT: Record<string, React.FC> = {
  'getting-started': GettingStartedContent,
  'repository-scanning': RepositoryScanningContent,
  'secret-scanning': SecretScanningContent,
  'dependency-scanning': DependencyScanningContent,
  'aws-integration': AwsIntegrationContent,
  'kubernetes-integration': KubernetesIntegrationContent,
  'azure-integration': AzureIntegrationContent,
  'github-integration': GithubIntegrationContent,
  'gitlab-integration': GitlabIntegrationContent,
  'kubernetes-security': KubernetesSecurityContent,
  'terraform-security': TerraformSecurityContent,
  'docker-security': DockerSecurityContent,
  'cicd-security': CicdSecurityContent,
  'ai-recommendations': AiRecommendationsContent,
  'ai-fix-generation': AiFixGenerationContent,
  'pull-request-creation': PullRequestCreationContent,
  'security-findings': SecurityFindingsContent,
  'pdf-reports': PdfReportsContent,
  'excel-reports': ExcelReportsContent,
  'cli': CliContent,
  'api-reference': ApiReferenceContent,
  'faq': FaqContent,
  'troubleshooting': TroubleshootingContent,
}
