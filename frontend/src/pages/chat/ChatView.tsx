import { useMemo } from 'react'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type UIMessage } from 'ai'

import { ChatInput } from '@/components/chat/ChatInput'
import { MessageItem } from '@/components/chat/MessageItem'
import { ThinkingIndicator } from '@/components/chat/ThinkingIndicator'
import { Button } from '@/components/ui/button'
import type { ChatMessage, Thread } from '@/lib/api'
import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

const SUGGESTIONS = [
  'What are the main risk factors for the last three filings?',
  'How did revenue trend across the years?',
  'What changed in the latest annual report vs the prior one?',
]

function toUIMessage(message: ChatMessage): UIMessage {
  const parts = message.parts?.length
    ? (message.parts as unknown as UIMessage['parts'])
    : ([{ type: 'text' as const, text: message.content }] as UIMessage['parts'])
  return { id: message.id, role: message.role, parts }
}

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
    .trim()
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
  const lastMessage = messages[messages.length - 1]
  const lastIsEmptyAssistant =
    lastMessage?.role === 'assistant' && messageText(lastMessage).length === 0
  const showThinking = busy && !lastIsEmptyAssistant

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-background">
      {/* Header bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-6">
        <h1 className="truncate text-sm font-semibold text-foreground">{thread.title}</h1>
      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="mx-auto flex h-full max-w-3xl flex-col space-y-4">
          {messages.length === 0 && !busy ? (
            <div className="flex flex-1 flex-col items-start justify-center gap-4 py-8">
              <div>
                <h2 className="text-lg font-semibold">Ask about the filings</h2>
                <p className="text-sm text-muted-foreground">
                  Every answer cites the source filing, page, and passage.
                </p>
              </div>
              <div className="flex flex-col gap-2">
                {SUGGESTIONS.map((question) => (
                  <Button
                    key={question}
                    variant="outline"
                    className="h-auto justify-start whitespace-normal px-3 py-2 text-left text-sm"
                    onClick={() => void sendMessage({ text: question })}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message) => <MessageItem key={message.id} message={message} />)
          )}
          {showThinking ? <ThinkingIndicator /> : null}
        </div>
      </div>

      {/* Error notification */}
      {error ? (
        <div className="mx-auto mb-3 flex w-full max-w-3xl items-center justify-between gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2 text-sm text-destructive">
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

      {/* Stop button */}
      {busy ? (
        <div className="mb-2 flex justify-center">
          <Button variant="ghost" size="sm" onClick={stop}>
            Stop generating
          </Button>
        </div>
      ) : null}

      {/* Input container */}
      <div className="border-t border-border/40 p-4">
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={(text) => void sendMessage({ text })} disabled={busy} />
        </div>
      </div>
    </div>
  )
}