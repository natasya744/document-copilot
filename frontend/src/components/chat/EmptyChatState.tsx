export function EmptyChatState() {
  return (
    <div className="flex h-full w-full flex-col items-center justify-center p-8 text-center select-none">
      <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
        Start a conversation
      </h1>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
        Choose an existing thread from the sidebar or create a new chat to ask questions
        about SEC filings.
      </p>
    </div>
  )
}
