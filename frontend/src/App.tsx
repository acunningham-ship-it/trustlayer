import { Routes, Route } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar'
import TrustBadge from './components/TrustBadge'
import Dashboard from './pages/Dashboard'
import Verify from './pages/Verify'
import Connectors from './pages/Connectors'
import Compare from './pages/Compare'
import Costs from './pages/Costs'
import Knowledge from './pages/Knowledge'
import Workflows from './pages/Workflows'

export default function App() {
  const [darkMode, setDarkMode] = useState(
    () => window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode)
  }, [darkMode])

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar darkMode={darkMode} onToggleDark={() => setDarkMode(!darkMode)} />
      <main className="flex-1 overflow-y-auto p-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/verify" element={<Verify />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/compare" element={<Compare />} />
          <Route path="/costs" element={<Costs />} />
          <Route path="/knowledge" element={<Knowledge />} />
          <Route path="/workflows" element={<Workflows />} />
        </Routes>
      </main>
      <TrustBadge />
    </div>
  )
}
