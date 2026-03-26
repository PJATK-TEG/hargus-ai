import { useState } from 'react'
import { X, Plus, Trash2 } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import type { Vacancy } from '../types'

interface CreateVacancyModalProps {
  open: boolean
  onClose: () => void
  onCreate: (vacancy: Vacancy) => void
}

export default function CreateVacancyModal({ open, onClose, onCreate }: CreateVacancyModalProps) {
  const [title, setTitle] = useState('')
  const [department, setDepartment] = useState('')
  const [location, setLocation] = useState('')
  const [type, setType] = useState<Vacancy['type']>('full-time')
  const [description, setDescription] = useState('')
  const [requirements, setRequirements] = useState<string[]>([''])

  const addRequirement = () => setRequirements([...requirements, ''])
  const removeRequirement = (i: number) => setRequirements(requirements.filter((_, idx) => idx !== i))
  const updateRequirement = (i: number, val: string) => {
    const next = [...requirements]
    next[i] = val
    setRequirements(next)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const vacancy: Vacancy = {
      id: `v${Date.now()}`,
      title,
      department,
      location,
      type,
      status: 'active',
      description,
      requirements: requirements.filter(Boolean),
      createdAt: new Date().toISOString().split('T')[0]!,
      candidatesCount: 0,
      hiresTarget: 1,
    }
    onCreate(vacancy)
    onClose()
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
                  <h2 className="text-lg font-semibold text-white">Create Vacancy</h2>
                  <p className="text-sm text-slate-400 mt-0.5">Add a new open position</p>
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

                {/* Actions */}
                <div className="flex justify-end gap-3 pt-2">
                  <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary">
                    <Plus className="w-4 h-4" />
                    Create Vacancy
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
