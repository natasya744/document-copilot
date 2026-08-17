import { useState } from 'react'

import { Badge } from '@/components/ui/badge'
import type { Citation } from '@/lib/api'
import { cn } from '@/lib/utils'
import { ChevronDown } from 'lucide-react'

function formatDate(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) {
    return iso
  }
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date)
}

/** One citation row: company, filing, date, page/section, and excerpt. */
function CitationRow({ citation }: { citation: Citation }) {
  const [open, setOpen] = useState(false)
  const location = [citation.page, citation.section].filter(Boolean).join(' · ')

  return (
    <div className="rounded-lg border border-border/70 bg-card px-3 py-2">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between gap-2 text-left"
      >
        <span className="min-w-0">
          <span className="block truncate text-sm font-medium">
            {citation.companyName}{' '}
            <span className="text-muted-foreground">({citation.ticker})</span>
          </span>
          <span className="block truncate text-xs text-muted-foreground">
            {citation.filingType} · {formatDate(citation.filingDate)}
            {location ? ` · ${location}` : ''}
          </span>
        </span>
        <ChevronDown
          className={cn(
            'size-4 shrink-0 text-muted-foreground transition-transform',
            open && 'rotate-180',
          )}
        />
      </button>
      {open ? (
        <p className="mt-2 border-l-2 border-border pl-3 text-xs text-muted-foreground">
          {citation.excerpt}
        </p>
      ) : null}
    </div>
  )
}

/** Collapsible source list under an assistant answer. */
export function SourcePassagePanel({ citations }: { citations: Citation[] }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Badge variant="secondary" className="w-fit">
        Sources
      </Badge>
      {citations.map((citation) => (
        <CitationRow key={citation.chunkId} citation={citation} />
      ))}
    </div>
  )
}