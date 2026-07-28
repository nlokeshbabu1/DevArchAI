import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Award,
  BarChart3,
  Calendar,
  CheckCircle2,
  ChevronDown,
  Download,
  FileText,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  XCircle,
} from "lucide-react";

interface VulnerabilitySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface ScanSummary {
  total_tests: number;
  passed: number;
  failed: number;
  warnings: number;
  score?: number;
}

interface DashboardData {
  last_scan: string;
  branch: string;
  commit: string;
  summary: Record<string, ScanSummary>;
  vulnerabilities: VulnerabilitySummary;
  trend?: Array<{ date: string; score: number }>;
}

const SEVERITY_COLORS = {
  critical: "text-red-500 bg-red-500/10 border-red-500/30",
  high: "text-orange-500 bg-orange-500/10 border-orange-500/30",
  medium: "text-yellow-500 bg-yellow-500/10 border-yellow-500/30",
  low: "text-blue-500 bg-blue-500/10 border-blue-500/30",
};

const SEVERITY_BG = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-blue-500",
};

function SeverityBadge({ severity, count }: { severity: string; count: number }) {
  const color = SEVERITY_COLORS[severity as keyof typeof SEVERITY_COLORS] || SEVERITY_COLORS.low;
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border ${color}`}>
      {severity === "critical" && <XCircle className="w-4 h-4" />}
      {severity === "high" && <ShieldAlert className="w-4 h-4" />}
      {severity === "medium" && <AlertTriangle className="w-4 h-4" />}
      {severity === "low" && <ShieldCheck className="w-4 h-4" />}
      <span className="font-semibold text-lg">{count}</span>
      <span className="text-xs uppercase tracking-wider opacity-70">{severity}</span>
    </div>
  );
}

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 90 ? "text-green-500" : score >= 70 ? "text-yellow-500" : "text-red-500";
  const barColor = score >= 90 ? "bg-green-500" : score >= 70 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`text-4xl font-bold ${color}`}>{score}%</div>
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <div className={`h-2.5 rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-gray-400">Security Score</span>
    </div>
  );
}

function ScanSummaryCard({ name, summary }: { name: string; summary: ScanSummary }) {
  const score = summary.score ?? (summary.total_tests > 0
    ? Math.round((summary.passed / summary.total_tests) * 100)
    : 0);
  return (
    <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/50 hover:border-gray-600/50 transition-all">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-300 capitalize">{name.replace(/_/g, " ")}</h4>
        <span className={`text-xs font-mono ${score >= 80 ? "text-green-400" : score >= 50 ? "text-yellow-400" : "text-red-400"}`}>
          {score}%
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="text-gray-400">Tests</div>
        <div className="text-right font-mono">{summary.total_tests}</div>
        <div className="text-green-400">Passed</div>
        <div className="text-right font-mono text-green-400">{summary.passed}</div>
        <div className="text-red-400">Failed</div>
        <div className="text-right font-mono text-red-400">{summary.failed}</div>
        <div className="text-yellow-400">Warnings</div>
        <div className="text-right font-mono text-yellow-400">{summary.warnings}</div>
      </div>
    </div>
  );
}

function TrendChart({ data }: { data: Array<{ date: string; score: number }> }) {
  if (!data.length) return (
    <div className="flex items-center justify-center h-32 text-gray-500 text-sm">
      No trend data available yet
    </div>
  );
  const maxScore = Math.max(...data.map(d => d.score));
  const minScore = Math.min(...data.map(d => d.score));
  const range = maxScore - minScore || 1;
  return (
    <div className="flex items-end gap-1 h-32">
      {data.map((point, i) => {
        const height = ((point.score - minScore) / range) * 100;
        return (
          <div key={i} className="flex-1 flex flex-col items-center gap-1 group relative">
            <div
              className="w-full bg-blue-500 rounded-t hover:bg-blue-400 transition-all cursor-pointer"
              style={{ height: `${Math.max(height, 5)}%` }}
            >
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-900 text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 whitespace-nowrap z-10">
                {point.score}% on {point.date}
              </div>
            </div>
            {i % 3 === 0 && <span className="text-[10px] text-gray-500 -rotate-45 mt-1">{point.date.slice(5)}</span>}
          </div>
        );
      })}
    </div>
  );
}

