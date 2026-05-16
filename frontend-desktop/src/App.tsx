import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Inventory from './pages/Inventory'
import Purchase from './pages/Purchase'
import Production from './pages/Production'
import Sales from './pages/Sales'
import Quality from './pages/Quality'
import EventsPage from './pages/Events'
import Permissions from './pages/Permissions'
import MyPermissions from './pages/MyPermissions'
import Settings from './pages/Settings'
import Crm from './pages/Crm'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/purchase" element={<Purchase />} />
        <Route path="/production" element={<Production />} />
        <Route path="/sales" element={<Sales />} />
        <Route path="/quality" element={<Quality />} />
        <Route path="/events" element={<EventsPage />} />
        <Route path="/permissions" element={<Permissions />} />
        <Route path="/me/permissions" element={<MyPermissions />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/crm" element={<Crm />} />
      </Route>
    </Routes>
  )
}
