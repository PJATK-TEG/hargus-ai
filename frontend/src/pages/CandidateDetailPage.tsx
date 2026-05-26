import { useState, useRef, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Mail, Phone, MapPin, ExternalLink, Briefcase, GraduationCap,
  Award, Globe, FileText, MessageSquare, Send, ChevronDown, ChevronUp,
  File, Clock, User, Sparkles, BookOpen, Shield, Loader2, Play, Trash2,
  Plus, AlertTriangle,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import TextareaAutosize from 'react-textarea-autosize'
import { getStatusColor, getTagColors, getScoreColor, cn, formatDate } from '../lib/utils'
import { api } from '../lib/api'
import ScoreRing from '../components/ScoreRing'
import type { Message, CandidateFile, FileType, Candidate, AnalysisReport } from '../types'

type Tab = 'overview' | 'files' | 'chat'

const fileTypeConfig: Record<FileType, { icon: typeof FileText; color: string; bg: string }> = {
  cv: { icon: FileText, color: 'text-aurora-purple', bg: 'bg-aurora-purple/10' },
  transcript: { icon: BookOpen, color: 'text-aurora-cyan', bg: 'bg-aurora-cyan/10' },
  note: { icon: File, color: 'text-aurora-amber', bg: 'bg-aurora-amber/10' },
  background: { icon: Shield, color: 'text-aurora-emerald', bg: 'bg-aurora-emerald/10' },
}

export default function CandidateDetailPage() {
  const { vacancyId, candidateId } = useParams<{ vacancyId: string; candidateId: string }>()
  const navigate = useNavigate()
  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [expandedFile, setExpandedFile] = useState<string | null>(null)
  const [reports, setReports] = useState<AnalysisReport[]>([])
  const [filesChanged, setFilesChanged] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadType, setUploadType] = useState<'cv' | 'transcript'>('cv')
  const chatEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    Promise.all([
      api.getCandidate(candidateId!),
      api.listMessages(candidateId!),
      api.listCandidateReports(candidateId!),
    ])
      .then(([c, msgs, rpts]) => {
        setCandidate(c)
        setMessages(msgs)
        setReports(rpts)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [candidateId])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const pollTask = async (taskId: string, attempts: number) => {
    if (attempts >= 60) {
      setMessages((prev) => [
        ...prev,
        {
          id: `m${Date.now()}`,
          role: 'assistant' as const,
          content: 'The request timed out. Please try again.',
          timestamp: new Date().toISOString(),
        },
      ])
      setThinking(false)
      return
    }
    try {
      const task = await api.getAiTask(taskId)
      if (task.status === 'completed') {
        setMessages((prev) => [
          ...prev,
          {
            id: `m${Date.now()}`,
            role: 'assistant' as const,
            content: task.result?.answer ?? task.result?.message ?? task.result?.summary ?? 'Analysis complete.',
            timestamp: new Date().toISOString(),
          },
        ])
        setThinking(false)
      } else if (task.status === 'failed') {
        setMessages((prev) => [
          ...prev,
          {
            id: `m${Date.now()}`,
            role: 'assistant' as const,
            content: 'The analysis failed. Please try again.',
            timestamp: new Date().toISOString(),
          },
        ])
        setThinking(false)
      } else {
        setTimeout(() => pollTask(taskId, attempts + 1), 2000)
      }
    } catch {
      setThinking(false)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || thinking) return
    const prompt = input.trim()
    const userMsg: Message = {
      id: `m${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    setThinking(true)
    try {
      const task = await api.queryCandidate(candidateId!, prompt, vacancyId)
      pollTask(task.id, 0)
    } catch {
      setThinking(false)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this candidate? This cannot be undone.')) return
    await api.deleteCandidate(candidateId!)
    navigate(`/vacancies/${vacancyId}`)
  }

  const handleAnalyze = async () => {
    if (analyzing || thinking) return
    setAnalyzing(true)
    setActiveTab('chat')
    const systemMsg = {
      id: `m${Date.now()}`,
      role: 'assistant' as const,
      content: `Starting full AI analysis for **${candidate?.name}**. This will extract skills, score experience, and generate a report…`,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, systemMsg])
    setThinking(true)
    try {
      const task = await api.analyzeCandidate(candidateId!, vacancyId)
      pollTask(task.id, 0)
    } catch {
      setThinking(false)
    } finally {
      setAnalyzing(false)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    if (!files.length || !candidateId) return
    setUploading(true)
    try {
      const uploaded = await Promise.all(
        files.map((f) => api.uploadCandidateFile(candidateId, f, uploadType))
      )
      setCandidate((prev) => prev ? { ...prev, files: [...prev.files, ...uploaded] } : prev)
      setFilesChanged(true)
    } catch (err) {
      console.error(err)
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleReportDelete = async (reportId: string) => {
    if (!candidateId) return
    try {
      await api.deleteAnalysisReport(candidateId, reportId)
      setReports((prev) => prev.filter((r) => r.id !== reportId))
    } catch (err) {
      console.error(err)
    }
  }

  const handleFileDelete = async (fileId: string) => {
    if (!candidateId) return
    try {
      await api.deleteCandidateFile(candidateId, fileId)
      setCandidate((prev) => prev ? { ...prev, files: prev.files.filter((f) => f.id !== fileId) } : prev)
      setFilesChanged(true)
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-aurora-purple animate-spin" />
      </div>
    )
  }

  if (!candidate) {
    return (
      <div className="flex items-center justify-center h-full text-slate-400">
        Candidate not found.
      </div>
    )
  }

  const cStatus = getStatusColor(candidate.status)
  const { parsedFields } = candidate

  const tabs: { id: Tab; label: string; icon: typeof User }[] = [
    { id: 'overview', label: 'Overview', icon: User },
    { id: 'files', label: 'Files', icon: FileText },
    { id: 'chat', label: 'AI Chat', icon: MessageSquare },
  ]

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Breadcrumb */}
      <Link
        to={`/vacancies/${vacancyId}`}
        className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-aurora-violet transition-colors mb-6"
      >
        <ArrowLeft className="w-4 h-4" />
        Back to Candidates
      </Link>

      {/* Candidate header */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card rounded-2xl p-6 mb-6"
      >
        <div className="flex items-start gap-5">
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center text-xl font-bold flex-shrink-0 border"
            style={{
              backgroundColor: candidate.avatarColor + '20',
              color: candidate.avatarColor,
              borderColor: candidate.avatarColor + '30',
            }}
          >
            {candidate.avatarInitials}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-1.5">
              <h1 className="text-2xl font-bold text-white">{candidate.name}</h1>
              <span className={cn('tag-badge', cStatus.bg, cStatus.text)}>
                <span className={cn('status-dot', cStatus.dot)} />
                {candidate.status}
              </span>
            </div>

            <div className="flex items-center gap-4 text-sm text-slate-400 mb-3">
              <span className="flex items-center gap-1.5"><Mail className="w-3.5 h-3.5" />{candidate.email}</span>
              <span className="flex items-center gap-1.5"><Phone className="w-3.5 h-3.5" />{candidate.phone}</span>
              <span className="flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5" />{candidate.location}</span>
              {candidate.linkedinUrl && (
                <a href={candidate.linkedinUrl} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-aurora-cyan hover:text-aurora-teal transition-colors">
                  <ExternalLink className="w-3.5 h-3.5" />
                  LinkedIn
                </a>
              )}
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {candidate.tags.map((tag) => {
                const ts = getTagColors(tag.color)
                return (
                  <span key={tag.id} className={cn('tag-badge', ts.bg, ts.text)}>
                    {tag.label}
                  </span>
                )
              })}
            </div>
          </div>

          <div className="flex items-center gap-6 flex-shrink-0">
            <ScoreRing score={candidate.score} size={80} strokeWidth={5} label="Overall" />
            <ScoreRing score={candidate.relevancyScore} size={80} strokeWidth={5} label="Relevancy" description="How relevant the candidate is to the position based purely on skill match — not interview performance or truthfulness." />
            <button
              onClick={handleAnalyze}
              disabled={analyzing || thinking}
              className={cn(
                'flex flex-col items-center gap-1.5 px-4 py-3 rounded-2xl border transition-all',
                analyzing || thinking
                  ? 'border-aurora-purple/20 bg-aurora-purple/5 cursor-not-allowed opacity-60'
                  : 'border-aurora-purple/30 bg-aurora-purple/10 hover:bg-aurora-purple/20 hover:border-aurora-purple/50'
              )}
              title="Run AI analysis workflow for this candidate"
            >
              {analyzing ? (
                <Loader2 className="w-5 h-5 text-aurora-violet animate-spin" />
              ) : (
                <Play className="w-5 h-5 text-aurora-violet" />
              )}
              <span className="text-[11px] font-semibold text-aurora-violet whitespace-nowrap">
                {analyzing ? 'Starting…' : 'Analyze'}
              </span>
            </button>
            <button
              onClick={handleDelete}
              className="p-2.5 rounded-xl border border-red-500/20 bg-red-500/5 hover:bg-red-500/15 hover:border-red-500/40 transition-all"
              title="Delete candidate"
            >
              <Trash2 className="w-5 h-5 text-red-400" />
            </button>
          </div>
        </div>
      </motion.div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 glass-card rounded-xl w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.id
                ? 'bg-aurora-purple/20 text-white border border-aurora-purple/30 shadow-glow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
            {tab.id === 'files' && (
              <span className="ml-1 text-[11px] bg-white/10 px-1.5 py-0.5 rounded-md">{candidate.files.length + reports.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <AnimatePresence mode="wait">
        {activeTab === 'overview' && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="grid grid-cols-3 gap-6"
          >
            <div className="col-span-2 space-y-6">
              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-3">
                  <Sparkles className="w-4 h-4 text-aurora-purple" />
                  AI Summary
                </h3>
                <p className="text-sm text-slate-300 leading-relaxed">{parsedFields.summary}</p>
              </div>

              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
                  <Award className="w-4 h-4 text-aurora-cyan" />
                  Skill Assessment
                </h3>
                <div className="space-y-3">
                  {parsedFields.skillScores.map((ss) => (
                    <div key={ss.skill} className="group">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm text-slate-300">{ss.skill}</span>
                        <span className="text-xs font-bold" style={{ color: getScoreColor(ss.score) }}>
                          {ss.score}
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${ss.score}%` }}
                          transition={{ duration: 0.8, ease: 'easeOut' }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: getScoreColor(ss.score), boxShadow: `0 0 8px ${getScoreColor(ss.score)}40` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card rounded-2xl p-6">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2 mb-4">
                  <Briefcase className="w-4 h-4 text-aurora-amber" />
                  Experience
                  <span className="text-xs font-normal text-slate-500">{parsedFields.totalYearsExp} years total</span>
                </h3>
                <div className="space-y-4">
                  {parsedFields.experience.map((exp, i) => (
                    <div key={i} className="relative pl-6 pb-4 last:pb-0">
                      {i < parsedFields.experience.length - 1 && (
                        <div className="absolute left-[7px] top-[18px] bottom-0 w-px bg-gradient-to-b from-aurora-purple/30 to-transparent" />
                      )}
                      <div className="absolute left-0 top-[6px] w-[15px] h-[15px] rounded-full bg-void-800 border-2 border-aurora-purple/40 flex items-center justify-center">
                        <div className="w-[5px] h-[5px] rounded-full bg-aurora-purple" />
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-white">{exp.role}</h4>
                        <p className="text-xs text-aurora-violet font-medium">{exp.company}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">{exp.from} – {exp.to}</p>
                        <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">{exp.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="glass-card rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Skills</h3>
                <div className="flex flex-wrap gap-1.5">
                  {parsedFields.skills.map((skill) => (
                    <span key={skill} className="tag-badge bg-aurora-purple/10 text-aurora-violet text-[11px]">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>

              <div className="glass-card rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-3">
                  <GraduationCap className="w-4 h-4" />
                  Education
                </h3>
                <div className="space-y-3">
                  {parsedFields.education.map((edu, i) => (
                    <div key={i}>
                      <p className="text-sm font-medium text-white">{edu.degree} in {edu.field}</p>
                      <p className="text-xs text-aurora-cyan">{edu.institution}</p>
                      <p className="text-[11px] text-slate-500">{edu.year}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="glass-card rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-3">
                  <Globe className="w-4 h-4" />
                  Languages
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {parsedFields.languages.map((lang) => (
                    <span key={lang} className="tag-badge bg-aurora-teal/10 text-aurora-teal text-[11px]">{lang}</span>
                  ))}
                </div>
              </div>

              {parsedFields.certifications.length > 0 && (
                <div className="glass-card rounded-2xl p-5">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-3">
                    <Award className="w-4 h-4" />
                    Certifications
                  </h3>
                  <div className="space-y-2">
                    {parsedFields.certifications.map((cert) => (
                      <div key={cert} className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-aurora-amber" />
                        <span className="text-sm text-slate-300">{cert}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="glass-card rounded-2xl p-5">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Details</h3>
                <div className="space-y-2.5 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Applied</span>
                    <span className="text-slate-300">{formatDate(candidate.appliedAt)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Files</span>
                    <span className="text-slate-300">{candidate.files.length} documents</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Exp.</span>
                    <span className="text-slate-300">{parsedFields.totalYearsExp} years</span>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'files' && (
          <motion.div
            key="files"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {candidate.files.length + reports.length} document(s)
              </span>
              <div className="flex items-center gap-2">
                <div className="flex rounded-lg border border-white/[0.08] overflow-hidden text-xs font-medium">
                  <button
                    onClick={() => setUploadType('cv')}
                    className={cn(
                      'px-3 py-1.5 transition-all',
                      uploadType === 'cv'
                        ? 'bg-aurora-purple/20 text-aurora-purple'
                        : 'text-slate-400 hover:text-slate-300 hover:bg-white/[0.04]'
                    )}
                  >
                    CV
                  </button>
                  <button
                    onClick={() => setUploadType('transcript')}
                    className={cn(
                      'px-3 py-1.5 transition-all border-l border-white/[0.08]',
                      uploadType === 'transcript'
                        ? 'bg-aurora-cyan/20 text-aurora-cyan'
                        : 'text-slate-400 hover:text-slate-300 hover:bg-white/[0.04]'
                    )}
                  >
                    Transcript
                  </button>
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium border border-aurora-violet/30 bg-aurora-violet/10 text-aurora-violet hover:bg-aurora-violet/20 transition-all disabled:opacity-50"
                >
                  {uploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
                  {uploading ? 'Uploading…' : 'Add Files'}
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept=".pdf,.txt,.doc,.docx"
                  onChange={handleFileUpload}
                />
              </div>
            </div>

            {filesChanged && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-aurora-amber/10 border border-aurora-amber/20 text-aurora-amber text-sm">
                <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                Files changed — re-run <strong className="mx-1">Analyze</strong> for the results to reflect the updated documents.
              </div>
            )}

            {reports.map((report, i) => (
              <ReportCard
                key={report.id}
                report={report}
                index={i}
                candidateId={candidateId!}
                expanded={expandedFile === report.id}
                onToggle={() => setExpandedFile(expandedFile === report.id ? null : report.id)}
                onDelete={() => handleReportDelete(report.id)}
              />
            ))}
            {candidate.files.map((file, i) => (
              <FileCard
                key={file.id}
                file={file}
                index={reports.length + i}
                expanded={expandedFile === file.id}
                onToggle={() => setExpandedFile(expandedFile === file.id ? null : file.id)}
                onDelete={() => handleFileDelete(file.id)}
              />
            ))}
            {reports.length === 0 && candidate.files.length === 0 && (
              <div className="glass-card rounded-2xl p-12 text-center text-slate-500 text-sm">
                No files yet. Upload files or run an analysis to generate a report.
              </div>
            )}
          </motion.div>
        )}

        {activeTab === 'chat' && (
          <motion.div
            key="chat"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            className="glass-card rounded-2xl flex flex-col"
            style={{ height: 'calc(100vh - 380px)' }}
          >
            <div className="px-6 py-4 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-aurora-purple" />
                <h3 className="text-sm font-semibold text-white">AI Candidate Analysis</h3>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Ask questions about {candidate.name}'s profile, CV, transcripts, and assessment
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {messages.length === 0 && !thinking && (
                <div className="flex flex-col items-center justify-center h-full text-center">
                  <div className="w-14 h-14 rounded-2xl bg-aurora-purple/10 border border-aurora-purple/20 flex items-center justify-center mb-4">
                    <MessageSquare className="w-7 h-7 text-aurora-purple" />
                  </div>
                  <h4 className="text-sm font-semibold text-white mb-1">Start a conversation</h4>
                  <p className="text-xs text-slate-500 max-w-sm">
                    Ask me anything about this candidate — strengths, red flags, skill comparisons, or interview insights.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-4 max-w-md justify-center">
                    {[
                      'What are the key strengths?',
                      'Any red flags?',
                      'Summarize the interviews',
                      'How do skills match the role?',
                    ].map((q) => (
                      <button
                        key={q}
                        onClick={() => setInput(q)}
                        className="text-[11px] px-3 py-1.5 rounded-lg bg-white/5 text-slate-400 hover:text-white hover:bg-aurora-purple/10 border border-white/5 hover:border-aurora-purple/20 transition-all"
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={cn('flex gap-3 max-w-[85%]', msg.role === 'user' ? 'ml-auto flex-row-reverse' : '')}
                >
                  <div
                    className={cn(
                      'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold',
                      msg.role === 'user'
                        ? 'bg-aurora-cyan/20 text-aurora-cyan'
                        : 'bg-aurora-purple/20 text-aurora-purple'
                    )}
                  >
                    {msg.role === 'user' ? 'You' : <Sparkles className="w-4 h-4" />}
                  </div>
                  <div
                    className={cn(
                      'rounded-2xl px-4 py-3 text-sm leading-relaxed',
                      msg.role === 'user'
                        ? 'bg-aurora-cyan/10 text-slate-200 border border-aurora-cyan/15'
                        : 'bg-white/[0.04] text-slate-300 border border-white/[0.06]'
                    )}
                  >
                    {msg.content.split('\n').map((line, i) => (
                      <p key={i} className={i > 0 ? 'mt-2' : ''}>
                        {line.split(/(\*\*[^*]+\*\*)/).map((part, j) =>
                          part.startsWith('**') && part.endsWith('**') ? (
                            <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>
                          ) : (
                            part
                          )
                        )}
                      </p>
                    ))}
                  </div>
                </div>
              ))}

              {thinking && (
                <div className="flex gap-3 max-w-[85%]">
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-aurora-purple/20 text-aurora-purple">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div className="rounded-2xl px-4 py-3 bg-white/[0.04] border border-white/[0.06] flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-aurora-purple animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-aurora-purple animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-aurora-purple animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}

              <div ref={chatEndRef} />
            </div>

            <div className="px-6 py-4 border-t border-white/[0.06]">
              <div className="flex items-end gap-3">
                <TextareaAutosize
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      handleSend()
                    }
                  }}
                  placeholder={`Ask about ${candidate.name}...`}
                  className="input-field resize-none min-h-[44px] max-h-32"
                  minRows={1}
                  maxRows={4}
                />
                <button
                  onClick={handleSend}
                  disabled={!input.trim() || thinking}
                  className={cn(
                    'p-3 rounded-xl transition-all flex-shrink-0',
                    input.trim() && !thinking
                      ? 'btn-primary'
                      : 'bg-white/5 text-slate-600 cursor-not-allowed'
                  )}
                >
                  {thinking ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

const recommendationColor: Record<string, string> = {
  strong_match: 'text-aurora-emerald',
  possible: 'text-aurora-cyan',
  weak: 'text-aurora-amber',
  manual_review: 'text-aurora-amber',
  red_flag: 'text-red-400',
}

function ReportCard({
  report,
  index,
  candidateId,
  expanded,
  onToggle,
  onDelete,
}: {
  report: AnalysisReport
  index: number
  candidateId: string
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  const recColor = recommendationColor[report.recommendation] ?? 'text-slate-300'
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [pdfError, setPdfError] = useState(false)

  useEffect(() => {
    if (!expanded || !report.hasPdf || blobUrl) return
    let cancelled = false
    setPdfLoading(true)
    setPdfError(false)
    api.downloadCandidateReportPdf(candidateId, report.id)
      .then((blob) => { if (!cancelled) setBlobUrl(URL.createObjectURL(blob)) })
      .catch(() => { if (!cancelled) setPdfError(true) })
      .finally(() => { if (!cancelled) setPdfLoading(false) })
    return () => { cancelled = true }
  }, [expanded, report.hasPdf, report.id, candidateId, blobUrl])

  useEffect(() => {
    return () => { if (blobUrl) URL.revokeObjectURL(blobUrl) }
  }, [blobUrl])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="glass-card rounded-2xl overflow-hidden"
    >
      <div className="flex items-center">
        <button
          onClick={onToggle}
          className="flex-1 flex items-center gap-4 p-5 text-left hover:bg-white/[0.02] transition-all"
        >
          <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 bg-aurora-purple/10">
            <FileText className="w-5 h-5 text-aurora-purple" />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-white truncate">
              AI Analysis Report
            </h4>
            <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5">
              <span className={cn('capitalize font-medium', recColor)}>
                {report.recommendation.replace(/_/g, ' ')}
              </span>
              <span>Score: {Math.round(report.overallScore)}%</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDate(report.createdAt)}
              </span>
              {report.hasPdf && (
                <span className="text-aurora-purple font-medium">PDF available</span>
              )}
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </button>
        <button
          onClick={onDelete}
          className="p-3 mr-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all flex-shrink-0"
          title="Delete report"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5">
              <div className="section-divider mb-4" />
              {report.hasPdf ? (
                pdfLoading ? (
                  <div className="flex items-center justify-center h-24 text-sm text-slate-500">Loading PDF…</div>
                ) : pdfError ? (
                  <p className="text-sm text-red-400 italic">Failed to load PDF. Please try again.</p>
                ) : blobUrl ? (
                  <iframe
                    src={blobUrl}
                    className="w-full rounded-xl border border-white/[0.06]"
                    style={{ height: '70vh' }}
                    title="Analysis Report PDF"
                  />
                ) : null
              ) : (
                <p className="text-sm text-slate-500 italic">PDF not yet available for this report.</p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function FileCard({
  file,
  index,
  expanded,
  onToggle,
  onDelete,
}: {
  file: CandidateFile
  index: number
  expanded: boolean
  onToggle: () => void
  onDelete: () => void
}) {
  const config = fileTypeConfig[file.type]
  const Icon = config.icon

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="glass-card rounded-2xl overflow-hidden"
    >
      <div className="flex items-center">
        <button
          onClick={onToggle}
          className="flex-1 flex items-center gap-4 p-5 text-left hover:bg-white/[0.02] transition-all"
        >
          <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', config.bg)}>
            <Icon className={cn('w-5 h-5', config.color)} />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-white truncate">{file.name}</h4>
            <div className="flex items-center gap-3 text-[11px] text-slate-500 mt-0.5">
              <span className="capitalize">{file.type}</span>
              <span>{file.size}</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatDate(file.uploadedAt)}
              </span>
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-slate-500" />
          ) : (
            <ChevronDown className="w-4 h-4 text-slate-500" />
          )}
        </button>
        <button
          onClick={onDelete}
          className="p-3 mr-2 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-400/10 transition-all flex-shrink-0"
          title="Delete file"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5">
              <div className="section-divider mb-4" />
              <pre className="text-sm text-slate-300 font-mono leading-relaxed whitespace-pre-wrap bg-void-950/50 rounded-xl p-4 border border-white/[0.04] max-h-64 overflow-y-auto">
                {file.content}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
