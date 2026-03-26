import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import VacanciesPage from './pages/VacanciesPage'
import VacancyDetailPage from './pages/VacancyDetailPage'
import CandidateDetailPage from './pages/CandidateDetailPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/vacancies" replace />} />
        <Route path="/vacancies" element={<VacanciesPage />} />
        <Route path="/vacancies/:vacancyId" element={<VacancyDetailPage />} />
        <Route path="/vacancies/:vacancyId/candidates/:candidateId" element={<CandidateDetailPage />} />
      </Route>
    </Routes>
  )
}
