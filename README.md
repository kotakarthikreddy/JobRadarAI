# 🎯 JobRadar AI v5.0

> Elite autonomous job intelligence system built for Karthik — Senior ML/AI Engineer on OPT → H1B track.

---

## What This Does

- **Monitors 100+ company career pages** every 5 minutes (Greenhouse × 40, Lever × 27, Ashby × 22, Workday × 22, Google, Amazon, H1B GitHub Feed, JobSpy)
- **3-layer deduplication** (Job ID → URL hash → Fuzzy title+company)
- **AI scoring** with Gemini 2.0 Flash → Groq → OpenRouter fallback chain
- **Instant Telegram alerts** via @KotaKarthik_bot — Wave 1 (raw detection) + Wave 2 (full AI analysis)
- **Google Sheets tracking** — all jobs logged with score, verdict, cover letter
- **Premium Streamlit UI** — dark-mode dashboard, job feed with score rings, application tracker

---

## Quick Start

### 1. Install Dependencies
```powershell
cd d:\GITHUB\JobRadarAI
pip install -r requirements.txt
```

### 2. Configure `.env`
Copy `.env.example` → `.env` (or use the generated `.env` in the repo root).

**Required for alerts:**
1. Open Telegram → [@KotaKarthik_bot](https://t.me/KotaKarthik_bot) → send `/start`
2. Run: `python scripts/get_telegram_chat_id.py`
3. Set `TELEGRAM_CHAT_ID=<your numeric id>` in `.env`

**Optional — Google Sheets** (SQLite works without this):
1. Google Cloud → enable Sheets + Drive API → create Service Account → download JSON
2. Share [your sheet](https://docs.google.com/spreadsheets/d/12aDfDaW4LP1s97q8CJHG0GPFb1lahRCuCIus0k5Tjho/edit) with the service account email (Editor)
3. Paste full JSON into `GOOGLE_CREDS_JSON=` (one line) in `.env`
4. Run: `python scripts/init_sheets.py`

### 3. Run the Streamlit UI
```powershell
streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### 4. Or Run Scanner Only (Headless)
```powershell
python run_scanner.py
```
Scans every 5 minutes, sends Telegram alerts, logs to `data/jobradar.log`.

**Test one cycle:**
```powershell
python scripts/run_one_scan.py
```

---

## Telegram Bot Commands

| Command | Action |
|---|---|
| `/top5` | Show top 5 new matches |
| `/status` | Scanner health & daily stats |
| `/cl_<id>` | Get AI-generated cover letter |
| `/applied_<id>` | Mark job as Applied |
| `/interview_<id>` | Mark as Interviewing |
| `/reject_<id>` | Mark as Rejected |
| `/skip_<id>` | Skip job |
| `/help` | Show all commands |

---

## Scoring System (100 pts)

| Category | Points |
|---|---|
| Skills match | 40 |
| Seniority fit | 20 |
| Domain (ML/AI/LLM) | 20 |
| Company quality | 10 |
| Visa friendliness | 10 |

**Verdict thresholds:**
- 🔥 80–100 → STRONG APPLY
- ✅ 65–79 → APPLY
- ⚡ 50–64 → APPLY WITH GAPS
- ❌ < 50 → SKIP

---

## Google Sheets Setup (Optional)

1. Create a Google Cloud project → enable Sheets API + Drive API
2. Create a Service Account → download JSON key
3. Share your Sheet with the service account email (Editor access)
4. Paste full JSON content into `GOOGLE_CREDS_JSON` in `.env`

Sheet ID already configured: `12aDfDaW4LP1s97q8CJHG0GPFb1lahRCuCIus0k5Tjho`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google Gemini (250 free/day) |
| `TELEGRAM_BOT_TOKEN` | ✅ | @KotaKarthik_bot token |
| `TELEGRAM_CHAT_ID` | ✅ | Your personal Telegram ID |
| `GROQ_API_KEY` | Optional | Groq Llama (14,400 free/day) |
| `OPENROUTER_API_KEY` | Optional | OpenRouter (200 free/day) |
| `GOOGLE_SHEET_ID` | Optional | Already pre-set |
| `GOOGLE_CREDS_JSON` | Optional | Service account JSON |
| `MIN_MATCH_SCORE` | Optional | Default: 60 |
| `SCAN_INTERVAL_MINUTES` | Optional | Default: 5 |

---

## Project Structure

```
JobRadarAI/
├── app.py                  # Streamlit UI entry point
├── run_scanner.py          # Headless scanner (no UI)
├── scanner/
│   ├── orchestrator.py     # Main async scan loop (8 sources in parallel)
│   └── filters.py          # H1B, keyword, location, date, experience filters
├── ai/
│   ├── scorer.py           # Groq→OpenRouter→Gemini AI scoring
│   └── cover_letter.py     # Gemini cover letter generator
├── db/
│   └── storage.py          # SQLite (3-layer dedup + job tracker)
├── telegram/
│   ├── alerts.py           # Wave 1 + Wave 2 alert formatters
│   └── bot.py              # Command handler + polling thread
├── sheets/
│   └── client.py           # Google Sheets 3-sheet integration
├── config/
│   ├── settings.py         # Pydantic env vars
│   ├── candidate.py        # Karthik's profile, skills, H1B sponsors list
│   └── companies.py        # 100+ ATS endpoints
└── ui/
    ├── dashboard.py
    ├── job_feed.py
    ├── applications.py
    ├── scanner_control.py
    └── profile.py
```

---

## Sources Monitored

| Source | Companies |
|---|---|
| Greenhouse | 40 (Stripe, Coinbase, Airbnb, Palantir, Datadog…) |
| Lever | 27 (Netflix, Cohere, Databricks, Rippling…) |
| Ashby | 22 (OpenAI, Anthropic, Mistral, Vercel, Linear…) |
| Workday | 22 (NVIDIA, Intel, Salesforce, CMU, UT Austin…) |
| Google Careers | Direct API |
| Amazon Jobs | Direct API |
| H1B GitHub Feed | Daily verified H1B listings |
| JobSpy | Indeed + Glassdoor + ZipRecruiter |

---

*Built by merging: OPT-Job-Scrapper + career-ops + F1_H1B_Scraper + Karthik jobs finder + AutoJobAI + JobMatchAI*