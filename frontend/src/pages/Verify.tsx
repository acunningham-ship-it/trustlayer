import { useState } from 'react'
import { Shield, AlertTriangle, CheckCircle } from 'lucide-react'

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

  const verify = async () => {
    if (!text.trim()) return
    setLoading(true)
    try {
      const r = await fetch('/api/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text }),
      })
      setResult(await r.json())
    } finally {
      setLoading(false)
    }
  }

  const scoreColor = result
    ? result.trust_score >= 85 ? 'text-green-600' : result.trust_score >= 60 ? 'text-amber-600' : 'text-red-600'
    : ''

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Verify AI Output</h1>
        <p className="text-stone-500 mt-1">Paste any AI-generated text to get a trust score.</p>
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border p-6 mb-4">
        <textarea
          value={text}
          onChange={e => setText(e.target.value)}
          placeholder="Paste AI-generated content here..."
          className="w-full h-48 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400"
        />
        <div className="flex items-center justify-between mt-4 pt-4 border-t border-stone-100 dark:border-stone-800">
          <span className="text-xs text-stone-400">{text.split(/\s+/).filter(Boolean).length} words</span>
          <button
            onClick={verify}
            disabled={loading || !text.trim()}
            className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {loading ? 'Analyzing...' : 'Verify'}
          </button>
        </div>
      </div>

      {result && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className={`text-4xl font-bold ${scoreColor}`}>{result.trust_score}<span className="text-xl font-normal text-stone-400">/100</span></div>
              <div className="text-sm text-stone-500 mt-1 capitalize">{result.trust_label} trust</div>
            </div>
            <div className="h-16 w-16 rounded-full border-4 flex items-center justify-center" style={{
              borderColor: result.trust_score >= 85 ? '#16a34a' : result.trust_score >= 60 ? '#d97706' : '#dc2626'
            }}>
              {result.trust_score >= 85
                ? <CheckCircle className="h-8 w-8 text-green-600" />
                : <AlertTriangle className="h-8 w-8 text-amber-600" />}
            </div>
          </div>

          <p className="text-sm text-stone-600 dark:text-stone-400">{result.summary}</p>

          {result.issues.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-stone-700 dark:text-stone-300">Concerns</h3>
              {result.issues.map((issue, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-stone-600 dark:text-stone-400">
                  <AlertTriangle className="h-4 w-4 text-amber-500 flex-shrink-0 mt-0.5" />
                  {issue}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
