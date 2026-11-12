import { Building2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useBusiness } from '../lib/business'
import type { Business } from '../lib/types'
import { Empty, Panel, Spinner } from './ui'

export default function NeedBusiness({ children }: { children: (b: Business) => ReactNode }) {
  const { current, loading } = useBusiness()
  const { user } = useAuth()
  if (loading) return <Spinner />
  if (!current)
    return (
      <Panel>
        <Empty icon={<Building2 className="h-10 w-10" />} title="No business yet">
          {user?.role === 'agent'
            ? 'No owner has granted your organisation consent yet. Businesses appear here only after the owner says yes.'
            : <>Add your business to start. <Link className="link" to="/onboard">Add business →</Link></>}
        </Empty>
      </Panel>
    )
  return <>{children(current)}</>
}
