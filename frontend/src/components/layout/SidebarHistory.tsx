import { useMemo, useState } from "react"
import { NavLink, useNavigate, useParams } from "react-router-dom"
import { MessageSquare, MoreHorizontal, RefreshCw, Trash2 } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import type { Thread } from "@/lib/api"
import { cn } from "@/lib/utils"
import { api } from "@/lib/api"

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
    return truncate(thread.firstMessage, 60)
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
  const [deletingThreadId, setDeletingThreadId] = useState<string | null>(null)
  const navigate = useNavigate()
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
      await api.deleteThread(threadId)
      if (threadId === activeThreadId) {
        navigate("/")
      }
      onRetry()
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
            {group.items.map((thread) => (
              <div
                key={thread.id}
                className="group flex items-center gap-1.5 rounded-lg py-2 text-xs font-normal transition-all"
              >
                <NavLink
                  to={`/thread/${thread.id}`}
                  title={getThreadPreview(thread)}
                  className={({ isActive }) =>
                    cn(
                      "flex-1 flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-normal transition-all select-none cursor-pointer",
                      isActive
                        ? "bg-foreground text-background font-medium shadow-xs"
                        : "text-muted-foreground hover:bg-muted/80 hover:text-foreground",
                      collapsed && "justify-center px-2"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <MessageSquare
                        className={cn(
                          "size-3.5 shrink-0 transition-colors",
                          isActive
                            ? "text-background"
                            : "text-muted-foreground group-hover:text-foreground"
                        )}
                      />
                      {!collapsed && (
                        <span className="truncate flex-1">{getThreadPreview(thread)}</span>
                      )}
                    </>
                  )}
                </NavLink>
                {!collapsed && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className={cn(
                          "size-7 p-0 text-muted-foreground hover:text-foreground transition-opacity",
                          (deletingThreadId === thread.id || thread.id === activeThreadId) ||
                            "opacity-0 group-hover:opacity-100"
                        )}
                        disabled={deletingThreadId === thread.id}
                      >
                        <MoreHorizontal className="size-3.5" />
                        <span className="sr-only">Thread options</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent side="left" className="p-1">
                      <DropdownMenuItem
                        onClick={() => handleDeleteThread(thread.id)}
                        disabled={deletingThreadId === thread.id}
                        className="py-1.5 px-2 text-xs text-destructive hover:bg-muted/80"
                      >
                        <Trash2 className="size-2.5 mr-1" /> Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
