import React, { useMemo } from "react"
import type { Citation } from "@/lib/api"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

interface MarkdownContentProps {
  content: string
  citations?: Citation[]
}

function CitationBadge({
  index,
  citation,
}: {
  index: number
  citation?: Citation
}) {
  function handleClick(e: React.MouseEvent) {
    e.preventDefault()
    if (!citation) return
    const el = document.getElementById(`citation-${citation.chunkId}`)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
      el.classList.add("ring-2", "ring-primary", "ring-offset-2")
      setTimeout(() => {
        el.classList.remove("ring-2", "ring-primary", "ring-offset-2")
      }, 2500)
    }
  }

  const tooltipLabel = citation
    ? `${citation.companyName} (${citation.ticker}) ${citation.filingType} · ${citation.section || "Passage"}`
    : `Citation [${index}]`

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          onClick={handleClick}
          className="inline-flex items-center justify-center font-mono text-[10px] font-semibold text-primary bg-primary/10 hover:bg-primary/20 transition-colors rounded px-1.5 py-0.5 mx-0.5 align-baseline cursor-pointer border border-primary/20"
        >
          [{index}]
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs max-w-xs">
        {tooltipLabel}
      </TooltipContent>
    </Tooltip>
  )
}

/** Lightweight, XSS-safe markdown renderer with table, bullet, and citation pill support. */
export function MarkdownContent({ content, citations = [] }: MarkdownContentProps) {
  // Map chunk IDs to citation indices and objects
  const chunkMap = useMemo(() => {
    const map = new Map<string, { index: number; citation: Citation }>()
    citations.forEach((c, idx) => {
      map.set(c.chunkId.toLowerCase(), { index: idx + 1, citation: c })
    })
    return map
  }, [citations])

  const elements = useMemo(() => {
    if (!content) return null

    const lines = content.split("\n")
    const nodes: React.ReactNode[] = []
    let inList = false
    let listItems: React.ReactNode[] = []
    let keyCounter = 0

    function flushList() {
      if (inList && listItems.length > 0) {
        nodes.push(
          <ul key={`ul-${keyCounter++}`} className="my-2 list-disc pl-5 space-y-1 text-xs">
            {listItems}
          </ul>
        )
        listItems = []
        inList = false
      }
    }

    function renderFormattedText(text: string): React.ReactNode {
      // Tokenize by citations, bold (**text**), and inline code (`code`)
      const tokens: React.ReactNode[] = []
      let lastIndex = 0
      
      // Combined tokenizer
      const combinedRegex = /(\[chunk\s+[0-9a-fA-F-]{32,36}\]|\[[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\]|\[\d+\]|\*\*.*?\*\*|`.*?`)/g
      
      let match: RegExpExecArray | null
      while ((match = combinedRegex.exec(text)) !== null) {
        if (match.index > lastIndex) {
          tokens.push(text.slice(lastIndex, match.index))
        }
        
        const tokenStr = match[0]
        if (tokenStr.startsWith("**") && tokenStr.endsWith("**")) {
          tokens.push(
            <strong key={`b-${keyCounter++}`} className="font-semibold text-foreground">
              {tokenStr.slice(2, -2)}
            </strong>
          )
        } else if (tokenStr.startsWith("`") && tokenStr.endsWith("`")) {
          tokens.push(
            <code
              key={`c-${keyCounter++}`}
              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground border border-border/50"
            >
              {tokenStr.slice(1, -1)}
            </code>
          )
        } else if (tokenStr.startsWith("[") && tokenStr.endsWith("]")) {
          // It's a citation candidate
          const inner = tokenStr.slice(1, -1).trim()
          const chunkIdMatch = inner.replace(/^chunk\s+/i, "").toLowerCase()
          
          if (chunkMap.has(chunkIdMatch)) {
            const entry = chunkMap.get(chunkIdMatch)!
            tokens.push(
              <CitationBadge key={`cit-${keyCounter++}`} index={entry.index} citation={entry.citation} />
            )
          } else if (/^\d+$/.test(inner)) {
            const num = parseInt(inner, 10)
            const targetCitation = citations[num - 1]
            tokens.push(
              <CitationBadge key={`cit-${keyCounter++}`} index={num} citation={targetCitation} />
            )
          } else {
            // Not a known chunk, render as plain token
            tokens.push(tokenStr)
          }
        }
        
        lastIndex = combinedRegex.lastIndex
      }
      
      if (lastIndex < text.length) {
        tokens.push(text.slice(lastIndex))
      }

      return tokens.length > 0 ? tokens : text
    }

    // Helper to check if a line is a table separator (e.g. |---|---| or |:---|---:|)
    function isSeparatorLine(line: string): boolean {
      const trimmed = line.trim()
      if (!trimmed.startsWith("|") || !trimmed.endsWith("|")) return false
      const parts = trimmed.slice(1, -1).split("|")
      return parts.length > 0 && parts.every((p) => /^[\s:-]+$/.test(p.trim()) && p.includes("-"))
    }

    // Helper to extract clean table row cells
    function parseTableRow(line: string): string[] {
      const trimmed = line.trim()
      let inner = trimmed
      if (inner.startsWith("|")) inner = inner.slice(1)
      if (inner.endsWith("|")) inner = inner.slice(0, -1)
      return inner.split("|").map((cell) => cell.trim())
    }

    // Helper to detect if a table is actually Docling bullet extraction (e.g. | | • | text |)
    function isDoclingBulletRow(cells: string[]): { isBullet: boolean; text: string } {
      const nonEmpties = cells.filter((c) => c.length > 0)
      if (nonEmpties.length === 1 && (cells.includes("•") || cells.includes("-") || cells.includes("*"))) {
        return { isBullet: true, text: nonEmpties[0] }
      }
      if (nonEmpties.length === 2 && (nonEmpties[0] === "•" || nonEmpties[0] === "-" || nonEmpties[0] === "*")) {
        return { isBullet: true, text: nonEmpties[1] }
      }
      return { isBullet: false, text: "" }
    }

    let i = 0
    while (i < lines.length) {
      const line = lines[i]
      const trimmed = line.trim()

      if (!trimmed) {
        flushList()
        i++
        continue
      }

      // Check if line looks like a table row (starts with |)
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        // Collect all consecutive table lines
        const tableLines: string[] = []
        while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
          tableLines.push(lines[i].trim())
          i++
        }

        // Check if all rows are actually Docling bullet rows
        const bulletItems: string[] = []
        let allBullets = true

        for (const tLine of tableLines) {
          if (isSeparatorLine(tLine)) continue
          const cells = parseTableRow(tLine)
          const bulletCheck = isDoclingBulletRow(cells)
          if (bulletCheck.isBullet) {
            bulletItems.push(bulletCheck.text)
          } else {
            allBullets = false
            break
          }
        }

        if (allBullets && bulletItems.length > 0) {
          inList = true
          for (const bText of bulletItems) {
            listItems.push(
              <li key={`li-${keyCounter++}`} className="text-xs text-foreground leading-relaxed">
                {renderFormattedText(bText)}
              </li>
            )
          }
          continue
        }

        // Otherwise, it's a real table
        flushList()
        
        let headerRow: string[] | null = null
        const bodyRows: string[][] = []
        
        for (let tIdx = 0; tIdx < tableLines.length; tIdx++) {
          const tLine = tableLines[tIdx]
          if (isSeparatorLine(tLine)) {
            continue
          }
          const cells = parseTableRow(tLine)
          if (!headerRow && tIdx === 0 && tableLines.length > 1 && isSeparatorLine(tableLines[1])) {
            headerRow = cells
          } else if (!headerRow && tableLines.length === 1) {
            // Single table row
            bodyRows.push(cells)
          } else if (!headerRow && tIdx === 0) {
            headerRow = cells
          } else {
            bodyRows.push(cells)
          }
        }

        nodes.push(
          <div
            key={`table-wrap-${keyCounter++}`}
            className="my-3 overflow-x-auto rounded-xl border border-border/80 bg-card/40 shadow-2xs"
          >
            <table className="w-full text-left border-collapse text-xs">
              {headerRow && (
                <thead className="bg-muted/60 border-b border-border/80">
                  <tr>
                    {headerRow.map((h, hIdx) => (
                      <th
                        key={`th-${hIdx}`}
                        className="px-3 py-2 text-[11px] font-semibold text-foreground border-r border-border/40 last:border-r-0 tracking-tight"
                      >
                        {renderFormattedText(h)}
                      </th>
                    ))}
                  </tr>
                </thead>
              )}
              <tbody className="divide-y divide-border/40">
                {bodyRows.map((row, rIdx) => (
                  <tr key={`tr-${rIdx}`} className="hover:bg-muted/30 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td
                        key={`td-${cIdx}`}
                        className="px-3 py-2 text-foreground/90 border-r border-border/40 last:border-r-0 align-top leading-relaxed text-xs"
                      >
                        {renderFormattedText(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
        continue
      }

      // Headings
      if (trimmed.startsWith("### ")) {
        flushList()
        nodes.push(
          <h4 key={`h4-${keyCounter++}`} className="mt-3 mb-1.5 text-xs font-semibold text-foreground tracking-tight">
            {renderFormattedText(trimmed.slice(4))}
          </h4>
        )
      } else if (trimmed.startsWith("## ")) {
        flushList()
        nodes.push(
          <h3 key={`h3-${keyCounter++}`} className="mt-4 mb-2 text-sm font-semibold text-foreground tracking-tight">
            {renderFormattedText(trimmed.slice(3))}
          </h3>
        )
      } else if (trimmed.startsWith("# ")) {
        flushList()
        nodes.push(
          <h2 key={`h2-${keyCounter++}`} className="mt-4 mb-2 text-base font-bold text-foreground tracking-tight">
            {renderFormattedText(trimmed.slice(2))}
          </h2>
        )
      } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ") || /^\d+\.\s/.test(trimmed)) {
        inList = true
        const itemText = trimmed.replace(/^([-*]|\d+\.)\s+/, "")
        listItems.push(
          <li key={`li-${keyCounter++}`} className="text-xs text-foreground leading-relaxed">
            {renderFormattedText(itemText)}
          </li>
        )
      } else if (trimmed.startsWith("> ")) {
        flushList()
        nodes.push(
          <blockquote
            key={`bq-${keyCounter++}`}
            className="my-2 border-l-2 border-border pl-3 text-xs italic text-muted-foreground"
          >
            {renderFormattedText(trimmed.slice(2))}
          </blockquote>
        )
      } else {
        flushList()
        nodes.push(
          <p key={`p-${keyCounter++}`} className="my-1.5 text-xs leading-relaxed text-foreground">
            {renderFormattedText(trimmed)}
          </p>
        )
      }

      i++
    }

    flushList()
    return nodes
  }, [content, chunkMap, citations])

  return <div className="prose-clean">{elements}</div>
}

