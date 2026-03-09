import { useNavigate } from 'react-router-dom'
import { Shield, Zap, GitBranch, BarChart3, Sparkles, Check, ArrowRight, Github, FileCode, Brain, Rocket } from 'lucide-react'
import { Button, Card } from '../components/ui'
import { cn } from '../lib/utils'
import { useState, useEffect } from 'react'

export function Landing() {
  const navigate = useNavigate()
  const [animationStep, setAnimationStep] = useState(0)

  const animationSteps = [
    { text: 'Connecting to GitHub repository...', icon: Github },
    { text: 'Detecting DevOps stack...', icon: GitBranch },
    { text: 'Scanning Docker, Terraform, CI/CD files...', icon: Shield },
    { text: 'Running security and architecture checks...', icon: Zap },
    { text: 'Generating AI recommendations...', icon: Sparkles },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setAnimationStep((prev) => (prev + 1) % animationSteps.length)
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  const howItWorks = [
    {
      step: '01',
      icon: Github,
      title: 'Connect Repository',
      description: 'Provide your GitHub repository URL to begin the analysis.',
    },
    {
      step: '02',
      icon: FileCode,
      title: 'Scan Infrastructure',
      description: 'DevArchAI scans your Docker, Terraform, Kubernetes and CI/CD files.',
    },
    {
      step: '03',
      icon: Shield,
      title: 'Execute Rules',
      description: 'Security and architecture rules are executed against your infrastructure.',
    },
    {
      step: '04',
      icon: Brain,
      title: 'AI Analysis',
      description: 'AI analyzes the results and identifies potential issues.',
    },
    {
      step: '05',
      icon: Rocket,
      title: 'Get Report',
      description: 'Receive a comprehensive DevOps production readiness report.',
    },
  ]

  const features = [
    {
      icon: Shield,
      title: 'Repository Analysis',
      description: 'Scan Dockerfiles, Terraform, Kubernetes and CI/CD pipelines for best practices.',
      gradient: 'from-blue-500/10 to-cyan-500/10',
      borderColor: 'border-blue-500/30',
      iconBg: 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20',
    },
    {
      icon: Zap,
      title: 'Security Misconfiguration Detection',
      description: 'Detect production risks like root containers, missing policies, and exposed secrets.',
      gradient: 'from-red-500/10 to-orange-500/10',
      borderColor: 'border-red-500/30',
      iconBg: 'bg-gradient-to-br from-red-500/20 to-orange-500/20',
    },
    {
      icon: BarChart3,
      title: 'DevOps Production Score',
      description: 'Get a comprehensive production readiness score for your infrastructure.',
      gradient: 'from-green-500/10 to-emerald-500/10',
      borderColor: 'border-green-500/30',
      iconBg: 'bg-gradient-to-br from-green-500/20 to-emerald-500/20',
    },
    {
      icon: Sparkles,
      title: 'AI Architecture Suggestions',
      description: 'AI recommends improvements for production readiness and best practices.',
      gradient: 'from-purple-500/10 to-pink-500/10',
      borderColor: 'border-purple-500/30',
      iconBg: 'bg-gradient-to-br from-purple-500/20 to-pink-500/20',
    },
  ]

  const stats = [
    { label: 'Repositories Analyzed', value: '10,000+' },
    { label: 'DevOps Rules', value: '500+' },
    { label: 'Avg. Analysis Time', value: '< 30s' },
    { label: 'Accuracy Rate', value: '99.9%' },
  ]

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-white/10">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 border border-white/20">
                <Shield className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-bold gradient-text">DevArchAI</span>
            </div>
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/login')}
                className="hidden sm:flex"
              >
                Login
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/register')}
                glow
              >
                Get Started
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative py-20 lg:py-32 overflow-hidden">
        {/* Background gradient orbs */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-96 h-96 bg-primary/20 rounded-full blur-3xl" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl" />
        </div>

        <div className="container mx-auto px-4 relative">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/15 border border-primary/30 animate-fade-in backdrop-blur-sm shadow-lg shadow-primary/20">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="text-sm font-medium text-primary">AI-Powered DevOps Architecture Analyzer</span>
            </div>

            {/* Title */}
            <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight animate-fade-in-delayed">
              <span className="gradient-text">Analyze Your DevOps</span>
              <br />
              <span className="text-foreground">Architecture in Seconds</span>
            </h1>

            {/* Description */}
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto animate-fade-in-delayed-2">
              Analyze GitHub repositories to detect infrastructure issues in Docker, Terraform, Kubernetes and CI/CD pipelines.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4 animate-fade-in-delayed-2">
              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/analyze')}
                className="w-full sm:w-auto px-8 py-6 text-lg"
                glow
              >
                Start Analysis
                <ArrowRight className="h-5 w-5" />
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => navigate('/login')}
                className="w-full sm:w-auto px-8 py-6 text-lg"
              >
                Login
              </Button>
            </div>

            {/* Animation Demo */}
            <div className="mt-12 max-w-2xl mx-auto">
              <Card className="p-6" hover={false}>
                <div className="space-y-4">
                  <h3 className="text-sm font-medium text-muted-foreground text-left">
                    Live Analysis Demo
                  </h3>
                  <div className="space-y-3">
                    {animationSteps.map((step, index) => {
                      const Icon = step.icon
                      const isActive = index === animationStep
                      const isCompleted = index < animationStep || (animationStep === 0 && index === animationSteps.length - 1 && animationStep !== 0)

                      return (
                        <div
                          key={index}
                          className={cn(
                            'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
                            isActive
                              ? 'bg-primary/15 border border-primary/30'
                              : isCompleted
                              ? 'bg-green-500/10 border border-green-500/30'
                              : 'bg-white/5 border border-white/10'
                          )}
                        >
                          <div className={cn(
                            'p-2 rounded-lg transition-all duration-300',
                            isActive
                              ? 'bg-primary/20'
                              : isCompleted
                              ? 'bg-green-500/20'
                              : 'bg-white/10'
                          )}>
                            {isCompleted ? (
                              <Check className="h-4 w-4 text-green-400" />
                            ) : (
                              <Icon className={cn(
                                'h-4 w-4',
                                isActive ? 'text-primary animate-pulse' : 'text-muted-foreground'
                              )} />
                            )}
                          </div>
                          <span className={cn(
                            'text-sm font-medium transition-colors duration-300',
                            isActive
                              ? 'text-primary'
                              : isCompleted
                              ? 'text-green-400'
                              : 'text-muted-foreground'
                          )}>
                            {step.text}
                          </span>
                          {isActive && (
                            <div className="ml-auto">
                              <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-12 border-y border-white/10 bg-white/5">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 max-w-4xl mx-auto">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-3xl md:text-4xl font-bold gradient-text">{stat.value}</p>
                <p className="text-sm text-muted-foreground mt-2">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-20 lg:py-32 bg-white/5">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">How It Works</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get your DevOps production readiness report in 5 simple steps.
            </p>
          </div>

          <div className="max-w-5xl mx-auto">
            <div className="grid gap-8">
              {howItWorks.map((item, index) => {
                const Icon = item.icon
                return (
                  <div
                    key={item.step}
                    className="flex items-start gap-6 p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/0 border border-white/10 hover:border-white/20 transition-all duration-300"
                  >
                    <div className="flex-shrink-0">
                      <div className="relative">
                        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center shadow-lg shadow-primary/30">
                          <Icon className="h-8 w-8 text-white" />
                        </div>
                        <div className="absolute -top-2 -right-2 w-8 h-8 rounded-full bg-background border-2 border-primary flex items-center justify-center">
                          <span className="text-xs font-bold text-primary">{item.step}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex-1 pt-2">
                      <h3 className="text-xl font-semibold text-foreground mb-2">
                        {item.title}
                      </h3>
                      <p className="text-muted-foreground">
                        {item.description}
                      </p>
                    </div>
                    {index < howItWorks.length - 1 && (
                      <div className="absolute left-12 top-20 w-0.5 h-8 bg-gradient-to-b from-primary/50 to-transparent hidden lg:block" />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl lg:text-5xl font-bold mb-4">
              <span className="gradient-text">Comprehensive Analysis</span>
            </h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Get deep insights into your infrastructure security, scalability, and best practices.
            </p>
          </div>

          <div className="grid grid-auto-fit gap-6 max-w-6xl mx-auto">
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
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 lg:py-32">
        <div className="container mx-auto px-4">
          <Card className="max-w-4xl mx-auto p-12 text-center glow-primary" hover={false}>
            <div className="space-y-8">
              <div className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30">
                <Shield className="h-12 w-12 text-white" />
              </div>

              <div>
                <h2 className="text-3xl md:text-4xl font-bold mb-4">
                  <span className="gradient-text">Ready to Analyze?</span>
                </h2>
                <p className="text-lg text-muted-foreground max-w-xl mx-auto">
                  Analyze your DevOps architecture in seconds and get actionable recommendations.
                </p>
              </div>

              <Button
                variant="primary"
                size="lg"
                onClick={() => navigate('/analyze')}
                className="px-8 py-6 text-lg"
                glow
              >
                Start Analysis Now
                <ArrowRight className="h-5 w-5" />
              </Button>
            </div>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-white/10">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-indigo-600">
                <Shield className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold gradient-text">DevArchAI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              &copy; 2024 DevArchAI. Production Readiness Engine.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
