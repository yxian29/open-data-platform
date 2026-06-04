import { NavLink, Outlet } from 'react-router-dom'
import {
  LayoutDashboard, Database, GitBranch, Play, Search,
  Shield, Tag, GitMerge, Bot
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/datasets', icon: Database, label: 'Datasets' },
  { to: '/ontology', icon: GitBranch, label: 'Ontology' },
  { to: '/pipelines', icon: Play, label: 'Pipelines' },
  { to: '/explorer', icon: Search, label: 'Data Explorer' },
  { to: '/lineage', icon: GitMerge, label: 'Lineage' },
  { to: '/classification', icon: Tag, label: 'Classification' },
  { to: '/audit', icon: Shield, label: 'Audit Log' },
  { to: '/ai', icon: Bot, label: 'AI Assistant' },
]

export default function Layout() {
  return (
    <div className="flex h-screen">
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        <div className="p-6 border-b border-gray-700">
          <h1 className="text-xl font-bold">ODP</h1>
          <p className="text-xs text-gray-400 mt-1">Open Data Platform</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-gray-700 text-xs text-gray-500">
          v0.3.0 - Phase 3
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
