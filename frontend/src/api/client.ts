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

export default api
