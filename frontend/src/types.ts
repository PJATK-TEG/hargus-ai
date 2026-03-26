export interface Vacancy {
  id: string
  title: string
  department: string
  location: string
  type: 'full-time' | 'part-time' | 'contract' | 'remote'
  status: 'active' | 'paused' | 'closed'
  description: string
  requirements: string[]
  createdAt: string
  candidatesCount: number
  hiresTarget: number
}

export interface Tag {
  id: string
  label: string
  color: 'purple' | 'cyan' | 'emerald' | 'amber' | 'pink' | 'red' | 'indigo'
}

export interface ExperienceItem {
  company: string
  role: string
  from: string
  to: string
  description: string
}

export interface EducationItem {
  institution: string
  degree: string
  field: string
  year: string
}

export interface SkillScore {
  skill: string
  score: number
}

export interface ParsedFields {
  summary: string
  skills: string[]
  skillScores: SkillScore[]
  experience: ExperienceItem[]
  education: EducationItem[]
  languages: string[]
  certifications: string[]
  totalYearsExp: number
}

export type FileType = 'cv' | 'transcript' | 'note' | 'background'

export interface CandidateFile {
  id: string
  type: FileType
  name: string
  content: string
  uploadedAt: string
  size: string
}

export type CandidateStatus = 'new' | 'screening' | 'interview' | 'offer' | 'hired' | 'rejected'

export interface Candidate {
  id: string
  name: string
  email: string
  phone: string
  location: string
  avatarInitials: string
  avatarColor: string
  vacancyId: string
  score: number
  relevancyScore: number
  tags: Tag[]
  status: CandidateStatus
  parsedFields: ParsedFields
  files: CandidateFile[]
  appliedAt: string
  linkedinUrl?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}
