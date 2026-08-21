/**
 * Pipeline status events streamed by the backend as transient `data-status`
 * parts (see backend `app/chat/streaming.py::status_event`). They reach the
 * client through `useChat`'s `onData` callback as a part object shaped
 * `{ type, id, transient, data: { stage, label } }`; they are never persisted
 * into message history.
 */

export interface PipelineStatus {
  stage: string
  label: string
}

export const DEFAULT_STATUS_LABEL = 'Preparing…'

/** Extracts the label from a `data-status` part passed to `onData`. */
export function statusLabelFromData(data: unknown): string | null {
  if (typeof data !== 'object' || data === null) return null
  const payload = (data as { data?: unknown }).data
  if (typeof payload !== 'object' || payload === null) return null
  const { label } = payload as { label?: unknown }
  return typeof label === 'string' && label.length > 0 ? label : null
}
