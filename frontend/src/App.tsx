import { lazy, Suspense, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Boot from './components/Boot'
import Layout from './components/Layout'
import { Spinner } from './components/ui'
import { useAuth } from './lib/auth'
import { BusinessProvider } from './lib/business'
import Login from './pages/Login'

const CommandCenter = lazy(() => import('./pages/CommandCenter'))
const Agents = lazy(() => import('./pages/Agents'))
const Schemes = lazy(() => import('./pages/Schemes'))
const Cashflow = lazy(() => import('./pages/Cashflow'))
const Risk = lazy(() => import('./pages/Risk'))
const Documents = lazy(() => import('./pages/Documents'))
const Applications = lazy(() => import('./pages/Applications'))
const ConsentPage = lazy(() => import('./pages/Consent'))
const Onboard = lazy(() => import('./pages/Onboard'))
const MoneyTrail = lazy(() => import('./pages/MoneyTrail'))
const Field = lazy(() => import('./pages/Field'))
const Model = lazy(() => import('./pages/Model'))
const Audit = lazy(() => import('./pages/Audit'))

export default function App() {
  const { user, ready } = useAuth()
  const [booted, setBooted] = useState(() => sessionStorage.getItem('artha.booted') === '1')

  if (!booted) return <Boot onDone={() => { sessionStorage.setItem('artha.booted', '1'); setBooted(true) }} />
  if (!ready) return <Spinner label="Restoring secure session" />
  if (!user) return <Login />

  return (
    <BusinessProvider>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<CommandCenter />} />
            <Route path="agents" element={<Agents />} />
            <Route path="schemes" element={<Schemes />} />
            <Route path="cashflow" element={<Cashflow />} />
            <Route path="risk" element={<Risk />} />
            <Route path="documents" element={<Documents />} />
            <Route path="applications" element={<Applications />} />
            <Route path="consent" element={<ConsentPage />} />
            <Route path="onboard" element={<Onboard />} />
            <Route path="money" element={<MoneyTrail />} />
            <Route path="field" element={<Field />} />
            <Route path="model" element={<Model />} />
            <Route path="audit" element={<Audit />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </Suspense>
    </BusinessProvider>
  )
}
