import { useMemo, useState } from "react"
import { NavLink, useLocation, useNavigate, useParams } from "react-router-dom"
import { Loader2, MessageSquare, MoreHorizontal, RefreshCw, Trash2 } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import type { Thread } from "@/lib/api"
import { cn } from "@/lib/utils"
import { useThreads } from "@/lib/threads"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface SidebarHistoryProps {
  threads: Thread[] | null
  loading: boolean
  error: string | null
  searchQuery: string
  onRetry: () => void
  collapsed?: boolean
}

type GroupedThreads = {
  label: string
  items: Thread[]
}[]

function groupThreadsByDate(threads: Thread[]): GroupedThreads {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const yesterdayStart = todayStart - 86400000
  const sevenDaysAgoStart = todayStart - 6 * 86400000

  const today: Thread[] = []
  const yesterday: Thread[] = []
  const previous7Days: Thread[] = []
  const older: Thread[] = []

  for (const thread of threads) {
    const threadDate = new Date(thread.updatedAt || thread.createdAt).getTime()
    if (threadDate >= todayStart) {
      today.push(thread)
    } else if (threadDate >= yesterdayStart) {
      yesterday.push(thread)
    } else if (threadDate >= sevenDaysAgoStart) {
      previous7Days.push(thread)
    } else {
      older.push(thread)
    }
  }

  const groups: GroupedThreads = []
  if (today.length > 0) groups.push({ label: "Today", items: today })
  if (yesterday.length > 0) groups.push({ label: "Yesterday", items: yesterday })
  if (previous7Days.length > 0) groups.push({ label: "Previous 7 Days", items: previous7Days })
  if (older.length > 0) groups.push({ label: "Older", items: older })

  return groups
}

function truncate(text: string, maxLength: number): string {
  return text.length > maxLength ? text.slice(0, maxLength - 1) + "…" : text
}

function getThreadPreview(thread: Thread): string {
  if (thread.firstMessage) {
    return truncate(thread.firstMessage, 50)
  }
  return thread.title
}

