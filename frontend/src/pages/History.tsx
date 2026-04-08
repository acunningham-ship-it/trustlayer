import { useEffect, useState } from 'react'
import { Clock, Shield, Zap, ChevronDown, ChevronUp, Filter, BarChart3 } from 'lucide-react'

interface Interaction {
  id: string
  provider: string
  model: string
  prompt: string
  response: string
  trust_score: number | null
  tokens_used: number
  cost_usd: number
  latency_ms: number
  created_at: string
}

interface Stats {
  total_interactions: number
  avg_trust_score: number | null
  total_cost_usd: number
  total_tokens: number
  by_provider: { provider: string; count: number }[]
}

function trustColor(score: number | null): string {
  if (score === null) return 'text-stone-400'
  if (score >= 85) return 'text-green-600 dark:text-green-400'
  if (score >= 60) return 'text-amber-600 dark:text-amber-400'
  return 'text-red-600 dark:text-red-400'
}

function trustBg(score: number | null): string {
  if (score === null) return 'bg-stone-100 dark:bg-stone-800'
  if (score >= 85) return 'bg-green-50 dark:bg-green-950/30'
  if (score >= 60) return 'bg-amber-50 dark:bg-amber-950/30'
  return 'bg-red-50 dark:bg-red-950/30'
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

export default function History() {
  const [items, setItems] = useState<Interaction[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [filterProvider, setFilterProvider] = useState<string>('')
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (filterProvider) params.set('provider', filterProvider)
      const [histRes, statsRes] = await Promise.all([
        fetch(`/api/history?${params}`).then(r => r.json()),
        fetch('/api/history/stats').then(r => r.json()),
      ])
      setItems(histRes)
      setStats(statsRes)
    } catch {
      // empty
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filterProvider])

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-3">
          <Clock className="h-6 w-6 text-stone-500" />
          History
        </h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">Every AI interaction, verified and tracked.</p>
      </div>

      {/* Stats row */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-4">
            <div className="text-2xl font-bold text-stone-900 dark:text-stone-100">{stats.total_interactions}</div>
            <div className="text-xs text-stone-500 mt-1">Total queries</div>
          </div>
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-4">
            <div className={`text-2xl font-bold ${trustColor(stats.avg_trust_score)}`}>
              {stats.avg_trust_score !== null ? stats.avg_trust_score : '—'}
            </div>
            <div className="text-xs text-stone-500 mt-1">Avg trust score</div>
          </div>
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-4">
            <div className="text-2xl font-bold text-stone-900 dark:text-stone-100">
              ${stats.total_cost_usd.toFixed(2)}
            </div>
            <div className="text-xs text-stone-500 mt-1">Total spent</div>
          </div>
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-4">
            <div className="text-2xl font-bold text-stone-900 dark:text-stone-100">
              {stats.total_tokens > 1000 ? `${(stats.total_tokens / 1000).toFixed(1)}K` : stats.total_tokens}
            </div>
            <div className="text-xs text-stone-500 mt-1">Total tokens</div>
          </div>
        </div>
      )}

      {/* Filter */}
      {stats && stats.by_provider.length > 1 && (
        <div className="flex items-center gap-2 mb-4">
          <Filter className="h-4 w-4 text-stone-400" />
          <div className="flex gap-1.5">
            <button
              onClick={() => setFilterProvider('')}
              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                !filterProvider
                  ? 'bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 font-medium'
                  : 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 hover:bg-stone-200 dark:hover:bg-stone-700'
              }`}
            >
              All
            </button>
            {stats.by_provider.map(p => (
              <button
                key={p.provider}
                onClick={() => setFilterProvider(p.provider)}
                className={`px-3 py-1 text-xs rounded-full capitalize transition-colors ${
                  filterProvider === p.provider
                    ? 'bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 font-medium'
                    : 'bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 hover:bg-stone-200 dark:hover:bg-stone-700'
                }`}
              >
                {p.provider} ({p.count})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Interaction list */}
      {loading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => (
            <div key={i} className="animate-pulse bg-stone-100 dark:bg-stone-800 rounded-xl h-20" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-16 bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800">
          <Clock className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="text-sm text-stone-600 dark:text-stone-400 font-medium">No history yet.</p>
          <p className="text-xs text-stone-500 dark:text-stone-500 mt-1">
            Start using the Verify or Compare features to build your history.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map(item => (
            <div
              key={item.id}
              className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 overflow-hidden transition-shadow hover:shadow-md"
            >
              <button
                onClick={() => setExpanded(expanded === item.id ? null : item.id)}
                className="w-full flex items-center gap-4 p-4 text-left"
              >
                {/* Trust score badge */}
                <div className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 ${trustBg(item.trust_score)}`}>
                  {item.trust_score !== null ? (
                    <span className={`text-sm font-bold ${trustColor(item.trust_score)}`}>{item.trust_score}</span>
                  ) : (
                    <Shield className="h-4 w-4 text-stone-400" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-stone-800 dark:text-stone-200 truncate">{item.prompt}</div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-stone-500 capitalize flex items-center gap-1">
                      <Zap className="h-3 w-3" />
                      {item.provider}/{item.model}
                    </span>
                    <span className="text-xs text-stone-400">{item.latency_ms}ms</span>
                    <span className="text-xs text-stone-400">{item.tokens_used} tok</span>
                    {item.cost_usd > 0 && (
                      <span className="text-xs text-stone-400">${item.cost_usd.toFixed(4)}</span>
                    )}
                  </div>
                </div>

                {/* Time + expand */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-xs text-stone-400">{item.created_at ? timeAgo(item.created_at) : ''}</span>
                  {expanded === item.id ? (
                    <ChevronUp className="h-4 w-4 text-stone-400" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-stone-400" />
                  )}
                </div>
              </button>

              {/* Expanded detail */}
              {expanded === item.id && (
                <div className="border-t border-stone-100 dark:border-stone-800 p-4 space-y-3">
                  <div>
                    <div className="text-xs uppercase tracking-wider text-stone-500 font-medium mb-1">Prompt</div>
                    <div className="text-sm text-stone-700 dark:text-stone-300 bg-stone-50 dark:bg-stone-800/50 rounded-lg p-3 whitespace-pre-wrap">
                      {item.prompt}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs uppercase tracking-wider text-stone-500 font-medium mb-1">Response</div>
                    <div className="text-sm text-stone-700 dark:text-stone-300 bg-stone-50 dark:bg-stone-800/50 rounded-lg p-3 whitespace-pre-wrap">
                      {item.response}
                    </div>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
