import { useState, useCallback } from 'react'
import { Shield, AlertTriangle, CheckCircle, Zap } from 'lucide-react'

interface VerifyResult {
  trust_score: number
  trust_label: string
  summary: string
  issues: string[]
  word_count: number
}

export default function Verify() {
  const [text, setText] = useState('')
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [isAnimatingScore, setIsAnimatingScore] = useState(false)

  const verify = useCallback(async () => {
    if (!text.trim()) return
    setLoading(true)
    setIsAnimatingScore(true)

    // Show badge notification
    if ((window as any).trustLayerBadge?.show) {
      (window as any).trustLayerBadge.show()
    }

    try {
      const r = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      })
      const data = await r.json()
      setResult(data)

      // Update badge with result
      if ((window as any).trustLayerBadge?.complete) {
        (window as any).trustLayerBadge.complete(
          data.trust_score,
          `${data.trust_label} trust – ${data.issues.length > 0 ? `${data.issues.length} concern(s)` : 'No concerns'}`
        )
      }

      // Animate score
      setIsAnimatingScore(false)
      setTimeout(() => setIsAnimatingScore(false), 500)
    } finally {
      setLoading(false)
    }
  }, [text])

  const scoreColor = result
    ? result.trust_score >= 85 ? 'text-green-600 dark:text-green-400' : result.trust_score >= 60 ? 'text-amber-600 dark:text-amber-400' : 'text-red-600 dark:text-red-400'
    : ''

  const scoreRingColor = result
    ? result.trust_score >= 85 ? '#16a34a' : result.trust_score >= 60 ? '#d97706' : '#dc2626'
    : ''

  const wordCount = text.split(/\s+/).filter(Boolean).length

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Verify AI Output</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">Paste any AI-generated text to get a trust score and detailed analysis.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 sticky top-8">
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
              Content to verify
            </label>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              onKeyDown={e => {
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                  verify()
                }
              }}
              placeholder="Paste AI-generated content here... (Cmd/Ctrl + Enter to verify)"
              className="w-full h-64 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 mb-4"
            />
            <div className="flex items-center justify-between pt-4 border-t border-stone-100 dark:border-stone-800">
              <div className="flex items-center gap-4">
                <span className="text-xs text-stone-400 dark:text-stone-500">{wordCount} words</span>
                <span className="text-xs text-stone-300 dark:text-stone-600">
                  {wordCount > 0 && `~${Math.round(wordCount / 200)} min read`}
                </span>
              </div>
              <button
                onClick={verify}
                disabled={loading || !text.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
              >
                <Zap className="h-4 w-4" />
                {loading ? 'Analyzing...' : 'Verify'}
              </button>
            </div>
          </div>
        </div>

        {result && (
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 sticky top-8 space-y-6">
              <div className="text-center">
                <div className={`text-5xl font-bold ${scoreColor} transition-all duration-500 ${isAnimatingScore ? 'scale-110' : 'scale-100'}`}>
                  {result.trust_score}
                </div>
                <div className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium mt-2">{result.trust_label} trust</div>
                <div className="h-16 w-16 rounded-full border-4 flex items-center justify-center mx-auto mt-4" style={{
                  borderColor: scoreRingColor,
                  boxShadow: `0 0 20px ${scoreRingColor}30`
                }}>
                  {result.trust_score >= 85
                    ? <CheckCircle className="h-8 w-8 text-green-600 dark:text-green-400" />
                    : result.trust_score >= 60
                    ? <AlertTriangle className="h-8 w-8 text-amber-600 dark:text-amber-400" />
                    : <AlertTriangle className="h-8 w-8 text-red-600 dark:text-red-400" />}
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm text-stone-600 dark:text-stone-400 line-clamp-3">{result.summary}</p>
              </div>

              {result.issues.length === 0 && (
                <div className="text-xs text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-950/30 border border-green-200 dark:border-green-800 rounded-lg p-3 text-center">
                  No concerns detected
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {result && result.issues.length > 0 && (
        <div className="mt-6 bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
          <h3 className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-4 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            {result.issues.length} concern{result.issues.length !== 1 ? 's' : ''} found
          </h3>
          <div className="space-y-3">
            {result.issues.map((issue, i) => (
              <div key={i} className="flex gap-3 p-3 bg-stone-50 dark:bg-stone-800/50 rounded-lg">
                <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-stone-600 dark:text-stone-400">{issue}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
