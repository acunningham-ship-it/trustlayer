import { useEffect, useState } from 'react'

export default function Costs() {
  const [summary, setSummary] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [tips, setTips] = useState<string[]>([])

  useEffect(() => {
    fetch('/api/costs/summary').then(r => r.json()).then(setSummary).catch(() => {})
    fetch('/api/costs/history').then(r => r.json()).then(setHistory).catch(() => {})
    fetch('/api/costs/optimize').then(r => r.json()).then(d => setTips(d.tips || [])).catch(() => {})
  }, [])

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Cost Tracker</h1>
        <p className="text-stone-500 mt-1">Real-time AI spending across all your providers.</p>
      </div>

      {summary && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="bg-white dark:bg-stone-900 rounded-xl border p-5">
            <div className="text-xs text-stone-500 uppercase tracking-wider mb-1">{summary.month}</div>
            <div className="text-3xl font-bold text-stone-900 dark:text-stone-100">${summary.total_usd.toFixed(2)}</div>
            <div className="text-sm text-stone-400 mt-1">of ${summary.budget_usd} budget</div>
          </div>
          <div className="bg-white dark:bg-stone-900 rounded-xl border p-5">
            <div className="text-xs text-stone-500 uppercase tracking-wider mb-2">Budget used</div>
            <div className="h-2 bg-stone-100 dark:bg-stone-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${summary.alert ? 'bg-amber-500' : 'bg-green-500'}`}
                style={{ width: `${Math.min(100, summary.budget_pct)}%` }}
              />
            </div>
            <div className="text-sm text-stone-500 mt-2">{summary.budget_pct}%</div>
          </div>
        </div>
      )}

      {summary?.by_provider?.length > 0 && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border p-6 mb-4">
          <h2 className="font-medium text-stone-800 dark:text-stone-200 mb-4">By Provider</h2>
          <div className="space-y-2">
            {summary.by_provider.map((p: any) => (
              <div key={p.provider} className="flex justify-between text-sm">
                <span className="capitalize text-stone-600 dark:text-stone-400">{p.provider}</span>
                <span className="text-stone-800 dark:text-stone-200">${p.cost_usd.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tips.length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl p-5">
          <h2 className="font-medium text-amber-800 dark:text-amber-400 mb-3">Optimization Tips</h2>
          <ul className="space-y-1.5">
            {tips.map((tip, i) => (
              <li key={i} className="text-sm text-amber-700 dark:text-amber-500">• {tip}</li>
            ))}
          </ul>
        </div>
      )}

      {summary && summary.total_usd === 0 && (
        <div className="bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800 p-8 text-center">
          <p className="text-stone-500">No spending recorded yet. Start using AI through TrustLayer to track costs.</p>
        </div>
      )}
    </div>
  )
}
