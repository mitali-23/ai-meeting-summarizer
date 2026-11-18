# Meeting Summarizer — React Edition

Full frontend rewrite in **React + TypeScript + Tailwind CSS + shadcn/ui +
Recharts + Framer Motion**, per your request. The backend (Flask API) and the
AI pipeline are **completely unchanged** — this only replaces how the pages
look and behave in the browser.

## What's unchanged
- `backend/meeting_summarizer.py` — the AI pipeline (transcription, prompt,
  extraction). Not touched.
- `backend/insights.py`, `backend/analytics.py`, `backend/pdf_export.py`,
  `backend/db.py` — same logic as before.
- Every `/api/...` route: same URL, same request shape, same response shape.
  The React app calls the exact same endpoints the old HTML/JS version did.

## What's new
- The old server-rendered pages (`templates/*.html`, `static/*`) are
  **replaced** by a React app (`frontend/`), built with Vite.
- `backend/app.py` now serves the *built* React app (`frontend/dist`)
  instead of Jinja templates. It's still the same Flask process, same API
  routes, same port (5000) — just a different frontend.
- UI stack: React Router (page navigation), Tailwind CSS v4, hand-built
  shadcn/ui-style components (Button, Card, Tabs, Dialog, Badge, etc. — the
  shadcn CLI registry wasn't reachable in the build sandbox, so these were
  written by hand using the same Radix primitives + Tailwind classes shadcn
  itself generates), Lucide icons, Recharts (keyword bar chart + meeting
  breakdown doughnut chart), Framer Motion (subtle fade/slide transitions),
  and Sonner for toast notifications.

## Project structure

```
meeting-summarizer-react/
├── backend/                 Flask API (was the whole app before; now API + static server)
│   ├── app.py                Routes: /api/* (unchanged) + serves frontend/dist
│   ├── meeting_summarizer.py UNCHANGED — the AI pipeline
│   ├── insights.py           Separate AI Insights call (meeting type/topic/sentiment)
│   ├── db.py                 SQLite storage
│   ├── analytics.py          Word/sentence counts, keywords, breakdown
│   ├── pdf_export.py         PDF report generation
│   └── requirements.txt
└── frontend/                 React app (Vite + TS)
    ├── dist/                 Prebuilt — the app works out of the box without npm
    ├── src/
    │   ├── components/ui/    Hand-built shadcn-style components
    │   ├── components/dashboard/  Hero, UploadCard, ProcessingChecklist, AnalyticsSection, OutputCards
    │   ├── components/history/    MeetingDetailDialog
    │   ├── components/layout/     Navbar
    │   ├── pages/             HomePage, HistoryPage
    │   └── lib/                api.ts (typed fetch client), theme.tsx, types.ts, utils.ts
    ├── package.json
    └── vite.config.ts
```

## Quick start (no Node.js needed — uses the prebuilt frontend)

```bash
cd backend
pip install -r requirements.txt
```

Set `GEMINI_API_KEY` exactly like before, then:

```bash
python app.py
```

Open **http://127.0.0.1:5000**. The prebuilt React app in `frontend/dist`
is served automatically — you don't need Node.js/npm just to run it.

## If you want to modify the frontend

You'll need [Node.js](https://nodejs.org) (v20+) installed.

**Development mode** (hot-reload, runs on its own port and proxies API
calls to Flask):
```bash
cd frontend
npm install
npm run dev
```
This opens on **http://127.0.0.1:5173** — keep `python app.py` running in
another terminal at the same time (the dev server forwards `/api/*` calls
to it).

**Rebuild for production** (after making changes, so `python app.py` serves
your updated version):
```bash
cd frontend
npm run build
```
This regenerates `frontend/dist` — then just run `python app.py` as usual.

## Notes
- Same `GEMINI_API_KEY` requirement as before — nothing changed there.
- Same `meetings.db` (SQLite) — old databases from the previous version
  still work; new columns are added automatically.
- Charts (Recharts) and icons (Lucide) are bundled into the build — no
  external CDN needed, unlike the previous vanilla-JS version which loaded
  Chart.js from a CDN.
