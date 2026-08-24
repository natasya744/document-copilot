import { ArrowUpRight, BarChart3, FileSpreadsheet, ShieldAlert, Sparkles, TrendingUp } from "lucide-react"

import { Badge } from "@/components/ui/badge"

interface EmptyChatStateProps {
  onSelectSuggestion: (question: string) => void
}

const SUGGESTIONS = [
  {
    category: "Revenue & Segments",
    icon: BarChart3,
    title: "Apple Revenue Mix (2021–2025)",
    question:
      "How did Apple's revenue mix across iPhone, Services, Mac, iPad, and Wearables change from 2021–2025?",
  },
  {
    category: "Segment Profitability",
    icon: TrendingUp,
    title: "Amazon AWS vs Retail Operating Margins",
    question:
      "How did Amazon's AWS operating income compare with its North America and International segments?",
  },
  {
    category: "Risk Factor Evolution",
    icon: ShieldAlert,
    title: "AI Infrastructure Disclosures",
    question:
      "Which of the five companies changed AI or cloud infrastructure risk-factor language between 2021 and 2025?",
  },
  {
    category: "CapEx & Commitments",
    icon: FileSpreadsheet,
    title: "Big Tech CapEx Comparison",
    question:
      "Compare capital expenditures and purchase commitments across Microsoft, Alphabet, Amazon, and NVIDIA.",
  },
]

export function EmptyChatState({ onSelectSuggestion }: EmptyChatStateProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center py-8 px-4 text-center select-none max-w-2xl mx-auto my-auto animate-in fade-in-50 duration-300">
      {/* Hero Badge & Icon */}
      <div className="mb-4 flex size-12 items-center justify-center rounded-2xl bg-foreground text-background shadow-md">
        <Sparkles className="size-6" />
      </div>

      <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">
        SEC Document Copilot
      </h1>
      <p className="mt-2 text-xs text-muted-foreground max-w-lg leading-relaxed">
        Query multi-year financial statements, MD&A disclosures, and risk factors across AAPL, AMZN, GOOGL, MSFT, and NVDA with verifiable citations.
      </p>

      {/* Suggestion Cards Grid */}
      <div className="mt-8 grid w-full grid-cols-1 gap-2.5 sm:grid-cols-2 text-left">
        {SUGGESTIONS.map((item) => {
          const Icon = item.icon
          return (
            <button
              key={item.title}
              type="button"
              onClick={() => onSelectSuggestion(item.question)}
              className="group relative flex flex-col justify-between rounded-xl border border-border/80 bg-card/60 p-3.5 transition-all hover:border-foreground/40 hover:bg-muted/40 hover:shadow-xs cursor-pointer disabled:opacity-50"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Badge
                    variant="outline"
                    className="text-[10px] font-normal text-muted-foreground bg-muted/40"
                  >
                    <Icon className="size-2.5 mr-1 text-muted-foreground" />
                    {item.category}
                  </Badge>
                  <ArrowUpRight className="size-3.5 text-muted-foreground group-hover:text-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
                <h3 className="text-xs font-semibold text-foreground group-hover:text-foreground">
                  {item.title}
                </h3>
                <p className="mt-1 text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                  {item.question}
                </p>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
