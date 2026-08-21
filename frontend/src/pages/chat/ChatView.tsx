import { useEffect, useMemo, useRef, useState } from "react"
import { useChat } from "@ai-sdk/react"
import { DefaultChatTransport, type UIMessage } from "ai"
import { ArrowDown, RotateCcw, XCircle } from "lucide-react"

import { ChatHeader } from "@/components/chat/ChatHeader"
import { ChatInput } from "@/components/chat/ChatInput"
import { EmptyChatState } from "@/components/chat/EmptyChatState"
import { MessageItem } from "@/components/chat/MessageItem"
import { PipelineStatus } from "@/components/chat/PipelineStatus"
import { Button } from "@/components/ui/button"
import type { ChatMessage, Thread } from "@/lib/api"
import { env } from "@/lib/env"
import { statusLabelFromData } from "@/lib/status"
import { getAccessToken } from "@/lib/supabase"

function toUIMessage(message: ChatMessage): UIMessage {
  const parts = message.parts?.length
    ? (message.parts as unknown as UIMessage["parts"])
    : ([{ type: "text" as const, text: message.content }] as UIMessage["parts"])
  return { id: message.id, role: message.role, parts }
}

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("")
    .trim()
}

/** Enhanced ChatView orchestrating AI SDK useChat, citations, and streaming status. */
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
    [thread.id]
  )

  const { messages, sendMessage, status, error, stop, clearError, regenerate } = useChat({
    id: thread.id,
    messages: initialMessages.map(toUIMessage),
    transport,
    onData: (data) => {
      const label = statusLabelFromData(data)
      if (label) setStatusLabel(label)
    },
  })

  const [statusLabel, setStatusLabel] = useState<string | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const [showScrollBottom, setShowScrollBottom] = useState(false)

  useEffect(() => {
    setStatusLabel(null)
  }, [thread.id])

  const busy = status === "submitted" || status === "streaming"
  const lastMessage = messages[messages.length - 1]
  const hasStreamedText =
    lastMessage?.role === "assistant" && messageText(lastMessage).length > 0
  const showStatus = busy && !hasStreamedText

  // Handle auto-scrolling
  useEffect(() => {
    if (!scrollContainerRef.current) return
    const el = scrollContainerRef.current
    const isScrolledToBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120
    if (isScrolledToBottom || busy) {
      el.scrollTop = el.scrollHeight
    }
  }, [messages, showStatus, busy])

  function handleScroll() {
    if (!scrollContainerRef.current) return
    const el = scrollContainerRef.current
    const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    setShowScrollBottom(!isNearBottom && messages.length > 0)
  }

  function scrollToBottom() {
    if (!scrollContainerRef.current) return
    scrollContainerRef.current.scrollTo({
      top: scrollContainerRef.current.scrollHeight,
      behavior: "smooth",
    })
  }

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-background">
      {/* Header bar */}
      <ChatHeader title={thread.title} />

      {/* Messages Scroll Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="relative flex-1 overflow-y-auto px-4 sm:px-8 py-4"
      >
        <div className="mx-auto flex min-h-full max-w-3xl flex-col">
          {messages.length === 0 && !busy ? (
            <EmptyChatState
              onSelectSuggestion={(question) => void sendMessage({ text: question })}
            />
          ) : (
            <div className="flex-1 space-y-1 pb-4">
              {messages.map((message) => (
                <MessageItem key={message.id} message={message} />
              ))}
              {showStatus ? <PipelineStatus label={statusLabel ?? undefined} /> : null}
            </div>
          )}
        </div>

        {/* Scroll to bottom button */}
        {showScrollBottom && (
          <button
            type="button"
            onClick={scrollToBottom}
            className="fixed bottom-24 right-8 z-20 flex size-8 items-center justify-center rounded-full border border-border/80 bg-background/90 text-foreground shadow-md backdrop-blur-xs hover:bg-muted transition-all cursor-pointer"
          >
            <ArrowDown className="size-4" />
            <span className="sr-only">Scroll to bottom</span>
          </button>
        )}
      </div>

      {/* Error notification */}
      {error ? (
        <div className="mx-auto mb-2 flex w-full max-w-3xl items-center justify-between gap-3 rounded-xl border border-destructive/40 bg-destructive/5 px-4 py-2 text-xs text-destructive">
          <div className="flex items-center gap-2 min-w-0">
            <XCircle className="size-4 shrink-0" />
            <span className="truncate">{error.message}</span>
          </div>
          <div className="flex shrink-0 gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={clearError}
              className="h-7 text-xs px-2.5"
            >
              Dismiss
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void regenerate()}
              className="h-7 text-xs px-2.5 gap-1"
            >
              <RotateCcw className="size-3" />
              Retry
            </Button>
          </div>
        </div>
      ) : null}

      {/* Input Composer */}
      <div className="border-t border-border/60 p-4 bg-background/80 backdrop-blur-xs">
        <div className="mx-auto max-w-3xl">
          <ChatInput
            onSend={(text) => void sendMessage({ text })}
            onStop={stop}
            disabled={busy}
            busy={busy}
          />
        </div>
      </div>
    </div>
  )
}