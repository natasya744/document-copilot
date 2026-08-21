import { Loader2 } from 'lucide-react'

import { DEFAULT_STATUS_LABEL } from '@/lib/status'

/** Live pipeline status shown while the assistant is working. */
export function PipelineStatus({ label }: { label?: string }) {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-2 rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        <span>{label ?? DEFAULT_STATUS_LABEL}</span>
      </div>
    </div>
  )
}
