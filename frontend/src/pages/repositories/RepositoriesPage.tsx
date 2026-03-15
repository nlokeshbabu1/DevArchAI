import { motion } from 'framer-motion'
import { Plus, Github, Gitlab, Cloud, Server } from 'lucide-react'
import { Button, Card, RepositoryCard } from '../../components/ui-animated'

const repositories = [
  {
    name: 'aws-infrastructure',
    description: 'Main AWS infrastructure Terraform code',
    lastScan: '2 hours ago',
    score: 87.5,
    status: 'scanned' as const,
  },
  {
    name: 'kubernetes-manifests',
    description: 'K8s deployment configurations',
    lastScan: '1 day ago',
    score: 72.3,
    status: 'scanned' as const,
  },
  {
    name: 'ci-cd-pipelines',
    description: 'GitHub Actions workflows',
    lastScan: undefined,
    score: undefined,
    status: 'pending' as const,
  },
  {
    name: 'docker-services',
    description: 'Docker Compose services',
    lastScan: '3 days ago',
    score: 91.2,
    status: 'scanned' as const,
  },
]

export function RepositoriesPage() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <motion.div 
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div>
          <h1 className="text-3xl font-bold text-foreground">Repositories</h1>
          <p className="text-muted-foreground mt-1">
            Manage and scan your connected repositories
          </p>
        </div>
        <Button variant="primary" icon={<Plus className="h-4 w-4" />}>
          Add Repository
        </Button>
      </motion.div>

      {/* Integration Cards */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        {[
          { name: 'GitHub', icon: Github, connected: true },
          { name: 'GitLab', icon: Gitlab, connected: false },
          { name: 'AWS', icon: Cloud, connected: true },
          { name: 'Azure', icon: Server, connected: false },
        ].map((integration) => (
          <Card key={integration.name} className="p-4" hover>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <integration.icon className="h-6 w-6 text-muted-foreground" />
                <span className="font-medium">{integration.name}</span>
              </div>
              <div className={cn(
                'px-2 py-1 rounded-full text-xs font-medium',
                integration.connected 
                  ? 'bg-green-500/15 text-green-400 border border-green-500/30' 
                  : 'bg-white/5 text-muted-foreground border border-white/10'
              )}>
                {integration.connected ? 'Connected' : 'Connect'}
              </div>
            </div>
          </Card>
        ))}
      </motion.div>

      {/* Repositories Grid */}
      <motion.div
        className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {repositories.map((repo, index) => (
          <motion.div
            key={repo.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 + index * 0.1 }}
          >
            <RepositoryCard
              {...repo}
              onScan={() => console.log('Scan', repo.name)}
              onView={() => console.log('View', repo.name)}
            />
          </motion.div>
        ))}
      </motion.div>
    </div>
  )
}

function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(' ')
}
