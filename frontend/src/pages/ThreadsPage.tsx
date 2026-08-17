import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import type { Thread } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import { ApiError } from '@/lib/http'

function formatUpdatedAt(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return `Updated ${new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)}`
}

export function ThreadsPage() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const [threads, setThreads] = useState<Thread[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    let active = true
    api
      .listThreads()
      .then((list) => {
        if (active) {
          setThreads(list)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.message : 'Failed to load chats')
        }
      })
    return () => {
      active = false
    }
  }, [])

  async function handleNewChat() {
    setCreating(true)
    setError(null)
    try {
      const thread = await api.createThread('New chat')
      navigate(`/thread/${thread.id}`)
    } catch (err) {
      setCreating(false)
      setError(err instanceof ApiError ? err.message : 'Failed to create chat')
    }
  }

  async function handleSignOut() {
    await signOut()
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-2xl flex-col p-6">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Your chats</h1>
          <p className="text-sm text-muted-foreground">{session?.user.email}</p>
        </div>
        <Button variant="outline" onClick={handleSignOut}>
          Sign out
        </Button>
      </header>

      <Button onClick={handleNewChat} disabled={creating} className="mb-6 self-start">
        {creating ? 'Creating…' : 'New chat'}
      </Button>

      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}

      {threads === null ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-12 w-full" />
        </div>
      ) : threads.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No chats yet. Start a new chat to ask about the filings.
        </p>
      ) : (
        <ul className="space-y-2">
          {threads.map((thread) => (
            <li key={thread.id}>
              <Link
                to={`/thread/${thread.id}`}
                className="block rounded-lg border p-4 transition-colors hover:bg-muted"
              >
                <span className="block truncate font-medium">{thread.title}</span>
                <span className="mt-1 block text-xs text-muted-foreground">
                  {formatUpdatedAt(thread.updatedAt)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}