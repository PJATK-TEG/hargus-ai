import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, MapPin, Clock, Users, ChevronRight, ExternalLink } from 'lucide-react'
import { motion } from 'framer-motion'
import { mockVacancies, mockCandidates } from '../data/mock'
import { formatDate, getStatusColor, getTagColors, cn } from '../lib/utils'
import ScoreRing from '../components/ScoreRing'

export default function VacancyDetailPage() {
  const { vacancyId } = useParams<{ vacancyId: string }>()
  const vacancy = mockVacancies.find((v) => v.id === vacancyId)
  const candidates = mockCandidates.filter((c) => c.vacancyId === vacancyId)

  if (!vacancy) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Vacancy not found.
      </div>
    )
  }

  const statusStyle = getStatusColor(vacancy.status)

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <Link to="/vacancies" className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-aurora-violet transition-colors mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Vacancies
      </Link>

      {/* Vacancy header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-6 mb-6"
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-2xl font-bold text-white">{vacancy.title}</h1>
              <span className={cn('tag-badge', statusStyle.bg, statusStyle.text)}>
                <span className={cn('status-dot', statusStyle.dot)} />
                {vacancy.status}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-slate-400">
              <span className="flex items-center gap-1.5"><MapPin className="w-4 h-4" />{vacancy.location}</span>
              <span className="flex items-center gap-1.5"><Clock className="w-4 h-4" />{vacancy.type}</span>
              <span>{vacancy.department}</span>
              <span className="text-slate-500">Created {formatDate(vacancy.createdAt)}</span>
            </div>
          </div>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-white">{candidates.length}</p>
              <p className="text-xs text-slate-500">candidates</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold text-aurora-emerald">{vacancy.hiresTarget}</p>
              <p className="text-xs text-slate-500">target</p>
            </div>
          </div>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed mb-4">{vacancy.description}</p>

        <div className="flex flex-wrap gap-2">
          {vacancy.requirements.map((req) => (
            <span key={req} className="tag-badge bg-aurora-purple/10 text-aurora-violet border border-aurora-purple/20">
              {req}
            </span>
          ))}
        </div>
      </motion.div>

      {/* Candidates section */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Users className="w-5 h-5 text-slate-400" />
          Candidates
          <span className="text-sm font-normal text-slate-500">({candidates.length})</span>
        </h2>
      </div>

      {candidates.length === 0 ? (
        <div className="glass-card rounded-2xl p-12 text-center">
          <Users className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No candidates yet for this vacancy.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {candidates.map((candidate, i) => {
            const cStatus = getStatusColor(candidate.status)
            return (
              <motion.div
                key={candidate.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <Link
                  to={`/vacancies/${vacancyId}/candidates/${candidate.id}`}
                  className="glass-card glass-card-hover rounded-2xl p-5 flex items-center gap-5 group block"
                >
                  {/* Avatar */}
                  <div
                    className="w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
                    style={{ backgroundColor: candidate.avatarColor + '30', color: candidate.avatarColor }}
                  >
                    {candidate.avatarInitials}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-[15px] font-semibold text-white group-hover:text-aurora-violet transition-colors">
                        {candidate.name}
                      </h3>
                      <span className={cn('tag-badge text-[11px]', cStatus.bg, cStatus.text)}>
                        <span className={cn('status-dot', cStatus.dot)} />
                        {candidate.status}
                      </span>
                      {candidate.linkedinUrl && (
                        <ExternalLink className="w-3.5 h-3.5 text-slate-500" />
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      {candidate.tags.map((tag) => {
                        const tagStyle = getTagColors(tag.color)
                        return (
                          <span key={tag.id} className={cn('tag-badge text-[10px]', tagStyle.bg, tagStyle.text)}>
                            {tag.label}
                          </span>
                        )
                      })}
                      <span className="text-[11px] text-slate-500 ml-1">
                        {candidate.location} · {candidate.parsedFields.totalYearsExp}y exp · Applied {formatDate(candidate.appliedAt)}
                      </span>
                    </div>
                  </div>

                  {/* Score */}
                  <div className="flex items-center gap-5 flex-shrink-0">
                    <ScoreRing score={candidate.score} size={56} strokeWidth={4} label="Score" />
                    <ScoreRing score={candidate.relevancyScore} size={56} strokeWidth={4} label="Relevancy" />
                    <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-400 group-hover:translate-x-0.5 transition-all" />
                  </div>
                </Link>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}
