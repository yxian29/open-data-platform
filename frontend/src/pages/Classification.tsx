import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Tag, Plus, Trash2, Wand2 } from 'lucide-react'
import {
  getClassificationSummary,
  listClassificationRules,
  createClassificationRule,
  deleteClassificationRule,
  autoDetectClassification,
  getDatasetClassifications,
} from '../api/client'

const levelColors: Record<string, string> = {
  public: 'bg-green-100 text-green-700',
  internal: 'bg-blue-100 text-blue-700',
  confidential: 'bg-yellow-100 text-yellow-800',
  restricted: 'bg-red-100 text-red-700',
}

export default function Classification() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<'overview' | 'rules'>('overview')
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null)
  const [newRule, setNewRule] = useState({ name: '', pattern: '', classification: 'internal' })

  const { data: summary } = useQuery({
    queryKey: ['classification-summary'],
    queryFn: () => getClassificationSummary().then(r => r.data),
  })

  const { data: rules } = useQuery({
    queryKey: ['classification-rules'],
    queryFn: () => listClassificationRules().then(r => r.data),
  })

  const { data: datasetClassifications } = useQuery({
    queryKey: ['dataset-classifications', selectedDataset],
    queryFn: () => getDatasetClassifications(selectedDataset!).then(r => r.data),
    enabled: !!selectedDataset,
  })

  const createRule = useMutation({
    mutationFn: () => createClassificationRule(newRule),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['classification-rules'] })
      setNewRule({ name: '', pattern: '', classification: 'internal' })
    },
  })

  const deleteRule = useMutation({
    mutationFn: (id: string) => deleteClassificationRule(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['classification-rules'] }),
  })

  const autoDetect = useMutation({
    mutationFn: (datasetId: string) => autoDetectClassification(datasetId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['classification-summary'] })
      if (selectedDataset) qc.invalidateQueries({ queryKey: ['dataset-classifications', selectedDataset] })
    },
  })

  const levelCounts = (summary || []).reduce((acc: Record<string, number>, s: any) => {
    const lvl = s.overall_classification || 'unclassified'
    acc[lvl] = (acc[lvl] || 0) + 1
    return acc
  }, {})

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Tag className="text-blue-600" size={28} />
        <h1 className="text-2xl font-bold">Data Classification</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        {['public', 'internal', 'confidential', 'restricted', 'unclassified'].map(lvl => (
          <div key={lvl} className="bg-white rounded-lg border p-4">
            <p className="text-sm text-gray-500 capitalize">{lvl}</p>
            <p className="text-2xl font-bold">{levelCounts[lvl] || 0}</p>
          </div>
        ))}
      </div>

      <div className="flex gap-2 mb-4">
        <button
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'overview' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
          onClick={() => setTab('overview')}
        >
          Datasets
        </button>
        <button
          className={`px-4 py-2 text-sm rounded-lg ${tab === 'rules' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
          onClick={() => setTab('rules')}
        >
          Rules
        </button>
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="text-left px-4 py-3">Dataset</th>
                  <th className="text-left px-4 py-3">Classification</th>
                  <th className="text-left px-4 py-3">Columns</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {(summary || []).map((s: any) => (
                  <tr
                    key={s.dataset_id}
                    className={`border-b hover:bg-gray-50 cursor-pointer ${selectedDataset === s.dataset_id ? 'bg-blue-50' : ''}`}
                    onClick={() => setSelectedDataset(s.dataset_id)}
                  >
                    <td className="px-4 py-3 font-medium">{s.dataset_name}</td>
                    <td className="px-4 py-3">
                      {s.overall_classification ? (
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[s.overall_classification] || ''}`}>
                          {s.overall_classification}
                        </span>
                      ) : (
                        <span className="text-gray-400 text-xs">unclassified</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-500">{s.classified_count}/{s.column_count}</td>
                    <td className="px-4 py-3">
                      <button
                        className="text-blue-600 hover:text-blue-800"
                        title="Auto-detect"
                        onClick={e => { e.stopPropagation(); autoDetect.mutate(s.dataset_id) }}
                      >
                        <Wand2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="bg-white rounded-lg border p-4">
            <h3 className="font-medium mb-3">Column Classifications</h3>
            {selectedDataset && datasetClassifications ? (
              <div className="space-y-2">
                {datasetClassifications.length === 0 && (
                  <p className="text-gray-400 text-sm">No classifications yet. Click auto-detect to scan.</p>
                )}
                {datasetClassifications.map((c: any) => (
                  <div key={c.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <span className="text-sm font-mono">{c.column_name || '(dataset-level)'}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[c.classification] || ''}`}>
                      {c.classification}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 text-sm">Select a dataset to view column classifications</p>
            )}
          </div>
        </div>
      )}

      {tab === 'rules' && (
        <div className="bg-white rounded-lg border">
          <div className="p-4 border-b">
            <h3 className="font-medium mb-3">Add Rule</h3>
            <div className="flex gap-2 items-end">
              <div>
                <label className="block text-xs text-gray-500 mb-1">Name</label>
                <input
                  className="border rounded px-2 py-1 text-sm w-40"
                  value={newRule.name}
                  onChange={e => setNewRule(r => ({ ...r, name: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Pattern (regex)</label>
                <input
                  className="border rounded px-2 py-1 text-sm w-48 font-mono"
                  value={newRule.pattern}
                  onChange={e => setNewRule(r => ({ ...r, pattern: e.target.value }))}
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">Level</label>
                <select
                  className="border rounded px-2 py-1 text-sm"
                  value={newRule.classification}
                  onChange={e => setNewRule(r => ({ ...r, classification: e.target.value }))}
                >
                  <option value="public">Public</option>
                  <option value="internal">Internal</option>
                  <option value="confidential">Confidential</option>
                  <option value="restricted">Restricted</option>
                </select>
              </div>
              <button
                className="bg-blue-600 text-white px-3 py-1 rounded text-sm disabled:opacity-50"
                disabled={!newRule.name || !newRule.pattern}
                onClick={() => createRule.mutate()}
              >
                <Plus size={14} />
              </button>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Pattern</th>
                <th className="text-left px-4 py-3">Classification</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {(rules || []).map((r: any) => (
                <tr key={r.id} className="border-b">
                  <td className="px-4 py-3">{r.name}</td>
                  <td className="px-4 py-3 font-mono text-xs">{r.pattern}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${levelColors[r.classification] || ''}`}>
                      {r.classification}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      className="text-red-500 hover:text-red-700"
                      onClick={() => deleteRule.mutate(r.id)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
