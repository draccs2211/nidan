# MediAssist AI — Agentic Doctor Appointment System

Full-stack agentic AI application using **GPT-4o tool-calling**, **FastAPI**, **MCP**, **PostgreSQL**, **React**, **Google Calendar**, **Gmail**, and **Slack**.

---

## Architecture

```
React (Vite)
  └── POST /chat/patient  ──►  FastAPI
  └── POST /chat/doctor   ──►  FastAPI
                                  └── GPT-4o (tool-calling)
                                        ├── check_doctor_availability  → PostgreSQL
                                        ├── book_appointment           → PostgreSQL + Google Calendar + Gmail
                                        ├── get_doctor_summary         → PostgreSQL → Slack
                                        ├── list_doctors               → PostgreSQL
                                        └── cancel_appointment         → PostgreSQL
```

**MCP Tools** (defined in `mcp_tools.py`):
| Tool | Description |
|------|-------------|
| `check_doctor_availability` | Fetch available slots by doctor name / specialization / date |
| `book_appointment` | Book slot, create Google Calendar event, send Gmail confirmation |
| `get_doctor_summary` | Aggregate appointment stats for a period with optional symptom filter |
| `list_doctors` | List all doctors with specialization |
| `cancel_appointment` | Cancel an appointment and free the slot |

---

## Tech Stack

| Layer | Tech |
|-------|------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | FastAPI + SQLAlchemy |
| Database | PostgreSQL |
| LLM | GPT-4o (tool-calling / function-calling) |
| Calendar | Google Calendar API |
| Email | Gmail API (patient confirmation) |
| Notification | Slack Incoming Webhooks (doctor summary) |
| Auth | JWT (patient / doctor roles) |

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL running locally

### 1. Clone & configure backend

```bash
cd backend
cp .env.example .env
# Fill in: DATABASE_URL, OPENAI_API_KEY, SLACK_WEBHOOK_URL, Google OAuth creds
pip install -r requirements.txt
```

### 2. Run backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 3. Seed sample data (first time only)

```bash
curl -X POST http://localhost:8000/seed
```

This creates:
- 4 doctors (Dr. Ahuja, Dr. Sharma, Dr. Gupta, Dr. Singh)
- 1 sample patient
- 7 days × 7 daily slots per doctor

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Sample Prompts

### Scenario 1 — Patient Appointment Booking

| Prompt | What happens |
|--------|-------------|
| `"Show me available doctors"` | `list_doctors` tool called |
| `"Check Dr. Ahuja's availability tomorrow morning"` | `check_doctor_availability` with date + time filter |
| `"Book the 10 AM slot"` | `book_appointment` → Calendar event + Gmail confirmation |
| `"Cancel my appointment"` | `cancel_appointment` |

**Multi-turn example:**
```
User:  "Check Dr. Ahuja's availability for Friday afternoon."
AI:    "Here are the available slots: 2:00 PM, 3:00 PM, 4:00 PM"
User:  "Book the 3 PM slot."
AI:    "Done! Your appointment with Dr. Ahuja is confirmed for Friday 3:00 PM..."
```

### Scenario 2 — Doctor Summary

| Prompt | What happens |
|--------|-------------|
| `"How many patients do I have today?"` | `get_doctor_summary(period=today)` → Slack notification |
| `"How many appointments tomorrow?"` | `get_doctor_summary(period=tomorrow)` |
| `"How many patients with fever this week?"` | `get_doctor_summary(period=this_week, filter_symptom=fever)` |
| `"Give me yesterday's summary"` | `get_doctor_summary(period=yesterday)` |

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register patient or doctor |
| POST | `/auth/login` | — | Login → JWT |
| GET | `/doctors` | — | List doctors |
| GET | `/doctors/{id}/slots` | — | Available slots |
| POST | `/chat/patient` | patient | Agent chat (Scenario 1) |
| POST | `/chat/doctor` | doctor | Agent chat (Scenario 2) |
| POST | `/doctor/summary` | doctor | Button-triggered summary |
| GET | `/appointments/mine` | patient | Patient's appointments |
| GET | `/doctor/appointments` | doctor | Doctor's schedule |
| GET | `/chat/history` | any | Session history |
| DELETE | `/chat/session` | any | Clear session |
| POST | `/seed` | — | Seed dev data |

---

## Google OAuth Setup (for Calendar + Gmail)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API** and **Gmail API**
3. Create OAuth 2.0 credentials (web application)
4. Add `http://localhost:8000/auth/google/callback` as redirect URI
5. Copy `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` to `.env`

> **Note:** Without Google credentials, the app still works fully — appointments are booked in PostgreSQL, Calendar/Gmail steps are gracefully skipped.

---

## Slack Webhook Setup

1. Go to your Slack workspace → Apps → Incoming Webhooks
2. Create a new webhook for a channel
3. Copy the webhook URL to `SLACK_WEBHOOK_URL` in `.env`

---

## Demo Credentials (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Patient | patient@test.com | patient123 |
| Doctor | priya@clinic.com | doctor123 |

---

## Bonus Features Implemented

- ✅ Role-based login (patient vs doctor JWT)
- ✅ Multi-turn conversation with session history
- ✅ Prompt history display in chat
- ✅ Quick report buttons on doctor dashboard
- ✅ Tool call indicators shown in UI
- ✅ Appointment confirmation badge with Calendar status
- ✅ Symptom-based filtering in summary queries
