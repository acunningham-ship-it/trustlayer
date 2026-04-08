import { useEffect, useState, useRef } from 'react'
import { BookOpen, Upload, Search, Trash2, MessageCircle } from 'lucide-react'

export default function Knowledge() {
  const [items, setItems] = useState<any[]>([])
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
  const [question, setQuestion] = useState('')
  const [qaResult, setQaResult] = useState<any>(null)
  const [isAskingQuestion, setIsAskingQuestion] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const load = () => {
    fetch('/api/knowledge/').then(r => r.json()).then(setItems).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const upload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    try {
      await fetch('/api/knowledge/upload', { method: 'POST', body: form })
      load()
    } finally {
      setUploading(false)
    }
  }

  const search = async () => {
    if (!query.trim()) return
    const r = await fetch(`/api/knowledge/search?q=${encodeURIComponent(query)}`)
    setResults(await r.json())
  }

  const remove = async (id: string) => {
    await fetch(`/api/knowledge/${id}`, { method: 'DELETE' })
    load()
  }

  const askQuestion = async () => {
    if (!question.trim()) return
    setIsAskingQuestion(true)
    try {
      const r = await fetch('/api/knowledge/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
      })
      setQaResult(await r.json())
    } finally {
      setIsAskingQuestion(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Knowledge Base</h1>
        <p className="text-stone-500 mt-1">Your docs and notes, indexed locally. AI uses your context.</p>
      </div>

      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6 sticky top-8">
        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
              Upload documents
            </label>
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="flex items-center gap-2 px-4 py-3 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all w-full justify-center"
            >
              <Upload className="h-4 w-4" />
              {uploading ? 'Uploading...' : 'Upload Document'}
            </button>
            <input ref={fileRef} type="file" className="hidden" onChange={upload} accept=".txt,.md,.pdf,.py,.js,.ts" />
            <p className="text-xs text-stone-400 dark:text-stone-500 mt-2">Supported: TXT, MD, PDF, PY, JS, TS</p>
          </div>

          <div className="border-t border-stone-100 dark:border-stone-800 pt-4">
            <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
              Search documents
            </label>
            <div className="flex gap-2">
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && search()}
                placeholder="Search your knowledge base..."
                className="flex-1 px-3 py-2 text-sm border border-stone-200 dark:border-stone-700 rounded-lg bg-stone-50 dark:bg-stone-800 text-stone-800 dark:text-stone-200 outline-none focus:ring-2 focus:ring-stone-300 dark:focus:ring-stone-600"
              />
              <button
                onClick={search}
                className="px-3 py-2 border border-stone-200 dark:border-stone-700 rounded-lg hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors"
              >
                <Search className="h-4 w-4 text-stone-500" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {results.length > 0 && (
        <div className="mb-6 space-y-3">
          <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-2">
            <Search className="h-4 w-4 text-stone-500" />
            Search results ({results.length})
          </h2>
          {results.map(r => (
            <div key={r.id} className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-4 hover:shadow-lg transition-shadow">
              <div className="text-xs font-semibold text-stone-600 dark:text-stone-400 mb-2 uppercase tracking-wider">{r.filename}</div>
              <p className="text-sm text-stone-700 dark:text-stone-300 italic">...{r.snippet}...</p>
            </div>
          ))}
        </div>
      )}

      <div className="mb-8">
        <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-stone-500" />
          Documents ({items.length})
        </h2>
        {items.length === 0 ? (
          <div className="text-center py-16 bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800">
            <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-20" />
            <p className="text-sm text-stone-600 dark:text-stone-400 font-medium">No documents indexed yet.</p>
            <p className="text-xs text-stone-500 dark:text-stone-500 mt-1">Upload docs, notes, PDFs, or code to get started.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map(item => (
              <div key={item.id} className="flex items-center justify-between bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 px-4 py-3 hover:shadow-lg transition-shadow hover:bg-stone-50 dark:hover:bg-stone-800/50">
                <div>
                  <div className="text-sm font-medium text-stone-900 dark:text-stone-100">{item.filename}</div>
                  <div className="text-xs text-stone-400 dark:text-stone-500 mt-0.5">{item.words.toLocaleString()} words</div>
                </div>
                <button
                  onClick={() => remove(item.id)}
                  className="text-stone-400 dark:text-stone-600 hover:text-red-500 dark:hover:text-red-400 transition-colors"
                  aria-label="Delete document"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {items.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
            <MessageCircle className="h-4 w-4 text-stone-500" />
            Ask a Question
          </h2>
          <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium block mb-3">
                Your question
              </label>
              <textarea
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && e.ctrlKey && askQuestion()}
                placeholder="Ask anything about your knowledge base..."
                className="w-full h-32 text-sm bg-transparent outline-none resize-none text-stone-800 dark:text-stone-200 placeholder-stone-400 dark:placeholder-stone-500 border border-stone-200 dark:border-stone-700 rounded-lg p-3"
              />
            </div>
            <div className="flex justify-end pt-4 border-t border-stone-100 dark:border-stone-800">
              <button
                onClick={askQuestion}
                disabled={isAskingQuestion || !question.trim()}
                className="px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40 transition-all"
              >
                {isAskingQuestion ? 'Thinking...' : 'Ask'}
              </button>
            </div>

            {qaResult && !qaResult.error && (
              <div className="mt-6 pt-6 border-t border-stone-100 dark:border-stone-800 space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium mb-2">Answer</p>
                  <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-4">
                    <p className="text-sm text-stone-700 dark:text-stone-300 whitespace-pre-wrap">{qaResult.answer}</p>
                  </div>
                </div>
                {qaResult.sources && qaResult.sources.length > 0 && (
                  <div>
                    <p className="text-xs uppercase tracking-wider text-stone-500 dark:text-stone-400 font-medium mb-2">Sources</p>
                    <div className="space-y-2">
                      {qaResult.sources.map((source: string, i: number) => (
                        <div key={i} className="text-xs bg-stone-50 dark:bg-stone-800/50 rounded-lg p-2 text-stone-600 dark:text-stone-400">
                          📄 {source}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
