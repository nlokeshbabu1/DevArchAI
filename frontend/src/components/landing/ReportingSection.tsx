import { motion, useReducedMotion } from 'framer-motion'
import { FileDown, FileSpreadsheet, BarChart3, Shield, AlertTriangle, CheckCircle, Download, FileText } from 'lucide-react'
import { memo } from 'react'

import { cn } from '../../lib/utils'

const reportTypes = [
  {
    title: 'PDF Reports',
    icon: FileDown,
    description: 'Professional-grade PDF reports with executive summaries, severity breakdowns, and detailed findings.',
    color: 'text-red-400',
    bg: 'bg-red-500/10 border-red-500/20',
    features: ['Executive Summary', 'Risk Distribution', 'Remediation Guidance'],
  },
  {
    title: 'Excel Reports',
    icon: FileSpreadsheet,
    description: 'Export all findings to Excel for custom filtering, pivot tables, and integration with your workflows.',
    color: 'text-green-400',
    bg: 'bg-green-500/10 border-green-500/20',
    features: ['All Findings', 'Severity Filters', 'Custom Analysis'],
  },
  {
    title: 'Security Dashboard',
    icon: BarChart3,
    description: 'Real-time dashboard with security scores, trends, and actionable insights for your entire portfolio.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/20',
    features: ['Risk Overview', 'Severity Trends', 'Repository Insights'],
  },
]

const ReportCard = memo(function ReportCard({
  report,
  index,
}: {
  report: typeof reportTypes[0]
  index: number
}) {
  const Icon = report.icon

  return (
    <motion.div
      className="group p-5 rounded-2xl border border-white/[0.06] bg-card/30 backdrop-blur-sm hover:border-white/[0.12] transition-all duration-300"
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-50px' }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="space-y-4">
        <div className={cn('p-2.5 rounded-xl w-fit border', report.bg)}>
          <Icon className={cn('h-6 w-6', report.color)} />
        </div>

        <div>
          <h3 className="text-lg font-semibold text-foreground mb-1.5">{report.title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{report.description}</p>
        </div>

        <div className="space-y-2 pt-1">
          {report.features.map((feature) => (
            <div key={feature} className="flex items-center gap-2 text-xs">
              <CheckCircle className="h-3.5 w-3.5 text-green-400/80 flex-shrink-0" />
              <span className="text-muted-foreground">{feature}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  )
})

export function ReportingSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-14 space-y-3">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/[0.06] border border-primary/20"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <FileText className="h-4 w-4 text-primary/80" />
            <span className="text-sm font-medium text-primary/90">Enterprise-Grade Reporting</span>
          </motion.div>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground tracking-tight">
            Comprehensive Security Reports
          </h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            From executive summaries to technical deep-dives, get the reports your team and stakeholders need
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-4 max-w-5xl mx-auto mb-14">
          {reportTypes.map((report, index) => (
            <ReportCard key={report.title} report={report} index={index} />
          ))}
        </div>

        {/* Mock Report Preview */}
        <motion.div
          className="max-w-4xl mx-auto rounded-2xl border border-white/[0.08] bg-card/40 backdrop-blur-xl overflow-hidden shadow-2xl shadow-black/20"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="p-5 border-b border-white/[0.06]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground text-sm">Executive Security Summary</h4>
                  <p className="text-xs text-muted-foreground">terraform-infrastructure &bull; Generated Apr 15, 2024</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Download className="h-4 w-4" />
                <span>Download PDF</span>
              </div>
            </div>
          </div>

          <div className="p-5 space-y-5">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { count: '7', label: 'Critical', bg: 'bg-red-500/10 border-red-500/20', color: 'text-red-400' },
                { count: '12', label: 'High', bg: 'bg-orange-500/10 border-orange-500/20', color: 'text-orange-400' },
                { count: '18', label: 'Medium', bg: 'bg-yellow-500/10 border-yellow-500/20', color: 'text-yellow-400' },
                { count: '9', label: 'Low', bg: 'bg-blue-500/10 border-blue-500/20', color: 'text-blue-400' },
              ].map((item) => (
                <div key={item.label} className={cn('p-3 rounded-xl border text-center', item.bg)}>
                  <div className={cn('text-2xl font-bold', item.color)}>{item.count}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{item.label}</div>
                </div>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-3">
              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <h5 className="text-sm font-semibold text-foreground mb-3">Risk Distribution</h5>
                <div className="space-y-2">
                  {[
                    { label: 'Critical', count: 7, color: 'bg-red-500', width: '70%' },
                    { label: 'High', count: 12, color: 'bg-orange-500', width: '60%' },
                    { label: 'Medium', count: 18, color: 'bg-yellow-500', width: '45%' },
                    { label: 'Low', count: 9, color: 'bg-blue-500', width: '30%' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-2.5">
                      <span className="text-[11px] text-muted-foreground w-14">{item.label}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                        <motion.div
                          className={cn('h-full rounded-full', item.color)}
                          initial={{ width: 0 }}
                          whileInView={{ width: item.width }}
                          viewport={{ once: true }}
                          transition={{ duration: 0.8, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
                        />
                      </div>
                      <span className="text-[11px] text-muted-foreground w-5 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-white/[0.03] border border-white/[0.06]">
                <h5 className="text-sm font-semibold text-foreground mb-3">Top Categories</h5>
                <div className="space-y-2">
                  {[
                    { label: 'Secrets Exposure', count: 8, severity: 'critical' },
                    { label: 'K8s Misconfigurations', count: 12, severity: 'high' },
                    { label: 'Terraform Risks', count: 10, severity: 'high' },
                    { label: 'Container Security', count: 6, severity: 'medium' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/[0.03] transition-colors">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground/60" />
                        <span className="text-sm text-foreground/90">{item.label}</span>
                      </div>
                      <span className={cn(
                        'text-xs font-medium',
                        item.severity === 'critical' ? 'text-red-400' :
                        item.severity === 'high' ? 'text-orange-400' : 'text-yellow-400'
                      )}>
                        {item.count} findings
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
