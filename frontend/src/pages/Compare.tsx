import { useState, useEffect } from 'react'
import { GitCompare } from 'lucide-react'

export default function Compare() {
  const [prompt, setPrompt] = useState('')
  const [connectors, setConnectors] = useState<any[]>([])
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch('/api/connectors/').then(r => r.json()).then(setConnectors).catch(() => {})
  }, [])

  const compare = async () => {
    if (!prompt.trim()) return
    const available = connectors.filter(c => c.available && c.models.length > 0)
    const targets = available.slice(0, 3).map(c => ({ provider: c.name, model: c.models[0] }))
    if (targets.length === 0) return

    setLoading(true)
    try {
      const r = await fetch('/api/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, providers: targets }),
      })
      setResult(await r.json())
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Model Comparison</h1>
        <p className="text-stone-500 mt-1">Test your actual tasks across multiple models.</p>
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border p-6 mb-6">
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Enter a task or question to test across all your AI providers..."
          className="w-full h-32 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400"
        />
        <div className="flex justify-between items-center mt-4 pt-4 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs text-stone-400">
            Will test {connectors.filter(c => c.available).length} available provider(s)
          </span>
          <button
            onClick={compare}
            disabled={loading || !prompt.trim()}
            className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {loading ? 'Comparing...' : 'Compare'}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          {result.winner && (
            <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-xl p-4 text-sm text-green-700 dark:text-green-400">
              {result.summary}
            </div>
          )}
          <div className="grid gap-4">
            {(result.ranked || []).map((r: any, i: number) => {
              const color = r.trust_score >= 85 ? 'green' : r.trust_score >= 60 ? 'amber' : 'red'
              return (
                <div key={i} className="bg-white dark:bg-stone-900 rounded-xl border p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-stone-800 dark:text-stone-200">{r.provider}/{r.model}</span>
                    <div className="flex items-center gap-3 text-xs text-stone-500">
                      <span>{r.latency_ms}ms</span>
                      <span>${r.cost_usd.toFixed(4)}</span>
                      <span className={`font-semibold text-${color}-600`}>{r.trust_score}/100</span>
                    </div>
                  </div>
                  <p className="text-sm text-stone-600 dark:text-stone-400 whitespace-pre-wrap">{r.content}</p>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
