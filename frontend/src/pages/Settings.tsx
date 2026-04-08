import { useEffect, useState } from 'react'
import { Eye, EyeOff, Check, X } from 'lucide-react'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState({
    anthropic: '',
    openai: '',
    google: '',
    ollamaBaseUrl: ''
  })

  const [visibleKeys, setVisibleKeys] = useState({
    anthropic: false,
    openai: false,
    google: false
  })

  const [budget, setBudget] = useState<number | null>(null)
  const [testResults, setTestResults] = useState<Record<string, boolean | null>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [appVersion, setAppVersion] = useState('1.0.0')
  const [dataDirectory, setDataDirectory] = useState('/home/user/.trustlayer')

  useEffect(() => {
    // Load settings from API
    fetch('/api/settings').then(r => r.json()).then(settings => {
      if (settings.apiKeys) {
        setApiKeys(settings.apiKeys)
      }
      if (settings.budget) {
        setBudget(settings.budget)
      }
    }).catch(() => {})

    // Load app info
    fetch('/api/info').then(r => r.json()).then(info => {
      setAppVersion(info.version || '1.0.0')
      setDataDirectory(info.dataDir || '/home/user/.trustlayer')
    }).catch(() => {})
  }, [])

  const toggleKeyVisibility = (provider: string) => {
    setVisibleKeys(prev => ({
      ...prev,
      [provider]: !prev[provider]
    }))
  }

  const handleKeyChange = (provider: string, value: string) => {
    setApiKeys(prev => ({
      ...prev,
      [provider]: value
    }))
  }

  const testProvider = async (provider: string) => {
    setTestResults(prev => ({
      ...prev,
      [provider]: null
    }))

    try {
      const response = await fetch(`/api/test-provider/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          apiKey: apiKeys[provider as keyof typeof apiKeys],
          baseUrl: provider === 'ollama' ? apiKeys.ollamaBaseUrl : undefined
        })
      })

      const success = response.ok
      setTestResults(prev => ({
        ...prev,
        [provider]: success
      }))
    } catch {
      setTestResults(prev => ({
        ...prev,
        [provider]: false
      }))
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)
    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          apiKeys,
          budget
        })
      })

      if (response.ok) {
        // Success message could go here
      }
    } catch {
      // Error handling
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-stone-900 dark:text-stone-100">Settings</h1>
        <p className="text-stone-500 mt-1">Configure your AI providers, budget, and preferences.</p>
      </div>

      {/* AI Providers Section */}
      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
        <h2 className="font-semibold text-stone-900 dark:text-stone-100 mb-6 text-lg">AI Providers</h2>

        <div className="space-y-6">
          {/* Anthropic */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
              Anthropic API Key
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={visibleKeys.anthropic ? 'text' : 'password'}
                  value={apiKeys.anthropic}
                  onChange={(e) => handleKeyChange('anthropic', e.target.value)}
                  className="w-full px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
                  placeholder="sk-ant-..."
                />
                <button
                  onClick={() => toggleKeyVisibility('anthropic')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
                >
                  {visibleKeys.anthropic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <button
                onClick={() => testProvider('anthropic')}
                className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-lg text-sm font-medium text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
              >
                Test
              </button>
              {testResults.anthropic !== null && (
                <div className={`flex items-center ${testResults.anthropic ? 'text-green-600' : 'text-red-600'}`}>
                  {testResults.anthropic ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                </div>
              )}
            </div>
          </div>

          {/* OpenAI */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
              OpenAI API Key
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={visibleKeys.openai ? 'text' : 'password'}
                  value={apiKeys.openai}
                  onChange={(e) => handleKeyChange('openai', e.target.value)}
                  className="w-full px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
                  placeholder="sk-..."
                />
                <button
                  onClick={() => toggleKeyVisibility('openai')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
                >
                  {visibleKeys.openai ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <button
                onClick={() => testProvider('openai')}
                className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-lg text-sm font-medium text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
              >
                Test
              </button>
              {testResults.openai !== null && (
                <div className={`flex items-center ${testResults.openai ? 'text-green-600' : 'text-red-600'}`}>
                  {testResults.openai ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                </div>
              )}
            </div>
          </div>

          {/* Google */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
              Google API Key
            </label>
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type={visibleKeys.google ? 'text' : 'password'}
                  value={apiKeys.google}
                  onChange={(e) => handleKeyChange('google', e.target.value)}
                  className="w-full px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
                  placeholder="AIza..."
                />
                <button
                  onClick={() => toggleKeyVisibility('google')}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
                >
                  {visibleKeys.google ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              <button
                onClick={() => testProvider('google')}
                className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-lg text-sm font-medium text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
              >
                Test
              </button>
              {testResults.google !== null && (
                <div className={`flex items-center ${testResults.google ? 'text-green-600' : 'text-red-600'}`}>
                  {testResults.google ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                </div>
              )}
            </div>
          </div>

          {/* Ollama */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
              Ollama Base URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={apiKeys.ollamaBaseUrl}
                onChange={(e) => handleKeyChange('ollamaBaseUrl', e.target.value)}
                className="flex-1 px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
                placeholder="http://localhost:11434"
              />
              <button
                onClick={() => testProvider('ollama')}
                className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-lg text-sm font-medium text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
              >
                Test
              </button>
              {testResults.ollama !== null && (
                <div className={`flex items-center ${testResults.ollama ? 'text-green-600' : 'text-red-600'}`}>
                  {testResults.ollama ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Budget Section */}
      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
        <h2 className="font-semibold text-stone-900 dark:text-stone-100 mb-6 text-lg">Budget</h2>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
            Monthly Budget Limit (USD)
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              value={budget ?? ''}
              onChange={(e) => setBudget(e.target.value ? parseFloat(e.target.value) : null)}
              min="0"
              step="10"
              className="flex-1 px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
              placeholder="100.00"
            />
            <span className="flex items-center px-3 text-stone-500 dark:text-stone-400">USD</span>
          </div>
          <p className="text-xs text-stone-500 dark:text-stone-400 mt-2">
            You'll receive alerts when approaching this limit.
          </p>
        </div>
      </div>

      {/* About Section */}
      <div className="bg-white dark:bg-stone-900 rounded-xl border border-stone-200 dark:border-stone-800 p-6 mb-6">
        <h2 className="font-semibold text-stone-900 dark:text-stone-100 mb-6 text-lg">About</h2>

        <div className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wider font-medium text-stone-500 dark:text-stone-400 mb-1">
              Version
            </p>
            <p className="text-sm text-stone-900 dark:text-stone-100">{appVersion}</p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider font-medium text-stone-500 dark:text-stone-400 mb-1">
              Data Directory
            </p>
            <p className="text-sm text-stone-900 dark:text-stone-100 font-mono break-all">{dataDirectory}</p>
          </div>

          <div>
            <p className="text-xs uppercase tracking-wider font-medium text-stone-500 dark:text-stone-400 mb-3">
              Links
            </p>
            <a
              href="https://github.com/anthropics/trustlayer"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              GitHub Repository →
            </a>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex gap-3">
        <button
          onClick={saveSettings}
          disabled={isSaving}
          className="px-6 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 rounded-lg text-sm font-medium hover:bg-stone-800 dark:hover:bg-stone-200 transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
