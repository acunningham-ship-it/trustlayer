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
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Workflows</h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">No-code automations for your AI tasks.</p>
      </div>

      {templates.length > 0 && (
        <div className="mb-8">
          <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
            <Plus className="h-4 w-4 text-stone-500" />
            Templates
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {templates.map(t => (
              <div key={t.id} className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-5 hover:shadow-lg transition-shadow flex flex-col">
                <div className="flex-1 mb-4">
                  <div className="font-semibold text-sm text-stone-900 dark:text-stone-100">{t.name}</div>
                  <div className="text-xs text-stone-500 dark:text-stone-400 mt-2">{t.description}</div>
                  <div className="flex items-center gap-1.5 text-xs text-stone-400 dark:text-stone-500 mt-3">
                    <Workflow className="h-3.5 w-3.5" />
                    {t.steps.length} step{t.steps.length !== 1 ? 's' : ''}
                  </div>
                </div>
                <button
                  onClick={() => createFromTemplate(t)}
                  className="w-full flex items-center justify-center gap-1.5 text-xs px-3 py-2 border border-stone-200 dark:border-stone-700 rounded-lg hover:bg-stone-50 dark:hover:bg-stone-800 text-stone-700 dark:text-stone-300 transition-colors font-medium"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Create from template
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {workflows.length > 0 && (
        <div>
          <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
            <Workflow className="h-4 w-4 text-stone-500" />
            My Workflows ({workflows.length})
          </h2>
          <div className="space-y-3">
            {workflows.map(w => (
              <div key={w.id} className="flex items-center justify-between bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-5 hover:shadow-lg transition-shadow">
                <div>
                  <div className="font-semibold text-sm text-stone-900 dark:text-stone-100">{w.name}</div>
                  <div className="flex items-center gap-2 text-xs text-stone-400 dark:text-stone-500 mt-2">
                    <Workflow className="h-3.5 w-3.5" />
                    {w.steps} step{w.steps !== 1 ? 's' : ''}
                  </div>
                </div>
                <button
                  onClick={() => run(w.id)}
                  disabled={running === w.id}
                  className="flex items-center gap-2 text-xs px-4 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 rounded-lg hover:opacity-90 disabled:opacity-40 transition-all font-medium"
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
        <div className="mt-8 bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6">
          <div className={`text-sm font-semibold mb-4 flex items-center gap-2 ${
            runResult.status === 'success'
              ? 'text-green-700 dark:text-green-400'
              : runResult.status === 'failed'
              ? 'text-red-700 dark:text-red-400'
              : 'text-stone-700 dark:text-stone-300'
          }`}>
            {runResult.status === 'success' && '✓'}
            {runResult.status === 'failed' && '✕'}
            {runResult.name} — {runResult.status}
          </div>
          <div className="space-y-2">
            {runResult.log.map((step: any) => (
              <div key={step.step} className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-3">
                <div className="text-xs font-medium text-stone-600 dark:text-stone-400 mb-1">
                  Step {step.step} <span className="text-stone-400 dark:text-stone-600">({step.type})</span>
                </div>
                <div className="text-xs text-stone-700 dark:text-stone-300">{step.output}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {templates.length === 0 && workflows.length === 0 && !runResult && (
        <div className="text-center py-16 bg-stone-50 dark:bg-stone-900/50 rounded-xl border border-stone-200 dark:border-stone-800">
          <Workflow className="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p className="text-sm text-stone-600 dark:text-stone-400 font-medium">No workflows available yet.</p>
          <p className="text-xs text-stone-500 dark:text-stone-500 mt-1">Create your first workflow from a template to get started.</p>
        </div>
      )}
    </div>
  )
}
