import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, PieChart, Pie, Cell, Legend, Tooltip } from "recharts"
import type { Analytics } from "@/lib/types"

function cssVar(name: string) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function AnalyticsSection({ analytics }: { analytics: Analytics }) {
  const stats = [
    { label: "Duration", value: analytics.duration_display ?? "N/A" },
    { label: "Words", value: analytics.word_count ?? "—" },
    { label: "Sentences", value: analytics.sentence_count ?? "—" },
    { label: "Action Items", value: analytics.action_item_count ?? 0 },
    { label: "Decisions", value: analytics.decision_count ?? 0 },
    { label: "Deadlines", value: analytics.deadline_count ?? 0 },
  ]

  const border = `hsl(${cssVar("--border")})`
  const muted = `hsl(${cssVar("--muted-foreground")})`
  const primary = `hsl(${cssVar("--primary")})`
  const info = `hsl(${cssVar("--info")})`
  const success = `hsl(${cssVar("--success")})`
  const destructive = `hsl(${cssVar("--destructive")})`

  const breakdownData = [
    { name: "Discussion", value: analytics.breakdown.discussion, color: border },
    { name: "Action Items", value: analytics.breakdown.action_items, color: info },
    { name: "Decisions", value: analytics.breakdown.decisions, color: success },
    { name: "Deadlines", value: analytics.breakdown.deadlines, color: destructive },
  ]

  return (
    <Card>
      <CardHeader><CardTitle>Meeting Insights</CardTitle></CardHeader>
      <CardContent>
        <div className="mb-5 grid grid-cols-3 gap-2.5 sm:grid-cols-6">
          {stats.map((s) => (
            <div key={s.label} className="flex flex-col items-center gap-0.5 rounded-lg border border-border bg-secondary/60 py-3.5">
              <span className="text-xl font-extrabold tracking-tight">{s.value}</span>
              <span className="font-mono text-[9.5px] uppercase tracking-wide text-muted-foreground">{s.label}</span>
            </div>
          ))}
        </div>

        <div className="grid gap-5 md:grid-cols-[1.3fr_1fr]">
          <div className="rounded-lg border border-border bg-secondary/60 p-4">
            <p className="mb-3 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">Keyword Frequency</p>
            <div style={{ height: 190 }}>
              {analytics.keyword_freq.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analytics.keyword_freq} layout="vertical" margin={{ left: 4, right: 10 }}>
                    <XAxis type="number" hide />
                    <YAxis dataKey="word" type="category" width={70} tick={{ fill: muted, fontSize: 11 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: "hsl(var(--card))", border: `1px solid hsl(var(--border))`, borderRadius: 8, fontSize: 12 }}
                    />
                    <Bar dataKey="count" fill={primary} radius={[0, 4, 4, 0]} barSize={14} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <p className="flex h-full items-center justify-center text-sm italic text-muted-foreground">No keyword data</p>
              )}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-secondary/60 p-4">
            <p className="mb-3 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">Meeting Breakdown</p>
            <div style={{ height: 190 }}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={breakdownData} dataKey="value" nameKey="name" innerRadius={45} outerRadius={70} paddingAngle={2}>
                    {breakdownData.map((d, i) => <Cell key={i} fill={d.color} stroke="none" />)}
                  </Pie>
                  <Legend
                    layout="horizontal" verticalAlign="bottom" align="center"
                    wrapperStyle={{ fontSize: 10.5, color: muted }}
                  />
                  <Tooltip contentStyle={{ background: "hsl(var(--card))", border: `1px solid hsl(var(--border))`, borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        <p className="mb-2.5 mt-5 font-mono text-[10.5px] uppercase tracking-wide text-muted-foreground">Top Keywords</p>
        <div className="flex flex-wrap gap-2">
          {analytics.top_keywords.length > 0
            ? analytics.top_keywords.map((k) => <Badge key={k}>{k}</Badge>)
            : <span className="text-sm italic text-muted-foreground">No standout keywords</span>}
        </div>
      </CardContent>
    </Card>
  )
}
