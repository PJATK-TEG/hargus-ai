import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { Briefcase, Users, BarChart3, Settings, Sparkles, Search, Bell } from 'lucide-react'
import { cn } from '../lib/utils'

const navItems = [
  { to: '/vacancies', icon: Briefcase, label: 'Vacancies' },
  { to: '/candidates', icon: Users, label: 'All Candidates' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-[260px] flex-shrink-0 flex flex-col border-r border-white/[0.06] bg-void-950/80">
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-16 border-b border-white/[0.06]">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-aurora-purple to-aurora-indigo shadow-glow-purple">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-[15px] font-bold tracking-tight text-white">Hargus AI</h1>
            <p className="text-[10px] font-medium text-slate-500 tracking-widest uppercase">Candidate Intelligence</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.to)
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn('nav-item', isActive && 'active')}
              >
                <item.icon className="w-[18px] h-[18px]" />
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom section */}
        <div className="px-4 py-4 border-t border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-aurora-cyan to-aurora-teal flex items-center justify-center text-xs font-bold text-white">
              MM
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">Mykyta M.</p>
              <p className="text-[11px] text-slate-500">Admin</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="h-16 flex items-center justify-between px-6 border-b border-white/[0.06] bg-void-950/50 backdrop-blur-xl flex-shrink-0">
          <div className="relative w-80">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search candidates, vacancies..."
              className="input-field pl-10 py-2.5 text-sm"
            />
          </div>
          <div className="flex items-center gap-3">
            <button className="relative p-2.5 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all">
              <Bell className="w-[18px] h-[18px]" />
              <span className="absolute top-2 right-2 w-2 h-2 rounded-full bg-aurora-purple animate-pulse-slow" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <div className="flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
