import { PanelLeftOpen } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useLayout } from "@/components/layout/layout-context"

interface ChatHeaderProps {
  title: string
}

export function ChatHeader({ title }: ChatHeaderProps) {
  const { sidebarOpen, toggleSidebar } = useLayout()

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border/70 bg-background/80 px-4 backdrop-blur-xs select-none">
      <div className="flex items-center gap-3 min-w-0">
        {!sidebarOpen && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="size-8 text-muted-foreground hover:text-foreground cursor-pointer shrink-0"
              >
                <PanelLeftOpen className="size-4" />
                <span className="sr-only">Expand sidebar (⌘B)</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Expand sidebar (⌘B)</TooltipContent>
          </Tooltip>
        )}
        <div className="flex items-center gap-2 min-w-0">
          <h1 className="truncate text-sm font-semibold text-foreground tracking-tight">
            {title}
          </h1>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <Badge
          variant="outline"
          className="hidden sm:inline-flex items-center gap-1.5 text-[11px] font-normal text-muted-foreground border-border/80 bg-muted/30 py-1"
        >
          <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>SEC Corpus (2021–2025)</span>
        </Badge>
      </div>
    </header>
  )
}
