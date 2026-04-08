import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TrustBadge from './components/TrustBadge'
import Dashboard from './pages/Dashboard'
import Verify from './pages/Verify'
import Connectors from './pages/Connectors'
import Compare from './pages/Compare'
import SmartRouter from './pages/SmartRouter'
import Consistency from './pages/Consistency'
import Costs from './pages/Costs'
import Knowledge from './pages/Knowledge'
import History from './pages/History'
import Settings from './pages/Settings'
import AuditLog from './pages/AuditLog'
import Profile from './pages/Profile'

export default function App() {
  const [darkMode, setDarkMode] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )
  const [hasAnyKey, setHasAnyKey] = useState<boolean | null>(null)
  const location = useLocation()

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  useEffect(() => {
    // Check if the user has configured at least one API key
    fetch('/api/settings')
      .then(r => r.json())
      .then(settings => {
        const cfg = settings.configured ?? {}
        const anyConfigured = Object.values(cfg).some(Boolean)
        setHasAnyKey(anyConfigured)
      })
      .catch(() => setHasAnyKey(false))
  }, [location.pathname]) // Re-check after navigating (e.g. after saving settings)

  // Show nothing until we know whether keys are set
  if (hasAnyKey === null) return null

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar darkMode={darkMode} onToggleDark={() => setDarkMode(!darkMode)} />
      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          {/* Redirect new users to Settings first */}
          <Route path="/" element={hasAnyKey ? <Dashboard /> : <Navigate to="/settings" replace />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/smart-router" element={<SmartRouter />} />
          <Route path="/consistency" element={<Consistency />} />
          <Route path="/costs" element={<Costs />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/history" element={<History />} />
          <Route path="/audit" element={<AuditLog />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
      <TrustBadge />
    </div>
  )
}
