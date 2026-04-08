import { useEffect, useState } from 'react'
import { User, Brain, TrendingUp, Trash2, Sparkles, Clock, BarChart3 } from 'lucide-react'

interface ProfileData {
  [key: string]: any
}

interface Insights {
  total_interactions: number
  top_providers: { provider: string; count: number }[]
  personalization_level: number
  message: string
}

export default function Profile() {
  const [profile, setProfile] = useState<ProfileData>({})
  const [insights, setInsights] = useState<Insights | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const [profileRes, insightsRes] = await Promise.all([
        fetch('/api/learn/profile').then(r => r.json()),
        fetch('/api/learn/insights').then(r => r.json()),
      ])
      setProfile(profileRes)
      setInsights(insightsRes)
    } catch {
      // empty
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const deleteKey = async (key: string) => {
    await fetch(`/api/learn/profile/${encodeURIComponent(key)}`, { method: 'DELETE' })
    load()
  }

  // Filter out settings.* keys — those belong in Settings page
  const profileKeys = Object.entries(profile).filter(([k]) => !k.startsWith('settings.'))
  const settingsKeys = Object.entries(profile).filter(([k]) => k.startsWith('settings.'))

  const level = insights?.personalization_level ?? 0
  const levelLabel = level >= 80 ? 'Expert' : level >= 50 ? 'Familiar' : level >= 20 ? 'Learning' : 'New'
  const levelColor = level >= 80 ? 'text-green-600 dark:text-green-400' : level >= 50 ? 'text-amber-600 dark:text-amber-400' : 'text-stone-500 dark:text-stone-400'

  if (loading) {
    return (
      <div className="max-w-4xl">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-stone-200 dark:bg-stone-800 rounded w-48"></div>
          <div className="h-4 bg-stone-100 dark:bg-stone-800 rounded w-64"></div>
          <div className="h-48 bg-stone-100 dark:bg-stone-800 rounded-xl"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100 flex items-center gap-3">
          <Brain className="h-6 w-6 text-stone-500" />
          Your Profile
        </h1>
        <p className="text-stone-500 dark:text-stone-400 mt-1">
          What TrustLayer has learned about how you work.
        </p>
      </div>

      {/* Personalization Level */}
      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-stone-100 dark:bg-stone-800 flex items-center justify-center">
              <Sparkles className="h-6 w-6 text-stone-500 dark:text-stone-400" />
            </div>
            <div>
              <div className="font-semibold text-stone-900 dark:text-stone-100">Personalization Level</div>
              <div className={`text-sm font-medium ${levelColor}`}>{levelLabel} — {level}%</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-stone-900 dark:text-stone-100">{insights?.total_interactions ?? 0}</div>
            <div className="text-xs text-stone-500">total sessions</div>
          </div>
        </div>

        {/* Progress bar */}
        <div className="w-full bg-stone-100 dark:bg-stone-800 rounded-full h-2 mb-3">
          <div
            className="h-2 rounded-full transition-all duration-1000 bg-gradient-to-r from-stone-400 to-green-500"
            style={{ width: `${Math.min(100, level)}%` }}
          />
        </div>
        <p className="text-xs text-stone-500 dark:text-stone-400">{insights?.message}</p>
      </div>

      {/* Top Providers */}
      {insights && insights.top_providers.length > 0 && (
        <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
          <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-stone-500" />
            Your Most Used Providers
          </h2>
          <div className="space-y-3">
            {insights.top_providers.map((p) => {
              const maxCount = insights.top_providers[0]?.count ?? 1
              const pct = Math.round((p.count / maxCount) * 100)
              return (
                <div key={p.provider} className="flex items-center gap-3">
                  <div className="w-24 text-sm font-medium text-stone-700 dark:text-stone-300 capitalize">{p.provider}</div>
                  <div className="flex-1 bg-stone-100 dark:bg-stone-800 rounded-full h-2">
                    <div className="h-2 rounded-full bg-stone-500 dark:bg-stone-400 transition-all" style={{ width: `${pct}%` }} />
                  </div>
                  <div className="text-xs text-stone-500 w-12 text-right">{p.count}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* What TrustLayer Knows */}
      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
        <h2 className="text-sm font-semibold text-stone-900 dark:text-stone-100 mb-4 flex items-center gap-2">
          <User className="h-4 w-4 text-stone-500" />
          What TrustLayer Knows About You
        </h2>

        {profileKeys.length === 0 ? (
          <div className="text-center py-8">
            <Brain className="h-10 w-10 mx-auto mb-3 opacity-20" />
            <p className="text-sm text-stone-500 dark:text-stone-400">Nothing yet — TrustLayer will learn as you use it.</p>
            <p className="text-xs text-stone-400 dark:text-stone-500 mt-1">Your preferences, writing style, and common tasks are stored locally.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {profileKeys.map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-4 p-3 bg-stone-50 dark:bg-stone-800/50 rounded-lg group">
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-medium text-stone-500 dark:text-stone-400 uppercase tracking-wider">{key.replace(/_/g, ' ')}</div>
                  <div className="text-sm text-stone-800 dark:text-stone-200 mt-0.5 break-words">
                    {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
                  </div>
                </div>
                <button
                  onClick={() => deleteKey(key)}
                  className="opacity-0 group-hover:opacity-100 p-1.5 text-stone-400 hover:text-red-500 transition-all rounded"
                  title="Forget this"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Privacy Notice */}
      <div className="flex items-start gap-3 p-4 bg-stone-50 dark:bg-stone-800/30 rounded-xl border border-stone-200 dark:border-stone-800">
        <Clock className="h-4 w-4 text-stone-400 mt-0.5 flex-shrink-0" />
        <div>
          <p className="text-xs text-stone-600 dark:text-stone-400">
            <span className="font-medium">All data stays on your machine.</span> TrustLayer never sends your profile, preferences, or usage data to any external server. You can delete any learned data at any time.
          </p>
        </div>
      </div>
    </div>
  )
}
