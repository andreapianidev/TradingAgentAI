import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, decimals = 2): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}

export function formatDate(date: string | Date): string {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(date))
}

export function formatTimeAgo(date: string | Date): string {
  const now = new Date()
  const past = new Date(date)
  const diffMs = now.getTime() - past.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return `${diffSecs}s ago`
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}

export function getPnlColor(value: number): string {
  if (value > 0) return 'text-green-500'
  if (value < 0) return 'text-red-500'
  return 'text-gray-500'
}

export function getDirectionColor(direction: 'long' | 'short'): string {
  return direction === 'long' ? 'text-green-500' : 'text-red-500'
}

export function getDirectionBgColor(direction: 'long' | 'short'): string {
  return direction === 'long' ? 'bg-green-500/10 text-green-500' : 'bg-red-500/10 text-red-500'
}

export function getStatusColor(status: string): string {
  switch (status) {
    case 'open':
    case 'running':
    case 'executed':
      return 'bg-green-500/10 text-green-500'
    case 'closed':
    case 'completed':
      return 'bg-blue-500/10 text-blue-500'
    case 'pending':
      return 'bg-yellow-500/10 text-yellow-500'
    case 'failed':
    case 'skipped':
      return 'bg-red-500/10 text-red-500'
    default:
      return 'bg-gray-500/10 text-gray-500'
  }
}

export function getSeverityColor(severity: 'info' | 'warning' | 'critical'): string {
  switch (severity) {
    case 'info':
      return 'bg-blue-500/10 text-blue-500'
    case 'warning':
      return 'bg-yellow-500/10 text-yellow-500'
    case 'critical':
      return 'bg-red-500/10 text-red-500'
    default:
      return 'bg-gray-500/10 text-gray-500'
  }
}

export function truncateAddress(address: string, chars = 4): string {
  return `${address.slice(0, chars + 2)}...${address.slice(-chars)}`
}
