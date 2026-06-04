import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import OntologyExplorer from './pages/OntologyExplorer'
import Pipelines from './pages/Pipelines'
import DataExplorer from './pages/DataExplorer'
import AuditLog from './pages/AuditLog'
import Classification from './pages/Classification'
import Lineage from './pages/Lineage'
import AIAssistant from './pages/AIAssistant'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="datasets" element={<Datasets />} />
          <Route path="ontology" element={<OntologyExplorer />} />
          <Route path="pipelines" element={<Pipelines />} />
          <Route path="explorer" element={<DataExplorer />} />
          <Route path="lineage" element={<Lineage />} />
          <Route path="classification" element={<Classification />} />
          <Route path="audit" element={<AuditLog />} />
          <Route path="ai" element={<AIAssistant />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
