import { NavLink } from 'react-router-dom'
import {
  Shield, Zap, GitCompare, DollarSign, BookOpen,
  Clock, LayoutDashboard, Moon, Sun, Settings as SettingsIcon, Brain
} from 'lucide-react'
import clsx from 'clsx'

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/verify', label: 'Verify', icon: Shield },
  { to: '/connectors', label: 'Connectors', icon: Zap },
  { to: '/compare', label: 'Compare', icon: GitCompare },
  { to: '/costs', label: 'Costs', icon: DollarSign },
  { to: '/knowledge', label: 'Knowledge', icon: BookOpen },
  { to: '/history', label: 'History', icon: Clock },
  { to: '/profile', label: 'Profile', icon: Brain },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
]

interface Props {
  darkMode: boolean
  onToggleDark: () => void
}

export default function Sidebar({ darkMode, onToggleDark }: Props) {
  return (
    <aside className="w-56 flex-shrink-0 border-r border-stone-200 dark:border-stone-800 bg-white dark:bg-stone-900 flex flex-col">
      <div className="px-5 py-6 border-b border-stone-100 dark:border-stone-800">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-stone-700 dark:text-stone-300" />
          <span className="font-semibold text-stone-900 dark:text-stone-100 tracking-tight">TrustLayer</span>
        </div>
        <p className="text-xs text-stone-500 mt-1">You bring the AI. We bring the trust.</p>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5">
        {nav.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                isActive
                  ? 'bg-stone-100 dark:bg-stone-800 text-stone-900 dark:text-stone-100 font-medium'
                  : 'text-stone-500 hover:text-stone-900 dark:text-stone-400 dark:hover:text-stone-100 hover:bg-stone-50 dark:hover:bg-stone-800/50'
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-stone-100 dark:border-stone-800">
        <button
          onClick={onToggleDark}
          className="flex items-center gap-2 text-xs text-stone-500 hover:text-stone-700 dark:hover:text-stone-300 transition-colors"
        >
          {darkMode ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {darkMode ? 'Light mode' : 'Dark mode'}
        </button>
      </div>
    </aside>
  )
}
