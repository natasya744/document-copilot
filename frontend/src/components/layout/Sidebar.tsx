import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { LogOut, SquarePen } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/lib/auth'
import { useThreads } from '@/lib/threads'
import { cn } from '@/lib/utils'

export function Sidebar() {
  const { session, signOut } = useAuth()
  const { threads, loading, error, createThread, refreshThreads } = useThreads()
  const navigate = useNavigate()
  const [isCreating, setIsCreating] = useState(false)

  async function handleNewChat() {
    setIsCreating(true)
    try {
      const thread = await createThread('New chat')
      navigate(`/thread/${thread.id}`)
    } catch {
      // Failed to create chat
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <aside className="flex h-screen w-64 min-w-64 flex-col border-r border-border bg-background p-4 select-none">
      {/* App Branding */}
      <div className="mb-4">
        <h2 className="text-base font-semibold tracking-tight text-foreground">
          Document Copilot
        </h2>
        <p className="text-xs text-muted-foreground">SEC filing assistant</p>
      </div>

      {/* New Chat Button */}
      <Button
        onClick={handleNewChat}
        disabled={isCreating}
        className="w-full justify-start gap-2.5 rounded-lg bg-foreground text-background shadow-none hover:bg-foreground/90 font-medium text-sm h-10 px-3"
      >
        <SquarePen className="h-4 w-4" />
        {isCreating ? 'Creating…' : 'New chat'}
      </Button>

      {/* Conversations Section */}
      <div className="mt-6 flex flex-1 flex-col overflow-hidden">
        <h3 className="mb-2 text-xs font-normal text-muted-foreground">Conversations</h3>

        <div className="flex-1 overflow-y-auto space-y-1 pr-1">
          {error ? (
            <div className="py-2 text-xs text-destructive">
              <p>{error}</p>
              <button
                type="button"
                onClick={() => void refreshThreads()}
                className="mt-1 underline hover:text-foreground"
              >
                Retry
              </button>
            </div>
          ) : loading && threads === null ? (
            <div className="space-y-2 py-1">
              <Skeleton className="h-7 w-full rounded-md" />
              <Skeleton className="h-7 w-full rounded-md" />
              <Skeleton className="h-7 w-full rounded-md" />
            </div>
          ) : !threads || threads.length === 0 ? (
            <p className="py-2 text-xs text-muted-foreground">No conversations yet.</p>
          ) : (
            threads.map((thread) => (
              <NavLink
                key={thread.id}
                to={`/thread/${thread.id}`}
                className={({ isActive }) =>
                  cn(
                    'block truncate rounded-md px-2.5 py-1.5 text-sm transition-colors',
                    isActive
                      ? 'bg-muted font-medium text-foreground'
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground',
                  )
                }
                title={thread.title}
              >
                {thread.title}
              </NavLink>
            ))
          )}
        </div>
      </div>

      {/* User Footer */}
      <div className="mt-auto border-t border-border pt-3 flex items-center justify-between gap-2">
        <span
          className="truncate text-xs text-muted-foreground"
          title={session?.user.email}
        >
          {session?.user.email}
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => void signOut()}
          className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
          title="Sign out"
        >
          <LogOut className="h-3.5 w-3.5" />
          <span className="sr-only">Sign out</span>
        </Button>
      </div>
    </aside>
  )
}
