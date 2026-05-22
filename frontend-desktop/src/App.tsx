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
import Accounting from './pages/Accounting'
import Reports from './pages/Reports'
import EInvoicePage from './pages/EInvoice'
import Approvals from './pages/Approvals'

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
        <Route path="/accounting" element={<Accounting />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/einvoice" element={<EInvoicePage />} />
        <Route path="/approvals" element={<Approvals />} />
        <Route path="*" element={
          <div className="flex flex-col items-center justify-center h-screen text-gray-400">
            <div className="text-7xl mb-4">🔍</div>
            <div className="text-xl font-semibold text-gray-600">找不到此頁面</div>
            <div className="mt-2 text-sm">請從左側選單選擇功能模組</div>
          </div>
        } />
      </Route>
    </Routes>
  )
}
