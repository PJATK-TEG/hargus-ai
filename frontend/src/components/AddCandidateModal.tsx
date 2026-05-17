import { useRef, useState } from 'react'
import { X, Plus, Trash2, Loader2, Upload, FileText, BookOpen } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/api'
import type { Candidate, Vacancy } from '../types'

interface AddCandidateModalProps {
  open: boolean
  vacancies: Vacancy[]
  defaultVacancyId?: string
  onClose: () => void
  onCreated: (candidate: Candidate) => void
}

export default function AddCandidateModal({
  open,
  vacancies,
  defaultVacancyId,
  onClose,
  onCreated,
}: AddCandidateModalProps) {
  const [vacancyId, setVacancyId] = useState(defaultVacancyId ?? '')
  const [cvFile, setCvFile] = useState<File | null>(null)
  const [transcriptFiles, setTranscriptFiles] = useState<File[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const cvInputRef = useRef<HTMLInputElement>(null)
  const transcriptInputRef = useRef<HTMLInputElement>(null)

  const handleTranscriptPick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? [])
    setTranscriptFiles((prev) => [...prev, ...picked])
    e.target.value = ''
  }

  const removeTranscript = (i: number) =>
    setTranscriptFiles((prev) => prev.filter((_, idx) => idx !== i))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cvFile) { setError('Please select a CV file.'); return }
    if (!vacancyId) { setError('Please select a vacancy.'); return }

    setSubmitting(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('vacancy_id', vacancyId)
      fd.append('cv', cvFile)
      for (const t of transcriptFiles) fd.append('transcripts', t)
      const candidate = await api.createCandidate(fd)
      onCreated(candidate)
      onClose()
    } catch {
      setError('Upload failed. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const defaultVacancy = vacancies.find((v) => v.id === defaultVacancyId)

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="glass-card rounded-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-5 border-b border-white/[0.06]">
                <div>
                  <h2 className="text-lg font-semibold text-white">Add Candidate</h2>
                  <p className="text-sm text-slate-400 mt-0.5">
                    Upload a CV and optional transcripts — info is extracted automatically
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-all"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-5">
                {/* Vacancy */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Vacancy</label>
                  {defaultVacancy ? (
                    <div className="input-field text-white/70 cursor-default select-none">
                      {defaultVacancy.title}
                    </div>
                  ) : (
                    <select
                      value={vacancyId}
                      onChange={(e) => setVacancyId(e.target.value)}
                      className="input-field"
                      required
                    >
                      <option value="">Select a vacancy…</option>
                      {vacancies.map((v) => (
                        <option key={v.id} value={v.id}>
                          {v.title} — {v.department}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* CV */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    CV / Resume <span className="text-red-400">*</span>
                  </label>
                  <input
                    ref={cvInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    className="hidden"
                    onChange={(e) => setCvFile(e.target.files?.[0] ?? null)}
                  />
                  {cvFile ? (
                    <div className="flex items-center gap-3 p-3 rounded-xl bg-aurora-purple/10 border border-aurora-purple/20">
                      <FileText className="w-4 h-4 text-aurora-purple flex-shrink-0" />
                      <span className="text-sm text-white flex-1 truncate">{cvFile.name}</span>
                      <button
                        type="button"
                        onClick={() => setCvFile(null)}
                        className="text-slate-500 hover:text-red-400 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => cvInputRef.current?.click()}
                      className="w-full flex items-center justify-center gap-2 p-4 rounded-xl border border-dashed border-white/[0.12] hover:border-aurora-purple/40 hover:bg-aurora-purple/5 text-slate-400 hover:text-white transition-all"
                    >
                      <Upload className="w-4 h-4" />
                      <span className="text-sm">Click to select CV file</span>
                    </button>
                  )}
                </div>

                {/* Transcripts */}
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    Interview Transcripts <span className="text-slate-500">(optional)</span>
                  </label>
                  <input
                    ref={transcriptInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.txt"
                    multiple
                    className="hidden"
                    onChange={handleTranscriptPick}
                  />
                  <div className="space-y-2">
                    {transcriptFiles.map((f, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 p-3 rounded-xl bg-aurora-cyan/10 border border-aurora-cyan/20"
                      >
                        <BookOpen className="w-4 h-4 text-aurora-cyan flex-shrink-0" />
                        <span className="text-sm text-white flex-1 truncate">{f.name}</span>
                        <button
                          type="button"
                          onClick={() => removeTranscript(i)}
                          className="text-slate-500 hover:text-red-400 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={() => transcriptInputRef.current?.click()}
                    className="mt-2 flex items-center gap-1.5 text-xs font-medium text-aurora-cyan hover:text-aurora-teal transition-colors"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Add transcript
                  </button>
                </div>

                {error && <p className="text-sm text-red-400">{error}</p>}

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={onClose} disabled={submitting} className="btn-ghost">
                    Cancel
                  </button>
                  <button type="submit" disabled={submitting} className="btn-primary">
                    {submitting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Upload className="w-4 h-4" />
                    )}
                    {submitting ? 'Uploading…' : 'Add Candidate'}
                  </button>
                </div>
              </form>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
