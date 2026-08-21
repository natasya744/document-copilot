import { useEffect, useRef, useState } from "react"
import type { FormEvent, KeyboardEvent } from "react"
import { ArrowUp, Square } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

interface ChatInputProps {
  onSend: (text: string) => void
  onStop?: () => void
  disabled: boolean
  busy?: boolean
}

/** Modern composer with auto-growing textarea and keyboard controls. */
export function ChatInput({ onSend, onStop, disabled, busy }: ChatInputProps) {
  const [text, setText] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea height
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = "auto"
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }, [text])

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = text.trim()
    if (trimmed.length === 0 || disabled) {
      return
    }
    onSend(trimmed)
    setText("")
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      event.currentTarget.form?.requestSubmit()
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="relative flex flex-col rounded-2xl border border-border/80 bg-card/80 p-2 shadow-xs transition-all focus-within:border-foreground/40 focus-within:shadow-md"
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask a question about the filings…"
        rows={1}
        disabled={disabled && !busy}
        className="w-full resize-none bg-transparent px-2.5 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-hidden disabled:cursor-not-allowed disabled:opacity-50 min-h-[38px] max-h-[160px] leading-relaxed"
      />

      <div className="flex items-center justify-between pt-1 px-1">
        <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
          <span>Enter to send · Shift+Enter for new line</span>
        </div>

        <div className="flex items-center gap-1.5">
          {busy && onStop ? (
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={onStop}
              className="h-7 gap-1 px-2.5 text-xs font-normal text-muted-foreground hover:text-foreground cursor-pointer rounded-lg"
            >
              <Square className="size-3 fill-current" />
              <span>Stop</span>
            </Button>
          ) : (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="submit"
                  size="icon"
                  disabled={disabled || text.trim().length === 0}
                  className="size-7 rounded-lg bg-foreground text-background hover:bg-foreground/90 disabled:opacity-40 cursor-pointer shadow-none"
                >
                  <ArrowUp className="size-3.5" />
                  <span className="sr-only">Send message</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent side="top">Send message</TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>
    </form>
  )
}