import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { ChatInput } from '@/components/chat/ChatInput'
import { EmptyChatState } from '@/components/chat/EmptyChatState'
import { useThreads } from '@/lib/threads'

export function NewChatPage() {
  const navigate = useNavigate()
  const { createThread } = useThreads()
  const [starting, setStarting] = useState(false)

  async function handleSend(text: string) {
    if (starting) return
    setStarting(true)
    try {
      const thread = await createThread(text.slice(0, 80))
      navigate(`/thread/${thread.id}`, { state: { pendingMessage: text } })
    } catch {
      setStarting(false)
    }
  }

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-background">
      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-8">
        <EmptyChatState onSelectSuggestion={(question) => void handleSend(question)} />
      </div>

      {/* Input Composer */}
      <div className="border-t border-border/60 p-4 bg-background/80 backdrop-blur-xs">
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={(text) => void handleSend(text)} disabled={starting} />
        </div>
      </div>
    </div>
  )
}