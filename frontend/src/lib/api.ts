import type { Vacancy, Candidate, Message, AnalysisReport } from '../types'

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000/api/v1'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

interface ListResponse<T> {
  items: T[]
  meta: { total: number; limit: number; offset: number; returned: number }
}

export interface AiTaskRecord {
  id: string
  type: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  result?: Record<string, string> | null
}

export const api = {
  listVacancies: () =>
    get<ListResponse<Vacancy>>('/vacancies').then((r) => r.items),

  getVacancy: (id: string) =>
    get<Vacancy>(`/vacancies/${id}`),

  createVacancy: (body: Omit<Vacancy, 'id' | 'createdAt' | 'candidatesCount' | 'status'>) =>
    post<Vacancy>('/vacancies', body),

  updateVacancy: (id: string, body: Partial<Omit<Vacancy, 'id' | 'createdAt' | 'candidatesCount'>>) =>
    put<Vacancy>(`/vacancies/${id}`, body),

  deleteVacancy: (id: string): Promise<void> =>
    fetch(`${BASE}/vacancies/${id}`, { method: 'DELETE' }).then((res) => {
      if (!res.ok && res.status !== 204) throw new Error(`API ${res.status}: /vacancies/${id}`)
    }),

  listVacancyCandidates: (vacancyId: string) =>
    get<ListResponse<Candidate>>(`/vacancies/${vacancyId}/candidates`).then((r) => r.items),

  listCandidates: (params?: { vacancyId?: string }) => {
    const qs = params?.vacancyId ? `?vacancyId=${encodeURIComponent(params.vacancyId)}` : ''
    return get<ListResponse<Candidate>>(`/candidates${qs}`).then((r) => r.items)
  },

  getCandidate: (id: string) =>
    get<Candidate>(`/candidates/${id}`),

  listMessages: (candidateId: string) =>
    get<ListResponse<Message>>(`/candidates/${candidateId}/messages`).then((r) => r.items),

  queryCandidate: (candidateId: string, query: string, vacancyId?: string) =>
    post<AiTaskRecord>(`/candidates/${candidateId}/query`, { query, vacancyId: vacancyId ?? '' }),

  submitAiTask: (body: { type: string; candidateId: string; prompt: string }) =>
    post<AiTaskRecord>('/ai/tasks', body),

  analyzeCandidate: (candidateId: string, vacancyId?: string) =>
    post<AiTaskRecord>('/ai/tasks', { type: 'candidate_summary', candidateId, vacancyId }),

  getAiTask: (id: string) =>
    get<AiTaskRecord>(`/ai/tasks/${id}`),

  listCandidateReports: (candidateId: string) =>
    get<AnalysisReport[]>(`/candidates/${candidateId}/reports`),

  getCandidateReportPdfUrl: (candidateId: string, reportId: string) =>
    `${BASE}/candidates/${candidateId}/reports/${reportId}/pdf`,

  deleteCandidate: (id: string): Promise<void> =>
    fetch(`${BASE}/candidates/${id}`, { method: 'DELETE' }).then((res) => {
      if (!res.ok && res.status !== 204) throw new Error(`API ${res.status}: /candidates/${id}`)
    }),

  createCandidate: (formData: FormData): Promise<Candidate> =>
    fetch(`${BASE}/candidates`, { method: 'POST', body: formData }).then(async (res) => {
      if (!res.ok) throw new Error(await res.text())
      return res.json()
    }),
}
