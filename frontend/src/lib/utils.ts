import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

type StatusStyles = {
  bg: string
  text: string
  dot: string
}

const statusStyles: Record<string, StatusStyles> = {
  active: {
    bg: 'bg-aurora-emerald/10 border border-aurora-emerald/20',
    text: 'text-aurora-emerald',
    dot: 'bg-aurora-emerald',
  },
  paused: {
    bg: 'bg-aurora-amber/10 border border-aurora-amber/20',
    text: 'text-aurora-amber',
    dot: 'bg-aurora-amber',
  },
  closed: {
    bg: 'bg-slate-500/10 border border-slate-500/20',
    text: 'text-slate-400',
    dot: 'bg-slate-500',
  },
  new: {
    bg: 'bg-aurora-cyan/10 border border-aurora-cyan/20',
    text: 'text-aurora-cyan',
    dot: 'bg-aurora-cyan',
  },
  screening: {
    bg: 'bg-aurora-purple/10 border border-aurora-purple/20',
    text: 'text-aurora-violet',
    dot: 'bg-aurora-purple',
  },
  interview: {
    bg: 'bg-indigo-500/10 border border-indigo-400/20',
    text: 'text-indigo-300',
    dot: 'bg-indigo-400',
  },
  offer: {
    bg: 'bg-emerald-500/10 border border-emerald-400/20',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  hired: {
    bg: 'bg-emerald-500/10 border border-emerald-400/20',
    text: 'text-emerald-300',
    dot: 'bg-emerald-400',
  },
  rejected: {
    bg: 'bg-red-500/10 border border-red-400/20',
    text: 'text-red-300',
    dot: 'bg-red-400',
  },
}

const tagColorStyles: Record<string, Omit<StatusStyles, 'dot'>> = {
  purple: {
    bg: 'bg-aurora-purple/10 border border-aurora-purple/20',
    text: 'text-aurora-violet',
  },
  cyan: {
    bg: 'bg-aurora-cyan/10 border border-aurora-cyan/20',
    text: 'text-aurora-cyan',
  },
  emerald: {
    bg: 'bg-aurora-emerald/10 border border-aurora-emerald/20',
    text: 'text-aurora-emerald',
  },
  amber: {
    bg: 'bg-aurora-amber/10 border border-aurora-amber/20',
    text: 'text-aurora-amber',
  },
  pink: {
    bg: 'bg-pink-500/10 border border-pink-400/20',
    text: 'text-pink-300',
  },
  red: {
    bg: 'bg-red-500/10 border border-red-400/20',
    text: 'text-red-300',
  },
  indigo: {
    bg: 'bg-indigo-500/10 border border-indigo-400/20',
    text: 'text-indigo-300',
  },
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(value: string) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return value
  }

  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

export function getStatusColor(status: string): StatusStyles {
  return statusStyles[status] ?? {
    bg: 'bg-slate-500/10 border border-slate-500/20',
    text: 'text-slate-400',
    dot: 'bg-slate-500',
  }
}

export function getTagColors(color: string) {
  return tagColorStyles[color] ?? {
    bg: 'bg-slate-500/10 border border-slate-500/20',
    text: 'text-slate-300',
  }
}

export function getScoreColor(score: number) {
  if (score >= 85) return '#10B981'
  if (score >= 70) return '#06B6D4'
  if (score >= 50) return '#F59E0B'
  return '#EF4444'
}
