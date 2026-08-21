import { useState } from "react"
import { Check, ChevronDown, Copy, FileText, Quote } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Citation } from "@/lib/api"
import { cn } from "@/lib/utils"

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date)
}

function CitationRow({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const location = [citation.page ? `Page ${citation.page}` : null, citation.section]
    .filter(Boolean)
    .join(" · ")

  async function handleCopy(e: React.MouseEvent) {
    e.stopPropagation()
    try {
      await navigator.clipboard.writeText(
        `[${citation.companyName} (${citation.ticker}) ${citation.filingType} - ${citation.filingDate}]\n${citation.excerpt}`
      )
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Clipboard write failed
    }
  }

  return (
    <div className="group rounded-xl border border-border/80 bg-card/80 transition-all hover:border-border select-none">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 p-3 text-left cursor-pointer"
      >
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground group-hover:text-foreground">
            <FileText className="size-3.5" />
          </div>
          <div className="flex flex-col min-w-0">
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-xs font-semibold text-foreground truncate">
                {citation.companyName}
              </span>
              <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0">
                {citation.ticker}
              </Badge>
              <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-normal">
                {citation.filingType}
              </Badge>
            </div>
            <span className="text-[11px] text-muted-foreground truncate mt-0.5">
              {formatDate(citation.filingDate)}
              {location ? ` · ${location}` : ""}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                onClick={handleCopy}
                className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
              >
                {copied ? (
                  <Check className="size-3 text-emerald-500" />
                ) : (
                  <Copy className="size-3" />
                )}
                <span className="sr-only">Copy excerpt</span>
              </button>
            </TooltipTrigger>
            <TooltipContent side="top">
              {copied ? "Copied excerpt!" : "Copy excerpt"}
            </TooltipContent>
          </Tooltip>

          <ChevronDown
            className={cn(
              "size-4 text-muted-foreground transition-transform duration-200",
              open && "rotate-180 text-foreground"
            )}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-border/60 bg-muted/20 px-3.5 py-2.5 animate-in fade-in-50 duration-200">
          <div className="flex items-start gap-2">
            <Quote className="size-3 text-muted-foreground mt-0.5 shrink-0" />
            <p className="text-xs leading-relaxed text-muted-foreground select-text font-normal">
              {citation.excerpt}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

/** Collapsible source cards under an assistant answer. */
export function SourcePassagePanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Sources & Citations ({citations.length})
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-1">
        {citations.map((citation) => (
          <CitationRow key={citation.chunkId} citation={citation} />
        ))}
      </div>
    </div>
  )
}