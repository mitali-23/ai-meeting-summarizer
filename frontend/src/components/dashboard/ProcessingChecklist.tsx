import { useEffect, useState } from "react"
import { Check } from "lucide-react"
import { motion } from "framer-motion"
import { Card } from "@/components/ui/card"

const STAGES_AUDIO = ["Upload Complete", "Speech Recognition", "NLP Processing", "AI Analysis", "Summary Generation", "Extracting Action Items", "Detecting Decisions", "Detecting Deadlines", "Preparing Dashboard"]
const STAGES_TEXT = ["Upload Complete", "NLP Processing", "AI Analysis", "Summary Generation", "Extracting Action Items", "Detecting Decisions", "Detecting Deadlines", "Preparing Dashboard"]

export function ProcessingChecklist({ isAudio, done }: { isAudio: boolean; done: boolean }) {
  const stages = isAudio ? STAGES_AUDIO : STAGES_TEXT
  const [index, setIndex] = useState(0)

  useEffect(() => {
    const stepMs = isAudio ? 900 : 700
    const timer = setInterval(() => {
      // Cap at the LAST index (not stages.length) so the final stage stays
      // "active/pulsing" instead of turning green — this display is only a
      // rough visual estimate, not real backend progress, and for longer
      // recordings the actual request often takes longer than this
      // animation. Marking everything "done" while still waiting for the
      // real response was misleading — it looked finished but wasn't,
      // which is why it seemed "stuck" with no output. Only the `done`
      // prop (set once the server actually responds) marks true completion.
      setIndex((i) => (i < stages.length - 1 ? i + 1 : i))
    }, stepMs)
    return () => clearInterval(timer)
  }, [isAudio, stages.length])

  const reachedEnd = index >= stages.length - 1

  useEffect(() => {
    if (done) setIndex(stages.length)
  }, [done, stages.length])

  return (
    <Card className="mx-auto max-w-md p-7">
      <p className="mb-5 text-sm font-bold">Processing your meeting</p>
      <ul className="flex flex-col gap-3">
        {stages.map((label, i) => {
          const isDone = i < index
          const isActive = i === index
          return (
            <li key={label} className={`flex items-center gap-3 text-sm transition-colors ${isDone ? "text-foreground" : isActive ? "text-primary" : "text-muted-foreground/50"}`}>
              <span
                className={`flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full border transition-colors ${
                  isDone ? "border-success bg-success" : isActive ? "border-primary" : "border-border"
                }`}
                style={{ width: 18, height: 18 }}
              >
                {isDone && <Check className="h-3 w-3 text-white" strokeWidth={3} />}
                {isActive && !isDone && (
                  <motion.span
                    className="h-1.5 w-1.5 rounded-full bg-primary"
                    animate={{ opacity: [0.4, 1, 0.4], scale: [0.8, 1, 0.8] }}
                    transition={{ repeat: Infinity, duration: 1 }}
                  />
                )}
              </span>
              {label}
            </li>
          )
        })}
      </ul>

      {reachedEnd && !done && (
        <p className="mt-5 text-center text-xs text-muted-foreground">
          Still working — longer recordings can take a bit more time.
        </p>
      )}
    </Card>
  )
}
