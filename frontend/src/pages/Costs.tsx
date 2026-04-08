import { useEffect, useState } from 'react'

export default function Costs() {
  const [summary, setSummary] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [tips, setTips] = useState<string[]>([])
  const [savings, setSavings] = useState<any>(null)

  useEffect(() => {
    fetch('/api/costs/summary').then(r => r.json()).then(setSummary).catch(() => {})
    fetch('/api/costs/history').then(r => r.json()).then(setHistory).catch(() => {})
    fetch('/api/costs/optimize').then(r => r.json()).then(d => setTips(d.tips || [])).catch(() => {})
    fetch('/api/costs/savings').then(r => r.json()).then(setSavings).catch(() => {})
  }, [])

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Cost Tracker</h1>
        <p className="text-stone-500 mt-1">Real-time AI spending across all your providers.</p>
      </div>

      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className={`rounded-xl border p-6 ${summary.alert ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800' : 'bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800'}`}>
            <div className={`text-xs uppercase tracking-wider font-medium mb-2 ${summary.alert ? 'text-amber-600 dark:text-amber-400' : 'text-stone-500 dark:text-stone-400'}`}>{summary.month}</div>
            <div className="text-4xl font-bold text-stone-900 dark:text-stone-100">${summary.total_usd.toFixed(2)}</div>
            <div className={`text-sm mt-2 ${summary.alert ? 'text-amber-600 dark:text-amber-400/75' : 'text-stone-600 dark:text-stone-400'}`}>of ${summary.budget_usd} budget</div>
          </div>
          <div className={`rounded-xl border p-6 ${summary.alert ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800' : 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800'}`}>
            <div className={`text-xs uppercase tracking-wider font-medium mb-3 ${summary.alert ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}`}>Budget used</div>
            <div className="space-y-2">
              <div className="h-3 bg-stone-200 dark:bg-stone-700 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${summary.alert ? 'bg-amber-500' : 'bg-green-500'}`}
                  style={{ width: `${Math.min(100, summary.budget_pct)}%` }}
                />
              </div>
              <div className={`text-2xl font-bold ${summary.alert ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-green-400'}`}>{summary.budget_pct}%</div>
            </div>
          </div>
        </div>
      )}

      {summary?.by_provider?.length > 0 && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
          <h2 className="font-semibold text-stone-900 dark:text-stone-100 mb-5">Spending by Provider</h2>
          <div className="space-y-3">
            {summary.by_provider.map((p: any) => (
              <div key={p.provider} className="flex items-center justify-between p-3 hover:bg-stone-50 dark:hover:bg-stone-800/50 rounded-lg transition-colors">
                <span className="capitalize text-sm font-medium text-stone-700 dark:text-stone-300">{p.provider}</span>
                <span className="text-sm font-semibold text-stone-900 dark:text-stone-100">${p.cost_usd.toFixed(4)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {savings && savings.savings_usd > 0 && (
        <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-xl p-6 mb-6">
          <h2 className="font-semibold text-green-900 dark:text-green-100 mb-4">Savings with Ollama</h2>
          <div className="mb-5">
            <p className="text-3xl font-bold text-green-700 dark:text-green-400">${savings.savings_usd.toFixed(2)}</p>
            <p className="text-sm text-green-700 dark:text-green-400 mt-1">saved this month vs cloud APIs</p>
          </div>
          {savings.breakdown && (
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-wider font-medium text-green-700 dark:text-green-400 mb-3">Equivalent cost comparison</p>
              <div className="space-y-2">
                {savings.breakdown.claude_haiku && (
                  <div className="flex items-center justify-between text-sm p-2 bg-white/50 dark:bg-green-900/20 rounded">
                    <span className="text-green-700 dark:text-green-300">Claude Haiku equivalent</span>
                    <span className="font-semibold text-green-900 dark:text-green-100">${savings.breakdown.claude_haiku.toFixed(2)}</span>
                  </div>
                )}
                {savings.breakdown.gpt_4o_mini && (
                  <div className="flex items-center justify-between text-sm p-2 bg-white/50 dark:bg-green-900/20 rounded">
                    <span className="text-green-700 dark:text-green-300">GPT-4o-mini equivalent</span>
                    <span className="font-semibold text-green-900 dark:text-green-100">${savings.breakdown.gpt_4o_mini.toFixed(2)}</span>
                  </div>
                )}
                {savings.breakdown.gemini_flash && (
                  <div className="flex items-center justify-between text-sm p-2 bg-white/50 dark:bg-green-900/20 rounded">
                    <span className="text-green-700 dark:text-green-300">Gemini Flash equivalent</span>
                    <span className="font-semibold text-green-900 dark:text-green-100">${savings.breakdown.gemini_flash.toFixed(2)}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {tips.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 rounded-xl p-6 mb-6">
          <h2 className="font-semibold text-blue-900 dark:text-blue-100 mb-4 flex items-center gap-2">
            💡 Optimization Tips
          </h2>
          <ul className="space-y-2">
            {tips.map((tip, i) => (
              <li key={i} className="text-sm text-blue-700 dark:text-blue-400 flex items-start gap-2">
                <span className="flex-shrink-0">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {summary && summary.total_usd === 0 && (
        <div className="bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800 p-12 text-center">
          <p className="text-stone-600 dark:text-stone-400 text-sm">No spending recorded yet. Start using AI through TrustLayer to track costs.</p>
        </div>
      )}
    </div>
  )
}
