import { useEffect, useRef, useState } from "react"
import { UploadCloud, Languages, ChevronDown } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { toast } from "sonner"
import { listLanguages, type LanguageOption } from "@/lib/api"

interface Props {
  onSubmitAudio: (file: File, title: string, language: string) => void
  onSubmitText: (text: string, title: string, language: string) => void
  busy: boolean
}

export function UploadCard({ onSubmitAudio, onSubmitText, busy }: Props) {
  const [mode, setMode] = useState<"audio" | "text">("audio")
  const [title, setTitle] = useState("")
  const [text, setText] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [dragActive, setDragActive] = useState(false)
  const [languageOptions, setLanguageOptions] = useState<LanguageOption[]>([{ code: "en", name: "English" }])
  const [language, setLanguage] = useState("en")
  const fileInputRef = useRef<HTMLInputElement>(null)
  const txtInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listLanguages()
      .then((langs) => { if (langs.length) setLanguageOptions(langs) })
      .catch(() => { /* fall back to English-only option already set */ })
  }, [])

  function handleAudioDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragActive(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  function handleTxtFile(f: File) {
    if (!f.name.toLowerCase().endsWith(".txt")) return toast.error("Please choose a .txt file")
    const reader = new FileReader()
    reader.onload = (e) => { setText((e.target?.result as string) || ""); toast.success(`Loaded ${f.name}`) }
    reader.onerror = () => toast.error("Couldn't read that file")
    reader.readAsText(f)
  }

  function handleGenerate() {
    if (mode === "audio") {
      if (!file) return toast.error("Choose an audio file first.")
      onSubmitAudio(file, title.trim(), language)
    } else {
      if (!text.trim()) return toast.error("Paste a transcript or upload a .txt file first.")
      onSubmitText(text.trim(), title.trim(), language)
    }
  }

  return (
    <Card className="p-2">
      <div className="flex flex-col gap-2 px-3 pb-1 pt-2 sm:flex-row sm:items-center sm:justify-between">
        <Input
          placeholder="Meeting title (optional — auto-generated if left blank)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="border-0 border-b border-border rounded-none px-1 shadow-none focus-visible:ring-0 focus-visible:border-primary sm:flex-1"
        />

        <div className="flex shrink-0 items-center gap-1.5 pb-1">
          <Languages className="h-3.5 w-3.5 text-muted-foreground" />
          <div className="relative">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              aria-label="Meeting language"
              className="h-8 appearance-none rounded-md border border-input bg-card text-foreground pl-2 pr-7 text-sm font-medium shadow-sm outline-none transition-colors hover:border-primary/50 focus-visible:ring-1 focus-visible:ring-ring"
            >
              {languageOptions.map((l) => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          </div>
        </div>
      </div>

      <div className="p-3">
        <Tabs value={mode} onValueChange={(v) => setMode(v as "audio" | "text")}>
          <TabsList className="w-full">
            <TabsTrigger value="audio" className="flex-1">Upload Audio</TabsTrigger>
            <TabsTrigger value="text" className="flex-1">Upload Text</TabsTrigger>
          </TabsList>

          <TabsContent value="audio">
            <label
              htmlFor="audioInput"
              onDragOver={(e) => { e.preventDefault(); setDragActive(true) }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleAudioDrop}
              className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-9 text-center transition-colors ${
                dragActive ? "border-primary bg-primary/5 text-primary" : "border-border text-muted-foreground hover:border-primary/60"
              }`}
            >
              <UploadCloud className="h-5.5 w-5.5 opacity-70" />
              <p className="text-sm">
                {file ? (
                  <>Selected: <span className="font-semibold text-primary">{file.name}</span></>
                ) : (
                  <>Drag an audio file here, or <span className="font-semibold text-primary">browse</span></>
                )}
              </p>
              <p className="font-mono text-[10.5px] tracking-wide text-muted-foreground/70">MP3 · MP4 · WAV · M4A · OGG · FLAC</p>
              <input
                ref={fileInputRef}
                id="audioInput"
                type="file"
                accept=".mp3,.mp4,.wav,.m4a,.ogg,.flac"
                hidden
                onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])}
              />
            </label>
          </TabsContent>

          <TabsContent value="text">
            <label
              htmlFor="txtInput"
              onDragOver={(e) => { e.preventDefault() }}
              onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleTxtFile(f) }}
              className="mb-2.5 flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-border py-4 text-center text-sm text-muted-foreground transition-colors hover:border-primary/60"
            >
              <UploadCloud className="h-4 w-4 opacity-70" />
              Drop a .txt file, or <span className="font-semibold text-primary">browse</span> — or paste below
              <input
                ref={txtInputRef}
                id="txtInput"
                type="file"
                accept=".txt"
                hidden
                onChange={(e) => e.target.files?.[0] && handleTxtFile(e.target.files[0])}
              />
            </label>
            <Textarea
              placeholder="Paste your meeting transcript here…"
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="min-h-40"
            />
          </TabsContent>
        </Tabs>

        <div className="mt-3 flex items-center justify-end">
          <Button onClick={handleGenerate} disabled={busy}>
            Generate Meeting Insights
          </Button>
        </div>
      </div>
    </Card>
  )
}
