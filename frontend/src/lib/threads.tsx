import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { api } from './api'
import type { Thread } from './api'
import { useAuth } from './auth'
import { ApiError } from './http'

interface ThreadsContextValue {
  threads: Thread[] | null
  loading: boolean
  error: string | null
  refreshThreads: () => Promise<void>
  createThread: (title?: string) => Promise<Thread>
}

const ThreadsContext = createContext<ThreadsContextValue | null>(null)

export function ThreadsProvider({ children }: { children: ReactNode }) {
  const { session } = useAuth()
  const [threads, setThreads] = useState<Thread[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refreshThreads = useCallback(async () => {
    if (!session) {
      setThreads(null)
      return
    }
    setLoading(true)
    setError(null)
    try {
      const list = await api.listThreads()
      setThreads(list)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load conversations')
    } finally {
      setLoading(false)
    }
  }, [session])

  useEffect(() => {
    let active = true
    if (session) {
      setLoading(true)
      api
        .listThreads()
        .then((list) => {
          if (active) {
            setThreads(list)
          }
        })
        .catch((err) => {
          if (active) {
            setError(err instanceof ApiError ? err.message : 'Failed to load conversations')
          }
        })
        .finally(() => {
          if (active) {
            setLoading(false)
          }
        })
    } else {
      setThreads(null)
    }
    return () => {
      active = false
    }
  }, [session])

  const createThread = useCallback(async (title = 'New chat') => {
    const newThread = await api.createThread(title)
    setThreads((prev) => (prev ? [newThread, ...prev] : [newThread]))
    return newThread
  }, [])

  const value = useMemo(
    () => ({
      threads,
      loading,
      error,
      refreshThreads,
      createThread,
    }),
    [threads, loading, error, refreshThreads, createThread],
  )

  return <ThreadsContext.Provider value={value}>{children}</ThreadsContext.Provider>
}

export function useThreads(): ThreadsContextValue {
  const context = useContext(ThreadsContext)
  if (context === null) {
    throw new Error('useThreads must be used within ThreadsProvider')
  }
  return context
}
