import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import AnalyticsPage from './pages/AnalyticsPage'
import CandidatesPage from './pages/CandidatesPage'
import SettingsPage from './pages/SettingsPage'
import VacanciesPage from './pages/VacanciesPage'
import VacancyDetailPage from './pages/VacancyDetailPage'
import CandidateDetailPage from './pages/CandidateDetailPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Navigate to="/vacancies" replace />} />
        <Route path="/vacancies" element={<VacanciesPage />} />
        <Route path="/candidates" element={<CandidatesPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/vacancies/:vacancyId" element={<VacancyDetailPage />} />
        <Route path="/vacancies/:vacancyId/candidates/:candidateId" element={<CandidateDetailPage />} />
      </Route>
    </Routes>
  )
}
