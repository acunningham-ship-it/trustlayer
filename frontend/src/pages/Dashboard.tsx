import { useEffect, useState } from 'react'
import { Shield, Zap, DollarSign, BookOpen } from 'lucide-react'

interface ConnectorInfo {
  name: string
  available: boolean
  models: string[]
}

interface Insights {
  total_interactions: number
  personalization_level: number
  message: string
  top_providers: { provider: string; count: number }[]
}

interface CostSummary {
  total_usd: number
  budget_usd: number
  budget_pct: number
  month: string
  alert: boolean
}

export default function Dashboard() {
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([])
  const [insights, setInsights] = useState<Insights | null>(null)
  const [costs, setCosts] = useState<CostSummary | null>(null)

  useEffect(() => {
    fetch('/api/connectors/').then(r => r.json()).then(setConnectors).catch(() => {})
    fetch('/api/learn/insights').then(r => r.json()).then(setInsights).catch(() => {})
    fetch('/api/costs/summary').then(r => r.json()).then(setCosts).catch(() => {})
  }, [])

  const availableCount = connectors.filter(c => c.available).length

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Dashboard</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">Your AI usage at a glance.</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <StatCard
          icon={<Zap className="h-5 w-5" />}
          label="Active Connectors"
          value={`${availableCount} / ${connectors.length}`}
          note={availableCount === 0 ? 'No AI providers detected' : `${availableCount} provider(s) ready`}
        />
        <StatCard
          icon={<Shield className="h-5 w-5" />}
          label="Sessions Tracked"
          value={insights?.total_interactions?.toString() ?? '—'}
          note={`${insights?.personalization_level ?? 0}% personalized`}
        />
        <StatCard
          icon={<DollarSign className="h-5 w-5" />}
          label="Spending This Month"
          value={costs ? `$${costs.total_usd.toFixed(2)}` : '—'}
          note={costs ? `${costs.budget_pct}% of $${costs.budget_usd} budget` : ''}
          alert={costs?.alert}
        />
        <StatCard
          icon={<BookOpen className="h-5 w-5" />}
          label="Knowledge Base"
          value="Local"
          note="All data stored on your machine"
        />
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border p-6 mb-4">
        <h2 className="font-medium text-stone-800 dark:text-stone-200 mb-4">AI Connectors</h2>
        {connectors.length === 0 ? (
          <p className="text-stone-400 text-sm">Checking for AI providers...</p>
        ) : (
          <div className="space-y-3">
            {connectors.map(c => (
              <div key={c.name} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`h-2 w-2 rounded-full ${c.available ? 'bg-green-500' : 'bg-stone-300 dark:bg-stone-600'}`} />
                  <span className="text-sm font-medium text-stone-700 dark:text-stone-300 capitalize">{c.name}</span>
                </div>
                <span className="text-xs text-stone-400">
                  {c.available ? `${c.models.length} model(s)` : 'Not available'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {insights?.message && (
        <div className="bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800 p-5">
          <p className="text-sm text-stone-600 dark:text-stone-400">{insights.message}</p>
        </div>
      )}
    </div>
  )
}

function StatCard({ icon, label, value, note, alert }: {
  icon: React.ReactNode
  label: string
  value: string
  note: string
  alert?: boolean
}) {
  return (
    <div className={`bg-white dark:bg-stone-900 rounded-xl border p-5 ${alert ? 'border-amber-400 dark:border-amber-600' : ''}`}>
      <div className="flex items-center gap-2 text-stone-500 dark:text-stone-400 mb-2">
        {icon}
        <span className="text-xs uppercase tracking-wider">{label}</span>
      </div>
      <div className="text-2xl font-semibold text-stone-900 dark:text-stone-100">{value}</div>
      {note && <div className="text-xs text-stone-400 mt-1">{note}</div>}
    </div>
  )
}
