import { useState, useEffect } from 'react'
import { Zap, Sparkles, ChevronRight } from 'lucide-react'

interface Alternative {
  provider: string
  model: string
  confidence: number
}

interface RouterResult {
  task_type: string
  recommended_provider: string
  recommended_model: string
  reasoning: string
  confidence: number
  alternatives: Alternative[]
  response?: string
}

export default function SmartRouter() {
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState<RouterResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)

  const getTaskTypeIcon = (taskType: string) => {
    const icons: Record<string, string> = {
      code: '💻',
      creative: '🎨',
      analysis: '📊',
      factual: '📚',
      quick: '⚡',
    }
    return icons[taskType] || '✨'
  }

  const getTaskTypeBg = (taskType: string) => {
    const colors: Record<string, string> = {
      code: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400',
      creative: 'bg-purple-50 dark:bg-purple-950/30 border-purple-200 dark:border-purple-800 text-purple-700 dark:text-purple-400',
      analysis: 'bg-emerald-50 dark:bg-emerald-950/30 border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400',
      factual: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400',
      quick: 'bg-rose-50 dark:bg-rose-950/30 border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-400',
    }
    return colors[taskType] || 'bg-stone-50 dark:bg-stone-950/30 border-stone-200 dark:border-stone-800 text-stone-700 dark:text-stone-400'
  }

  const suggest = async (autoExecute: boolean = false) => {
    if (!prompt.trim()) return
    setLoading(true)
    try {
      const r = await fetch('/api/router/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, auto_execute: autoExecute }),
      })
      const data = await r.json()
      setResult(data)
    } finally {
      setLoading(false)
    }
  }

  const executeWithRouter = async () => {
    setExecuting(true)
    await suggest(true)
    setExecuting(false)
  }

  const confidenceColor = (conf: number) => {
    if (conf >= 0.85) return 'bg-green-200 dark:bg-green-800'
    if (conf >= 0.65) return 'bg-amber-200 dark:bg-amber-800'
    return 'bg-stone-200 dark:bg-stone-800'
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Smart Router</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">Let TrustLayer pick the best model for your task</p>
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6 sticky top-8">
        <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
          What do you want to do?
        </label>
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          placeholder="Describe your task or paste a prompt..."
          className="w-full h-40 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 mb-4"
        />
        <div className="flex justify-between items-center pt-4 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs text-stone-400 dark:text-stone-500 font-medium">
            {prompt.split(/\s+/).filter(Boolean).length} words
          </span>
          <div className="flex gap-3">
            <button
              onClick={() => suggest(false)}
              disabled={loading || executing || !prompt.trim()}
              className="px-4 py-2 bg-stone-100 dark:bg-stone-800 text-stone-900 dark:text-stone-100 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
            >
              {loading ? 'Analyzing...' : 'Get Recommendation'}
            </button>
            <button
              onClick={executeWithRouter}
              disabled={loading || executing || !prompt.trim()}
              className="flex items-center gap-2 px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
            >
              <Sparkles className="h-4 w-4" />
              {executing ? 'Executing...' : 'Route & Execute'}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="space-y-6">
          {/* Recommendation Card */}
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
            <div className="mb-4">
              <div className={`inline-block px-3 py-1 rounded-full border text-sm font-medium ${getTaskTypeBg(result.task_type)}`}>
                <span className="mr-1">{getTaskTypeIcon(result.task_type)}</span>
                {result.task_type.charAt(0).toUpperCase() + result.task_type.slice(1)}
              </div>
            </div>

            <div className="mb-6">
              <h3 className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium mb-2">
                Recommended Model
              </h3>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg font-semibold text-stone-900 dark:text-stone-100">
                  {result.recommended_provider} / {result.recommended_model}
                </span>
              </div>

              {/* Confidence bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-stone-500 dark:text-stone-400">Confidence</span>
                  <span className="font-medium text-stone-700 dark:text-stone-300">{Math.round(result.confidence * 100)}%</span>
                </div>
                <div className="w-full h-2 bg-stone-200 dark:bg-stone-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${confidenceColor(result.confidence)} transition-all duration-300`}
                    style={{ width: `${result.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="mb-6 p-4 bg-stone-50 dark:bg-stone-800/50 rounded-lg">
              <p className="text-sm text-stone-700 dark:text-stone-300">{result.reasoning}</p>
            </div>

            {result.alternatives && result.alternatives.length > 0 && (
              <div>
                <h3 className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium mb-3">
                  Alternatives
                </h3>
                <div className="space-y-2">
                  {result.alternatives.map((alt, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between p-3 bg-stone-50 dark:bg-stone-800/50 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
                    >
                      <div className="flex items-center gap-2">
                        <ChevronRight className="h-4 w-4 text-stone-400" />
                        <span className="text-sm text-stone-700 dark:text-stone-300">
                          {alt.provider} / {alt.model}
                        </span>
                      </div>
                      <span className="text-xs font-medium text-stone-500 dark:text-stone-400">
                        {Math.round(alt.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Response section if executed */}
          {result.response && (
            <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
              <h3 className="text-sm font-medium text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-500" />
                Response from {result.recommended_provider}
              </h3>
              <div className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-wrap">{result.response}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
