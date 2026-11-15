import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Line } from 'recharts'

import { cn } from '../../lib/utils'
import { Button } from '../ui-animated'

interface FindingsChartProps {
  data: Array<{ name: string; critical: number; high: number; medium: number; low: number }>
  className?: string
}

export function FindingsChart({ data, className }: FindingsChartProps) {
  const navigate = useNavigate()

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
    >
      <div className={cn(
        'rounded-2xl bg-card/60 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/30 overflow-hidden',
        className
      )}>
        <div className="p-5 pb-0">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Findings Trend</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Security issues detected over time</p>
            </div>
            <div className="flex items-center gap-3">
              {[
                { color: 'bg-red-500', label: 'Critical' },
                { color: 'bg-orange-500', label: 'High' },
                { color: 'bg-yellow-500', label: 'Medium' },
                { color: 'bg-green-500', label: 'Low' },
              ].map((item) => (
                <div key={item.label} className="hidden sm:flex items-center gap-1.5">
                  <div className={cn('w-2 h-2 rounded-full', item.color)} />
                  <span className="text-[10px] text-muted-foreground">{item.label}</span>
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/findings')}
                icon={<ArrowRight className="h-3.5 w-3.5" />}
              >
                <span className="text-xs">All</span>
              </Button>
            </div>
          </div>
        </div>
        <div className="h-[280px] px-2">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
              <defs>
                <linearGradient id="fcCritical" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="fcHigh" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f97316" stopOpacity={0.25}/>
                  <stop offset="95%" stopColor="#f97316" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="fcMedium" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#eab308" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#eab308" stopOpacity={0}/>
                </linearGradient>
                <linearGradient id="fcLow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#22c55e" stopOpacity={0.15}/>
                  <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#ffffff08" />
              <XAxis dataKey="name" stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#666" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1a1d2e',
                  border: '1px solid #ffffff20',
                  borderRadius: '12px',
                  fontSize: '12px',
                }}
                cursor={{ stroke: '#ffffff15', strokeWidth: 1 }}
              />
              <Area type="monotone" dataKey="critical" stroke="#ef4444" strokeWidth={2} fillOpacity={1} fill="url(#fcCritical)" />
              <Area type="monotone" dataKey="high" stroke="#f97316" strokeWidth={2} fillOpacity={1} fill="url(#fcHigh)" />
              <Line type="monotone" dataKey="medium" stroke="#eab308" strokeWidth={2} dot={{ fill: '#eab308', r: 3, strokeWidth: 0 }} />
              <Line type="monotone" dataKey="low" stroke="#22c55e" strokeWidth={2} dot={{ fill: '#22c55e', r: 3, strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </motion.div>
  )
}
