import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function getStatusColor(status: string) {
  const map: Record<string, { bg: string; text: string; dot: string }> = {
    active: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
    paused: { bg: 'bg-amber-500/10', text: 'text-amber-400', dot: 'bg-amber-400' },
    closed: { bg: 'bg-slate-500/10', text: 'text-slate-400', dot: 'bg-slate-500' },
    new: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', dot: 'bg-cyan-400' },
    screening: { bg: 'bg-purple-500/10', text: 'text-purple-400', dot: 'bg-purple-400' },
    interview: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', dot: 'bg-indigo-400' },
    offer: { bg: 'bg-amber-500/10', text: 'text-amber-400', dot: 'bg-amber-400' },
    hired: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
    rejected: { bg: 'bg-red-500/10', text: 'text-red-400', dot: 'bg-red-400' },
  }
  return map[status] ?? map.new!
}

export function getTagColors(color: string) {
  const map: Record<string, { bg: string; text: string }> = {
    purple: { bg: 'bg-purple-500/15', text: 'text-purple-300' },
    cyan: { bg: 'bg-cyan-500/15', text: 'text-cyan-300' },
    emerald: { bg: 'bg-emerald-500/15', text: 'text-emerald-300' },
    amber: { bg: 'bg-amber-500/15', text: 'text-amber-300' },
    pink: { bg: 'bg-pink-500/15', text: 'text-pink-300' },
    red: { bg: 'bg-red-500/15', text: 'text-red-300' },
    indigo: { bg: 'bg-indigo-500/15', text: 'text-indigo-300' },
  }
  return map[color] ?? map.purple!
}

export function getScoreColor(score: number): string {
  if (score >= 85) return '#10B981'
  if (score >= 70) return '#06B6D4'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}
