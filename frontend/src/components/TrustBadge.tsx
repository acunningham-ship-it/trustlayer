import { useEffect, useState } from 'react'

interface TrustBadgeState {
  visible: boolean
  status: 'verifying' | 'verified' | 'warning' | 'error'
  score?: number
  message?: string
}

// Inline SVG icons to avoid external dependencies
const SpinnerIcon = ({ className }: { className: string }) => (
  <svg className={`${className} animate-spin`} fill="none" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
  </svg>
)

const CheckIcon = ({ className }: { className: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" />
    <path d="M8 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

const WarningIcon = ({ className }: { className: string }) => (
  <svg className={className} fill="currentColor" viewBox="0 0 24 24">
    <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z" />
  </svg>
)

export default function TrustBadge() {
  const [state, setState] = useState<TrustBadgeState>({
    visible: false,
    status: 'verifying',
  })

  const handleVerificationStart = () => {
    setState({ visible: true, status: 'verifying' })
  }

  const handleVerificationComplete = (score: number, message: string) => {
    const status = score >= 85 ? 'verified' : score >= 60 ? 'warning' : 'error'
    setState({ visible: true, status, score, message })
    // Auto-hide after 4 seconds
    setTimeout(() => setState(prev => ({ ...prev, visible: false })), 4000)
  }

  const handleDismiss = () => {
    setState(prev => ({ ...prev, visible: false }))
  }

  // Expose methods globally for integration
  useEffect(() => {
    ;(window as any).trustLayerBadge = {
      show: handleVerificationStart,
      complete: handleVerificationComplete,
      hide: handleDismiss,
    }
  }, [])

  if (!state.visible) return null

  const bgColor = {
    verifying: 'bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800',
    verified: 'bg-green-50 dark:bg-green-950/30 border-green-200 dark:border-green-800',
    warning: 'bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800',
    error: 'bg-red-50 dark:bg-red-950/30 border-red-200 dark:border-red-800',
  }[state.status]

  const textColor = {
    verifying: 'text-blue-700 dark:text-blue-400',
    verified: 'text-green-700 dark:text-green-400',
    warning: 'text-amber-700 dark:text-amber-400',
    error: 'text-red-700 dark:text-red-400',
  }[state.status]

  const iconColor = {
    verifying: 'text-blue-500',
    verified: 'text-green-500',
    warning: 'text-amber-500',
    error: 'text-red-500',
  }[state.status]

  return (
    <div
      className={`fixed bottom-6 right-6 max-w-sm animate-in fade-in slide-in-from-bottom-4 ${bgColor} border rounded-xl p-4 shadow-lg z-50`}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">
          {state.status === 'verifying' && (
            <SpinnerIcon className={`h-5 w-5 ${iconColor}`} />
          )}
          {state.status === 'verified' && (
            <CheckIcon className={`h-5 w-5 ${iconColor}`} />
          )}
          {(state.status === 'warning' || state.status === 'error') && (
            <WarningIcon className={`h-5 w-5 ${iconColor}`} />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className={`text-sm font-medium ${textColor}`}>
            {state.status === 'verifying' && 'Verifying content...'}
            {state.status === 'verified' && 'Verification complete'}
            {state.status === 'warning' && 'Review recommended'}
            {state.status === 'error' && 'Verification failed'}
          </div>
          {state.score !== undefined && (
            <div className={`text-xs ${textColor} opacity-90 mt-1`}>
              Trust score: {state.score}/100
            </div>
          )}
          {state.message && (
            <div className={`text-xs ${textColor} opacity-75 mt-1`}>
              {state.message}
            </div>
          )}
        </div>
        <button
          onClick={handleDismiss}
          className={`flex-shrink-0 text-2xl leading-none ${textColor} hover:opacity-70 transition-opacity`}
          aria-label="Close notification"
        >
          ×
        </button>
      </div>
    </div>
  )
}
