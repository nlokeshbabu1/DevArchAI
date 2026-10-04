import { BookOpen } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { CloudAccounts } from '../../components/cloud/CloudAccounts'
import { PageHeader } from '../../components/ui/PageHeader'

export function AwsPage() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <PageHeader
        title="AWS Accounts"
        description="Cloud posture, IAM analysis, inventory, compliance and cost optimization — separate from repository DevSecOps security scores."
        actions={
          <>
            <button
              type="button"
              onClick={() => navigate('/docs/aws-integration')}
              className="p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-white/5 transition-colors"
              title="View AWS documentation"
              aria-label="View AWS documentation"
            >
              <BookOpen className="h-4 w-4" />
            </button>
          </>
        }
      />

      <CloudAccounts provider="aws" title="AWS" description="Connect your AWS account to scan infrastructure for security, IAM, inventory, compliance, and cost insights." />
    </div>
  )
}
