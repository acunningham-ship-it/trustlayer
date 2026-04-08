import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Terminal, Zap } from 'lucide-react'

interface Connector {
  name: string
  type: string
  available: boolean
  models: string[]
}

interface CliTool {
  name: string
  type: string
  available: boolean
  version: string | null
  path: string | null
}

export default function Connectors() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [cliTools, setCliTools] = useState<CliTool[]>([])
  const [prompt, setPrompt] = useState(''
)
  const [selected, setSelected] = useState<{ provider: string; model: string } | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // Known models for CLI tools
  const CLI_MODELS: Record<string, string[]> = {
    'Claude Code': ['claude-opus-4-6', 'claude-sonnet-4-6', 'claude-haiku-4-5'],
    'Gemini CLI': ['gemini-2.5-pro', 'gemini-2.5-flash', 'gemini-2.0-flash'],
  }

  useEffect(() => {
    Promise.all([
      fetch('/api/connectors/').then(r => r.json()).catch(() => []),
      fetch('/api/connectors/cli').then(r => r.json()).catch(() => []),
    ]).then(([apiData, cliData]) => {
      setCliTools(cliData)
      // Merge CLI tools into a single providers list
      const cliAsConnectors = cliData
        .filter((t: CliTool) => t.available)
        .map((t: CliTool) => ({
          name: t.name,
          type: 'cli',
          available: true,
          models: CLI_MODELS[t.name] || ['cli'],
        }))
      const all = [...apiData, ...cliAsConnectors]
      setConnectors(all)
      const first = all.find((c: Connector) => c.available && c.models.length > 0)
      if (first) setSelected({ provider: first.name, model: first.models[0] })
    })
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
    <div className="max-w-5xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">AI Connectors</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">All your AI providers in one place.</p>
      </div>

      {/* All Providers */}
      <div className="mb-3 flex items-center gap-2">
        <Zap className="h-4 w-4 text-amber-500" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-500 dark:text-stone-400">Providers</h2>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {connectors.map(c => (
          <div
            key={c.name}
            className={`rounded-xl border p-5 transition-all cursor-pointer hover:shadow-lg ${
              c.available
                ? c.type === 'cli'
                  ? 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800/50 hover:border-emerald-300 dark:hover:border-emerald-700'
                  : 'bg-white dark:bg-stone-900 border-stone-200 dark:border-stone-800 hover:border-stone-300 dark:hover:border-stone-700'
                : 'bg-stone-50 dark:bg-stone-900/50 border-stone-200 dark:border-stone-800 opacity-60'
            }`}
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                {c.type === 'cli'
                  ? <Terminal className="h-4 w-4 text-emerald-500" />
                  : <Zap className="h-4 w-4 text-amber-500" />}
                <span className="font-semibold text-stone-900 dark:text-stone-100 text-sm">{c.name}</span>
              </div>
              {c.available
                ? <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
                : <XCircle className="h-5 w-5 text-stone-300 dark:text-stone-600 flex-shrink-0" />}
            </div>
            {c.available && c.models.length > 0 ? (
              <div className="space-y-1.5">
                {c.models.slice(0, 3).map(m => (
                  <button
                    key={m}
                    onClick={() => setSelected({ provider: c.name, model: m })}
                    className={`w-full text-left text-xs px-3 py-2 rounded-lg font-medium transition-all ${
                      selected?.provider === c.name && selected?.model === m
                        ? 'bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 shadow-md'
                        : 'text-stone-600 dark:text-stone-400 hover:bg-stone-100 dark:hover:bg-stone-800'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-stone-400 dark:text-stone-500">Not available</p>
            )}
          </div>
        ))}
      </div>

      {selected && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium">Selected</div>
              <div className="text-lg font-semibold text-stone-900 dark:text-stone-100 mt-1">{selected.provider} / {selected.model}</div>
            </div>
          </div>
          <textarea
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            placeholder="Ask anything..."
            className="w-full h-40 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 mb-4"
          />
          <div className="flex justify-end pt-4 border-t border-stone-100 dark:border-stone-800">
            <button
              onClick={ask}
              disabled={loading || !prompt.trim()}
              className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
            >
              {loading ? 'Thinking...' : 'Ask'}
            </button>
          </div>
          {result && !result.error && (
            <div className="mt-6 pt-6 border-t border-stone-100 dark:border-stone-800 space-y-4">
              <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-4">
                <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-wrap">{result.content}</p>
              </div>
              <div className="grid grid-cols-4 gap-3 text-xs">
                <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-2 text-center">
                  <div className="text-stone-500 dark:text-stone-400 mb-1">Input</div>
                  <div className="font-semibold text-stone-900 dark:text-stone-100">{result.tokens_in}</div>
                </div>
                <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-2 text-center">
                  <div className="text-stone-500 dark:text-stone-400 mb-1">Output</div>
                  <div className="font-semibold text-stone-900 dark:text-stone-100">{result.tokens_out}</div>
                </div>
                <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-2 text-center">
                  <div className="text-stone-500 dark:text-stone-400 mb-1">Cost</div>
                  <div className="font-semibold text-stone-900 dark:text-stone-100">${result.cost_usd.toFixed(4)}</div>
                </div>
                <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-2 text-center">
                  <div className="text-stone-500 dark:text-stone-400 mb-1">Latency</div>
                  <div className="font-semibold text-stone-900 dark:text-stone-100">{result.latency_ms}ms</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
