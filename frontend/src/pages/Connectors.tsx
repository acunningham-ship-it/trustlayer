import { useEffect, useState } from 'react'
import { Zap, CheckCircle, XCircle } from 'lucide-react'

interface Connector {
  name: string
  available: boolean
  models: string[]
}

export default function Connectors() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [prompt, setPrompt] = useState('')
  const [selected, setSelected] = useState<{ provider: string; model: string } | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch('/api/connectors/').then(r => r.json()).then(data => {
      setConnectors(data)
      const first = data.find((c: Connector) => c.available && c.models.length > 0)
      if (first) setSelected({ provider: first.name, model: first.models[0] })
    }).catch(() => {})
  }, [])

  const ask = async () => {
    if (!prompt.trim() || !selected) return
    setLoading(true)
    try {
      const r = await fetch('/api/connectors/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...selected, prompt }),
      })
      setResult(await r.json())
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">AI Connectors</h1>
        <p className="text-stone-500 mt-1">All your AI providers in one place.</p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-8">
        {connectors.map(c => (
          <div key={c.name} className="bg-white dark:bg-stone-900 rounded-xl border p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-stone-800 dark:text-stone-200 capitalize">{c.name}</span>
              {c.available
                ? <CheckCircle className="h-4 w-4 text-green-500" />
                : <XCircle className="h-4 w-4 text-stone-300" />}
            </div>
            {c.available && c.models.length > 0 && (
              <div className="space-y-1">
                {c.models.slice(0, 3).map(m => (
                  <button
                    key={m}
                    onClick={() => setSelected({ provider: c.name, model: m })}
                    className={`w-full text-left text-xs px-2 py-1 rounded transition-colors ${
                      selected?.provider === c.name && selected?.model === m
                        ? 'bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900'
                        : 'text-stone-500 hover:bg-stone-50 dark:hover:bg-stone-800'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
            {!c.available && (
              <p className="text-xs text-stone-400">Not available — add API key</p>
            )}
          </div>
        ))}
      </div>

      {selected && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border p-6">
          <div className="text-xs text-stone-400 mb-3">Asking: {selected.provider}/{selected.model}</div>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Ask anything..."
            className="w-full h-32 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400"
          />
          <div className="flex justify-end mt-3 pt-3 border-t border-stone-100 dark:border-stone-800">
            <button
              onClick={ask}
              disabled={loading || !prompt.trim()}
              className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity"
            >
              {loading ? 'Thinking...' : 'Ask'}
            </button>
          </div>
          {result && !result.error && (
            <div className="mt-4 pt-4 border-t border-stone-100 dark:border-stone-800">
              <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-wrap">{result.content}</p>
              <div className="flex gap-4 mt-3 text-xs text-stone-400">
                <span>↑ {result.tokens_in} tokens</span>
                <span>↓ {result.tokens_out} tokens</span>
                <span>${result.cost_usd.toFixed(4)}</span>
                <span>{result.latency_ms}ms</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
