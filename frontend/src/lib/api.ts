import { request } from './http'

/** Wire format for a chat thread as returned by the backend. */
export interface Thread {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}

/** Wire format for one chat message as returned by the backend. */
export interface ChatMessage {
  id: string
  threadId: string
  role: 'user' | 'assistant'
  content: string
  sequenceNumber: number
  createdAt: string
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

  getThread: (threadId: string) => request<Thread>(`/threads/${threadId}`),

  listMessages: (threadId: string) =>
    request<ChatMessage[]>(`/threads/${threadId}/messages`),
}