export function SecurityDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const resp = await fetch("/security/reports/dashboard_data.json");
        if (resp.ok) {
          const json = await resp.json();
          setData(json);
        }
      } catch {
        // Dashboard data not available yet
      } finally {
        setLoading(false);
      }
    }
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-gray-500" />
      </div>
    );
  }

  const vuln = data?.vulnerabilities ?? { critical: 0, high: 0, medium: 0, low: 0 };
  const totalVulns = vuln.critical + vuln.high + vuln.medium + vuln.low;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Security Dashboard</h2>
        </div>
        <div className="flex items-center gap-3">
          {data && (
            <span className="text-xs text-gray-500 flex items-center gap-1">
              <Calendar className="w-3 h-3" />
              Last scan: {new Date(data.last_scan).toLocaleDateString()}
            </span>
          )}
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-1 px-3 py-1.5 text-xs bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          >
            <RefreshCw className="w-3 h-3" />
            Refresh
          </button>
        </div>
      </div>

      {/* Score & Vulnerability Summary */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="md:col-span-2 bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
          {data && data.summary && (() => {
            const scores = Object.values(data.summary).map(s => s.score ?? 0);
            const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;
            return <ScoreGauge score={avgScore} />;
          })()}
        </div>

        <div className="md:col-span-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <SeverityBadge severity="critical" count={vuln.critical} />
          <SeverityBadge severity="high" count={vuln.high} />
          <SeverityBadge severity="medium" count={vuln.medium} />
          <SeverityBadge severity="low" count={vuln.low} />
        </div>
      </div>

      {/* Trend */}
      {data?.trend && data.trend.length > 0 && (
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <TrendingUp className="w-4 h-4" />
              Security Score Trend
            </h3>
            <span className="text-xs text-gray-500">Last {data.trend.length} scans</span>
          </div>
          <TrendChart data={data.trend} />
        </div>
      )}

      {/* Scan Summaries */}
      {data?.summary && Object.keys(data.summary).length > 0 && (
        <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Scan Results by Category
            </h3>
            <span className="text-xs text-gray-500">{Object.keys(data.summary).length} categories</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(data.summary).map(([name, summary]) => (
              <ScanSummaryCard key={name} name={name} summary={summary} />
            ))}
          </div>
        </div>
      )}

      {/* Coverage Matrix */}
      <div className="bg-gray-800/50 rounded-xl p-6 border border-gray-700/50">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-gray-300 flex items-center gap-2">
            <Award className="w-4 h-4" />
            Coverage Matrix
          </h3>
          <button
            onClick={() => setExpandedSection(expandedSection === "coverage" ? null : "coverage")}
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            <ChevronDown className={`w-4 h-4 transition-transform ${expandedSection === "coverage" ? "rotate-180" : ""}`} />
          </button>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { name: "OWASP Top 10", covered: true, count: 10 },
            { name: "OWASP API Top 10", covered: true, count: 10 },
            { name: "AWS Security", covered: true, count: 15 },
            { name: "Upload Security", covered: true, count: 20 },
          ].map(item => (
            <div key={item.name} className="bg-gray-900/50 rounded-lg p-3 border border-gray-700/30">
              <div className="flex items-center gap-2 mb-1">
                {item.covered ? (
                  <CheckCircle2 className="w-4 h-4 text-green-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
                <span className="text-xs text-gray-300">{item.name}</span>
              </div>
              <span className="text-lg font-bold text-white">{item.count}</span>
              <span className="text-xs text-gray-500 ml-1">tests</span>
            </div>
          ))}
        </div>
      </div>

      {/* Reports Download */}
      <div className="flex items-center justify-center gap-4 pt-2">
        <a
          href="/security/reports/owasp_top10_report.md"
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          download
        >
          <FileText className="w-4 h-4" />
          OWASP Top 10 Report
        </a>
        <a
          href="/security/reports/api_security_report.md"
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          download
        >
          <FileText className="w-4 h-4" />
          API Security Report
        </a>
        <a
          href="/security/reports/endpoint_inventory.md"
          className="flex items-center gap-2 px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors"
          download
        >
          <Download className="w-4 h-4" />
          Endpoint Inventory
        </a>
      </div>
    </div>
  );
}
