import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Copy } from "lucide-react"
import { toast } from "sonner"
import type { MeetingOutput } from "@/lib/types"

// ============================================================
// UNCHANGED AI OUTPUT — content, meaning, and structure below
// are exactly as produced by the backend. Only presentation
// (fonts/spacing/icons via shadcn Card) was updated.
// ============================================================

function isEmpty(items: string[]) {
  return !items || items.length === 0 || (items.length === 1 && /none/i.test(items[0]))
}

function copyList(items: string[], label: string) {
  const text = isEmpty(items) ? "None" : items.map((i) => `- ${i}`).join("\n")
  navigator.clipboard.writeText(text).then(() => toast.success(`${label} copied to clipboard`))
}

function ItemList({ items, dotClass }: { items: string[]; dotClass: string }) {
  if (isEmpty(items)) return <p className="text-sm italic text-muted-foreground">None</p>
  return (
    <ul className="flex flex-col gap-2.5">
      {items.map((item, i) => (
        <li key={i} className="relative pl-4.5 text-sm leading-relaxed" style={{ paddingLeft: 18 }}>
          <span className={`absolute left-0 top-2 h-1.5 w-1.5 rounded-full ${dotClass}`} />
          {item}
        </li>
      ))}
    </ul>
  )
}

export function OutputCards({ output }: { output: MeetingOutput }) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[13px] uppercase tracking-wide text-muted-foreground">
            <span className="text-base">📄</span>Summary
          </CardTitle>
          <Button variant="ghost" size="sm" className="h-7 gap-1.5 font-mono text-[11px]" onClick={() => copyList(output.summary, "Summary")}>
            <Copy className="h-3 w-3" />Copy
          </Button>
        </CardHeader>
        <CardContent>
          {output.summary?.length ? (
            <div className="font-display text-[19px] leading-snug text-foreground">
              {output.summary.map((line, i) => <p key={i} className="mb-1.5 last:mb-0">{line}</p>)}
            </div>
          ) : (
            <p className="text-sm italic text-muted-foreground">None</p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[13px] uppercase tracking-wide text-muted-foreground">
              <span className="text-base">✅</span>Action Items
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-7 gap-1.5 font-mono text-[11px]" onClick={() => copyList(output.action_items, "Action items")}>
              <Copy className="h-3 w-3" />Copy
            </Button>
          </CardHeader>
          <CardContent><ItemList items={output.action_items} dotClass="bg-info" /></CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[13px] uppercase tracking-wide text-muted-foreground">
              <span className="text-base">🎯</span>Decisions
            </CardTitle>
            <Button variant="ghost" size="sm" className="h-7 gap-1.5 font-mono text-[11px]" onClick={() => copyList(output.decisions, "Decisions")}>
              <Copy className="h-3 w-3" />Copy
            </Button>
          </CardHeader>
          <CardContent><ItemList items={output.decisions} dotClass="bg-success" /></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-[13px] uppercase tracking-wide text-muted-foreground">
            <span className="text-base">📅</span>Deadlines
          </CardTitle>
          <Button variant="ghost" size="sm" className="h-7 gap-1.5 font-mono text-[11px]" onClick={() => copyList(output.deadlines, "Deadlines")}>
            <Copy className="h-3 w-3" />Copy
          </Button>
        </CardHeader>
        <CardContent><ItemList items={output.deadlines} dotClass="bg-destructive" /></CardContent>
      </Card>
    </div>
  )
}
