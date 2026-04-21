import { BarChart3, Briefcase, Target, Users } from 'lucide-react'
import { mockCandidates, mockVacancies } from '../data/mock'

export default function AnalyticsPage() {
  const activeVacancies = mockVacancies.filter((vacancy) => vacancy.status === 'active').length
  const avgScore = Math.round(
    mockCandidates.reduce((sum, candidate) => sum + candidate.score, 0) / mockCandidates.length
  )
  const avgRelevancy = Math.round(
    mockCandidates.reduce((sum, candidate) => sum + candidate.relevancyScore, 0) / mockCandidates.length
  )

  const cards = [
    { label: 'Open Roles', value: activeVacancies, icon: Briefcase, tone: 'text-aurora-violet' },
    { label: 'Candidates Reviewed', value: mockCandidates.length, icon: Users, tone: 'text-aurora-cyan' },
    { label: 'Average Score', value: avgScore, icon: BarChart3, tone: 'text-aurora-emerald' },
    { label: 'Avg. Relevancy', value: avgRelevancy, icon: Target, tone: 'text-aurora-amber' },
  ]

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Analytics</h1>
        <p className="text-sm text-slate-400 mt-1">High-level pipeline metrics from the current mock dataset</p>
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
          <div className="space-y-3">
            {mockVacancies.map((vacancy) => (
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
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-semibold text-white mb-4">Hiring Notes</h2>
          <div className="space-y-3 text-sm text-slate-300">
            <p>The backend role currently has the largest candidate volume and the strongest average fit.</p>
            <p>The ML role has fewer applicants but the highest relevancy concentration among shortlisted candidates.</p>
            <p>Paused and closed roles remain visible for historical context, but are not counted as open roles.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
