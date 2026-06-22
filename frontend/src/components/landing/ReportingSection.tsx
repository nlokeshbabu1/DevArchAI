import { motion } from 'framer-motion'
import { FileDown, FileSpreadsheet, BarChart3, Shield, AlertTriangle, CheckCircle, ArrowRight, Download, FileText, PieChart, ListChecks, Target, BookOpen } from 'lucide-react'
import { cn } from '../../lib/utils'

const reportTypes = [
  {
    title: 'PDF Reports',
    icon: FileDown,
    description: 'Professional-grade PDF reports with executive summaries, severity breakdowns, and detailed findings.',
    gradient: 'from-red-500/20 to-orange-500/20',
    border: 'border-red-500/30',
    features: ['Executive Summary', 'Risk Distribution', 'Remediation Guidance'],
  },
  {
    title: 'Excel Reports',
    icon: FileSpreadsheet,
    description: 'Export all findings to Excel for custom filtering, pivot tables, and integration with your workflows.',
    gradient: 'from-green-500/20 to-emerald-500/20',
    border: 'border-green-500/30',
    features: ['All Findings', 'Severity Filters', 'Custom Analysis'],
  },
  {
    title: 'Security Dashboard',
    icon: BarChart3,
    description: 'Real-time dashboard with security scores, trends, and actionable insights for your entire portfolio.',
    gradient: 'from-blue-500/20 to-cyan-500/20',
    border: 'border-blue-500/30',
    features: ['Risk Overview', 'Severity Trends', 'Repository Insights'],
  },
]

export function ReportingSection() {
  return (
    <section className="py-20 lg:py-32">
      <div className="container mx-auto px-4">
        <div className="text-center mb-16 space-y-4">
          <motion.div
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/30"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
          >
            <FileText className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Enterprise-Grade Reporting</span>
          </motion.div>
          <h2 className="text-4xl md:text-5xl font-bold gradient-text">
            Comprehensive Security Reports
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            From executive summaries to technical deep-dives, get the reports your team and stakeholders need
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-16">
          {reportTypes.map((report, index) => {
            const Icon = report.icon

            return (
              <motion.div
                key={report.title}
                className={cn(
                  'group relative p-6 rounded-2xl bg-gradient-to-br border backdrop-blur-sm',
                  'hover:shadow-xl transition-all duration-300',
                  report.gradient,
                  report.border
                )}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
                whileHover={{ y: -5 }}
              >
                <div className="space-y-4">
                  <div className={cn(
                    'p-3 rounded-xl w-fit bg-gradient-to-br border border-white/10',
                    report.gradient
                  )}>
                    <Icon className="h-7 w-7 text-foreground" />
                  </div>

                  <div>
                    <h3 className="text-xl font-semibold text-foreground mb-2">{report.title}</h3>
                    <p className="text-sm text-muted-foreground leading-relaxed">{report.description}</p>
                  </div>

                  <div className="space-y-2 pt-2">
                    {report.features.map((feature) => (
                      <div key={feature} className="flex items-center gap-2 text-xs">
                        <CheckCircle className="h-3.5 w-3.5 text-green-400 flex-shrink-0" />
                        <span className="text-muted-foreground">{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </motion.div>
            )
          })}
        </div>

        {/* Mock Report Preview */}
        <motion.div
          className="max-w-4xl mx-auto rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-white/0 backdrop-blur-sm overflow-hidden"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 border border-primary/30">
                  <Shield className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-semibold text-foreground">Executive Security Summary</h4>
                  <p className="text-xs text-muted-foreground">terraform-infrastructure • Generated Apr 15, 2024</p>
                </div>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Download className="h-4 w-4" />
                <span>Download PDF</span>
              </div>
            </div>
          </div>

          <div className="p-6 space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-center">
                <div className="text-2xl font-bold text-red-400">7</div>
                <div className="text-xs text-muted-foreground mt-1">Critical</div>
              </div>
              <div className="p-4 rounded-xl bg-orange-500/10 border border-orange-500/30 text-center">
                <div className="text-2xl font-bold text-orange-400">12</div>
                <div className="text-xs text-muted-foreground mt-1">High</div>
              </div>
              <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-center">
                <div className="text-2xl font-bold text-yellow-400">18</div>
                <div className="text-xs text-muted-foreground mt-1">Medium</div>
              </div>
              <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 text-center">
                <div className="text-2xl font-bold text-blue-400">9</div>
                <div className="text-xs text-muted-foreground mt-1">Low</div>
              </div>
            </div>

            <div className="grid md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h5 className="text-sm font-semibold text-foreground mb-3">Risk Distribution</h5>
                <div className="space-y-2">
                  {[
                    { label: 'Critical', count: 7, color: 'bg-red-500', width: 'w-[70%]' },
                    { label: 'High', count: 12, color: 'bg-orange-500', width: 'w-[60%]' },
                    { label: 'Medium', count: 18, color: 'bg-yellow-500', width: 'w-[45%]' },
                    { label: 'Low', count: 9, color: 'bg-blue-500', width: 'w-[30%]' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center gap-3">
                      <span className="text-xs text-muted-foreground w-16">{item.label}</span>
                      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                        <motion.div
                          className={cn('h-full rounded-full', item.color)}
                          initial={{ width: 0 }}
                          whileInView={{ width: item.width }}
                          viewport={{ once: true }}
                          transition={{ duration: 1, delay: 0.3 }}
                        />
                      </div>
                      <span className="text-xs text-muted-foreground w-6 text-right">{item.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                <h5 className="text-sm font-semibold text-foreground mb-3">Top Categories</h5>
                <div className="space-y-2">
                  {[
                    { label: 'Secrets Exposure', count: 8, severity: 'critical' },
                    { label: 'K8s Misconfigurations', count: 12, severity: 'high' },
                    { label: 'Terraform Risks', count: 10, severity: 'high' },
                    { label: 'Container Security', count: 6, severity: 'medium' },
                  ].map((item) => (
                    <div key={item.label} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/5">
                      <div className="flex items-center gap-2">
                        <AlertTriangle className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-sm text-foreground">{item.label}</span>
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