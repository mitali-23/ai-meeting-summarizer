import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Download, FileDown, Copy, RotateCcw, TriangleAlert } from "lucide-react"
import { toast } from "sonner"
import { Hero } from "@/components/dashboard/Hero"
import { UploadCard } from "@/components/dashboard/UploadCard"
import { ProcessingChecklist } from "@/components/dashboard/ProcessingChecklist"
import { InfoRows } from "@/components/dashboard/InfoRows"
import { AnalyticsSection } from "@/components/dashboard/AnalyticsSection"
import { OutputCards } from "@/components/dashboard/OutputCards"
import { AssistantPanel } from "@/components/dashboard/AssistantPanel"
import { Button } from "@/components/ui/button"
import { analyzeAudio, analyzeText, pdfUrl } from "@/lib/api"
import type { AnalyzeResult } from "@/lib/types"

type Status = "idle" | "processing" | "done"

export default function HomePage() {
  const [status, setStatus] = useState<Status>("idle")
  const [isAudio, setIsAudio] = useState(true)
  const [result, setResult] = useState<AnalyzeResult | null>(null)

  async function handleAudio(file: File, title: string, language: string) {
    setIsAudio(true)
    setStatus("processing")
    try {
      const data = await analyzeAudio(file, title, language)
      setResult(data)
      setStatus("done")
      toast.success("Meeting analyzed and saved to history")
      if (data.language_warning) toast.warning(data.language_warning)
    } catch (e: any) {
      setStatus("idle")
      toast.error(e.message || "Something went wrong")
    }
  }

  async function handleText(text: string, title: string, language: string) {
    setIsAudio(false)
    setStatus("processing")
    try {
      const data = await analyzeText(text, title, language)
      setResult(data)
      setStatus("done")
      toast.success("Meeting analyzed and saved to history")
      if (data.language_warning) toast.warning(data.language_warning)
    } catch (e: any) {
      setStatus("idle")
      toast.error(e.message || "Something went wrong")
    }
  }

  function reset() {
    setResult(null)
    setStatus("idle")
  }

  function downloadTxt() {
    if (!result) return
    const blob = new Blob([result.report_text], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "meeting_summary_report.txt"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <main className="mx-auto max-w-3xl px-6 pb-24">
      <Hero />

      <div className="mt-10">
        {status === "idle" && (
          <UploadCard onSubmitAudio={handleAudio} onSubmitText={handleText} busy={false} />
        )}

        {status === "processing" && (
          <div className="py-8">
            <ProcessingChecklist isAudio={isAudio} done={false} />
          </div>
        )}

        <AnimatePresence>
          {status === "done" && result && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.35 }}
              className="flex flex-col gap-4"
            >
              {result.language_warning && (
                <div className="flex items-start gap-2.5 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
                  <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{result.language_warning}</span>
                </div>
              )}

              <div className="grid gap-4 md:grid-cols-2">
                <InfoRows
                  title="Meeting Information"
                  rows={[
                    ["Title", result.title],
                    ["Upload Date", result.created_at],
                    ["Input Type", result.input_type === "audio" ? "Audio" : "Text"],
                    ["Language", result.language],
                    ["Meeting Duration", result.analytics.duration_display],
                    ["Processing Time", `${result.analytics.processing_secs}s`],
                  ]}
                />
                <InfoRows
                  title="AI Insights"
                  rows={[
                    ["Meeting Type", result.ai_insights.meeting_type],
                    ["Primary Topic", result.ai_insights.primary_topic],
                    ["Overall Sentiment", result.ai_insights.sentiment],
                    ["Est. Reading Time", result.analytics.reading_time],
                  ]}
                />
              </div>

              <AnalyticsSection analytics={result.analytics} />

              <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">Meeting Output</p>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(result.report_text); toast.success("Report copied to clipboard") }}>
                    <Copy className="h-3.5 w-3.5" />Copy all
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => window.location.assign(pdfUrl(result.id))}>
                    <FileDown className="h-3.5 w-3.5" />PDF
                  </Button>
                  <Button variant="outline" size="sm" onClick={downloadTxt}>
                    <Download className="h-3.5 w-3.5" />.txt
                  </Button>
                  <Button variant="outline" size="sm" onClick={reset}>
                    <RotateCcw className="h-3.5 w-3.5" />New meeting
                  </Button>
                </div>
              </div>

              <OutputCards output={result} />

              <AssistantPanel meetingId={result.id} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </main>
  )
}
