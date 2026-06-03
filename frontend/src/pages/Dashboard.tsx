import { useQuery } from '@tanstack/react-query'
import { listDatasets, listObjectTypes, listPipelines } from '../api/client'
import { Database, GitBranch, Play, Activity } from 'lucide-react'

export default function Dashboard() {
  const datasets = useQuery({ queryKey: ['datasets'], queryFn: () => listDatasets() })
  const types = useQuery({ queryKey: ['types'], queryFn: () => listObjectTypes() })
  const pipelines = useQuery({ queryKey: ['pipelines'], queryFn: () => listPipelines() })

  const cards = [
    {
      title: 'Datasets',
      value: datasets.data?.data?.length ?? 0,
      icon: Database,
      color: 'bg-blue-500',
    },
    {
      title: 'Object Types',
      value: types.data?.data?.length ?? 0,
      icon: GitBranch,
      color: 'bg-purple-500',
    },
    {
      title: 'Pipelines',
      value: pipelines.data?.data?.length ?? 0,
      icon: Play,
      color: 'bg-green-500',
    },
    {
      title: 'System Status',
      value: 'Healthy',
      icon: Activity,
      color: 'bg-emerald-500',
    },
  ]

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {cards.map((card) => (
          <div key={card.title} className="bg-white rounded-xl shadow-sm p-6 border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">{card.title}</p>
                <p className="text-2xl font-bold mt-1">{card.value}</p>
              </div>
              <div className={`${card.color} p-3 rounded-lg`}>
                <card.icon size={20} className="text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-white rounded-xl shadow-sm p-6 border">
        <h2 className="text-lg font-semibold mb-4">Getting Started</h2>
        <div className="space-y-3 text-sm text-gray-600">
          <p>1. Upload a dataset (CSV, JSON, or Parquet) in the <strong>Datasets</strong> tab</p>
          <p>2. Define object types and map your data in the <strong>Ontology</strong> tab</p>
          <p>3. Create and run transformation pipelines in the <strong>Pipelines</strong> tab</p>
          <p>4. Query your transformed data in the <strong>Data Explorer</strong></p>
        </div>
      </div>
    </div>
  )
}
