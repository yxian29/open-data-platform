import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Datasets from './pages/Datasets'
import OntologyExplorer from './pages/OntologyExplorer'
import Pipelines from './pages/Pipelines'
import DataExplorer from './pages/DataExplorer'

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
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
