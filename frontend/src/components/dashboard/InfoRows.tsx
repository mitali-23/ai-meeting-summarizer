import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"

export function InfoRows({ title, rows }: { title: string; rows: [string, string | null | undefined][] }) {
  return (
    <Card>
      <CardHeader><CardTitle>{title}</CardTitle></CardHeader>
      <CardContent className="flex flex-col gap-0">
        {rows.map(([label, value], i) => {
          const isMuted = !value || value === "Not Available" || value === "N/A"
          return (
            <div key={label} className={`flex items-center justify-between py-2.5 text-sm ${i < rows.length - 1 ? "border-b border-border" : ""}`}>
              <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{label}</span>
              <span className={`text-right font-semibold ${isMuted ? "italic text-muted-foreground" : "text-foreground"}`}>
                {value || "Not Available"}
              </span>
            </div>
          )
        })}
      </CardContent>
    </Card>
  )
}
