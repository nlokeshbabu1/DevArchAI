import { motion } from 'framer-motion'
import { Search, Filter, Box, ExternalLink } from 'lucide-react'
import { useState, useEffect, useCallback } from 'react'

import { cloudApi, type CloudResource } from '@/api/endpoints/cloud'
import { cn } from '@/lib/utils'
import { useCloudStore } from '@/stores/cloud-store'

interface Props {
  connectionId: string
}

export function ResourceInventory({ connectionId }: Props) {
  const { resources, setResources } = useCloudStore()
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [serviceFilter, setServiceFilter] = useState<string>('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await cloudApi.resources(connectionId)
      setResources(data.resources)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [connectionId, setResources])

  useEffect(() => {
    load()
  }, [load])

  const services = Array.from(new Set(resources.map((r) => r.service))).sort()
  const filtered = resources.filter((r) => {
    if (serviceFilter !== 'all' && r.service !== serviceFilter) {return false}
    if (search) {
      const q = search.toLowerCase()
      return (
        r.resource_name.toLowerCase().includes(q) ||
        r.resource_id.toLowerCase().includes(q) ||
        r.resource_type.toLowerCase().includes(q)
      )
    }
    return true
  })

  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="h-16 rounded-xl bg-card/60 border border-white/10 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search resources..."
            className="w-full pl-10 pr-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-orange-500 text-sm"
          />
        </div>
        <select
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          className="px-4 py-2.5 bg-white/5 border border-white/10 rounded-xl text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
        >
          <option value="all">All Services</option>
          {services.map((s) => (
            <option key={s} value={s}>{s.toUpperCase()}</option>
          ))}
        </select>
      </div>

      {/* Count */}
      <p className="text-xs text-muted-foreground">
        {filtered.length} resource{filtered.length !== 1 ? 's' : ''}
        {serviceFilter !== 'all' && ` in ${serviceFilter.toUpperCase()}`}
      </p>

      {/* Table */}
      <div className="rounded-xl border border-white/10 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/5">
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Type</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Name / ID</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Service</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Region</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-muted-foreground">Status</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-muted-foreground">Cost/mo</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                    No resources found
                  </td>
                </tr>
              ) : (
                filtered.map((r) => (
                  <tr key={r.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Box className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs font-mono text-muted-foreground">{r.resource_type}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-foreground font-medium truncate max-w-[200px] block">
                        {r.resource_name || r.resource_id}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono uppercase text-muted-foreground">{r.service}</span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted-foreground">{r.region}</span>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-xs font-mono text-muted-foreground">
                        {r.cost_monthly ? `$${r.cost_monthly.toFixed(2)}` : '—'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </motion.div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { bg: string; text: string }> = {
    active: { bg: 'bg-green-500/10 border-green-500/30', text: 'text-green-400' },
    stopped: { bg: 'bg-gray-500/10 border-gray-500/30', text: 'text-gray-400' },
    available: { bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-400' },
    in_use: { bg: 'bg-blue-500/10 border-blue-500/30', text: 'text-blue-400' },
  }
  const c = config[status] || { bg: 'bg-white/5 border-white/10', text: 'text-muted-foreground' }

  return (
    <span className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border', c.bg, c.text)}>
      {status}
    </span>
  )
}
