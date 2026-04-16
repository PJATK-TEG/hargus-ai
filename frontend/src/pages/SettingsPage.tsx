import { Bell, Palette } from 'lucide-react'

const sections = [
  {
    title: 'Notifications',
    icon: Bell,
    description: 'Choose when to notify the hiring team about new candidates, interviews, and offers.',
  },
  {
    title: 'Appearance',
    icon: Palette,
    description: 'Theme, density, and dashboard layout preferences for the recruiting workspace.',
  },
]

export default function SettingsPage() {
  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Configuration areas for the Hargus AI workspace</p>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        {sections.map((section) => (
          <div key={section.title} className="glass-card rounded-2xl p-6">
            <div className="w-11 h-11 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-4">
              <section.icon className="w-5 h-5 text-aurora-violet" />
            </div>
            <h2 className="text-base font-semibold text-white mb-2">{section.title}</h2>
            <p className="text-sm text-slate-400 leading-relaxed">{section.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
