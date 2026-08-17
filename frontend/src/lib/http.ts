import { env } from './env'
import { getAccessToken } from './supabase'

const DEFAULT_TIMEOUT_MS = 30_000

/**
 * Error produced by the API client.
 *
 * `isNetworkError` is true for CORS / connectivity / timeout failures (no HTTP
 * response was received) and false for real HTTP errors, so callers can tell
 * the two apart.
 */
export class ApiError extends Error {
  readonly status: number | null
  readonly isNetworkError: boolean

  constructor(message: string, status: number | null, isNetworkError: boolean) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.isNetworkError = isNetworkError
  }
}

async function buildHeaders(init: RequestInit): Promise<Headers> {
  const headers = new Headers(init.headers)
  const token = await getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (typeof init.body === 'string' && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return headers
}

/**
 * Thin fetch wrapper: base URL, Supabase bearer token, JSON, timeout, and
 * typed errors. Use `api` from `./api` instead of calling this directly.
 */
export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS)

  try {
    const response = await fetch(`${env.apiBaseUrl}${path}`, {
      ...init,
      headers: await buildHeaders(init),
      signal: controller.signal,
    })

    if (!response.ok) {
      let detail = `Request failed with status ${response.status}`
      try {
        const body: unknown = await response.json()
        if (
          typeof body === 'object' &&
          body !== null &&
          'detail' in body &&
          typeof body.detail === 'string'
        ) {
          detail = body.detail
        }
      } catch {
        // Non-JSON error body; keep the fallback message.
      }
      throw new ApiError(detail, response.status, false)
    }

    if (response.status === 204) {
      return undefined as T
    }
    return (await response.json()) as T
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    const message = error instanceof Error ? error.message : 'Network error'
    throw new ApiError(message, null, true)
  } finally {
    clearTimeout(timeout)
  }
}