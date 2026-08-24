import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { PanelLeftClose, PanelLeftOpen, Plus, Search, Sparkles, SquarePen, X } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { useThreads } from "@/lib/threads"
import { cn } from "@/lib/utils"
import { useLayout } from "./layout-context"
import { SidebarHistory } from "./SidebarHistory"
import { UserMenu } from "./UserMenu"

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useLayout()
  const { threads, loading, error, refreshThreads } = useThreads()
  const navigate = useNavigate()
  const [searchQuery, setSearchQuery] = useState("")

  function handleNewChat() {
    navigate("/")
  }

  return (
    <aside
      className={cn(
        "relative flex h-screen flex-col border-r border-border/80 bg-sidebar transition-all duration-300 ease-in-out select-none z-30 shrink-0",
        sidebarOpen ? "w-64 min-w-64" : "w-16 min-w-16"
      )}
    >
      {/* Header & Branding */}
      <div className="relative flex h-14 items-center justify-between px-3 border-b border-border/60">
        {sidebarOpen ? (
          <div className="flex items-center gap-2 min-w-0">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-foreground text-background">
              <Sparkles className="size-4" />
            </div>
            <div className="flex flex-col min-w-0">
              <span className="truncate text-xs font-semibold text-foreground tracking-tight">
                Document Copilot
              </span>
              <span className="truncate text-[10px] text-muted-foreground">
                SEC Intelligence
              </span>
            </div>
          </div>
        ) : (
          <div className="flex size-8 mx-auto items-center justify-center rounded-lg bg-foreground text-background">
            <Sparkles className="size-4" />
          </div>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleSidebar}
              className={cn(
                "size-7 text-muted-foreground hover:text-foreground cursor-pointer",
                !sidebarOpen && "absolute -right-3 top-1/2 -translate-y-1/2 size-6 rounded-full border border-border/60 bg-background shadow-xs z-40"
              )}
            >
              {sidebarOpen ? <PanelLeftClose className="size-4" /> : <PanelLeftOpen className="size-3" />}
              <span className="sr-only">{sidebarOpen ? "Collapse sidebar (⌘B)" : "Expand sidebar (⌘B)"}</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent side="right">{sidebarOpen ? "Collapse sidebar (⌘B)" : "Expand sidebar (⌘B)"}</TooltipContent>
        </Tooltip>
      </div>

      {/* New Chat & Search Controls */}
      <div className="p-3 space-y-2 border-b border-border/40">
        {sidebarOpen ? (
          <>
            <Button
              onClick={handleNewChat}
              className="w-full justify-start gap-2 rounded-lg bg-foreground text-background hover:bg-foreground/90 font-medium text-xs h-9 px-3 shadow-xs cursor-pointer"
            >
              <SquarePen className="size-3.5" />
              <span>New chat</span>
            </Button>

            {/* Search Input */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3 text-muted-foreground" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search chats…"
                className="h-8 pl-7.5 pr-6 text-xs bg-muted/30 border-border/60 focus-visible:ring-1"
              />
              {searchQuery && (
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground cursor-pointer"
                >
                  <X className="size-3" />
                </button>
              )}
            </div>
          </>
        ) : (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                onClick={handleNewChat}
                variant="outline"
                size="icon"
                className="size-10 mx-auto rounded-lg text-foreground hover:bg-muted cursor-pointer"
              >
                <Plus className="size-4" />
                <span className="sr-only">New chat</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">New chat</TooltipContent>
          </Tooltip>
        )}
      </div>

      {/* Conversation History */}
      <ScrollArea className="flex-1 px-2 py-2">
        <SidebarHistory
          threads={threads}
          loading={loading}
          error={error}
          searchQuery={searchQuery}
          onRetry={() => void refreshThreads()}
          collapsed={!sidebarOpen}
        />
      </ScrollArea>

      {/* User Footer & Logout */}
      <div className="p-2 border-t border-border/60 mt-auto bg-sidebar/80">
        <UserMenu collapsed={!sidebarOpen} />
      </div>
    </aside>
  )
}
