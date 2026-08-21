import { useMemo } from "react"
import { NavLink } from "react-router-dom"
import { MessageSquare, RefreshCw } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import type { Thread } from "@/lib/api"
import { cn } from "@/lib/utils"

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

export function SidebarHistory({
  threads,
  loading,
  error,
  searchQuery,
  onRetry,
  collapsed = false,
}: SidebarHistoryProps) {
  const filteredThreads = useMemo(() => {
    if (!threads) return []
    const query = searchQuery.trim().toLowerCase()
    if (!query) return threads
    return threads.filter((t) => t.title.toLowerCase().includes(query))
  }, [threads, searchQuery])

  const groups = useMemo(() => groupThreadsByDate(filteredThreads), [filteredThreads])

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
              <NavLink
                key={thread.id}
                to={`/thread/${thread.id}`}
                title={thread.title}
                className={({ isActive }) =>
                  cn(
                    "group flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-xs font-normal transition-all select-none cursor-pointer",
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
                      <span className="truncate flex-1">{thread.title}</span>
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
