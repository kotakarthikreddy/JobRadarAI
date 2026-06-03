# 🎯 JobRadar AI

> Autonomous ML/AI job tracker — monitors 100+ companies, scores with AI, delivers Telegram alerts.

**Built for:** Senior ML/AI Engineers | H1B Track | $0/month

---

## ⚡ Quick Start

```powershell
# 1. Install
pip install -r requirements.txt

# 2. Configure .env (copy from .env.example)
copy .env.example .env
# Add your API keys: GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# 3. Run
streamlit run app.py          # Full UI at http://localhost:8501
# OR
python run_scanner.py          # Headless (no browser)
```

---

## 🔧 Setup

### Required API Keys

| Key | Get it from | Free Tier |
|-----|-------------|-----------|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/) | 1,500/day |
| `TELEGRAM_BOT_TOKEN` | [@BotFather](https://t.me/BotFather) → `/newbot` | Unlimited |
| `TELEGRAM_CHAT_ID` | [@userinfobot](https://t.me/userinfobot) | - |

### Optional Keys (Fallbacks)

| Key | Purpose | Free Tier |
|-----|---------|-----------|
| `GROQ_API_KEY` | Groq Llama scoring | 14,400/day |
| `OPENROUTER_API_KEY` | OpenRouter fallback | 200/day |
| `GOOGLE_CREDS_JSON` | Google Sheets sync | 60 writes/min |

**Telegram Setup:**
```powershell
# Option A: Get your chat ID from @userinfobot and paste in .env

# Option B: Auto-detect
python scripts/get_telegram_chat_id.py
```

**Google Sheets Setup (Optional):**
1. [Google Cloud Console](https://console.cloud.google.com/) → Create project
2. Enable **Google Sheets API** + **Google Drive API**
3. Create **Service Account** → download JSON
4. Share your sheet with service account email (Editor)
5. Paste JSON into `.env` as `GOOGLE_CREDS_JSON=` (single line)
6. Run: `python scripts/init_sheets.py`

---

## 🚀 Usage

### Full UI (Recommended)
```powershell
streamlit run app.py
```
Opens **http://localhost:8501** with:
- 📊 **Dashboard** — metrics, charts, job table
- 🔍 **Job Feed** — premium cards with scores
- 📝 **Applications** — pipeline tracker
- ⚙️ **Scanner** — manual scan + logs
- 👤 **Profile** — settings + API status

### Headless Scanner
```powershell
python run_scanner.py
```
Runs every 60 min, sends Telegram alerts. No browser needed.

### Single Test Scan
```powershell
python scripts/run_one_scan.py
```

---

## 🤖 Telegram Commands

Message [@KotaKarthik_bot](https://t.me/KotaKarthik_bot):

| Command | Action |
|---------|--------|
| `/start` | Connect bot |
| `/top5` | Top 5 ML jobs |
| `/status` | Scanner stats |
| `/cl_<id>` | Get cover letter |
| `/applied_<id>` | Mark applied |
| `/skip_<id>` | Skip job |

---

## 📊 Scoring (100 points)

| Category | Points |
|----------|--------|
| Skills match | 40 |
| Seniority fit | 20 |
| Domain (ML/AI) | 20 |
| Company tier | 10 |
| Visa friendly | 10 |

**Verdicts:**
- 🔥 **80-100** → STRONG APPLY
- ✅ **70-79** → APPLY
- ⚡ **60-69** → APPLY WITH GAPS
- ❌ **<70** → SKIP (no alert)

**AI Chain:** Gemini → Groq → OpenRouter → Local Rules

---

## 📡 Data Sources (9 Platforms, 101 Endpoints)

| Platform | Count | Jobs/Scan |
|----------|-------|-----------|
| Greenhouse | 46 | 4,364 |
| Ashby | 25 | 1,157 |
| Workday | 23 | 177 |
| RemoteOK | 1 | 82 |
| Amazon | 1 | 25 |
| JobSpy (Indeed+Google) | 2 | 25 |
| Remotive | 1 | 20 |
| YC/HN | 1 | 20 |
| H1B GitHub | 1 | 0-20 |

**Total:** ~5,800 jobs/scan

**Companies:** NVIDIA, OpenAI, Anthropic, Stripe, Coinbase, Airbnb, Palantir, Datadog, Vercel, Linear, Cursor, Mistral, Intel, Salesforce, IBM, Amazon, and 85+ more.

---

## 🛡️ Deduplication (3 Layers)

1. **Job ID** — exact match
2. **URL Hash** — MD5 of job URL
3. **Fuzzy Title** — 85% similarity within 30 days

---

## 📁 Project Structure

```
JobRadarAI/
├── app.py                  # Streamlit UI entry
├── run_scanner.py          # Headless scanner
├── requirements.txt        # Dependencies
├── .env                    # Your secrets
│
├── scanner/                # Scraping + orchestration
├── ai/                     # AI scoring + cover letters
├── db/                     # SQLite storage
├── telegram/               # Bot + alerts
├── sheets/                 # Google Sheets sync
├── config/                 # Settings + candidate profile
├── ui/                     # Streamlit pages
├── scripts/                # Utility scripts
└── data/                   # Database + logs
```

---

## 🌐 Configuration (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Required | Google Gemini API |
| `TELEGRAM_BOT_TOKEN` | Required | Bot token |
| `TELEGRAM_CHAT_ID` | Required | Your chat ID |
| `GROQ_API_KEY` | Optional | Groq fallback |
| `OPENROUTER_API_KEY` | Optional | OpenRouter fallback |
| `GOOGLE_SHEET_ID` | Pre-set | Your sheet ID |
| `GOOGLE_CREDS_JSON` | Optional | Service account JSON |
| `MIN_MATCH_SCORE` | 70 | Min score to alert |
| `H1B_ONLY` | true | Only H1B sponsors |
| `SCAN_INTERVAL_MINUTES` | 60 | Scan frequency |
| `MAX_ALERTS_PER_SCAN` | 15 | Alert cap |

---

## 🚢 Deploy (Hugging Face Spaces)

1. Create Space → Gradio → Python 3.10
2. Upload all files
3. Add secrets: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
4. Scanner auto-starts

---

## 📋 Useful Commands

```powershell
# Check database
python scripts/check_db.py

# Sync DB to Sheets
python scripts/sync_db_to_sheets.py

# Initialize Sheets
python scripts/init_sheets.py

# Get Telegram chat ID
python scripts/get_telegram_chat_id.py

# Run production tests
python scripts/test_all.py
```

---

## 💰 Cost

**$0/month** — All services use free tiers.

---

## 📝 Notes

- **Date Filter:** Last 7 days only
- **Scan Interval:** Every 60 minutes
- **Alert Format:** Batch (all jobs in one message)
- **Min Score:** 70/100 (balanced threshold)
- **H1B Only:** Yes (verified sponsors only)

---

**Version:** 5.0 | **Status:** Production Ready ✅
