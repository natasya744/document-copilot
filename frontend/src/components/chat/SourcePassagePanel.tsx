import { useState } from "react"
import {
  Check,
  ChevronDown,
  Copy,
  Layers,
  LayoutList,
  Loader2,
  Quote,
  Table2,
} from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { api, type Citation, type SurroundingChunk } from "@/lib/api"
import { cn } from "@/lib/utils"
import { MarkdownContent } from "./MarkdownContent"

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

function CitationRow({
  citation,
  index,
}: {
  citation: Citation
  index: number
}) {
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showSurrounding, setShowSurrounding] = useState(false)
  const [surrounding, setSurrounding] = useState<SurroundingChunk[] | null>(null)
  const [loadingSurrounding, setLoadingSurrounding] = useState(false)

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

  async function handleToggleSurrounding(e: React.MouseEvent) {
    e.stopPropagation()
    if (showSurrounding) {
      setShowSurrounding(false)
      return
    }

    setShowSurrounding(true)
    if (!surrounding) {
      setLoadingSurrounding(true)
      try {
        const data = await api.getSurroundingChunks(citation.chunkId, 1)
        setSurrounding(data)
      } catch {
        setSurrounding([])
      } finally {
        setLoadingSurrounding(false)
      }
    }
  }

  return (
    <div
      id={`citation-${citation.chunkId}`}
      className="group rounded-xl border border-border/80 bg-card/80 transition-all hover:border-border select-none"
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-3 p-3 text-left cursor-pointer"
      >
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-0.5 flex size-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground group-hover:text-foreground font-mono text-[11px] font-semibold">
            {index}
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
        <div className="border-t border-border/60 bg-muted/20 px-3.5 py-3 animate-in fade-in-50 duration-200 space-y-3">
          <div className="flex items-start gap-2.5">
            <Quote className="size-3.5 text-muted-foreground mt-1 shrink-0" />
            <div className="flex-1 min-w-0 select-text font-normal text-xs leading-relaxed text-foreground/90">
              <MarkdownContent content={citation.excerpt} />
            </div>
          </div>

          {/* Surrounding Context Controls */}
          <div className="pt-2 border-t border-border/40 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={handleToggleSurrounding}
                className="inline-flex items-center gap-1.5 text-[11px] font-medium text-primary hover:text-primary/80 transition-colors cursor-pointer"
              >
                {loadingSurrounding ? (
                  <Loader2 className="size-3 animate-spin" />
                ) : (
                  <Layers className="size-3" />
                )}
                {showSurrounding ? "Hide Neighboring Context" : "Expand Context (±1 chunk)"}
              </button>
            </div>

            {showSurrounding && (
              <div className="mt-1 space-y-2 text-xs">
                {loadingSurrounding && (
                  <p className="text-[11px] text-muted-foreground italic">
                    Loading preceding and succeeding passages…
                  </p>
                )}
                {!loadingSurrounding && surrounding && surrounding.length > 0 && (
                  <div className="space-y-2">
                    {surrounding.map((chunk) => {
                      const isTarget = chunk.chunkId === citation.chunkId
                      return (
                        <div
                          key={chunk.chunkId}
                          className={cn(
                            "rounded-lg p-2.5 transition-all text-xs",
                            isTarget
                              ? "bg-card border-2 border-primary/30 shadow-xs"
                              : "bg-muted/40 border border-border/60 opacity-80"
                          )}
                        >
                          <div className="flex items-center justify-between gap-2 mb-1">
                            <span className="font-mono text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                              {isTarget
                                ? "★ Matched Chunk"
                                : `Neighboring Chunk (${chunk.section || "Passage"})`}
                            </span>
                            <span className="text-[10px] text-muted-foreground font-mono">
                              Index #{chunk.chunkIndex}
                            </span>
                          </div>
                          <div className="select-text leading-relaxed">
                            <MarkdownContent content={chunk.text} />
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
                {!loadingSurrounding && surrounding && surrounding.length === 0 && (
                  <p className="text-[11px] text-muted-foreground italic">
                    No surrounding chunks available.
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function SourcesTableView({ citations }: { citations: Citation[] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border/80 bg-card/60 shadow-2xs">
      <table className="w-full text-left border-collapse text-xs">
        <thead className="bg-muted/60 border-b border-border/80">
          <tr>
            <th className="px-3 py-2 text-[11px] font-semibold text-foreground border-r border-border/40 w-8 text-center">
              #
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold text-foreground border-r border-border/40">
              Company
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold text-foreground border-r border-border/40">
              Filing & Date
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold text-foreground border-r border-border/40">
              Section
            </th>
            <th className="px-3 py-2 text-[11px] font-semibold text-foreground">
              Excerpt Preview
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border/40">
          {citations.map((c, idx) => (
            <tr
              key={c.chunkId}
              id={`citation-table-${c.chunkId}`}
              className="hover:bg-muted/30 transition-colors"
            >
              <td className="px-3 py-2.5 font-mono text-[11px] font-semibold text-center text-primary border-r border-border/40 align-top">
                [{idx + 1}]
              </td>
              <td className="px-3 py-2.5 border-r border-border/40 align-top whitespace-nowrap">
                <div className="font-semibold text-foreground">{c.companyName}</div>
                <Badge variant="outline" className="font-mono text-[10px] px-1 py-0 mt-0.5">
                  {c.ticker}
                </Badge>
              </td>
              <td className="px-3 py-2.5 border-r border-border/40 align-top whitespace-nowrap">
                <div className="font-medium text-foreground">{c.filingType}</div>
                <div className="text-[11px] text-muted-foreground">
                  {formatDate(c.filingDate)}
                </div>
              </td>
              <td className="px-3 py-2.5 text-muted-foreground border-r border-border/40 align-top text-[11px] max-w-[140px] truncate">
                {c.section || "General"}
                {c.page ? ` · p. ${c.page}` : ""}
              </td>
              <td className="px-3 py-2.5 text-foreground/90 align-top text-xs leading-relaxed max-w-sm">
                <p className="line-clamp-2 italic text-muted-foreground">
                  "{c.excerpt.slice(0, 160)}…"
                </p>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** Collapsible source cards with Table/Cards toggle under an assistant answer. */
export function SourcePassagePanel({ citations }: { citations: Citation[] }) {
  const [viewMode, setViewMode] = useState<"cards" | "table">("cards")

  if (citations.length === 0) return null

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Sources & Citations ({citations.length})
        </span>

        {/* View toggle */}
        <div className="inline-flex items-center rounded-lg border border-border/80 bg-muted/30 p-0.5 text-muted-foreground">
          <button
            type="button"
            onClick={() => setViewMode("cards")}
            className={cn(
              "flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer",
              viewMode === "cards"
                ? "bg-card text-foreground shadow-2xs"
                : "hover:text-foreground"
            )}
          >
            <LayoutList className="size-3" />
            Cards
          </button>
          <button
            type="button"
            onClick={() => setViewMode("table")}
            className={cn(
              "flex items-center gap-1 rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer",
              viewMode === "table"
                ? "bg-card text-foreground shadow-2xs"
                : "hover:text-foreground"
            )}
          >
            <Table2 className="size-3" />
            Table
          </button>
        </div>
      </div>

      {viewMode === "cards" ? (
        <div className="grid gap-2 sm:grid-cols-1">
          {citations.map((citation, idx) => (
            <CitationRow
              key={citation.chunkId}
              citation={citation}
              index={idx + 1}
            />
          ))}
        </div>
      ) : (
        <SourcesTableView citations={citations} />
      )}
    </div>
  )
}