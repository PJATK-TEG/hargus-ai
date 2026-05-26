import { Navigate, Outlet, Routes, Route } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import Layout from './components/Layout'
import AnalyticsPage from './pages/AnalyticsPage'
import CandidatesPage from './pages/CandidatesPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import LoginPage from './pages/LoginPage'
import SettingsPage from './pages/SettingsPage'
import VacanciesPage from './pages/VacanciesPage'
import VacancyDetailPage from './pages/VacancyDetailPage'
import { AuthProvider, useAuth } from './lib/auth'

function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-void-950">
        <Loader2 className="w-8 h-8 text-aurora-purple animate-spin" />
      </div>
    )
  }
  if (!user) return <Navigate to="/login" replace />
  return <Outlet />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route path="/" element={<Navigate to="/vacancies" replace />} />
            <Route path="/vacancies" element={<VacanciesPage />} />
            <Route path="/candidates" element={<CandidatesPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/vacancies/:vacancyId" element={<VacancyDetailPage />} />
            <Route path="/vacancies/:vacancyId/candidates/:candidateId" element={<CandidateDetailPage />} />
          </Route>
        </Route>
      </Routes>
    </AuthProvider>
  )
}
