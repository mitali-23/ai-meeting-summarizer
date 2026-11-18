import { useEffect, useState } from "react"
import { Copy, FileDown } from "lucide-react"
import { toast } from "sonner"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { InfoRows } from "@/components/dashboard/InfoRows"
import { AnalyticsSection } from "@/components/dashboard/AnalyticsSection"
import { OutputCards } from "@/components/dashboard/OutputCards"
import { AssistantPanel } from "@/components/dashboard/AssistantPanel"
import { Skeleton } from "@/components/ui/skeleton"
import { getMeeting, pdfUrl } from "@/lib/api"
import type { MeetingDetail } from "@/lib/types"

export function MeetingDetailDialog({ id, open, onOpenChange }: { id: number | null; open: boolean; onOpenChange: (o: boolean) => void }) {
  const [meeting, setMeeting] = useState<MeetingDetail | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || id == null) return
    setLoading(true)
    setMeeting(null)
    getMeeting(id)
      .then(setMeeting)
      .catch((e) => toast.error(e.message || "Couldn't load that meeting"))
      .finally(() => setLoading(false))
  }, [open, id])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {loading && (
          <div className="flex flex-col gap-4 py-4">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        )}

        {meeting && !loading && (
          <>
            <DialogHeader>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <DialogTitle>{meeting.title}</DialogTitle>
                  <DialogDescription className="mt-1 font-mono text-[11.5px]">
                    {meeting.created_at} · {meeting.input_type === "audio" ? "Audio" : "Text"} input
                  </DialogDescription>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => { navigator.clipboard.writeText(meeting.report_text); toast.success("Report copied to clipboard") }}>
                    <Copy className="h-3.5 w-3.5" />Copy all
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => window.location.assign(pdfUrl(meeting.id))}>
                    <FileDown className="h-3.5 w-3.5" />PDF
                  </Button>
                </div>
              </div>
            </DialogHeader>

            <div className="flex flex-col gap-4">
              <div className="grid gap-4 md:grid-cols-2">
                <InfoRows
                  title="Meeting Information"
                  rows={[
                    ["Title", meeting.title],
                    ["Upload Date", meeting.created_at],
                    ["Input Type", meeting.input_type === "audio" ? "Audio" : "Text"],
                    ["Language", meeting.language],
                    ["Meeting Duration", meeting.analytics.duration_display],
                    ["Processing Time", meeting.analytics.processing_secs ? `${meeting.analytics.processing_secs}s` : null],
                  ]}
                />
                <InfoRows
                  title="AI Insights"
                  rows={[
                    ["Meeting Type", meeting.ai_insights.meeting_type],
                    ["Primary Topic", meeting.ai_insights.primary_topic],
                    ["Overall Sentiment", meeting.ai_insights.sentiment],
                    ["Est. Reading Time", meeting.analytics.reading_time],
                  ]}
                />
              </div>

              <AnalyticsSection analytics={meeting.analytics} />

              <p className="font-mono text-[11px] uppercase tracking-widest text-muted-foreground">Meeting Output</p>
              <OutputCards output={meeting} />

              <AssistantPanel meetingId={meeting.id} />
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
