import { useEffect, useState } from 'react'
import { Eye, EyeOff, Check, X, CheckCircle, Loader } from 'lucide-react'

export default function Settings() {
  const [apiKeys, setApiKeys] = useState({
    anthropic: '',
    openai: '',
    google: '',
    ollamaBaseUrl: ''
  })

  // Track which keys are already configured (so we can show badge without exposing full key)
  const [configured, setConfigured] = useState({
    anthropic: false,
    openai: false,
    google: false,
    ollama: false,
  })

  // Track which key fields have been edited by the user this session
  const [edited, setEdited] = useState<Record<string, boolean>>({})

  const [visibleKeys, setVisibleKeys] = useState({
    anthropic: false,
    openai: false,
    google: false
  })

  const [budget, setBudget] = useState<number | null>(null)
  const [testResults, setTestResults] = useState<Record<string, boolean | null>>({})
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)
  const [appVersion, setAppVersion] = useState('1.0.0')
  const [dataDirectory, setDataDirectory] = useState('/home/user/.trustlayer')
  const [isTestingAll, setIsTestingAll] = useState(false)
  const [testAllResults, setTestAllResults] = useState<Record<string, {status: boolean, latency?: number}> | null>(null)

  useEffect(() => {
    // Load settings from API
    fetch('/api/settings').then(r => r.json()).then(settings => {
      if (settings.apiKeys) {
        setApiKeys(settings.apiKeys)
      }
      if (settings.configured) {
        setConfigured(settings.configured)
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
    setApiKeys(prev => ({ ...prev, [provider]: value }))
    setEdited(prev => ({ ...prev, [provider]: true }))
  }

  const testProvider = async (provider: string) => {
    setTestResults(prev => ({ ...prev, [provider]: null }))
    try {
      const response = await fetch(`/api/settings/test-provider/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          apiKey: apiKeys[provider as keyof typeof apiKeys],
          baseUrl: provider === 'ollama' ? apiKeys.ollamaBaseUrl : undefined
        })
      })
      const data = await response.json()
      setTestResults(prev => ({ ...prev, [provider]: data.status === true }))
    } catch {
      setTestResults(prev => ({ ...prev, [provider]: false }))
    }
  }

  const saveSettings = async () => {
    setIsSaving(true)
    setSaveSuccess(false)
    try {
      // Only send keys that were actually edited this session
      // (avoid saving masked placeholder values back)
      const keysToSend: Record<string, string> = {}
      for (const [k, v] of Object.entries(apiKeys)) {
        if (edited[k]) keysToSend[k] = v
      }
      // Always include ollamaBaseUrl if it was edited
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ apiKeys: keysToSend, budget })
      })
      if (response.ok) {
        setSaveSuccess(true)
        setEdited({})
        setTimeout(() => setSaveSuccess(false), 3000)
      }
    } catch {
      // silent fail — user can retry
    } finally {
      setIsSaving(false)
    }
  }

  const testAllProviders = async () => {
    setIsTestingAll(true)
    setTestAllResults(null)
    try {
      const response = await fetch('/api/settings/test-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const data = await response.json()
      setTestAllResults(data.results || {})
    } catch {
      setTestAllResults({})
    } finally {
      setIsTestingAll(false)
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
          {/* Reusable provider row renderer */}
          {([
            { id: 'anthropic', label: 'Anthropic API Key', placeholder: 'sk-ant-...', secret: true },
            { id: 'openai', label: 'OpenAI API Key', placeholder: 'sk-...', secret: true },
            { id: 'google', label: 'Google API Key', placeholder: 'AIza...', secret: true },
          ] as const).map(({ id, label, placeholder, secret }) => (
            <div key={id} className="space-y-2">
              <div className="flex items-center gap-2">
                <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
                  {label}
                </label>
                {configured[id] && !edited[id] && (
                  <span className="inline-flex items-center gap-1 text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
                    <CheckCircle className="h-3 w-3" /> Configured
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <input
                    type={secret && !visibleKeys[id as keyof typeof visibleKeys] ? 'password' : 'text'}
                    value={apiKeys[id as keyof typeof apiKeys]}
                    onChange={(e) => handleKeyChange(id, e.target.value)}
                    className="w-full px-3 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 rounded-lg text-stone-900 dark:text-stone-100 placeholder-stone-400 dark:placeholder-stone-500 text-sm"
                    placeholder={configured[id] && !edited[id] ? '••••••••••••' : placeholder}
                  />
                  {secret && (
                    <button
                      onClick={() => toggleKeyVisibility(id)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-500 hover:text-stone-700 dark:hover:text-stone-300"
                    >
                      {visibleKeys[id as keyof typeof visibleKeys] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  )}
                </div>
                <button
                  onClick={() => testProvider(id)}
                  className="px-4 py-2 border border-stone-300 dark:border-stone-700 rounded-lg text-sm font-medium text-stone-700 dark:text-stone-300 hover:bg-stone-50 dark:hover:bg-stone-800 transition-colors"
                >
                  Test
                </button>
                {testResults[id] !== undefined && testResults[id] !== null && (
                  <div className={`flex items-center ${testResults[id] ? 'text-green-600' : 'text-red-600'}`}>
                    {testResults[id] ? <Check className="h-5 w-5" /> : <X className="h-5 w-5" />}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Ollama */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <label className="block text-sm font-medium text-stone-700 dark:text-stone-300">
                Ollama Base URL
              </label>
              {configured.ollama && (
                <span className="inline-flex items-center gap-1 text-xs text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
                  <CheckCircle className="h-3 w-3" /> Detected
                </span>
              )}
            </div>
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
              {testResults.ollama !== undefined && testResults.ollama !== null && (
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
              href="https://github.com/acunningham-ship-it/trustlayer"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
            >
              GitHub Repository →
            </a>
          </div>
        </div>
      </div>

      {/* Test All and Save Buttons */}
      <div className="flex flex-col gap-4 mb-6">
        <div className="flex items-center gap-4">
          <button
            onClick={testAllProviders}
            disabled={isTestingAll}
            className="px-6 py-2 border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-800 text-stone-900 dark:text-stone-100 rounded-lg text-sm font-medium hover:bg-stone-50 dark:hover:bg-stone-700 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isTestingAll && <Loader className="h-4 w-4 animate-spin" />}
            Test All Providers
          </button>
          <button
            onClick={saveSettings}
            disabled={isSaving}
            className="px-6 py-2 bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 rounded-lg text-sm font-medium hover:bg-stone-800 dark:hover:bg-stone-200 transition-colors disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Settings'}
          </button>
          {saveSuccess && (
            <span className="flex items-center gap-1.5 text-sm text-green-700 dark:text-green-400">
              <CheckCircle className="h-4 w-4" /> Settings saved
            </span>
          )}
        </div>

        {testAllResults && (
          <div className="bg-stone-50 dark:bg-stone-800/50 rounded-lg p-4 space-y-2">
            <p className="text-xs uppercase tracking-wider font-medium text-stone-600 dark:text-stone-400 mb-3">Test Results</p>
            <div className="space-y-2">
              {Object.entries(testAllResults).map(([provider, result]) => (
                <div key={provider} className="flex items-center justify-between text-sm">
                  <span className="capitalize text-stone-700 dark:text-stone-300">{provider}</span>
                  <div className="flex items-center gap-2">
                    {result.status ? (
                      <>
                        <Check className="h-4 w-4 text-green-600" />
                        {result.latency && <span className="text-xs text-stone-500">{result.latency}ms</span>}
                      </>
                    ) : (
                      <X className="h-4 w-4 text-red-600" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
