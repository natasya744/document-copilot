import { useState } from "react"
import { LogOut, MoreVertical, Settings } from "lucide-react"

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAuth } from "@/lib/auth"
import { SettingsModal } from "./SettingsModal"

interface UserMenuProps {
  collapsed?: boolean
}

export function UserMenu({ collapsed = false }: UserMenuProps) {
  const { session, signOut } = useAuth()
  const [settingsOpen, setSettingsOpen] = useState(false)

  const email = session?.user.email ?? "analyst@driftwoodcapital.com"
  const initials = email.substring(0, 2).toUpperCase()

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className={`flex w-full items-center gap-2.5 rounded-lg p-2 text-left transition-colors hover:bg-muted/70 focus:outline-hidden cursor-pointer select-none ${
              collapsed ? "justify-center px-1" : "justify-between"
            }`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <Avatar className="size-7 shrink-0 border border-border/80 bg-foreground text-background">
                <AvatarFallback className="bg-foreground text-background text-[11px] font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>
              {!collapsed && (
                <div className="flex flex-col min-w-0">
                  <span className="truncate text-xs font-medium text-foreground">
                    {email}
                  </span>
                  <span className="truncate text-[10px] text-muted-foreground">
                    Financial Analyst
                  </span>
                </div>
              )}
            </div>
            {!collapsed && (
              <MoreVertical className="size-3.5 text-muted-foreground shrink-0" />
            )}
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          side={collapsed ? "right" : "top"}
          align="start"
          sideOffset={8}
          className="w-56"
        >
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-xs font-semibold leading-none text-foreground">{email}</p>
              <p className="text-[10px] leading-none text-muted-foreground">
                Document Copilot Enterprise
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setSettingsOpen(true)}>
            <Settings className="mr-2 size-3.5" />
            <span>Settings & Shortcuts</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            variant="destructive"
            onClick={() => void signOut()}
          >
            <LogOut className="mr-2 size-3.5" />
            <span>Sign out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SettingsModal open={settingsOpen} onOpenChange={setSettingsOpen} />
    </>
  )
}
