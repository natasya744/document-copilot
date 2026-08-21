import { Outlet } from "react-router-dom"
import { LayoutProvider } from "./layout-context"
import { Sidebar } from "./Sidebar"

export function AppLayout() {
  return (
    <LayoutProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        <Sidebar />
        <main className="flex h-full flex-1 flex-col overflow-hidden min-w-0">
          <Outlet />
        </main>
      </div>
    </LayoutProvider>
  )
}
