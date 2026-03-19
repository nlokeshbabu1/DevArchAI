import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Clock, AlertCircle, Loader2, GitBranch, Shield, Zap, Brain, BarChart3, Server } from 'lucide-react'
import { Card, Button } from './ui-animated'
import { cn } from '../lib/utils'

interface ScanProgressProps {
  progress: number
  currentStep: number
  isComplete: boolean
}

const scanSteps = [
  { id: 1, text: 'Cloning GitHub Repository', icon: GitBranch },
  { id: 2, text: 'Detecting DevOps Stack', icon: Server },
  { id: 3, text: 'Parsing Infrastructure Files', icon: Zap },
  { id: 4, text: 'Running Security Rules', icon: Shield },
  { id: 5, text: 'Generating AI Recommendations', icon: Brain },
  { id: 6, text: 'Calculating Security Score', icon: BarChart3 },
]

export function ProgressComponent({ progress, currentStep, isComplete }: ScanProgressProps) {
  return (
    <Card className="p-8 glow-primary animate-scale-in" hover={false}>
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-primary to-indigo-600 shadow-lg shadow-primary/30 mb-4">
            {isComplete ? (
              <CheckCircle className="h-8 w-8 text-white" />
            ) : (
              <GitBranch className="h-8 w-8 text-white animate-pulse" />
            )}
          </div>
          <h3 className="text-2xl font-bold text-foreground">
            {isComplete ? 'Analysis Complete!' : 'Analyzing Repository'}
          </h3>
          <p className="text-muted-foreground">
            {isComplete 
              ? 'Your security report is ready' 
              : 'Please wait while we scan your infrastructure'}
          </p>
        </div>

        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium text-primary">{progress.toFixed(0)}%</span>
          </div>
          <div className="h-3 bg-white/10 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-gradient-to-r from-primary to-indigo-500 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>

        {/* Scan Steps */}
        <div className="space-y-3">
          {scanSteps.map((step, index) => {
            const Icon = step.icon
            const isCompleted = index < currentStep
            const isCurrent = index === currentStep

            return (
              <motion.div
                key={step.id}
                className={cn(
                  'flex items-center gap-3 p-3 rounded-lg transition-all duration-300',
                  isCurrent
                    ? 'bg-primary/15 border border-primary/30'
                    : isCompleted
                    ? 'bg-green-500/10 border border-green-500/30'
                    : 'bg-white/5 border border-white/10'
                )}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                <div className={cn(
                  'p-2 rounded-lg transition-all duration-300',
                  isCurrent
                    ? 'bg-primary/20'
                    : isCompleted
                    ? 'bg-green-500/20'
                    : 'bg-white/10'
                )}>
                  {isCompleted ? (
                    <CheckCircle className="h-4 w-4 text-green-400" />
                  ) : isCurrent ? (
                    <Loader2 className="h-4 w-4 text-primary animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4 text-muted-foreground" />
                  )}
                </div>
                <span className={cn(
                  'text-sm font-medium transition-colors duration-300',
                  isCurrent
                    ? 'text-primary'
                    : isCompleted
                    ? 'text-green-400'
                    : 'text-muted-foreground'
                )}>
                  {step.text}
                </span>
                {isCurrent && (
                  <div className="ml-auto">
                    <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                  </div>
                )}
              </motion.div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
