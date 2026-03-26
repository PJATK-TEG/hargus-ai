import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Briefcase, MapPin, Clock, Users, ChevronRight, Target } from 'lucide-react'
import { motion } from 'framer-motion'
import { mockVacancies } from '../data/mock'
import { formatDate, getStatusColor, cn } from '../lib/utils'
import CreateVacancyModal from '../components/CreateVacancyModal'
import type { Vacancy } from '../types'

export default function VacanciesPage() {
  const [vacancies, setVacancies] = useState<Vacancy[]>(mockVacancies)
  const [modalOpen, setModalOpen] = useState(false)
  const [filterStatus, setFilterStatus] = useState<string>('all')

  const filtered = filterStatus === 'all' ? vacancies : vacancies.filter((v) => v.status === filterStatus)

  const stats = {
    total: vacancies.length,
    active: vacancies.filter((v) => v.status === 'active').length,
    totalCandidates: vacancies.reduce((sum, v) => sum + v.candidatesCount, 0),
  }

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Vacancies</h1>
          <p className="text-sm text-slate-400 mt-1">Manage open positions and track candidates</p>
        </div>
        <button onClick={() => setModalOpen(true)} className="btn-primary">
          <Plus className="w-4 h-4" />
          New Vacancy
        </button>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        {[
          { label: 'Total Positions', value: stats.total, icon: Briefcase, gradient: 'from-aurora-purple/20 to-aurora-indigo/5' },
          { label: 'Active Positions', value: stats.active, icon: Target, gradient: 'from-aurora-emerald/20 to-aurora-teal/5' },
          { label: 'Total Candidates', value: stats.totalCandidates, icon: Users, gradient: 'from-aurora-cyan/20 to-aurora-purple/5' },
        ].map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.08 }}
            className={cn('glass-card rounded-2xl p-5 bg-gradient-to-br', stat.gradient)}
          >
            <div className="flex items-center justify-between mb-3">
              <stat.icon className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-3xl font-bold text-white">{stat.value}</p>
            <p className="text-xs font-medium text-slate-400 mt-1">{stat.label}</p>
          </motion.div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {['all', 'active', 'paused', 'closed'].map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className={cn(
              'px-4 py-2 rounded-xl text-xs font-semibold transition-all capitalize',
              filterStatus === status
                ? 'bg-aurora-purple/20 text-aurora-violet border border-aurora-purple/30'
                : 'text-slate-400 hover:text-slate-200 border border-transparent hover:border-white/10 hover:bg-white/5'
            )}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Vacancy cards */}
      <div className="space-y-3">
        {filtered.map((vacancy, i) => {
          const statusStyle = getStatusColor(vacancy.status)
          return (
            <motion.div
              key={vacancy.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                to={`/vacancies/${vacancy.id}`}
                className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-6 group block"
              >
                {/* Icon */}
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-aurora-purple/20 to-aurora-indigo/10 border border-aurora-purple/20 flex items-center justify-center flex-shrink-0">
                  <Briefcase className="w-5 h-5 text-aurora-violet" />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1.5">
                    <h3 className="text-[15px] font-semibold text-white group-hover:text-aurora-violet transition-colors truncate">
                      {vacancy.title}
                    </h3>
                    <span className={cn('tag-badge', statusStyle.bg, statusStyle.text)}>
                      <span className={cn('status-dot', statusStyle.dot)} />
                      {vacancy.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5" />
                      {vacancy.location}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {vacancy.type}
                    </span>
                    <span className="text-slate-500">{vacancy.department}</span>
                  </div>
                </div>

                {/* Stats */}
                <div className="flex items-center gap-8 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-lg font-bold text-white">{vacancy.candidatesCount}</p>
                    <p className="text-[11px] text-slate-500">candidates</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-aurora-emerald">{vacancy.hiresTarget}</p>
                    <p className="text-[11px] text-slate-500">target hires</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-500">{formatDate(vacancy.createdAt)}</p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            </motion.div>
          )
        })}
      </div>

      <CreateVacancyModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onCreate={(v) => setVacancies([v, ...vacancies])}
      />
    </div>
  )
}
