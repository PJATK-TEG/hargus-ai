import { useState, useEffect } from 'react'
import { BarChart3, Briefcase, Loader2, Target, Users } from 'lucide-react'
import { api } from '../lib/api'
import type { Vacancy, Candidate } from '../types'

export default function AnalyticsPage() {
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.listVacancies(), api.listCandidates()])
      .then(([vs, cs]) => {
        setVacancies(vs)
        setCandidates(cs)
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

  const activeVacancies = vacancies.filter((v) => v.status === 'active').length
  const avgScore = candidates.length
    ? Math.round(candidates.reduce((sum, c) => sum + c.score, 0) / candidates.length)
    : 0
  const avgRelevancy = candidates.length
    ? Math.round(candidates.reduce((sum, c) => sum + c.relevancyScore, 0) / candidates.length)
    : 0

  const cards = [
    { label: 'Open Roles', value: activeVacancies, icon: Briefcase, tone: 'text-aurora-violet' },
    { label: 'Candidates Reviewed', value: candidates.length, icon: Users, tone: 'text-aurora-cyan' },
    { label: 'Average Score', value: avgScore, icon: BarChart3, tone: 'text-aurora-emerald' },
    { label: 'Avg. Relevancy', value: avgRelevancy, icon: Target, tone: 'text-aurora-amber' },
  ]

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">High-level pipeline metrics</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((card) => (
          <div key={card.label} className="glass-card rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <card.icon className={`w-5 h-5 ${card.tone}`} />
            </div>
            <p className="text-3xl font-bold text-white">{card.value}</p>
            <p className="text-xs font-medium text-slate-400 mt-1">{card.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Vacancy Pipeline</h2>
          {vacancies.length === 0 ? (
            <p className="text-sm text-slate-500">No vacancies yet.</p>
          ) : (
            <div className="space-y-3">
              {vacancies.map((vacancy) => (
                <div key={vacancy.id} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-200">{vacancy.title}</p>
                    <p className="text-xs text-slate-500">{vacancy.department}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-white">{vacancy.candidatesCount}</p>
                    <p className="text-xs text-slate-500">candidates</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Pipeline Summary</h2>
          {candidates.length === 0 ? (
            <p className="text-sm text-slate-500">No candidates yet.</p>
          ) : (
            <div className="space-y-3 text-sm text-slate-300">
              {[
                ['Screening', 'screening'],
                ['Interview', 'interview'],
                ['Offer', 'offer'],
                ['Hired', 'hired'],
                ['Rejected', 'rejected'],
              ].map(([label, status]) => (
                <div key={status} className="flex justify-between">
                  <span className="text-slate-500">{label}</span>
                  <span>{candidates.filter((c) => c.status === status).length}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
