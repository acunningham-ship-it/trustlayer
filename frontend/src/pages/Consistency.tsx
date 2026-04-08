import { useState, useEffect } from 'react'
import { RefreshCw, ChevronDown, Check, X } from 'lucide-react'

interface ConsistencyResult {
  consistency_score: number
  responses: string[]
  common_claims: string[]
  disputed_claims: string[]
  summary: string
}

export default function Consistency() {
  const [prompt, setPrompt] = useState('')
  const [provider, setProvider] = useState('openai')
  const [model, setModel] = useState('gpt-4')
  const [runs, setRuns] = useState(3)
  const [result, setResult] = useState<ConsistencyResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [connectors, setConnectors] = useState<any[]>([])
  const [expandedResponses, setExpandedResponses] = useState<number | null>(null)

  useEffect(() => {
    fetch('/api/connectors/').then(r => r.json()).then(setConnectors).catch(() => {})
  }, [])

  useEffect(() => {
    if (connectors.length > 0 && connectors[0].models?.length > 0) {
      setProvider(connectors[0].name)
      setModel(connectors[0].models[0])
    }
  }, [connectors])

  const check = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    try {
      const r = await fetch('/api/consistency/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, provider, model, runs }),
      })
      setResult(await r.json())
      setExpandedResponses(null)
    } finally {
      setLoading(false)
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return { bg: 'bg-green-50 dark:bg-green-950/30', text: 'text-green-700 dark:text-green-400', border: 'border-green-200 dark:border-green-800' }
    if (score >= 60) return { bg: 'bg-amber-50 dark:bg-amber-950/30', text: 'text-amber-700 dark:text-amber-400', border: 'border-amber-200 dark:border-amber-800' }
    return { bg: 'bg-red-50 dark:bg-red-950/30', text: 'text-red-700 dark:text-red-400', border: 'border-red-200 dark:border-red-800' }
  }

  const currentModels = connectors.find(c => c.name === provider)?.models || []

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Consistency Checker</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">Detect hallucinations by running prompts multiple times</p>
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6 sticky top-8">
        <div className="space-y-4 mb-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-2">
              Provider
            </label>
            <select
              value={provider}
              onChange={e => {
                setProvider(e.target.value)
                const models = connectors.find(c => c.name === e.target.value)?.models || []
                if (models.length > 0) setModel(models[0])
              }}
              className="w-full px-3 py-2 bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg text-sm text-stone-900 dark:text-stone-100"
            >
              {connectors.map(c => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-2">
              Model
            </label>
            <select
              value={model}
              onChange={e => setModel(e.target.value)}
              className="w-full px-3 py-2 bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700 rounded-lg text-sm text-stone-900 dark:text-stone-100"
            >
              {currentModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-2">
              Number of runs
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[2, 3, 5, 10].map(n => (
                <button
                  key={n}
                  onClick={() => setRuns(n)}
                  className={`py-2 rounded-lg text-sm font-medium transition-colors ${
                    runs === n
                      ? 'bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900'
                      : 'bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 hover:bg-stone-200 dark:hover:bg-stone-700'
                  }`}
                >
                  {n}x
                </button>
              ))}
            </div>
          </div>
        </div>

        <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
          Prompt
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Enter a prompt to test for consistency..."
          className="w-full h-24 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 mb-4"
        />

        <div className="flex justify-between items-center pt-4 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs text-stone-400 dark:text-stone-500 font-medium">
            {prompt.split(/\s+/).filter(Boolean).length} words × {runs} runs
          </span>
          <button
            onClick={check}
            disabled={loading || !prompt.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Checking...' : 'Check Consistency'}
          </button>
        </div>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Score Gauge */}
          <div className={`rounded-xl border p-8 text-center ${getScoreColor(result.consistency_score).bg} ${getScoreColor(result.consistency_score).border}`}>
            <div className="text-5xl font-bold mb-2" style={{ color: result.consistency_score >= 80 ? '#16a34a' : result.consistency_score >= 60 ? '#d97706' : '#dc2626' }}>
              {result.consistency_score}
            </div>
            <p className={`text-sm font-medium mb-3 ${getScoreColor(result.consistency_score).text}`}>
              {result.consistency_score >= 80 ? 'High Consistency' : result.consistency_score >= 60 ? 'Moderate Consistency' : 'Low Consistency'}
            </p>
            <p className={`text-sm ${getScoreColor(result.consistency_score).text}`}>
              {result.summary}
            </p>
          </div>

          {/* Consistent Claims */}
          {result.common_claims.length > 0 && (
            <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
              <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
                <Check className="h-5 w-5 text-green-600 dark:text-green-400" />
                Consistent Claims
              </h3>
              <div className="space-y-3">
                {result.common_claims.map((claim, i) => (
                  <div key={i} className="flex gap-3 p-3 bg-green-50 dark:bg-green-950/30 rounded-lg border border-green-200 dark:border-green-800">
                    <Check className="h-5 w-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0" />
                    <p className="text-sm text-green-700 dark:text-green-300">{claim}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Disputed Claims */}
          {result.disputed_claims.length > 0 && (
            <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
              <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
                <X className="h-5 w-5 text-red-600 dark:text-red-400" />
                Disputed Claims
              </h3>
              <div className="space-y-3">
                {result.disputed_claims.map((claim, i) => (
                  <div key={i} className="flex gap-3 p-3 bg-red-50 dark:bg-red-950/30 rounded-lg border border-red-200 dark:border-red-800">
                    <X className="h-5 w-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0" />
                    <p className="text-sm text-red-700 dark:text-red-300">{claim}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Responses Accordion */}
          {result.responses.length > 0 && (
            <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 overflow-hidden">
              <div className="px-6 py-4 border-b border-stone-200 dark:border-stone-800">
                <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100">All {result.responses.length} Responses</h3>
              </div>
              <div className="divide-y divide-stone-200 dark:divide-stone-800">
                {result.responses.map((response, i) => (
                  <div key={i}>
                    <button
                      onClick={() => setExpandedResponses(expandedResponses === i ? null : i)}
                      className="w-full px-6 py-3 flex items-center justify-between text-sm hover:bg-stone-50 dark:hover:bg-stone-800/50 transition-colors"
                    >
                      <span className="font-medium text-stone-700 dark:text-stone-300">Run {i + 1}</span>
                      <ChevronDown
                        className={`h-4 w-4 text-stone-400 transition-transform ${expandedResponses === i ? 'rotate-180' : ''}`}
                      />
                    </button>
                    {expandedResponses === i && (
                      <div className="px-6 py-4 bg-stone-50 dark:bg-stone-800/50 border-t border-stone-200 dark:border-stone-800">
                        <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-wrap">{response}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
