import { useEffect, useRef, useState } from "react"
import { Bot, User, Send, Copy, Loader2, Sparkles } from "lucide-react"
import { toast } from "sonner"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { getSuggestedQuestions, chatWithMeeting, type ChatMessage } from "@/lib/api"

export function AssistantPanel({ meetingId }: { meetingId: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [suggested, setSuggested] = useState<string[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Reset the assistant's context whenever the user switches to a
  // different meeting — each meeting gets its own isolated chat.
  useEffect(() => {
    setMessages([])
    setInput("")
    getSuggestedQuestions(meetingId).then(setSuggested).catch(() => setSuggested([]))
  }, [meetingId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, sending])

  async function send(text: string) {
    const question = text.trim()
    if (!question || sending) return

    const nextMessages: ChatMessage[] = [...messages, { role: "user", content: question }]
    setMessages(nextMessages)
    setInput("")
    setSending(true)

    try {
      const { reply } = await chatWithMeeting(meetingId, question, messages)
      setMessages([...nextMessages, { role: "assistant", content: reply }])
    } catch (e: any) {
      toast.error(e.message || "Something went wrong while analyzing the meeting. Please try again.")
      setMessages(messages) // roll back the optimistic user message on hard failure
    } finally {
      setSending(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-[13px] uppercase tracking-wide text-muted-foreground">
          <Bot className="h-4 w-4 text-primary" />AI Meeting Assistant
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div ref={scrollRef} className="mb-3 flex max-h-96 flex-col gap-3 overflow-y-auto pr-1">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">Ask anything about this meeting…</p>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-2.5 ${m.role === "user" ? "flex-row-reverse" : ""}`}>
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                  m.role === "user" ? "bg-secondary text-secondary-foreground" : "bg-primary/15 text-primary"
                }`}
              >
                {m.role === "user" ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
              </span>
              <div className={`group max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed ${
                m.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
              }`}>
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && (
                  <div className="mt-1.5 flex items-center justify-between gap-2">
                    <span className="text-[10px] font-mono uppercase tracking-wide text-muted-foreground">
                      Based on the meeting transcript
                    </span>
                    <button
                      className="text-muted-foreground opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
                      onClick={() => { navigator.clipboard.writeText(m.content); toast.success("Copied to clipboard") }}
                      aria-label="Copy response"
                    >
                      <Copy className="h-3 w-3" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex gap-2.5">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                <Bot className="h-3.5 w-3.5" />
              </span>
              <div className="flex items-center gap-1.5 rounded-xl bg-secondary px-3.5 py-2.5 text-sm text-muted-foreground">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />Thinking…
              </div>
            </div>
          )}
        </div>

        {suggested.length > 0 && messages.length === 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {suggested.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                className="flex items-center gap-1 rounded-full border border-border bg-secondary/60 px-3 py-1.5 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
              >
                <Sparkles className="h-3 w-3" />{q}
              </button>
            ))}
          </div>
        )}

        <form
          onSubmit={(e) => { e.preventDefault(); send(input) }}
          className="flex items-center gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question here…"
            disabled={sending}
          />
          <Button type="submit" size="icon" disabled={sending || !input.trim()} aria-label="Send">
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
