import { useState, useRef, useCallback, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ForceGraph2D from 'react-force-graph-2d'
import { listObjectTypes, createObjectType, deleteObjectType, getOntologyGraph, addProperty, deleteProperty, listDatasets, mapDataset } from '../api/client'
import { Plus, Trash2, GitBranch, Link } from 'lucide-react'

export default function OntologyExplorer() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [newType, setNewType] = useState({ name: '', description: '' })
  const [selectedTypeId, setSelectedTypeId] = useState<string | null>(null)
  const [newProp, setNewProp] = useState({ name: '', data_type: 'string', required: false })
  const [showMapping, setShowMapping] = useState(false)
  const [selectedDatasetId, setSelectedDatasetId] = useState<string | null>(null)
  const [columnMappings, setColumnMappings] = useState<Record<string, string>>({})

  const { data: typesData, isLoading } = useQuery({
    queryKey: ['ontology-types'],
    queryFn: () => listObjectTypes(),
  })

  const { data: datasetsData } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => listDatasets(),
  })

  const { data: graphData } = useQuery({
    queryKey: ['ontology-graph'],
    queryFn: () => getOntologyGraph(),
  })

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string }) => createObjectType(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontology-types'] })
      queryClient.invalidateQueries({ queryKey: ['ontology-graph'] })
      setShowCreate(false)
      setNewType({ name: '', description: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteObjectType(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontology-types'] })
      queryClient.invalidateQueries({ queryKey: ['ontology-graph'] })
      setSelectedTypeId(null)
    },
  })

  const deletePropMutation = useMutation({
    mutationFn: ({ typeId, propId }: { typeId: string; propId: string }) => deleteProperty(typeId, propId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ontology-types'] })
    },
  })

  const addPropMutation = useMutation({
    mutationFn: ({ typeId, data }: { typeId: string; data: any }) => addProperty(typeId, data),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['ontology-types'] })
      setNewProp({ name: '', data_type: 'string', required: false })
    },
  })

  const mapDatasetMutation = useMutation({
    mutationFn: ({ typeId, data }: { typeId: string; data: any }) => mapDataset(typeId, data),
    onSuccess: () => {
      setShowMapping(false)
      setSelectedDatasetId(null)
      setColumnMappings({})
    },
  })

  const types = typesData?.data ?? []
  const datasets = datasetsData?.data ?? []
  const graph = graphData?.data ?? { nodes: [], edges: [] }
  const selectedType = types.find((t: any) => t.id === selectedTypeId) || null

  const graphNodes = (graph.nodes ?? []).map((n: any) => ({
    id: n.id,
    name: n.name,
    propCount: n.properties?.length ?? 0,
  }))
  const graphLinks = (graph.edges ?? []).map((e: any) => ({
    source: e.source,
    target: e.target,
    label: e.name ?? '',
  }))

  const graphContainerRef = useRef<HTMLDivElement>(null)
  const fgRef = useRef<any>(null)

  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return
    fg.d3Force('charge').strength(-500)
    fg.d3Force('link').distance(160)
    fg.d3ReheatSimulation()
  }, [graphNodes.length])

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isSelected = node.id === selectedTypeId
    const radius = 20
    const fontSize = Math.max(10, 14 / globalScale)

    ctx.beginPath()
    ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI)
    ctx.fillStyle = isSelected ? '#2563eb' : '#6366f1'
    ctx.fill()
    if (isSelected) {
      ctx.strokeStyle = '#93c5fd'
      ctx.lineWidth = 3 / globalScale
      ctx.stroke()
    }

    ctx.font = `bold ${fontSize}px Sans-Serif`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = '#ffffff'
    ctx.fillText(node.name, node.x, node.y)

    if (globalScale > 1.2) {
      ctx.font = `${fontSize * 0.75}px Sans-Serif`
      ctx.fillStyle = 'rgba(255,255,255,0.7)'
      ctx.fillText(`${node.propCount} props`, node.x, node.y + fontSize)
    }
  }, [selectedTypeId])

  const handleNodeClick = useCallback((node: any) => {
    setSelectedTypeId(node.id)
  }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Ontology Explorer</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <Plus size={16} /> New Object Type
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Type List */}
        <div className="bg-white rounded-xl shadow-sm border p-4">
          <h2 className="font-semibold mb-3">Object Types</h2>
          {isLoading ? (
            <p className="text-gray-400 text-sm">Loading...</p>
          ) : (
            <div className="space-y-2">
              {types.map((t: any) => (
                <div
                  key={t.id}
                  onClick={() => setSelectedTypeId(t.id)}
                  className={`p-3 rounded-lg cursor-pointer flex items-center justify-between ${
                    selectedTypeId === t.id ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <GitBranch size={14} className="text-purple-500" />
                    <span className="text-sm font-medium">{t.name}</span>
                    <span className="text-xs text-gray-400">({t.properties?.length ?? 0} props)</span>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteMutation.mutate(t.id) }}
                    className="p-1 hover:bg-red-50 text-red-400 rounded"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              {types.length === 0 && (
                <p className="text-gray-400 text-sm text-center py-4">No object types defined yet.</p>
              )}
            </div>
          )}
        </div>

        {/* Type Details */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border p-4">
          {selectedType ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-semibold text-lg">{selectedType.name}</h2>
                  <p className="text-sm text-gray-500">{selectedType.description || 'No description'}</p>
                </div>
                <button
                  onClick={() => { setShowMapping(true); setSelectedDatasetId(null); setColumnMappings({}) }}
                  className="flex items-center gap-2 px-3 py-2 bg-purple-600 text-white rounded-lg text-sm hover:bg-purple-700"
                >
                  <Link size={14} /> Map Dataset
                </button>
              </div>

              <h3 className="font-medium mb-2">Properties</h3>
              <table className="w-full text-sm mb-4">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="text-left p-2">Name</th>
                    <th className="text-left p-2">Type</th>
                    <th className="text-left p-2">Required</th>
                    <th className="text-right p-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(selectedType.properties ?? []).map((p: any) => (
                    <tr key={p.id} className="border-b">
                      <td className="p-2">{p.name}</td>
                      <td className="p-2"><span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{p.data_type}</span></td>
                      <td className="p-2">{p.required ? 'Yes' : 'No'}</td>
                      <td className="p-2 text-right">
                        <button
                          onClick={() => deletePropMutation.mutate({ typeId: selectedType.id, propId: p.id })}
                          className="p-1 hover:bg-red-50 text-red-400 rounded"
                          title="Remove property"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Add Property Form */}
              <div className="flex gap-2 items-end flex-wrap">
                <input
                  placeholder="Property name"
                  value={newProp.name}
                  onChange={(e) => setNewProp({ ...newProp, name: e.target.value })}
                  className="flex-1 min-w-[120px] px-3 py-2 border rounded-lg text-sm"
                />
                <select
                  value={newProp.data_type}
                  onChange={(e) => setNewProp({ ...newProp, data_type: e.target.value })}
                  className="px-3 py-2 border rounded-lg text-sm"
                >
                  <option value="string">String</option>
                  <option value="integer">Integer</option>
                  <option value="float">Float</option>
                  <option value="boolean">Boolean</option>
                  <option value="date">Date</option>
                </select>
                <label className="flex items-center gap-1 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={newProp.required}
                    onChange={(e) => setNewProp({ ...newProp, required: e.target.checked })}
                    className="rounded"
                  />
                  Required
                </label>
                <button
                  onClick={() => {
                    if (newProp.name) {
                      addPropMutation.mutate({ typeId: selectedType.id, data: newProp })
                    }
                  }}
                  className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700"
                >
                  Add
                </button>
              </div>

              {selectedType.links?.length > 0 && (
                <div className="mt-4">
                  <h3 className="font-medium mb-2">Relationships</h3>
                  {selectedType.links.map((link: any) => (
                    <div key={link.id} className="text-sm text-gray-600">
                      {link.name} → {link.target_type_name || link.target_type_id}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center text-gray-400 py-12">
              <GitBranch size={40} className="mx-auto mb-3" />
              <p>Select an object type to view its details</p>
            </div>
          )}
        </div>
      </div>

      {/* Graph Visualization */}
      <div className="mt-6 bg-white rounded-xl shadow-sm border p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Type Graph</h2>
          <span className="text-xs text-gray-400">{graphNodes.length} types · {graphLinks.length} relationships</span>
        </div>
        <div ref={graphContainerRef} className="rounded-lg overflow-hidden bg-gray-950" style={{ height: 420 }}>
          {graphNodes.length === 0 ? (
            <div className="h-full flex items-center justify-center text-gray-500 text-sm">
              No object types yet — create one to see the graph
            </div>
          ) : (
            <ForceGraph2D
              ref={fgRef}
              width={graphContainerRef.current?.offsetWidth ?? 800}
              height={420}
              graphData={{ nodes: graphNodes, links: graphLinks }}
              nodeCanvasObject={paintNode}
              nodeCanvasObjectMode={() => 'replace'}
              nodePointerAreaPaint={(node: any, color, ctx) => {
                ctx.beginPath()
                ctx.arc(node.x, node.y, 20, 0, 2 * Math.PI)
                ctx.fillStyle = color
                ctx.fill()
              }}
              linkColor={() => '#6b7280'}
              linkWidth={1.5}
              linkDirectionalArrowLength={8}
              linkDirectionalArrowRelPos={1}
              onNodeClick={handleNodeClick}
              backgroundColor="#030712"
              warmupTicks={80}
              cooldownTicks={0}
              d3VelocityDecay={0.4}
              nodeLabel={(n: any) => `${n.name} (${n.propCount} properties)`}
            />
          )}
        </div>
        {graphNodes.length > 0 && (
          <p className="text-xs text-gray-400 mt-2">Click a node to inspect · Drag to rearrange · Scroll to zoom</p>
        )}
      </div>

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
             onClick={() => setShowCreate(false)}>
          <div className="bg-white rounded-xl p-6 w-96" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-4">Create Object Type</h3>
            <div className="space-y-3">
              <input
                placeholder="Type name (e.g., Customer)"
                value={newType.name}
                onChange={(e) => setNewType({ ...newType, name: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
              <textarea
                placeholder="Description (optional)"
                value={newType.description}
                onChange={(e) => setNewType({ ...newType, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
                rows={3}
              />
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowCreate(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                  Cancel
                </button>
                <button
                  onClick={() => createMutation.mutate(newType)}
                  disabled={!newType.name}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  Create
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Map Dataset Modal */}
      {showMapping && selectedType && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
             onClick={() => setShowMapping(false)}>
          <div className="bg-white rounded-xl p-6 w-[600px] max-h-[80vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="font-semibold mb-1">Map Dataset to {selectedType.name}</h3>
            <p className="text-sm text-gray-500 mb-4">Connect a dataset's columns to this type's properties</p>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Select Dataset</label>
              <select
                value={selectedDatasetId || ''}
                onChange={(e) => {
                  setSelectedDatasetId(e.target.value || null)
                  setColumnMappings({})
                }}
                className="w-full px-3 py-2 border rounded-lg text-sm"
              >
                <option value="">-- Choose a dataset --</option>
                {datasets.map((ds: any) => (
                  <option key={ds.id} value={ds.id}>
                    {ds.name} ({ds.source_type}, {ds.row_count} rows)
                  </option>
                ))}
              </select>
            </div>

            {selectedDatasetId && (() => {
              const dataset = datasets.find((ds: any) => ds.id === selectedDatasetId)
              const columns = dataset?.schema_info?.columns || []
              const properties = selectedType.properties || []

              return columns.length > 0 ? (
                <div>
                  <label className="block text-sm font-medium mb-2">Column → Property Mapping</label>
                  <table className="w-full text-sm border rounded-lg overflow-hidden">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-2 border-b">CSV Column</th>
                        <th className="text-left p-2 border-b">Column Type</th>
                        <th className="text-left p-2 border-b">→ Map to Property</th>
                      </tr>
                    </thead>
                    <tbody>
                      {columns.map((col: any) => (
                        <tr key={col.name} className="border-b">
                          <td className="p-2 font-mono text-xs">{col.name}</td>
                          <td className="p-2">
                            <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{col.data_type}</span>
                          </td>
                          <td className="p-2">
                            <select
                              value={columnMappings[col.name] || ''}
                              onChange={(e) => {
                                const newMappings = { ...columnMappings }
                                if (e.target.value) {
                                  newMappings[col.name] = e.target.value
                                } else {
                                  delete newMappings[col.name]
                                }
                                setColumnMappings(newMappings)
                              }}
                              className="w-full px-2 py-1 border rounded text-sm"
                            >
                              <option value="">-- skip --</option>
                              {properties.map((p: any) => (
                                <option key={p.id} value={p.name}>{p.name} ({p.data_type})</option>
                              ))}
                            </select>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  <button
                    onClick={() => {
                      const autoMap: Record<string, string> = {}
                      columns.forEach((col: any) => {
                        const match = properties.find((p: any) =>
                          p.name.toLowerCase() === col.name.toLowerCase()
                        )
                        if (match) autoMap[col.name] = match.name
                      })
                      setColumnMappings(autoMap)
                    }}
                    className="mt-2 text-sm text-blue-600 hover:text-blue-800"
                  >
                    Auto-map matching names
                  </button>

                  {Object.keys(columnMappings).length > 0 && (
                    <div className="mt-3 p-2 bg-green-50 rounded text-xs text-green-700">
                      {Object.keys(columnMappings).length} of {columns.length} columns mapped
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-400">No schema found for this dataset.</p>
              )
            })()}

            <div className="flex gap-2 justify-end mt-4">
              <button onClick={() => setShowMapping(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">
                Cancel
              </button>
              <button
                onClick={() => {
                  if (selectedDatasetId && Object.keys(columnMappings).length > 0) {
                    mapDatasetMutation.mutate({
                      typeId: selectedType.id,
                      data: { dataset_id: selectedDatasetId, column_mappings: columnMappings },
                    })
                  }
                }}
                disabled={!selectedDatasetId || Object.keys(columnMappings).length === 0}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {mapDatasetMutation.isPending ? 'Saving...' : 'Save Mapping'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