export function SidebarHistory({
  threads,
  loading,
  error,
  searchQuery,
  onRetry,
  collapsed = false,
}: SidebarHistoryProps) {
  const { deleteThread } = useThreads()
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const { threadId: activeThreadId } = useParams()

  const filteredThreads = useMemo(() => {
    if (!threads) return []
    const query = searchQuery.trim().toLowerCase()
    if (!query) return threads
    return threads.filter((t) => {
      const preview = getThreadPreview(t).toLowerCase()
      const title = t.title.toLowerCase()
      return preview.includes(query) || title.includes(query)
    })
  }, [threads, searchQuery])

  const groups = useMemo(() => groupThreadsByDate(filteredThreads), [filteredThreads])

  async function handleDeleteThread(threadId: string) {
    if (!window.confirm("Are you sure you want to permanently delete this conversation?")) {
      return
    }
    setDeletingThreadId(threadId)
    try {
      await deleteThread(threadId)
      if (threadId === activeThreadId || location.pathname.includes(threadId)) {
        navigate("/")
      }
    } catch {
      alert("Failed to delete conversation")
    } finally {
      setDeletingThreadId(null)
    }
  }

  if (error) {
    return (
      <div className="p-3 text-xs text-destructive flex flex-col gap-1.5">
        <p className="font-medium">Failed to load chats</p>
        {error && error !== "Failed to load conversations" && (
          <p className="text-[11px] opacity-80 break-words">{error}</p>
        )}
        <button
          type="button"
          onClick={onRetry}
          className="flex items-center gap-1 text-[11px] underline hover:text-foreground cursor-pointer"
        >
          <RefreshCw className="size-3" /> Retry
        </button>
      </div>
    )
  }

  if (loading && threads === null) {
    return (
      <div className="space-y-3 p-2">
        <Skeleton className="h-6 w-16 rounded-md" />
        <div className="space-y-1.5">
          <Skeleton className="h-8 w-full rounded-md" />
          <Skeleton className="h-8 w-full rounded-md" />
          <Skeleton className="h-8 w-full rounded-md" />
        </div>
      </div>
    )
  }

  if (!threads || threads.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-xs text-muted-foreground">No conversations yet.</p>
      </div>
    )
  }

  if (filteredThreads.length === 0) {
    return (
      <div className="p-4 text-center">
        <p className="text-xs text-muted-foreground">No matching chats found.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4 pb-2">
      {groups.map((group) => (
        <div key={group.label} className="space-y-1">
          {!collapsed && (
            <h4 className="px-2.5 text-[11px] font-medium tracking-wider text-muted-foreground uppercase">
              {group.label}
            </h4>
          )}
          <div className="space-y-0.5">
            {group.items.map((thread) => {
              const isActive =
                thread.id === activeThreadId || location.pathname === `/thread/${thread.id}`
              const isDeleting = deletingThreadId === thread.id

              return (
                <div
                  key={thread.id}
                  className={cn(
                    "group grid items-center rounded-lg text-xs font-normal transition-all duration-150 w-full",
                    collapsed ? "grid-cols-1" : "grid-cols-[1fr_auto]",
                    isActive
                      ? "bg-foreground text-background font-medium shadow-xs"
                      : "text-muted-foreground hover:bg-muted/80 hover:text-foreground"
                  )}
                >
                  <NavLink
                    to={`/thread/${thread.id}`}
                    title={getThreadPreview(thread)}
                    className={cn(
                      "flex items-center gap-2 min-w-0 px-2.5 py-2 select-none cursor-pointer overflow-hidden",
                      collapsed && "justify-center px-2"
                    )}
                  >
                    <MessageSquare
                      className={cn(
                        "size-3.5 shrink-0 transition-colors",
                        isActive
                          ? "text-background"
                          : "text-muted-foreground group-hover:text-foreground"
                      )}
                    />
                    {!collapsed && (
                      <span className="truncate text-left block w-full">
                        {getThreadPreview(thread)}
                      </span>
                    )}
                  </NavLink>

                  {!collapsed && (
                    <div className="flex items-center gap-0.5 pr-1.5 opacity-50 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                      {/* 3-dots Dropdown Menu */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            type="button"
                            title="Thread options"
                            className={cn(
                              "size-6 flex items-center justify-center rounded-md transition-all cursor-pointer shrink-0",
                              isActive
                                ? "text-background/80 hover:text-background hover:bg-background/20"
                                : "text-muted-foreground/70 hover:text-foreground hover:bg-muted group-hover:text-foreground"
                            )}
                            disabled={isDeleting}
                          >
                            {isDeleting ? (
                              <Loader2 className="size-3.5 animate-spin" />
                            ) : (
                              <MoreHorizontal className="size-3.5" />
                            )}
                            <span className="sr-only">Thread options</span>
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" sideOffset={4} className="w-36 p-1">
                          <DropdownMenuItem
                            onClick={(e) => {
                              e.stopPropagation()
                              handleDeleteThread(thread.id)
                            }}
                            disabled={isDeleting}
                            className="flex items-center gap-2 py-1.5 px-2 text-xs text-destructive focus:bg-destructive/10 focus:text-destructive hover:bg-destructive/10 cursor-pointer"
                          >
                            <Trash2 className="size-3.5 text-destructive shrink-0" />
                            <span>Delete</span>
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>

                      {/* Direct Trash / Delete Icon Button */}
                      <button
                        type="button"
                        title="Delete thread"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteThread(thread.id)
                        }}
                        disabled={isDeleting}
                        className={cn(
                          "size-6 flex items-center justify-center rounded-md transition-all cursor-pointer shrink-0",
                          isActive
                            ? "text-background/80 hover:text-red-300 hover:bg-background/20"
                            : "text-muted-foreground/70 hover:text-destructive hover:bg-destructive/10 group-hover:text-destructive"
                        )}
                      >
                        <Trash2 className="size-3.5 shrink-0" />
                        <span className="sr-only">Delete</span>
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
