import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { DetectionCoverage } from '../scan-results/DetectionCoverage'

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    span: ({ children, ...props }: any) => <span {...props}>{children}</span>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}))

vi.mock('../../lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
  getSeverityColor: () => ({ bg: 'bg-gray', text: 'text-gray' }),
}))

vi.mock('lucide-react', () => Object.fromEntries(
  [
    'Shield', 'Cloud', 'Server', 'GanttChartSquare', 'Globe', 'Lock', 'Package2',
    'CheckCircle2', 'AlertCircle', 'HelpCircle', 'XCircle', 'Layers',
    'ChevronDown', 'ChevronRight',
  ].map(name => [
    name,
    (props: any) => <span data-testid={`icon-${name}`} {...props}>{name}</span>,
  ]),
))

const backendDetails = [
  {
    technology: 'kubernetes',
    files_count: 4,
    findings_count: 22,
    total_findings: 22,
    severity_counts: { critical: 0, high: 2, medium: 1, low: 0, info: 19 },
    status: 'DETECTED',
  },
  {
    technology: 'helm',
    files_count: 11,
    findings_count: 0,
    total_findings: 0,
    severity_counts: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
    status: 'DETECTED',
  },
]

const findings = [
  ...Array.from({ length: 19 }, (_, i) => ({
    id: `k8s-info-${i}`,
    technology: 'kubernetes',
    severity: 'info',
    file_path: '/kubernetes/Backend/backend-deployemt.yaml',
    scanner_name: 'Checkov',
  })),
  { id: 'k8s-h1', technology: 'kubernetes', severity: 'high', file_path: '/kubernetes/Backend/backend-deployemt.yaml', scanner_name: '' },
  { id: 'k8s-h2', technology: 'kubernetes', severity: 'high', file_path: '/kubernetes/DB-Service/statefullset.yaml', scanner_name: '' },
  { id: 'k8s-m1', technology: 'kubernetes', severity: 'medium', file_path: '/kubernetes/Backend/backend-deployemt.yaml', scanner_name: '' },
]

describe('DetectionCoverage aggregation', () => {
  test('kubernetes card shows server findings total and full severity breakdown incl. info', () => {
    render(
      <DetectionCoverage
        findings={findings}
        detectedTechnologies={['kubernetes', 'docker']}
        technologyDetails={backendDetails}
      />,
    )

    const k8sCard = screen.getByText('Kubernetes').closest('div.rounded-xl')!
    expect(k8sCard).toHaveTextContent('4 files')
    expect(k8sCard).toHaveTextContent('22 findings')
    expect(k8sCard).toHaveTextContent('2 high')
    expect(k8sCard).toHaveTextContent('1 medium')
    expect(k8sCard).toHaveTextContent('19 info')
  })

  test('card displayed totals equal sum of displayed severity badges', () => {
    render(
      <DetectionCoverage
        findings={findings}
        detectedTechnologies={['kubernetes']}
        technologyDetails={backendDetails}
      />,
    )

    const k8sCard = screen.getByText('Kubernetes').closest('div.rounded-xl')!
    const badgeSum = ['2 high', '1 medium', '19 info']
      .map(t => parseInt(t, 10))
      .reduce((a, b) => a + b, 0)
    expect(badgeSum).toBe(22)
    expect(k8sCard).toHaveTextContent('22 findings')
  })

  test('helm card with zero findings shows files and no false breakdown', () => {
    render(
      <DetectionCoverage
        findings={[]}
        detectedTechnologies={['helm']}
        technologyDetails={backendDetails}
      />,
    )

    const helmCard = screen.getByText('Helm').closest('div.rounded-xl')!
    expect(helmCard).toHaveTextContent('11 files')
    expect(helmCard).toHaveTextContent('No security issues')
    expect(helmCard).not.toHaveTextContent('finding')
  })

  test('falls back to client-side counting when backend details are missing', () => {
    render(
      <DetectionCoverage
        findings={[
          { id: 'a', severity: 'high', file_path: '.github/workflows/ci.yml', scanner_name: '' },
          { id: 'b', severity: 'info', file_path: '.github/workflows/ci.yml', scanner_name: '' },
        ]}
        detectedTechnologies={['github_actions']}
        technologyDetails={[]}
      />,
    )

    const ghaCard = screen.getByText('GitHub Actions').closest('div.rounded-xl')!
    expect(ghaCard).toHaveTextContent('2 findings')
    expect(ghaCard).toHaveTextContent('1 high')
    expect(ghaCard).toHaveTextContent('1 info')
  })
})
