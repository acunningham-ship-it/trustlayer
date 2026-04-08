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

      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6 sticky top-8">
        <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
          Compare across providers
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Enter a task or question to test across all your AI providers..."
          className="w-full h-40 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 mb-4"
        />
        <div className="flex justify-between items-center pt-4 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs text-stone-400 dark:text-stone-500 font-medium">
            Testing {connectors.filter(c => c.available).length} available provider{connectors.filter(c => c.available).length !== 1 ? 's' : ''}
          </span>
          <button
            onClick={compare}
            disabled={loading || !prompt.trim()}
            className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
          >
            {loading ? 'Comparing...' : 'Compare'}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-4">
          {result.winner && (
            <div className="bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-xl p-5">
              <p className="text-sm font-medium text-green-700 dark:text-green-400">{result.summary}</p>
            </div>
          )}
          <div className="space-y-4">
            {(result.ranked || []).map((r: any, i: number) => {
              const color = r.trust_score >= 85 ? 'green' : r.trust_score >= 60 ? 'amber' : 'red'
              const colorBg = r.trust_score >= 85 ? 'bg-green-50 dark:bg-green-950/30' : r.trust_score >= 60 ? 'bg-amber-50 dark:bg-amber-950/30' : 'bg-red-50 dark:bg-red-950/30'
              const colorBorder = r.trust_score >= 85 ? 'border-green-200 dark:border-green-800' : r.trust_score >= 60 ? 'border-amber-200 dark:border-amber-800' : 'border-red-200 dark:border-red-800'
              const textColor = r.trust_score >= 85 ? 'text-green-700 dark:text-green-400' : r.trust_score >= 60 ? 'text-amber-700 dark:text-amber-400' : 'text-red-700 dark:text-red-400'
              return (
                <div key={i} className={`rounded-xl border p-5 ${i === 0 ? `${colorBg} ${colorBorder} shadow-lg` : 'bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800'}`}>
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <span className={`text-sm font-semibold ${i === 0 ? 'text-stone-900 dark:text-stone-100' : 'text-stone-800 dark:text-stone-200'}`}>{r.provider}/{r.model}</span>
                      {i === 0 && <div className="text-xs text-stone-600 dark:text-stone-400 mt-1">🏆 Best match</div>}
                    </div>
                    <div className="flex items-center gap-4 text-xs">
                      <div className="text-center">
                        <div className={`font-medium ${i === 0 ? 'text-stone-600 dark:text-stone-400' : 'text-stone-500 dark:text-stone-500'}`}>Latency</div>
                        <div className={`font-semibold ${i === 0 ? 'text-stone-900 dark:text-stone-100' : 'text-stone-800 dark:text-stone-200'}`}>{r.latency_ms}ms</div>
                      </div>
                      <div className="text-center">
                        <div className={`font-medium ${i === 0 ? 'text-stone-600 dark:text-stone-400' : 'text-stone-500 dark:text-stone-500'}`}>Cost</div>
                        <div className={`font-semibold ${i === 0 ? 'text-stone-900 dark:text-stone-100' : 'text-stone-800 dark:text-stone-200'}`}>${r.cost_usd.toFixed(4)}</div>
                      </div>
                      <div className={`text-center px-2 py-1 rounded-lg ${i === 0 ? 'bg-white/50 dark:bg-stone-800/50' : 'bg-stone-100 dark:bg-stone-800'}`}>
                        <div className={`font-medium ${color === 'green' ? 'text-green-700 dark:text-green-400' : color === 'amber' ? 'text-amber-700 dark:text-amber-400' : 'text-red-700 dark:text-red-400'}`}>Trust</div>
                        <div className={`font-bold text-lg ${color === 'green' ? 'text-green-700 dark:text-green-400' : color === 'amber' ? 'text-amber-700 dark:text-amber-400' : 'text-red-700 dark:text-red-400'}`}>{r.trust_score}</div>
                      </div>
                    </div>
                  </div>
                  <div className={`text-sm whitespace-pre-wrap ${i === 0 ? 'text-stone-700 dark:text-stone-300' : 'text-stone-600 dark:text-stone-400'}`}>{r.content}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
