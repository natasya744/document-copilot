import { useState } from "react"
import { Database, ShieldCheck, Sparkles } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useAuth } from "@/lib/auth"
import { env } from "@/lib/env"

interface SettingsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SettingsModal({ open, onOpenChange }: SettingsModalProps) {
  const { session } = useAuth()
  const [activeTab, setActiveTab] = useState<"general" | "shortcuts" | "system">("general")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold">Settings</DialogTitle>
          <DialogDescription>
            Manage your account preferences and view workspace details.
          </DialogDescription>
        </DialogHeader>

        {/* Tab Navigation */}
        <div className="flex border-b border-border/80 text-xs">
          <button
            type="button"
            onClick={() => setActiveTab("general")}
            className={`pb-2 px-3 font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
              activeTab === "general"
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Account & Workspace
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("shortcuts")}
            className={`pb-2 px-3 font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
              activeTab === "shortcuts"
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Keyboard Shortcuts
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("system")}
            className={`pb-2 px-3 font-medium transition-colors cursor-pointer border-b-2 -mb-px ${
              activeTab === "system"
                ? "border-foreground text-foreground"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            System Status
          </button>
        </div>

        {/* Tab Content */}
        <div className="py-2 text-xs space-y-4">
          {activeTab === "general" && (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/40 p-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex size-8 items-center justify-center rounded-full bg-foreground text-background font-medium text-xs">
                    {session?.user.email?.[0]?.toUpperCase() ?? "U"}
                  </div>
                  <div>
                    <p className="font-medium text-foreground text-xs">{session?.user.email}</p>
                    <p className="text-[11px] text-muted-foreground">Authenticated Analyst</p>
                  </div>
                </div>
                <Badge variant="outline" className="text-[10px] font-normal">Active</Badge>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between py-1">
                  <span className="text-muted-foreground">Organization</span>
                  <span className="font-medium text-foreground">Driftwood Capital</span>
                </div>
                <Separator />
                <div className="flex items-center justify-between py-1">
                  <span className="text-muted-foreground">Corpus Scope</span>
                  <span className="font-medium text-foreground">SEC Filings 2021–2025 (AAPL, AMZN, GOOGL, MSFT, NVDA)</span>
                </div>
                <Separator />
                <div className="flex items-center justify-between py-1">
                  <span className="text-muted-foreground">Retrieval Strategy</span>
                  <span className="font-medium text-foreground">Hybrid Vector + Keyword Reciprocal Rank</span>
                </div>
              </div>
            </div>
          )}

          {activeTab === "shortcuts" && (
            <div className="space-y-2">
              <div className="flex items-center justify-between py-1.5">
                <span className="text-muted-foreground">Toggle Sidebar</span>
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-foreground">
                  ⌘ + B
                </kbd>
              </div>
              <Separator />
              <div className="flex items-center justify-between py-1.5">
                <span className="text-muted-foreground">Send Message</span>
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-foreground">
                  Enter
                </kbd>
              </div>
              <Separator />
              <div className="flex items-center justify-between py-1.5">
                <span className="text-muted-foreground">New Line in Chat</span>
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-foreground">
                  Shift + Enter
                </kbd>
              </div>
              <Separator />
              <div className="flex items-center justify-between py-1.5">
                <span className="text-muted-foreground">Stop Generation</span>
                <kbd className="rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] font-mono text-foreground">
                  Esc
                </kbd>
              </div>
            </div>
          )}

          {activeTab === "system" && (
            <div className="space-y-2.5">
              <div className="flex items-center justify-between rounded-md border border-border/70 p-2.5">
                <div className="flex items-center gap-2">
                  <Database className="size-4 text-muted-foreground" />
                  <span className="font-medium text-foreground">API Base URL</span>
                </div>
                <code className="text-[11px] text-muted-foreground font-mono truncate max-w-[180px]">{env.apiBaseUrl}</code>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border/70 p-2.5">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="size-4 text-emerald-600 dark:text-emerald-400" />
                  <span className="font-medium text-foreground">Supabase Auth</span>
                </div>
                <Badge variant="outline" className="text-[10px] text-emerald-600 border-emerald-500/30 dark:text-emerald-400">Connected</Badge>
              </div>
              <div className="flex items-center justify-between rounded-md border border-border/70 p-2.5">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 text-muted-foreground" />
                  <span className="font-medium text-foreground">Embedding Model</span>
                </div>
                <span className="text-muted-foreground">text-embedding-3-small</span>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
