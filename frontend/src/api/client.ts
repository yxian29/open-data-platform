import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Datasets
export const uploadDataset = (file: File, name?: string) => {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  return api.post('/datasets/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const listDatasets = () => api.get('/datasets')
export const getDataset = (id: string) => api.get(`/datasets/${id}`)
export const previewDataset = (id: string, limit = 50) =>
  api.get(`/datasets/${id}/preview?limit=${limit}`)
export const deleteDataset = (id: string) => api.delete(`/datasets/${id}`)

// Ontology
export const listObjectTypes = () => api.get('/ontology/types')
export const createObjectType = (data: { name: string; description?: string }) =>
  api.post('/ontology/types', data)
export const deleteObjectType = (id: string) => api.delete(`/ontology/types/${id}`)
export const addProperty = (typeId: string, data: any) =>
  api.post(`/ontology/types/${typeId}/properties`, data)
export const deleteProperty = (typeId: string, propId: string) =>
  api.delete(`/ontology/types/${typeId}/properties/${propId}`)
export const addLink = (typeId: string, data: any) =>
  api.post(`/ontology/types/${typeId}/links`, data)
export const getOntologyGraph = () => api.get('/ontology/graph')
export const queryObjects = (typeId?: string) =>
  api.get('/ontology/objects', { params: { type_id: typeId } })
export const mapDataset = (typeId: string, data: any) =>
  api.post(`/ontology/types/${typeId}/map`, data)

// Pipelines
export const listPipelines = () => api.get('/pipelines')
export const createPipeline = (data: any) => api.post('/pipelines', data)
export const triggerPipeline = (id: string) => api.post(`/pipelines/${id}/run`)
export const listPipelineRuns = (id: string) => api.get(`/pipelines/${id}/runs`)
export const deletePipeline = (id: string) => api.delete(`/pipelines/${id}`)

// Data Explorer
export const executeQuery = (query: string) =>
  api.post('/explorer/query', { query })

// Audit
export const listAuditEvents = (params: Record<string, any>) =>
  api.get('/audit/events', { params })
export const getAuditStats = (days = 7) =>
  api.get('/audit/stats', { params: { days } })

// Classification
export const getDatasetClassifications = (datasetId: string) =>
  api.get(`/classification/datasets/${datasetId}`)
export const setClassification = (datasetId: string, data: any) =>
  api.post(`/classification/datasets/${datasetId}`, data)
export const autoDetectClassification = (datasetId: string) =>
  api.post(`/classification/datasets/${datasetId}/auto-detect`)
export const listClassificationRules = () =>
  api.get('/classification/rules')
export const createClassificationRule = (data: any) =>
  api.post('/classification/rules', data)
export const updateClassificationRule = (id: string, data: any) =>
  api.put(`/classification/rules/${id}`, data)
export const deleteClassificationRule = (id: string) =>
  api.delete(`/classification/rules/${id}`)
export const getClassificationSummary = () =>
  api.get('/classification/summary')

// Lineage
export const getLineageGraph = () => api.get('/lineage/graph')
export const getColumnLineage = (table: string, column: string) =>
  api.get(`/lineage/column/${table}/${column}`)
export const getDatasetLineage = (id: string) =>
  api.get(`/lineage/dataset/${id}`)
export const refreshLineage = () => api.post('/lineage/refresh')

// AI Assistant
export const aiChat = (data: { query: string; session_id?: string }) =>
  api.post('/ai/chat', data)
export const aiSuggest = (data: { dataset_name: string; columns: { name: string; type?: string }[] }) =>
  api.post('/ai/suggest', data)
export const aiSummarize = (data: { dataset_name: string; table_name?: string; sample_rows?: number }) =>
  api.post('/ai/summarize', data)
export const getAiHistory = (sessionId: string) =>
  api.get(`/ai/history/${sessionId}`)

export default api
