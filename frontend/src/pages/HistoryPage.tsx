import { useEffect, useState, useCallback } from "react"
import { Search, Mic, FileText, FileDown, Trash2 } from "lucide-react"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { MeetingDetailDialog } from "@/components/history/MeetingDetailDialog"
import { listMeetings, deleteMeeting, pdfUrl } from "@/lib/api"
import type { MeetingListItem } from "@/lib/types"

export default function HistoryPage() {
  const [meetings, setMeetings] = useState<MeetingListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState("")
  const [openId, setOpenId] = useState<number | null>(null)
  const [dialogOpen, setDialogOpen] = useState(false)

  const load = useCallback((q = "") => {
    setLoading(true)
    listMeetings(q).then(setMeetings).catch(() => toast.error("Couldn't load meetings")).finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const t = setTimeout(() => load(query), 250)
    return () => clearTimeout(t)
  }, [query, load])

  async function handleDelete(id: number) {
    if (!confirm("Delete this meeting permanently?")) return
    try {
      await deleteMeeting(id)
      setMeetings((m) => m.filter((x) => x.id !== id))
      toast.success("Meeting deleted")
    } catch {
      toast.error("Couldn't delete meeting")
    }
  }

  return (
    <main className="mx-auto max-w-4xl px-6 pb-24 pt-10">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="mb-1 font-mono text-[11.5px] font-medium tracking-widest text-primary">MEETING HISTORY</p>
          <h1 className="text-[28px] font-extrabold tracking-tight">Past meetings</h1>
        </div>
        <div className="relative w-full max-w-xs sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input placeholder="Search meetings by title…" value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9" />
        </div>
      </div>

      {loading && (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
        </div>
      )}

      {!loading && meetings.length === 0 && (
        <p className="py-16 text-center font-mono text-sm text-muted-foreground">No meetings found yet. Go analyze one!</p>
      )}

      <div className="flex flex-col gap-2">
        {meetings.map((m) => (
          <div key={m.id} className="flex flex-wrap items-center justify-between gap-4 rounded-lg border border-border bg-card p-4 transition-colors hover:border-primary/50">
            <div className="flex items-center gap-3">
              <span className="flex h-8.5 w-8.5 items-center justify-center rounded-lg border border-border bg-secondary" style={{ width: 34, height: 34 }}>
                {m.input_type === "audio" ? <Mic className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
              </span>
              <div>
                <p className="text-sm font-semibold">{m.title}</p>
                <p className="font-mono text-[11px] text-muted-foreground">{m.created_at}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => { setOpenId(m.id); setDialogOpen(true) }}>Open</Button>
              <Button variant="outline" size="sm" onClick={() => window.location.assign(pdfUrl(m.id))}>
                <FileDown className="h-3.5 w-3.5" />PDF
              </Button>
              <Button variant="outline" size="sm" className="hover:border-destructive hover:text-destructive" onClick={() => handleDelete(m.id)}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        ))}
      </div>

      <MeetingDetailDialog id={openId} open={dialogOpen} onOpenChange={setDialogOpen} />
    </main>
  )
}
