import { request } from './http'

/** Wire format for one chat thread as returned by the backend. */
export interface Thread {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  firstMessage: string | null
}

/** Wire format for a citation attached to an assistant answer. */
export interface Citation {
  chunkId: string
  documentId: string
  ticker: string
  companyName: string
  filingType: string
  filingDate: string
  year: number
  page: string | null
  section: string | null
  excerpt: string
}

/** A persisted AI SDK message part, as stored in `chat_messages.message_json`. */
export interface MessagePart {
  type: 'text' | 'data-citations'
  text?: string
  data?: { citations?: Citation[] }
}

/** Wire format for one chat message as returned by the backend. */
export interface ChatMessage {
  id: string
  threadId: string
  role: 'user' | 'assistant'
  content: string
  sequenceNumber: number
  createdAt: string
  /** Persisted UIMessage parts; restores citations when reopening a thread. */
  parts?: MessagePart[]
}

/**
 * Product-level API client. Always goes through `request` so the base URL,
 * bearer token, timeouts, and error shaping stay in one place.
 */
export const api = {
  listThreads: () => request<Thread[]>('/threads'),

  createThread: (title: string) =>
    request<Thread>('/threads', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  deleteThread: (threadId: string) =>
    request<void>(`/threads/${threadId}`, {
      method: 'DELETE',
    }),

  getThread: (threadId: string) => request<Thread>(`/threads/${threadId}`),

  listMessages: (threadId: string) =>
    request<ChatMessage[]>(`/threads/${threadId}/messages`),
}