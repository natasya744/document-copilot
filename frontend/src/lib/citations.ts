import type { UIMessage } from 'ai'

import type { Citation } from '@/lib/api'

/**
 * Extracts citations from a UI message's `data-citations` part. The backend
 * streams this part for every grounded answer and rehydrates it from
 * `chat_messages.message_json` when a thread is reopened.
 */
export function getCitations(message: UIMessage): Citation[] {
  for (const part of message.parts) {
    if (part.type === 'data-citations') {
      const data = (part as { data?: { citations?: Citation[] } }).data
      return data?.citations ?? []
    }
  }
  return []
}