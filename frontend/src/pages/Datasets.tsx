import { useState, useCallback } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { listDatasets, uploadDataset, deleteDataset, previewDataset } from '../api/client'
import { Upload, Trash2, Eye, FileText } from 'lucide-react'

export default function Datasets() {
  const queryClient = useQueryClient()
  const [previewData, setPreviewData] = useState<any>(null)
  const [dragActive, setDragActive] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => listDatasets(),
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDataset(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['datasets'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDataset(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['datasets'] }),
  })

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files[0]
    if (file) uploadMutation.mutate(file)
  }, [uploadMutation])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) uploadMutation.mutate(file)
  }

  const handlePreview = async (id: string) => {
    const res = await previewDataset(id)
    setPreviewData(res.data)
  }

  const datasets = data?.data ?? []

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Datasets</h1>

      {/* Upload Zone */}
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center mb-6 transition-colors ${
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
      >
        <Upload className="mx-auto mb-3 text-gray-400" size={40} />
        <p className="text-gray-600 mb-2">Drag and drop a file here, or click to browse</p>
        <p className="text-xs text-gray-400">Supports CSV, JSON, Parquet</p>
        <input
          type="file"
          accept=".csv,.json,.parquet"
          onChange={handleFileSelect}
          className="hidden"
          id="file-upload"
        />
        <label
          htmlFor="file-upload"
          className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700"
        >
          Select File
        </label>
        {uploadMutation.isPending && <p className="mt-2 text-sm text-blue-600">Uploading...</p>}
      </div>

      {/* Dataset Table */}
      {isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : (
        <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="text-left p-4 font-medium">Name</th>
                <th className="text-left p-4 font-medium">Type</th>
                <th className="text-left p-4 font-medium">Rows</th>
                <th className="text-left p-4 font-medium">Size</th>
                <th className="text-left p-4 font-medium">Created</th>
                <th className="text-right p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((ds: any) => (
                <tr key={ds.id} className="border-b hover:bg-gray-50">
                  <td className="p-4 flex items-center gap-2">
                    <FileText size={16} className="text-gray-400" />
                    {ds.name}
                  </td>
                  <td className="p-4">
                    <span className="px-2 py-1 bg-gray-100 rounded text-xs">{ds.source_type}</span>
                  </td>
                  <td className="p-4">{ds.row_count.toLocaleString()}</td>
                  <td className="p-4">{(ds.file_size_bytes / 1024).toFixed(1)} KB</td>
                  <td className="p-4 text-gray-500">
                    {new Date(ds.created_at).toLocaleDateString()}
                  </td>
                  <td className="p-4 text-right space-x-2">
                    <button
                      onClick={() => handlePreview(ds.id)}
                      className="p-1 hover:bg-gray-100 rounded"
                      title="Preview"
                    >
                      <Eye size={16} />
                    </button>
                    <button
                      onClick={() => deleteMutation.mutate(ds.id)}
                      className="p-1 hover:bg-red-50 text-red-500 rounded"
                      title="Delete"
                    >
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))}
              {datasets.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-400">
                    No datasets yet. Upload a file to get started.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Preview Modal */}
      {previewData && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
             onClick={() => setPreviewData(null)}>
          <div className="bg-white rounded-xl p-6 max-w-4xl max-h-[80vh] overflow-auto w-full mx-4"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold">Data Preview</h3>
              <button onClick={() => setPreviewData(null)} className="text-gray-400 hover:text-gray-600">
                Close
              </button>
            </div>
            <div className="overflow-auto">
              <table className="w-full text-xs border">
                {previewData.columns && (
                  <thead className="bg-gray-50">
                    <tr>
                      {previewData.columns.map((col: string) => (
                        <th key={col} className="p-2 border text-left font-medium">{col}</th>
                      ))}
                    </tr>
                  </thead>
                )}
                <tbody>
                  {(previewData.rows || []).slice(0, 20).map((row: any, i: number) => (
                    <tr key={i} className="border-b">
                      {Object.values(row).map((val: any, j: number) => (
                        <td key={j} className="p-2 border">{String(val)}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
