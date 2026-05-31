import { useState, useEffect } from 'react'
import { X, Plus, Trash2, Loader2, Save } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { api } from '../lib/api'
import type { Vacancy } from '../types'

interface EditVacancyModalProps {
  open: boolean
  vacancy: Vacancy
  onClose: () => void
  onUpdate: (updated: Vacancy) => void
}

export default function EditVacancyModal({ open, vacancy, onClose, onUpdate }: EditVacancyModalProps) {
  const [title, setTitle] = useState(vacancy.title)
  const [department, setDepartment] = useState(vacancy.department)
  const [location, setLocation] = useState(vacancy.location)
  const [type, setType] = useState<Vacancy['type']>(vacancy.type)
  const [status, setStatus] = useState<Vacancy['status']>(vacancy.status)
  const [description, setDescription] = useState(vacancy.description)
  const [requirements, setRequirements] = useState<string[]>(vacancy.requirements.length ? vacancy.requirements : [''])
  const [hiresTarget, setHiresTarget] = useState(vacancy.hiresTarget)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setTitle(vacancy.title)
    setDepartment(vacancy.department)
    setLocation(vacancy.location)
    setType(vacancy.type)
    setStatus(vacancy.status)
    setDescription(vacancy.description)
    setRequirements(vacancy.requirements.length ? vacancy.requirements : [''])
    setHiresTarget(vacancy.hiresTarget)
    setError(null)
  }, [vacancy])

  const addRequirement = () => setRequirements([...requirements, ''])
  const removeRequirement = (i: number) => setRequirements(requirements.filter((_, idx) => idx !== i))
  const updateRequirement = (i: number, val: string) => {
    const next = [...requirements]
    next[i] = val
    setRequirements(next)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const updated = await api.updateVacancy(vacancy.id, {
        title,
        department,
        location,
        type,
        status,
        description,
        requirements: requirements.filter(Boolean),
        hiresTarget,
      })
      onUpdate(updated)
      onClose()
    } catch {
      setError('Failed to update vacancy. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

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
            <div className="glass-card rounded-2xl w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
              {/* Header */}
              <div className="flex items-center justify-between px-6 py-5 border-b border-white/[0.06]">
                <div>
                  <h2 className="text-lg font-semibold text-white">Edit Vacancy</h2>
                  <p className="text-sm text-slate-400 mt-0.5">Update position details</p>
                </div>
                <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/5 text-slate-400 hover:text-white transition-all">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} className="p-6 space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Job Title</label>
                    <input
                      value={title}
                      onChange={(e) => setTitle(e.target.value)}
                      className="input-field"
                      placeholder="e.g. Senior Backend Engineer"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Department</label>
                    <input
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      className="input-field"
                      placeholder="e.g. Engineering"
                      required
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Location</label>
                    <input
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                      className="input-field"
                      placeholder="e.g. San Francisco, CA"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Type</label>
                    <select
                      value={type}
                      onChange={(e) => setType(e.target.value as Vacancy['type'])}
                      className="input-field"
                    >
                      <option value="full-time">Full-time</option>
                      <option value="part-time">Part-time</option>
                      <option value="contract">Contract</option>
                      <option value="remote">Remote</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Status</label>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value as Vacancy['status'])}
                      className="input-field"
                    >
                      <option value="active">Active</option>
                      <option value="paused">Paused</option>
                      <option value="closed">Closed</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">Hires Target</label>
                    <input
                      type="number"
                      min={1}
                      value={hiresTarget}
                      onChange={(e) => setHiresTarget(Number(e.target.value))}
                      className="input-field"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">Description</label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="input-field min-h-[100px] resize-none"
                    placeholder="Describe the role..."
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-2">Requirements</label>
                  <div className="space-y-2">
                    {requirements.map((req, i) => (
                      <div key={i} className="flex gap-2">
                        <input
                          value={req}
                          onChange={(e) => updateRequirement(i, e.target.value)}
                          className="input-field"
                          placeholder="e.g. 5+ years Python"
                        />
                        {requirements.length > 1 && (
                          <button type="button" onClick={() => removeRequirement(i)} className="p-3 rounded-xl text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-all">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <button type="button" onClick={addRequirement} className="mt-2 flex items-center gap-1.5 text-xs font-medium text-aurora-purple hover:text-aurora-violet transition-colors">
                    <Plus className="w-3.5 h-3.5" />
                    Add requirement
                  </button>
                </div>

                {error && (
                  <p className="text-sm text-red-400">{error}</p>
                )}

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={onClose} disabled={submitting} className="btn-ghost">Cancel</button>
                  <button type="submit" disabled={submitting} className="btn-primary">
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    {submitting ? 'Saving…' : 'Save Changes'}
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
