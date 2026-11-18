import type { AnalyzeResult, MeetingDetail, MeetingListItem } from "./types"

// All calls hit the UNCHANGED Flask API — this file is just a typed fetch wrapper.

export interface LanguageOption { code: string; name: string }

// Analysis (audio transcription + AI calls with retry/fallback) can
// legitimately take a while for longer recordings — this is generous, but
// it's a safety net: without ANY timeout, if something hangs unexpectedly
// server-side, the UI would wait forever with no error, which is the
// "stuck, no output" symptom this fixes. Everything else uses a shorter
// timeout since those calls are normally fast.
const ANALYZE_TIMEOUT_MS = 6 * 60 * 1000  // 6 minutes
const DEFAULT_TIMEOUT_MS = 30 * 1000       // 30 seconds

async function fetchWithTimeout(input: RequestInfo, init: RequestInit = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(input, { ...init, signal: controller.signal })
  } catch (e: any) {
    if (e.name === "AbortError") {
      throw new Error("This is taking longer than expected. The server may still be working — please check back or try again.")
    }
    throw e
  } finally {
    clearTimeout(timer)
  }
}

async function handle<T>(res: Response): Promise<T> {
  const data = await res.json()
  if (!res.ok || data.error) throw new Error(data.error || "Something went wrong.")
  return data as T
}

export async function listLanguages() {
  const res = await fetchWithTimeout("/api/languages")
  const data = await handle<{ languages: LanguageOption[] }>(res)
  return data.languages
}

export async function analyzeAudio(file: File, title: string, language: string) {
  const form = new FormData()
  form.append("mode", "audio")
  form.append("title", title)
  form.append("language", language)
  form.append("audio", file)
  const res = await fetchWithTimeout("/api/analyze", { method: "POST", body: form }, ANALYZE_TIMEOUT_MS)
  return handle<AnalyzeResult>(res)
}

export async function analyzeText(text: string, title: string, language: string) {
  const form = new FormData()
  form.append("mode", "text")
  form.append("title", title)
  form.append("language", language)
  form.append("text", text)
  const res = await fetchWithTimeout("/api/analyze", { method: "POST", body: form }, ANALYZE_TIMEOUT_MS)
  return handle<AnalyzeResult>(res)
}

export async function listMeetings(query = "") {
  const url = query ? `/api/meetings?q=${encodeURIComponent(query)}` : "/api/meetings"
  const res = await fetchWithTimeout(url)
  const data = await handle<{ meetings: MeetingListItem[] }>(res)
  return data.meetings
}

export async function getMeeting(id: number) {
  const res = await fetchWithTimeout(`/api/meetings/${id}`)
  return handle<MeetingDetail>(res)
}

export async function deleteMeeting(id: number) {
  const res = await fetchWithTimeout(`/api/meetings/${id}`, { method: "DELETE" })
  return handle<{ ok: boolean }>(res)
}

export interface ChatMessage { role: "user" | "assistant"; content: string }

export async function getSuggestedQuestions(id: number) {
  const res = await fetchWithTimeout(`/api/meetings/${id}/suggested-questions`)
  const data = await handle<{ questions: string[] }>(res)
  return data.questions
}

export async function chatWithMeeting(id: number, message: string, history: ChatMessage[]) {
  const res = await fetchWithTimeout(`/api/meetings/${id}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  }, 60 * 1000)
  return handle<{ reply: string; language: string }>(res)
}

export function pdfUrl(id: number) {
  return `/api/meetings/${id}/pdf`
}
