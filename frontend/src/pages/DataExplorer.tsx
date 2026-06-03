import { useState } from 'react'
import { Play } from 'lucide-react'
import api from '../api/client'

export default function DataExplorer() {
  const [query, setQuery] = useState('SELECT 1 AS test')
  const [results, setResults] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const executeQuery = async () => {
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      const res = await api.post('/explorer/query', { query })
      setResults(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Data Explorer</h1>

      <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">SQL Query (ClickHouse)</span>
          <button
            onClick={executeQuery}
            disabled={loading || !query.trim()}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
          >
            <Play size={14} /> {loading ? 'Running...' : 'Execute'}
          </button>
        </div>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full h-32 px-3 py-2 border rounded-lg font-mono text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="SELECT * FROM odp.analytics_customers LIMIT 10"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              executeQuery()
            }
          }}
        />
        <p className="text-xs text-gray-400 mt-1">Press Cmd+Enter to execute</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {results && (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <div className="p-3 border-b bg-gray-50 flex items-center justify-between">
            <span className="text-sm text-gray-600">
              {Array.isArray(results) ? `${results.length} rows` : 'Results'}
            </span>
          </div>
          <div className="overflow-auto max-h-[500px]">
            {Array.isArray(results) && results.length > 0 ? (
              <table className="w-full text-xs">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    {Object.keys(results[0]).map((col) => (
                      <th key={col} className="text-left p-2 border-b font-medium">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {results.map((row: any, i: number) => (
                    <tr key={i} className="border-b hover:bg-gray-50">
                      {Object.values(row).map((val: any, j: number) => (
                        <td key={j} className="p-2">{String(val ?? '')}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="p-4 text-sm text-gray-500">No results</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
