import { Routes, Route } from "react-router-dom"
import { Navbar } from "@/components/layout/Navbar"
import HomePage from "@/pages/HomePage"
import HistoryPage from "@/pages/HistoryPage"

export default function App() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/history" element={<HistoryPage />} />
      </Routes>
      <footer className="py-8 text-center font-mono text-[11px] tracking-wide text-muted-foreground">
        Runs on Gemini · Meetings are stored locally in your own database
      </footer>
    </div>
  )
}
