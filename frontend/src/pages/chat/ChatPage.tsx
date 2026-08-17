import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { Skeleton } from '@/components/ui/skeleton'
import { api } from '@/lib/api'
import type { ChatMessage, Thread } from '@/lib/api'
import { ApiError } from '@/lib/http'
import { ChatView } from './ChatView'

export function ChatPage() {
  const { threadId = '' } = useParams()
  const [thread, setThread] = useState<Thread | null>(null)
  const [messages, setMessages] = useState<ChatMessage[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    setThread(null)
    setMessages(null)
    setError(null)

    Promise.all([api.getThread(threadId), api.listMessages(threadId)])
      .then(([loadedThread, loadedMessages]) => {
        if (active) {
          setThread(loadedThread)
          setMessages(loadedMessages)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof ApiError ? err.message : 'Failed to load chat')
        }
      })

    return () => {
      active = false
    }
  }, [threadId])

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="text-center">
          <p className="text-sm text-destructive">{error}</p>
          <Link
            to="/"
            className="mt-2 inline-block text-sm text-primary underline-offset-4 hover:underline"
          >
            Back to chats
          </Link>
        </div>
      </div>
    )
  }

  if (thread === null || messages === null) {
    return (
      <div className="mx-auto flex h-screen w-full max-w-2xl flex-col p-6">
        <Skeleton className="mb-6 h-8 w-40" />
        <div className="flex-1 space-y-4">
          <Skeleton className="h-16 w-3/4" />
          <Skeleton className="h-16 w-2/3" />
        </div>
        <Skeleton className="h-12 w-full" />
      </div>
    )
  }

  return <ChatView key={threadId} thread={thread} initialMessages={messages} />
}