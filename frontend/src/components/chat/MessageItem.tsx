import type { UIMessage } from 'ai'

import { getCitations } from '@/lib/citations'
import { cn } from '@/lib/utils'
import { SourcePassagePanel } from './SourcePassagePanel'
import { ThinkingIndicator } from './ThinkingIndicator'

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === 'text')
    .map((part) => part.text)
    .join('')
}

/** Renders one chat message, including its source passages. */
export function MessageItem({ message }: { message: UIMessage }) {
  const isUser = message.role === 'user'
  const text = messageText(message)
  const citations = getCitations(message)

  if (!isUser && text.trim().length === 0 && citations.length === 0) {
    return <ThinkingIndicator />
  }

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn('max-w-[80%]', !isUser && 'flex flex-col gap-2')}>
        <div
          className={cn(
            'rounded-lg px-4 py-2 text-sm whitespace-pre-wrap',
            isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground',
          )}
        >
          {text}
        </div>
        {!isUser && citations.length > 0 ? (
          <SourcePassagePanel citations={citations} />
        ) : null}
      </div>
    </div>
  )
}