import { getScoreColor } from '../lib/utils'

interface ScoreRingProps {
  score: number
  size?: number
  strokeWidth?: number
  className?: string
  label?: string
}

export default function ScoreRing({ score, size = 80, strokeWidth = 6, className = '', label }: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = getScoreColor(score)

  return (
    <div className={`relative inline-flex flex-col items-center gap-1.5 ${className}`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="score-ring-animate"
          style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-lg font-bold text-white">{score}</span>
      </div>
      {label && <span className="text-[11px] font-medium text-slate-400">{label}</span>}
    </div>
  )
}
