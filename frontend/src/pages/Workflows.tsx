import { useEffect, useState } from 'react'
import { Workflow, Play, Plus } from 'lucide-react'

export default function Workflows() {
  const [templates, setTemplates] = useState<any[]>([])
  const [workflows, setWorkflows] = useState<any[]>([])
  const [running, setRunning] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<any>(null)

  const load = () => {
    fetch('/api/workflows/templates').then(r => r.json()).then(setTemplates).catch(() => {})
    fetch('/api/workflows/').then(r => r.json()).then(setWorkflows).catch(() => {})
  }

  useEffect(() => { load() }, [])

  const createFromTemplate = async (template: any) => {
    await fetch('/api/workflows/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: template.name, description: template.description, steps: template.steps }),
    })
    load()
  }

  const run = async (id: string) => {
    setRunning(id)
    try {
      const r = await fetch(`/api/workflows/${id}/run`, { method: 'POST' })
      setRunResult(await r.json())
    } finally {
      setRunning(null)
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Workflows</h1>
        <p className="text-stone-500 mt-1">No-code automations for your AI tasks.</p>
      </div>

      <div className="mb-8">
        <h2 className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">Templates</h2>
        <div className="grid gap-3">
          {templates.map(t => (
            <div key={t.id} className="flex items-center justify-between bg-white dark:bg-stone-900 rounded-xl border p-4">
              <div>
                <div className="font-medium text-sm text-stone-800 dark:text-stone-200">{t.name}</div>
                <div className="text-xs text-stone-400 mt-0.5">{t.description}</div>
                <div className="text-xs text-stone-300 dark:text-stone-600 mt-1">{t.steps.length} steps</div>
              </div>
              <button
                onClick={() => createFromTemplate(t)}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 border border-stone-200 dark:border-stone-700 rounded-lg hover:bg-stone-50 dark:hover:bg-stone-800 text-stone-600 dark:text-stone-400"
              >
                <Plus className="h-3.5 w-3.5" />
                Add
              </button>
            </div>
          ))}
        </div>
      </div>

      {workflows.length > 0 && (
        <div>
          <h2 className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">My Workflows</h2>
          <div className="space-y-3">
            {workflows.map(w => (
              <div key={w.id} className="flex items-center justify-between bg-white dark:bg-stone-900 rounded-xl border p-4">
                <div>
                  <div className="font-medium text-sm text-stone-800 dark:text-stone-200">{w.name}</div>
                  <div className="text-xs text-stone-400">{w.steps} steps</div>
                </div>
                <button
                  onClick={() => run(w.id)}
                  disabled={running === w.id}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 rounded-lg hover:opacity-90 disabled:opacity-40"
                >
                  <Play className="h-3.5 w-3.5" />
                  {running === w.id ? 'Running...' : 'Run'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {runResult && (
        <div className="mt-6 bg-stone-50 dark:bg-stone-900/50 rounded-xl border p-5">
          <div className="text-sm font-medium text-stone-700 dark:text-stone-300 mb-3">
            {runResult.name} — {runResult.status}
          </div>
          {runResult.log.map((step: any) => (
            <div key={step.step} className="text-xs text-stone-500 py-1">
              Step {step.step} ({step.type}): {step.output}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
