import { Loader2 } from "lucide-react"

import { DEFAULT_STATUS_LABEL } from "@/lib/status"

interface PipelineStatusProps {
  label?: string
}

export function PipelineStatus({ label }: PipelineStatusProps) {
  const currentText = label ?? DEFAULT_STATUS_LABEL

  return (
    <div className="flex justify-start my-2 animate-in fade-in-50 duration-300">
      <div className="flex items-center gap-3 rounded-xl border border-border/80 bg-card/90 px-3.5 py-2.5 text-xs text-foreground shadow-xs">
        <div className="relative flex size-5 items-center justify-center rounded-md bg-muted text-foreground">
          <Loader2 className="size-3.5 animate-spin" />
        </div>
        <div className="flex flex-col">
          <span className="font-medium text-xs tracking-tight text-foreground">
            {currentText}
          </span>
          <span className="text-[10px] text-muted-foreground">
            Analyzing 10-K/10-Q documents & verifying citations
          </span>
        </div>
      </div>
    </div>
  )
}
