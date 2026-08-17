import { useMemo } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'
import { Link } from 'react-router-dom'

import { ChatInput } from '@/components/chat/ChatInput'
import { MessageItem } from '@/components/chat/MessageItem'
import { Button } from '@/components/ui/button'
import type { ChatMessage, Thread } from '@/lib/api'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

function toUIMessage(message: ChatMessage): UIMessage {
  return {
    id: message.id,
    role: message.role,
    parts: [{ type: 'text', text: message.content }],
  }
}

/** Wires AI SDK `useChat` to the backend `/chat/stream` endpoint. */
export function ChatView({
  thread,
  initialMessages,
}: {
  thread: Thread
  initialMessages: ChatMessage[]
}) {
  const transport = useMemo(
    () =>
      new DefaultChatTransport({
        api: `${env.apiBaseUrl}/chat/stream`,
        headers: async () => ({
          Authorization: `Bearer ${await getAccessToken()}`,
        }),
        body: { threadId: thread.id },
      }),
    [thread.id],
  )

  const { messages, sendMessage, status, error, stop, clearError, regenerate } = useChat({
    id: thread.id,
    messages: initialMessages.map(toUIMessage),
    transport,
  })

  const busy = status === 'submitted' || status === 'streaming'

  return (
    <div className="mx-auto flex h-screen w-full max-w-2xl flex-col p-6">
      <header className="mb-4 flex items-center justify-between gap-4">
        <Link
          to="/"
          className="text-sm text-muted-foreground underline-offset-4 hover:underline"
        >
          ← Chats
        </Link>
        <h1 className="truncate text-lg font-semibold">{thread.title}</h1>
        <span className="w-10 shrink-0" />
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Ask about the filings — every answer cites the source document and page.
          </p>
        ) : (
          messages.map((message) => <MessageItem key={message.id} message={message} />)
        )}
      </div>

      {error ? (
        <div className="mb-3 flex items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
          <span className="min-w-0 truncate">{error.message}</span>
          <div className="flex shrink-0 gap-2">
            <Button variant="outline" size="sm" onClick={clearError}>
              Dismiss
            </Button>
            <Button variant="outline" size="sm" onClick={() => void regenerate()}>
              Retry
            </Button>
          </div>
        </div>
      ) : null}

      {busy ? (
        <div className="mb-3 flex justify-center">
          <Button variant="ghost" size="sm" onClick={stop}>
            Stop generating
          </Button>
        </div>
      ) : null}

      <ChatInput onSend={(text) => void sendMessage({ text })} disabled={busy} />
    </div>
  )
}