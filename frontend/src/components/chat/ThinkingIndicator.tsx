/** Pulsing dots shown while the assistant is generating its first tokens. */
export function ThinkingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="flex items-center gap-1 rounded-lg bg-muted px-4 py-3">
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:150ms]" />
        <span className="size-1.5 animate-pulse rounded-full bg-muted-foreground [animation-delay:300ms]" />
      </div>
    </div>
  )
}