# Free API Keys for Flight, Train & Bus

There is **no single free API** that covers all three modes across India. Use the mix below.

## Quick recommendation for your project

| Mode | Best free option | API key needed? |
|------|------------------|-----------------|
| **Flight** | Amadeus Self-Service | Yes — free test account |
| **Train** | NTES (Indian Railways enquiry) | **No key** — built into this app |
| **Bus** | Tavily web search fallback | Uses existing `TAVILY_API_KEY` |

---

## 1. Flights

### Amadeus (recommended — search + prices)

1. Register: https://developers.amadeus.com/register
2. Create an app in **My Self-Service Workspace**
3. Copy **API Key** → `AMADEUS_API_KEY`
4. Copy **API Secret** → `AMADEUS_API_SECRET`

Free test environment includes cached flight offers between most cities/airports.

### Aviationstack (optional — live status by flight number)

1. Sign up: https://aviationstack.com/signup/free
2. Copy key → `AVIATIONSTACK_API_KEY`
3. Free tier: **100 requests/month**

---

## 2. Trains (India)

### No key required (default)

This backend uses the **National Train Enquiry System (NTES)** via the `ntes-client` library. No signup needed.

Tools available:
- Trains between two station codes (e.g. `NDLS` → `BCT`)
- Live running status for a train number

### Optional paid/free-tier alternatives

| Provider | Free tier | Signup |
|----------|-----------|--------|
| **eRail.in** | Email approval | info@erail.in or http://api.erail.in/auth/register |
| **Parse RailYatri** | 100 calls/month | https://parse.bot/ |

Set `ERAIL_API_KEY` or `PARSE_API_KEY` in `.env` if you prefer those over NTES.

---

## 3. Buses (India)

**Important:** India has **no free national live bus API** like flights. Options are city-specific:

| City/State | Live data? | How to get access |
|------------|------------|-------------------|
| **Delhi** | Yes (GPS) | Request key at https://opendata.iiitd.edu.in/ → `DELHI_OTD_API_KEY` |
| **Telangana/Hyderabad** | GTFS static only | https://tgsrtc.telangana.gov.in/open-data (schedules, not live) |
| **Bengaluru (BMTC)** | Unofficial endpoints | No official key; community reverse-engineered APIs |
| **Other cities** | Limited | App uses **Tavily search** as fallback |

For Kerala / inter-city buses, Tavily search is the most practical free option for your college project.

---

## 4. Required keys for the AI agent

| Key | Signup |
|-----|--------|
| `GROQ_API_KEY` | https://console.groq.com/keys |
| `TAVILY_API_KEY` | https://app.tavily.com/ |
| `OPENWEATHER_API_KEY` | https://home.openweathermap.org/users/sign_up |

---

## Setup

```powershell
cd C:\Users\sampa\D12\ai_travel_backend
copy .env.example .env
# Edit .env and paste your keys
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Minimum to run: `GROQ_API_KEY` + `TAVILY_API_KEY`.
