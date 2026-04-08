import { Eye } from "lucide-react"

export default function AuditLog() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <Eye className="h-6 w-6 text-stone-600 dark:text-stone-400" />
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">
          Agent Audit Log
        </h1>
      </div>

      <div className="rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-800 p-8 text-center">
        <Eye className="h-10 w-10 text-stone-400 dark:text-stone-500 mx-auto mb-4" />
        <h2 className="text-lg font-medium text-stone-700 dark:text-stone-300 mb-2">
          Monitor what AI tools do on your filesystem.
        </h2>
        <p className="text-stone-500 dark:text-stone-400">
          Coming soon — will track file changes made by Claude Code, Codex, and other AI agents.
        </p>
      </div>
    </div>
  )
}
