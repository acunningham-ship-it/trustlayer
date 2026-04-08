import { useEffect, useState, useRef } from 'react'
import { BookOpen, Upload, Search, Trash2 } from 'lucide-react'

export default function Knowledge() {
  const [items, setItems] = useState<any[]>([])
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [uploading, setUploading] = useState(false)
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

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Knowledge Base</h1>
        <p className="text-stone-500 mt-1">Your docs and notes, indexed locally. AI uses your context.</p>
      </div>

      <div className="flex gap-3 mb-6">
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-2 px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 text-sm font-medium rounded-lg hover:opacity-90 disabled:opacity-40"
        >
          <Upload className="h-4 w-4" />
          {uploading ? 'Uploading...' : 'Upload Document'}
        </button>
        <input ref={fileRef} type="file" className="hidden" onChange={upload} accept=".txt,.md,.pdf,.py,.js,.ts" />
      </div>

      <div className="flex gap-2 mb-6">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="Search your knowledge base..."
          className="flex-1 px-4 py-2 text-sm border border-stone-200 dark:border-stone-700 rounded-lg bg-white dark:bg-stone-900 text-stone-800 dark:text-stone-200 outline-none focus:ring-2 focus:ring-stone-300 dark:focus:ring-stone-600"
        />
        <button
          onClick={search}
          className="px-4 py-2 border border-stone-200 dark:border-stone-700 rounded-lg hover:bg-stone-50 dark:hover:bg-stone-800"
        >
          <Search className="h-4 w-4 text-stone-500" />
        </button>
      </div>

      {results.length > 0 && (
        <div className="mb-6 space-y-3">
          <h2 className="text-sm font-medium text-stone-700 dark:text-stone-300">Search results</h2>
          {results.map(r => (
            <div key={r.id} className="bg-white dark:bg-stone-900 rounded-xl border p-4">
              <div className="text-xs font-medium text-stone-600 dark:text-stone-400 mb-1">{r.filename}</div>
              <p className="text-sm text-stone-700 dark:text-stone-300">...{r.snippet}...</p>
            </div>
          ))}
        </div>
      )}

      <div className="space-y-2">
        {items.length === 0 ? (
          <div className="text-center py-12 text-stone-400">
            <BookOpen className="h-10 w-10 mx-auto mb-3 opacity-30" />
            <p className="text-sm">No documents indexed yet.</p>
            <p className="text-xs mt-1">Upload docs, notes, PDFs, or code to get started.</p>
          </div>
        ) : (
          items.map(item => (
            <div key={item.id} className="flex items-center justify-between bg-white dark:bg-stone-900 rounded-xl border px-4 py-3">
              <div>
                <div className="text-sm font-medium text-stone-700 dark:text-stone-300">{item.filename}</div>
                <div className="text-xs text-stone-400">{item.words} words</div>
              </div>
              <button onClick={() => remove(item.id)} className="text-stone-300 hover:text-red-500 transition-colors">
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
