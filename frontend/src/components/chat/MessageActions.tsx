import { useState } from "react"
import { Check, Copy, ThumbsDown, ThumbsUp } from "lucide-react"

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

interface MessageActionsProps {
  content: string
}

export function MessageActions({ content }: MessageActionsProps) {
  const [copied, setCopied] = useState(false)
  const [liked, setLiked] = useState<boolean | null>(null)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Failed to copy
    }
  }

  return (
    <div className="flex items-center gap-1 mt-1 text-muted-foreground">
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={handleCopy}
            className="flex size-6 items-center justify-center rounded-md hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
          >
            {copied ? (
              <Check className="size-3 text-emerald-500" />
            ) : (
              <Copy className="size-3" />
            )}
            <span className="sr-only">Copy text</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {copied ? "Copied!" : "Copy message"}
        </TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => setLiked((prev) => (prev === true ? null : true))}
            className={`flex size-6 items-center justify-center rounded-md hover:bg-muted hover:text-foreground transition-colors cursor-pointer ${
              liked === true ? "text-foreground bg-muted font-bold" : ""
            }`}
          >
            <ThumbsUp className="size-3" />
            <span className="sr-only">Helpful</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Helpful response</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            onClick={() => setLiked((prev) => (prev === false ? null : false))}
            className={`flex size-6 items-center justify-center rounded-md hover:bg-muted hover:text-foreground transition-colors cursor-pointer ${
              liked === false ? "text-foreground bg-muted font-bold" : ""
            }`}
          >
            <ThumbsDown className="size-3" />
            <span className="sr-only">Not helpful</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom">Not helpful</TooltipContent>
      </Tooltip>
    </div>
  )
}
