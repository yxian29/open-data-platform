import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listPipelines, createPipeline, triggerPipeline, listPipelineRuns, deletePipeline } from '../api/client'
import { Plus, Play, Trash2, Clock, CheckCircle, XCircle, Loader } from 'lucide-react'

const statusIcons: Record<string, any> = {
  completed: <CheckCircle size={14} className="text-green-500" />,
  running: <Loader size={14} className="text-blue-500 animate-spin" />,
  failed: <XCircle size={14} className="text-red-500" />,
  pending: <Clock size={14} className="text-gray-400" />,
}

export default function Pipelines() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [selectedPipeline, setSelectedPipeline] = useState<string | null>(null)
  const [newPipeline, setNewPipeline] = useState({ name: '', description: '', pipeline_type: 'dbt' })

  const { data: pipelinesData, isLoading } = useQuery({
    queryKey: ['pipelines'],
    queryFn: () => listPipelines(),
  })

  const { data: runsData } = useQuery({
    queryKey: ['pipeline-runs', selectedPipeline],
    queryFn: () => listPipelineRuns(selectedPipeline!),
    enabled: !!selectedPipeline,
  })

  const createMutation = useMutation({
    mutationFn: (data: any) => createPipeline(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setShowCreate(false)
      setNewPipeline({ name: '', description: '', pipeline_type: 'dbt' })
    },
  })

  const triggerMutation = useMutation({
    mutationFn: (id: string) => {
      setSelectedPipeline(id)
      return triggerPipeline(id)
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      queryClient.invalidateQueries({ queryKey: ['pipeline-runs', id] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePipeline(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipelines'] })
      setSelectedPipeline(null)
    },
  })

  const pipelines = pipelinesData?.data ?? []
  const runs = runsData?.data ?? []

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Pipelines</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={16} /> New Pipeline
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pipeline List */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">All Pipelines</h2>
          </div>
          {isLoading ? (
            <p className="p-4 text-gray-400 text-sm">Loading...</p>
          ) : (
            <div className="divide-y">
              {pipelines.map((p: any) => (
                <div
                  key={p.id}
                  onClick={() => setSelectedPipeline(p.id)}
                  className={`p-4 cursor-pointer flex items-center justify-between hover:bg-gray-50 ${
                    selectedPipeline === p.id ? 'bg-blue-50' : ''
                  }`}
                >
                  <div>
                    <p className="font-medium text-sm">{p.name}</p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {p.pipeline_type} | {new Date(p.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); triggerMutation.mutate(p.id) }}
                      className="p-2 hover:bg-green-50 text-green-600 rounded-lg"
                      title="Run pipeline"
                    >
                      <Play size={16} />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(p.id) }}
                      className="p-2 hover:bg-red-50 text-red-400 rounded-lg"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
              {pipelines.length === 0 && (
                <p className="p-8 text-center text-gray-400 text-sm">No pipelines created yet.</p>
              )}
            </div>
          )}
        </div>

        {/* Run History */}
        <div className="bg-white rounded-xl shadow-sm border">
          <div className="p-4 border-b">
            <h2 className="font-semibold">Run History</h2>
          </div>
          {selectedPipeline ? (
            <div className="divide-y">
              {runs.map((run: any) => (
                <div key={run.id} className="p-4 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {statusIcons[run.status] || statusIcons.pending}
                    <span className="text-sm capitalize">{run.status}</span>
                  </div>
                  <div className="text-xs text-gray-400">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '-'}
                  </div>
                </div>
              ))}
              {runs.length === 0 && (
                <p className="p-8 text-center text-gray-400 text-sm">No runs yet. Click play to trigger.</p>
              )}
            </div>
          ) : (
            <p className="p-8 text-center text-gray-400 text-sm">Select a pipeline to view runs.</p>
          )}
        </div>
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
             onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl p-6 w-96" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-4">Create Pipeline</h3>
            <div className="space-y-3">
              <input
                placeholder="Pipeline name"
                value={newPipeline.name}
                onChange={(e) => setNewPipeline({ ...newPipeline, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
              <textarea
                placeholder="Description"
                value={newPipeline.description}
                onChange={(e) => setNewPipeline({ ...newPipeline, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                rows={2}
              />
              <select
                value={newPipeline.pipeline_type}
                onChange={(e) => setNewPipeline({ ...newPipeline, pipeline_type: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              >
                <option value="dbt">dbt (SQL transforms)</option>
                <option value="dagster">Dagster (Python assets)</option>
                <option value="spark">Spark (heavy ETL)</option>
              </select>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                  Cancel
                </button>
                <button
                  onClick={() => createMutation.mutate(newPipeline)}
                  disabled={!newPipeline.name}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
