import { Sparkles, User } from "lucide-react"
import type { UIMessage } from "ai"

import { getCitations } from "@/lib/citations"
import { cn } from "@/lib/utils"
import { MarkdownContent } from "./MarkdownContent"
import { MessageActions } from "./MessageActions"
import { SourcePassagePanel } from "./SourcePassagePanel"

function messageText(message: UIMessage): string {
  return message.parts
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("")
}

/** Renders one chat message with avatar, markdown formatting, citations, and actions. */
export function MessageItem({ message }: { message: UIMessage }) {
  const isUser = message.role === "user"
  const text = messageText(message)
  const citations = getCitations(message)

  // Empty placeholder assistant message handled by pipeline status
  if (!isUser && text.trim().length === 0) return null

  return (
    <div
      className={cn(
        "group flex w-full gap-3 py-3 select-text animate-in fade-in-30 duration-200",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-foreground text-background mt-0.5 shadow-2xs">
          <Sparkles className="size-3.5" />
        </div>
      )}

      <div
        className={cn(
          "flex flex-col min-w-0 max-w-[85%] sm:max-w-[78%]",
          isUser ? "items-end" : "items-start"
        )}
      >
        {isUser ? (
          <div className="rounded-2xl bg-foreground text-background px-4 py-2.5 text-xs leading-relaxed font-normal shadow-xs">
            <p className="whitespace-pre-wrap">{text}</p>
          </div>
        ) : (
          <div className="w-full space-y-2 rounded-2xl border border-border/80 bg-card/60 p-4 shadow-xs">
            <MarkdownContent content={text} />
            <SourcePassagePanel citations={citations} />
            <MessageActions content={text} />
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-border/80 bg-muted text-muted-foreground mt-0.5">
          <User className="size-3.5" />
        </div>
      )}
    </div>
  )
}