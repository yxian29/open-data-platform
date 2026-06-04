import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield, ChevronDown, ChevronRight } from 'lucide-react'
import { listAuditEvents, getAuditStats } from '../api/client'

export default function AuditLog() {
  const [filters, setFilters] = useState({
    user_id: '',
    action: '',
    resource_type: '',
    limit: 50,
    offset: 0,
  })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const { data: eventsData } = useQuery({
    queryKey: ['audit-events', filters],
    queryFn: () => listAuditEvents(filters).then(r => r.data),
  })

  const { data: stats } = useQuery({
    queryKey: ['audit-stats'],
    queryFn: () => getAuditStats().then(r => r.data),
  })

  const events = eventsData?.events || []
  const total = eventsData?.total || 0

  const statusColor = (s: string) =>
    s === 'success' ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Shield className="text-blue-600" size={28} />
        <h1 className="text-2xl font-bold">Audit Log</h1>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">Total Events (7d)</p>
            <p className="text-2xl font-bold">{stats.total_events}</p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">Unique Users</p>
            <p className="text-2xl font-bold">{Object.keys(stats.by_user || {}).length}</p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">Top Action</p>
            <p className="text-2xl font-bold">
              {Object.entries(stats.by_action || {}).sort((a, b) => (b[1] as number) - (a[1] as number))[0]?.[0] || '-'}
            </p>
          </div>
          <div className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500">Resource Types</p>
            <p className="text-2xl font-bold">{Object.keys(stats.by_resource_type || {}).length}</p>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg border mb-4 p-4 flex gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">User</label>
          <input
            className="border rounded px-2 py-1 text-sm w-32"
            value={filters.user_id}
            onChange={e => setFilters(f => ({ ...f, user_id: e.target.value, offset: 0 }))}
            placeholder="All users"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Action</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={filters.action}
            onChange={e => setFilters(f => ({ ...f, action: e.target.value, offset: 0 }))}
          >
            <option value="">All</option>
            <option value="create">Create</option>
            <option value="read">Read</option>
            <option value="update">Update</option>
            <option value="delete">Delete</option>
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Resource</label>
          <select
            className="border rounded px-2 py-1 text-sm"
            value={filters.resource_type}
            onChange={e => setFilters(f => ({ ...f, resource_type: e.target.value, offset: 0 }))}
          >
            <option value="">All</option>
            <option value="datasets">Datasets</option>
            <option value="ontology">Ontology</option>
            <option value="pipelines">Pipelines</option>
            <option value="explorer">Explorer</option>
            <option value="auth">Auth</option>
          </select>
        </div>
      </div>

      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-medium text-gray-600 w-8"></th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Timestamp</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">User</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Resource</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              <th className="text-left px-4 py-3 font-medium text-gray-600">Duration</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e: any) => (
              <>
                <tr
                  key={e.id}
                  className="border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => setExpandedId(expandedId === e.id ? null : e.id)}
                >
                  <td className="px-4 py-3 text-gray-400">
                    {expandedId === e.id ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </td>
                  <td className="px-4 py-3 text-gray-500 font-mono text-xs">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">{e.user_id}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-3">{e.resource_type}{e.resource_id ? ` / ${e.resource_id.slice(0, 8)}...` : ''}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${statusColor(e.status)}`}>
                      {e.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{e.duration_ms != null ? `${e.duration_ms}ms` : '-'}</td>
                </tr>
                {expandedId === e.id && (
                  <tr key={`${e.id}-detail`} className="bg-gray-50">
                    <td colSpan={7} className="px-8 py-4">
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div><span className="font-medium">IP Address:</span> {e.ip_address || '-'}</div>
                        <div><span className="font-medium">User Agent:</span> {e.user_agent?.slice(0, 80) || '-'}</div>
                        <div><span className="font-medium">Session ID:</span> {e.session_id || '-'}</div>
                        <div><span className="font-medium">Resource ID:</span> {e.resource_id || '-'}</div>
                        <div className="col-span-2">
                          <span className="font-medium">Details:</span>
                          <pre className="mt-1 bg-white border rounded p-2 overflow-x-auto">
                            {JSON.stringify(e.details, null, 2)}
                          </pre>
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
            {events.length === 0 && (
              <tr><td colSpan={7} className="text-center py-8 text-gray-400">No audit events found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {total > filters.limit && (
        <div className="flex justify-between items-center mt-4">
          <span className="text-sm text-gray-500">
            Showing {filters.offset + 1}-{Math.min(filters.offset + filters.limit, total)} of {total}
          </span>
          <div className="flex gap-2">
            <button
              className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              disabled={filters.offset === 0}
              onClick={() => setFilters(f => ({ ...f, offset: f.offset - f.limit }))}
            >
              Previous
            </button>
            <button
              className="px-3 py-1 text-sm border rounded disabled:opacity-50"
              disabled={filters.offset + filters.limit >= total}
              onClick={() => setFilters(f => ({ ...f, offset: f.offset + f.limit }))}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
