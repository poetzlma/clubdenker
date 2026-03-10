import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"

interface ChatMessageProps {
  role: "user" | "assistant"
  content: string
  timestamp: Date
  toolUsed: string | null
}

export function ChatMessage({ role, content, timestamp, toolUsed }: ChatMessageProps) {
  const isUser = role === "user"

  const formattedTime = timestamp.toLocaleTimeString("de-DE", {
    hour: "2-digit",
    minute: "2-digit",
  })

  return (
    <div
      className={cn("flex w-full", isUser ? "justify-end" : "justify-start")}
      data-testid={`chat-message-${role}`}
    >
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {/* Render content with newline support */}
        <div className="whitespace-pre-wrap break-words">
          {content.split("\n").map((line, i) => {
            // Simple bold (**text**) support
            const parts = line.split(/\*\*(.*?)\*\*/g)
            return (
              <span key={i}>
                {i > 0 && <br />}
                {parts.map((part, j) =>
                  j % 2 === 1 ? (
                    <strong key={j}>{part}</strong>
                  ) : (
                    <span key={j}>{part}</span>
                  )
                )}
              </span>
            )
          })}
        </div>

        <div
          className={cn(
            "mt-1 flex items-center gap-2 text-xs",
            isUser ? "text-primary-foreground/70" : "text-muted-foreground"
          )}
        >
          <span>{formattedTime}</span>
          {!isUser && toolUsed && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              {toolUsed}
            </Badge>
          )}
        </div>
      </div>
    </div>
  )
}
