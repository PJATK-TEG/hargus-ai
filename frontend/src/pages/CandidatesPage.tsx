import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Briefcase, ChevronRight, MapPin, Users, Loader2 } from 'lucide-react'
import { motion } from 'framer-motion'
import ScoreRing from '../components/ScoreRing'
import { cn, formatDate, getStatusColor, getTagColors } from '../lib/utils'
import { api } from '../lib/api'
import type { Candidate, Vacancy } from '../types'

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.listCandidates(), api.listVacancies()])
      .then(([cs, vs]) => {
        setCandidates(cs)
        setVacancies(vs)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-aurora-purple animate-spin" />
      </div>
    )
  }

  const vacancyMap = Object.fromEntries(vacancies.map((v) => [v.id, v]))

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">All Candidates</h1>
        <p className="text-sm text-slate-400 mt-1">Browse every candidate across all open roles</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total Candidates', value: candidates.length },
          { label: 'Active Interviews', value: candidates.filter((c) => c.status === 'interview').length },
          { label: 'Offers Extended', value: candidates.filter((c) => c.status === 'offer').length },
        ].map((stat, index) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.08 }}
            className="glass-card rounded-2xl p-5"
          >
            <p className="text-3xl font-bold text-white">{stat.value}</p>
            <p className="text-xs font-medium text-slate-400 mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      <div className="space-y-3">
        {candidates.map((candidate, index) => {
          const vacancy = vacancyMap[candidate.vacancyId]
          const statusStyle = getStatusColor(candidate.status)

          return (
            <motion.div
              key={candidate.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.04 }}
            >
              <Link
                to={`/vacancies/${candidate.vacancyId}/candidates/${candidate.id}`}
                className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-5 group block"
              >
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                  style={{ backgroundColor: `${candidate.avatarColor}30`, color: candidate.avatarColor }}
                >
                  {candidate.avatarInitials}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                    <h3 className="text-[15px] font-semibold text-white group-hover:text-aurora-violet transition-colors">
                      {candidate.name}
                    </h3>
                    <span className={cn('tag-badge', statusStyle.bg, statusStyle.text)}>
                      <span className={cn('status-dot', statusStyle.dot)} />
                      {candidate.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400 flex-wrap">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5" />
                      {candidate.location}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Briefcase className="w-3.5 h-3.5" />
                      {vacancy?.title ?? 'Unknown role'}
                    </span>
                    <span className="text-slate-500">Applied {formatDate(candidate.appliedAt)}</span>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap mt-2">
                    {candidate.tags.map((tag) => {
                      const tagStyle = getTagColors(tag.color)
                      return (
                        <span key={tag.id} className={cn('tag-badge text-[10px]', tagStyle.bg, tagStyle.text)}>
                          {tag.label}
                        </span>
                      )
                    })}
                  </div>
                </div>

                <div className="flex items-center gap-5 flex-shrink-0">
                  <div className="hidden md:flex items-center gap-1 text-slate-500 text-xs">
                    <Users className="w-4 h-4" />
                    {candidate.files.length} files
                  </div>
                  <ScoreRing score={candidate.score} size={56} strokeWidth={4} label="Score" />
                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
