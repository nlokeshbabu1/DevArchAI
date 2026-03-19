import { useNavigate } from 'react-router-dom'
import { RepoAnalyzerInput } from '../components/RepoAnalyzerInput'
import { Sparkles, Shield, Zap, GitBranch } from 'lucide-react'
import { Card, Button } from '../components/ui'
import { cn } from '../lib/utils'

export function Home() {
  const navigate = useNavigate()
  
  const features = [
    {
      icon: Shield,
      title: 'Security Analysis',
      description: 'Detect misconfigurations, vulnerabilities, and compliance issues across your infrastructure.',
      gradient: 'from-red-500/10 to-orange-500/10',
      borderColor: 'border-red-500/30',
      iconBg: 'bg-gradient-to-br from-red-500/20 to-orange-500/20',
    },
    {
      icon: Zap,
      title: 'Performance & Scalability',
      description: 'Identify bottlenecks and ensure your infrastructure can handle production workloads.',
      gradient: 'from-blue-500/10 to-cyan-500/10',
      borderColor: 'border-blue-500/30',
      iconBg: 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20',
    },
    {
      icon: GitBranch,
      title: 'Best Practices',
      description: 'Validate against industry standards and DevOps best practices automatically.',
      gradient: 'from-green-500/10 to-emerald-500/10',
      borderColor: 'border-green-500/30',
      iconBg: 'bg-gradient-to-br from-green-500/20 to-emerald-500/20',
    },
  ]

  return (
    <div className="min-h-[calc(100vh-4rem)] flex flex-col items-center py-12">
      <div className="w-full max-w-6xl mx-auto space-y-12">
        {/* Hero Section - Centered */}
        <div className="text-center space-y-6">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30 animate-fade-in backdrop-blur-sm shadow-lg shadow-primary/20">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">AI-Powered DevOps Architecture Analysis</span>
          </div>

          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight animate-fade-in-delayed">
            <span className="gradient-text">Analyze Your DevOps</span>
            <br />
            <span className="text-foreground">Architecture in Seconds</span>
          </h1>

          <p className="text-lg text-muted-foreground max-w-2xl mx-auto animate-fade-in-delayed-2">
            Paste a GitHub repository URL to detect DevOps tools, identify missing best practices, and get a DevOps maturity score.
          </p>
        </div>

        {/* Analyzer Component - Centered */}
        <div className="flex justify-center w-full">
          <div className="w-full max-w-3xl">
            <Card className="p-8" hover={false}>
              <div className="text-center space-y-6">
                <p className="text-muted-foreground">
                  Use our new scan interface for a better experience
                </p>
                <Button
                  variant="primary"
                  size="lg"
                  onClick={() => navigate('/scan')}
                  className="w-full"
                  glow
                >
                  <GitBranch className="h-5 w-5" />
                  Start New Scan
                </Button>
              </div>
            </Card>
          </div>
        </div>

        {/* Features Grid - Centered */}
        <div className="grid grid-auto-fit gap-6 pt-8 border-t border-white/10">
          {features.map((feature) => {
            const Icon = feature.icon

            return (
              <Card
                key={feature.title}
                className={cn(
                  'p-6 bg-gradient-to-br',
                  feature.gradient,
                  feature.borderColor,
                  'hover:border-white/30'
                )}
                hover
              >
                <div className="space-y-3">
                  <div className={cn(
                    'p-3 rounded-xl w-fit border border-white/10 backdrop-blur-sm',
                    feature.iconBg
                  )}>
                    <Icon className="h-6 w-6 text-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold text-foreground">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </Card>
            )
          })}
        </div>

        {/* Stats Section - Centered */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-8 border-t border-white/10">
          {[
            { label: 'Repositories Analyzed', value: '10,000+' },
            { label: 'DevOps Rules', value: '500+' },
            { label: 'Avg. Analysis Time', value: '< 30s' },
            { label: 'Accuracy Rate', value: '99.9%' },
          ].map((stat) => (
            <div key={stat.label} className="text-center p-4 rounded-xl bg-white/5 border border-white/10 backdrop-blur-sm">
              <p className="text-2xl md:text-3xl font-bold gradient-text">{stat.value}</p>
              <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
