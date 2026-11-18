export interface KeywordFreq { word: string; count: number }

export interface Breakdown {
  discussion: number
  action_items: number
  decisions: number
  deadlines: number
}

export interface Analytics {
  word_count: number
  sentence_count: number
  top_keywords: string[]
  keyword_freq: KeywordFreq[]
  action_item_count: number
  decision_count: number
  deadline_count: number
  duration_secs: number | null
  duration_display: string
  processing_secs: number
  reading_time: string
  breakdown: Breakdown
}

export interface AiInsights {
  meeting_type: string
  primary_topic: string
  sentiment: string
}

// The core AI output — unchanged in content, shape, and meaning.
export interface MeetingOutput {
  summary: string[]
  action_items: string[]
  decisions: string[]
  deadlines: string[]
}

export interface AnalyzeResult extends MeetingOutput {
  id: number
  title: string
  created_at: string
  input_type: "audio" | "text"
  report_text: string
  analytics: Analytics
  ai_insights: AiInsights
  language: string
  language_warning: string | null
}

export interface MeetingListItem extends MeetingOutput {
  id: number
  title: string
  created_at: string
  input_type: "audio" | "text"
  duration_secs: number | null
  word_count: number
  sentence_count: number
  top_keywords: string[]
  processing_secs: number | null
  meeting_type: string | null
  primary_topic: string | null
  sentiment: string | null
  language: string
}

export interface MeetingDetail extends AnalyzeResult {
  transcript: string
}
