import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Github, Loader2, Shield, CheckCircle, AlertTriangle } from 'lucide-react'
import { Button, Card } from '../ui-animated'
import { cn } from '../../lib/utils'
import { useNavigate } from 'react-router-dom'

interface LandingScannerProps {
  onScanComplete?: (sessionId: string) => void
}

export function LandingScanner({ onScanComplete }: LandingScannerProps) {
  const navigate = useNavigate()
  const [repoUrl, setRepoUrl] = useState('')
  const [isScanning, setIsScanning] = useState(false)
  const [scanProgress, setScanProgress] = useState(0)
  const [scanStatus, setScanStatus] = useState<'idle' | 'scanning' | 'complete' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!repoUrl.trim()) {
      setErrorMessage('Please enter a GitHub repository URL')
      return
    }

    // Validate GitHub URL
    const githubRegex = /^https?:\/\/(www\.)?github\.com\/[\w-]+\/[\w.-]+\/?$/
    if (!githubRegex.test(repoUrl)) {
      setErrorMessage('Please enter a valid GitHub repository URL')
      return
    }

    setIsScanning(true)
    setScanStatus('scanning')
    setScanProgress(0)
    setErrorMessage('')

    try {
      // Simulate scan progress
      const progressInterval = setInterval(() => {
        setScanProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval)
            return 90
          }
          return prev + 10
        })
      }, 500)

      // Call anonymous scan API
      const response = await fetch('/api/v1/public/scan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repository_url: repoUrl,
          branch: 'main',
        }),
      })

      clearInterval(progressInterval)
      setScanProgress(100)

      if (!response.ok) {
        throw new Error('Scan failed')
      }

      const data = await response.json()
      
      // Scan complete
      setScanStatus('complete')
      
      // Store session token and navigate to results
      sessionStorage.setItem('anonScanToken', data.session_token)
      sessionStorage.setItem('anonScanRepo', data.repository_name)
      
      setTimeout(() => {
        navigate(`/scan/results/${data.session_token}`)
        onScanComplete?.(data.session_token)
      }, 1000)

    } catch (error) {
      setScanStatus('error')
      setErrorMessage('Failed to start scan. Please try again.')
      setIsScanning(false)
    }
  }

  const resetScan = () => {
    setRepoUrl('')
    setIsScanning(false)
    setScanStatus('idle')
    setScanProgress(0)
    setErrorMessage('')
  }

  return (
    <div className="w-full max-w-3xl mx-auto">
      <AnimatePresence mode="wait">
        {scanStatus === 'idle' || scanStatus === 'error' ? (
          <motion.form
            key="scanner-form"
            onSubmit={handleScan}
            className="space-y-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Github className="h-5 w-5 text-muted-foreground" />
              </div>
              <input
                type="url"
                value={repoUrl}
                onChange={(e) => {
                  setRepoUrl(e.target.value)
                  setErrorMessage('')
                }}
                placeholder="github.com/organization/repository"
                className={cn(
                  'w-full pl-12 pr-4 py-4 rounded-xl bg-white/5 border text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 transition-all',
                  errorMessage
                    ? 'border-red-500/50 focus:ring-red-500/50'
                    : 'border-white/10 focus:ring-primary/50 focus:border-primary/50'
                )}
                disabled={isScanning}
              />
            </div>

            {errorMessage && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-2 text-red-400 text-sm"
              >
                <AlertTriangle className="h-4 w-4" />
                {errorMessage}
              </motion.div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              className="w-full py-6 text-lg"
              disabled={isScanning}
              glow
            >
              {isScanning ? (
                <>
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  Starting Scan...
                </>
              ) : (
                <>
                  Start Free Scan
                  <ArrowRight className="h-5 w-5 ml-2" />
                </>
              )}
            </Button>

            <p className="text-center text-sm text-muted-foreground">
              No login required • Free security analysis • Results in seconds
            </p>
          </motion.form>
        ) : scanStatus === 'scanning' ? (
          <motion.div
            key="scanning"
            className="space-y-6"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <Card className="p-8" hover={false}>
              <div className="text-center space-y-6">
                {/* Animated Shield Icon */}
                <motion.div
                  className="inline-flex p-4 rounded-2xl bg-gradient-to-br from-primary to-indigo-600"
                  animate={{
                    rotate: [0, 5, -5, 0],
                    scale: [1, 1.05, 1],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    repeatType: 'reverse',
                  }}
                >
                  <Shield className="h-12 w-12 text-white" />
                </motion.div>

                <div>
                  <h3 className="text-xl font-semibold text-foreground mb-2">
                    Scanning {repoUrl.split('/').slice(-2).join('/')}
                  </h3>
                  <p className="text-muted-foreground">
                    Analyzing infrastructure security and best practices
                  </p>
                </div>

                {/* Progress Bar */}
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="text-foreground font-medium">{scanProgress}%</span>
                  </div>
                  <div className="h-3 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      className="h-full bg-gradient-to-r from-primary to-indigo-600"
                      initial={{ width: 0 }}
                      animate={{ width: `${scanProgress}%` }}
                      transition={{ duration: 0.3 }}
                    />
                  </div>
                </div>

                {/* Scan Steps */}
                <div className="grid grid-cols-3 gap-4 pt-4">
                  {[
                    { label: 'Fetching Repo', done: scanProgress > 20 },
                    { label: 'Analyzing Files', done: scanProgress > 50 },
                    { label: 'Generating Report', done: scanProgress > 80 },
                  ].map((step) => (
                    <div
                      key={step.label}
                      className={cn(
                        'flex items-center gap-2 justify-center p-3 rounded-lg border transition-all',
                        step.done
                          ? 'bg-green-500/10 border-green-500/30'
                          : 'bg-white/5 border-white/10'
                      )}
                    >
                      {step.done ? (
                        <CheckCircle className="h-5 w-5 text-green-400" />
                      ) : (
                        <Loader2 className="h-5 w-5 text-primary animate-spin" />
                      )}
                      <span className={cn(
                        'text-sm font-medium',
                        step.done ? 'text-green-400' : 'text-muted-foreground'
                      )}>
                        {step.label}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          </motion.div>
        ) : null}
      </AnimatePresence>
    </div>
  )
}
