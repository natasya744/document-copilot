import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'

export function AppLayout() {
  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <Sidebar />
      <main className="flex h-full flex-1 flex-col overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
