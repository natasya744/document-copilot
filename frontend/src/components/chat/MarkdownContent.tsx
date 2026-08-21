import React, { useMemo } from "react"

interface MarkdownContentProps {
  content: string
}

/** Lightweight, XSS-safe markdown renderer for financial answers. */
export function MarkdownContent({ content }: MarkdownContentProps) {
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
      // Split by bold (**text**) and inline code (`code`)
      const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g)
      return parts.map((part, idx) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return (
            <strong key={idx} className="font-semibold text-foreground">
              {part.slice(2, -2)}
            </strong>
          )
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code
              key={idx}
              className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground border border-border/50"
            >
              {part.slice(1, -1)}
            </code>
          )
        }
        return part
      })
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const trimmed = line.trim()

      if (!trimmed) {
        flushList()
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
    }

    flushList()
    return nodes
  }, [content])

  return <div className="prose-clean">{elements}</div>
}
