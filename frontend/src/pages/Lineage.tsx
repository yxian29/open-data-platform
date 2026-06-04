import { useState, useCallback, useRef, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import ForceGraph2D from 'react-force-graph-2d'
import { GitMerge, RefreshCw, Search } from 'lucide-react'
import { getLineageGraph, refreshLineage, getColumnLineage } from '../api/client'

const NODE_COLORS: Record<string, string> = {
  source_column: '#3b82f6',
  transform: '#f59e0b',
  target_column: '#10b981',
}

const GRAPH_HEIGHT = 500

export default function Lineage() {
  const qc = useQueryClient()
  const graphRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [containerWidth, setContainerWidth] = useState(600)
  const [selectedNode, setSelectedNode] = useState<any>(null)
  const [columnInfo, setColumnInfo] = useState<any>(null)
  const [search, setSearch] = useState('')

  // Track container width so the graph never overflows
  useEffect(() => {
    if (!containerRef.current) return
    const observer = new ResizeObserver(entries => {
      setContainerWidth(entries[0].contentRect.width)
    })
    observer.observe(containerRef.current)
    setContainerWidth(containerRef.current.clientWidth)
    return () => observer.disconnect()
  }, [])

  const { data: graph, isLoading } = useQuery({
    queryKey: ['lineage-graph'],
    queryFn: () => getLineageGraph().then(r => r.data),
  })

  const refresh = useMutation({
    mutationFn: () => refreshLineage(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['lineage-graph'] }),
  })

  const graphData = (() => {
    if (!graph) return { nodes: [], links: [] }

    const nodes = graph.nodes.map((n: any) => ({
      id: n.id,
      label: n.column_name
        ? `${n.table_name}.${n.column_name}`
        : n.transform_name || n.table_name || 'unknown',
      nodeType: n.node_type,
      ...n,
    }))

    const nodeIds = new Set(nodes.map((n: any) => n.id))
    const links = graph.edges
      .filter((e: any) => nodeIds.has(e.source_node_id) && nodeIds.has(e.target_node_id))
      .map((e: any) => ({
        source: e.source_node_id,
        target: e.target_node_id,
        edgeType: e.edge_type,
      }))

    return { nodes, links }
  })()

  // Fit graph into view once simulation settles
  const handleEngineStop = useCallback(() => {
    graphRef.current?.zoomToFit(400, 30)
  }, [])

  const handleNodeClick = useCallback(async (node: any) => {
    setSelectedNode(node)
    if (node.table_name && node.column_name) {
      try {
        const resp = await getColumnLineage(node.table_name, node.column_name)
        setColumnInfo(resp.data)
      } catch {
        setColumnInfo(null)
      }
    }
  }, [])

  const handleSearch = () => {
    if (!search || !graphRef.current) return
    const node = graphData.nodes.find((n: any) =>
      n.label?.toLowerCase().includes(search.toLowerCase())
    )
    if (node) {
      graphRef.current.centerAt(node.x, node.y, 500)
      graphRef.current.zoom(3, 500)
      setSelectedNode(node)
    }
  }

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D) => {
    const size = 5
    const color = NODE_COLORS[node.nodeType] || '#94a3b8'
    const isSelected = selectedNode?.id === node.id

    ctx.beginPath()
    ctx.arc(node.x, node.y, isSelected ? size + 2 : size, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    if (isSelected) {
      ctx.strokeStyle = '#1e40af'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.fillStyle = '#374151'
    ctx.font = '3px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText(node.label || '', node.x, node.y + size + 4)
  }, [selectedNode])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <GitMerge className="text-blue-600" size={28} />
          <h1 className="text-2xl font-bold">Data Lineage</h1>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex">
            <input
              className="border rounded-l px-3 py-1.5 text-sm w-48"
              placeholder="Search column..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <button
              className="border border-l-0 rounded-r px-2 py-1.5 bg-gray-50 hover:bg-gray-100"
              onClick={handleSearch}
            >
              <Search size={14} />
            </button>
          </div>
          <button
            className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded text-sm"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
          >
            <RefreshCw size={14} className={refresh.isPending ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1 text-xs text-gray-500">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            {type.replace('_', ' ')}
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div
          ref={containerRef}
          className="lg:col-span-2 bg-white rounded-lg border overflow-hidden"
          style={{ height: GRAPH_HEIGHT }}
        >
          {isLoading ? (
            <div className="flex items-center justify-center h-full text-gray-400">Loading lineage graph...</div>
          ) : graphData.nodes.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400">
              <p>No lineage data yet.</p>
              <p className="text-sm mt-1">Click "Refresh" to parse dbt models and build the lineage graph.</p>
            </div>
          ) : (
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              nodeCanvasObject={paintNode}
              onNodeClick={handleNodeClick}
              onEngineStop={handleEngineStop}
              linkColor={() => '#d1d5db'}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              width={containerWidth}
              height={GRAPH_HEIGHT}
            />
          )}
        </div>

        <div className="bg-white rounded-lg border p-4">
          <h3 className="font-medium mb-3">Details</h3>
          {selectedNode ? (
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500">Type</p>
                <p className="text-sm font-medium">{selectedNode.nodeType?.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Table</p>
                <p className="text-sm font-mono">{selectedNode.table_name || '-'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500">Column</p>
                <p className="text-sm font-mono">{selectedNode.column_name || '-'}</p>
              </div>
              {selectedNode.transform_name && (
                <div>
                  <p className="text-xs text-gray-500">Transform</p>
                  <p className="text-sm font-mono">{selectedNode.transform_name}</p>
                </div>
              )}
              {columnInfo && (
                <>
                  <hr />
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Upstream ({columnInfo.upstream?.length || 0})</p>
                    {(columnInfo.upstream || []).map((n: any) => (
                      <p key={n.id} className="text-xs font-mono text-blue-600">
                        {n.table_name}.{n.column_name || n.transform_name}
                      </p>
                    ))}
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1">Downstream ({columnInfo.downstream?.length || 0})</p>
                    {(columnInfo.downstream || []).map((n: any) => (
                      <p key={n.id} className="text-xs font-mono text-green-600">
                        {n.table_name}.{n.column_name || n.transform_name}
                      </p>
                    ))}
                  </div>
                </>
              )}
            </div>
          ) : (
            <p className="text-sm text-gray-400">Click a node in the graph to view details</p>
          )}
        </div>
      </div>
    </div>
  )
}
