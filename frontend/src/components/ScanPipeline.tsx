/**
 * ScanPipeline - Visual pipeline showing scan stages
 */

import { motion } from 'framer-motion'
import { cn } from '../lib/utils'
import { GitBranch, Search, Brain, Shield, FileCheck } from 'lucide-react'

interface PipelineStep {
  id: number
  name: string
  icon: any
}

interface ScanPipelineProps {
  currentStep: number
  progress: number
}

const pipelineSteps: PipelineStep[] = [
  { id: 0, name: 'Scan Repo', icon: GitBranch },
  { id: 1, name: 'Detect Tech', icon: Search },
  { id: 2, name: 'Rule Engine', icon: Shield },
  { id: 3, name: 'AI Analysis', icon: Brain },
  { id: 4, name: 'Score', icon: FileCheck },
]

export function ScanPipeline({ currentStep, progress }: ScanPipelineProps) {
  return (
    <div className="w-full">
      {/* Pipeline Steps */}
      <div className="flex items-center justify-between mb-4">
        {pipelineSteps.map((step, index) => {
          const Icon = step.icon
          const isActive = index === currentStep
          const isCompleted = index < currentStep
          
          return (
            <div key={step.id} className="flex items-center">
              {/* Step Circle */}
              <motion.div
                className={cn(
                  'relative flex items-center justify-center w-12 h-12 rounded-full border-2 transition-all duration-500',
                  isActive && 'border-blue-500 bg-blue-500/20 scale-110 shadow-lg shadow-blue-500/30',
                  isCompleted && 'border-green-500 bg-green-500/20',
                  !isActive && !isCompleted && 'border-gray-700 bg-gray-800/50'
                )}
                initial={{ scale: 1 }}
                animate={{ 
                  scale: isActive ? 1.1 : 1,
                }}
              >
                <Icon className={cn(
                  'h-5 w-5 transition-colors',
                  isActive && 'text-blue-500',
                  isCompleted && 'text-green-400',
                  !isActive && !isCompleted && 'text-gray-400'
                )} />
                
                {/* Pulsing effect for active step */}
                {isActive && (
                  <motion.div
                    className="absolute inset-0 rounded-full border-2 border-blue-500"
                    animate={{ scale: [1, 1.5], opacity: [1, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  />
                )}
              </motion.div>
              
              {/* Connector Line */}
              {index < pipelineSteps.length - 1 && (
                <div className={cn(
                  'flex-1 h-1 mx-2 rounded-full transition-all duration-500',
                  isCompleted ? 'bg-green-500' : 'bg-gray-700'
                )}>
                  <motion.div
                    className={cn(
                      'h-full rounded-full',
                      isActive ? 'bg-gradient-to-r from-blue-500 to-transparent' : 'bg-green-500'
                    )}
                    initial={{ width: '0%' }}
                    animate={{ 
                      width: isCompleted ? '100%' : isActive ? '50%' : '0%' 
                    }}
                    transition={{ duration: 0.5 }}
                  />
                </div>
              )}
            </div>
          )
        })}
      </div>
      
      {/* Step Labels */}
      <div className="flex justify-between">
        {pipelineSteps.map((step, index) => (
          <div 
            key={step.id} 
            className="flex-1 text-center"
          >
            <motion.p
              className={cn(
                'text-xs font-medium transition-colors',
                index <= currentStep ? 'text-foreground' : 'text-muted-foreground'
              )}
              initial={{ opacity: 0.5 }}
              animate={{ opacity: index <= currentStep ? 1 : 0.5 }}
            >
              {step.name}
            </motion.p>
          </div>
        ))}
      </div>
    </div>
  )
}
