# निदान — Nidan

> **Sahi waqt par, sahi doctor.**  
> An AI-powered doctor appointment and reporting system built with GPT-4o tool-calling, FastAPI, MCP architecture, React, and PostgreSQL.

---

## What is Nidan?

Nidan (निदान) is a full-stack agentic AI application that allows:

- **Patients** to book doctor appointments using plain natural language
- **Doctors** to query their appointment data and receive summarized reports via Slack

The system demonstrates true agentic behavior — the LLM (GPT-4o) decides which tools to call, when to call them, and how to chain them together to fulfill a user's intent across multiple conversation turns.

---

## Architecture

```
React Frontend (Vite)
       │
       ▼
FastAPI Backend  ──►  GPT-4o (tool-calling)
       │                     │
       │         ┌───────────┼───────────────┐
       │         ▼           ▼               ▼
       │  check_availability  book_appointment  get_doctor_summary
       │         │           │               │
       ▼         ▼           ▼               ▼
  PostgreSQL  PostgreSQL  Google Calendar  PostgreSQL
                           + Gmail API      + Slack
```

### MCP Tools (defined in `mcp_tools.py`)

| Tool | Description |
|------|-------------|
| `check_doctor_availability` | Queries live slots from DB by doctor name, specialization, date, time preference |
| `book_appointment` | Books slot in DB, creates Google Calendar event, sends Gmail confirmation |
| `get_doctor_summary` | Aggregates appointment stats by period with optional symptom filter |
| `list_doctors` | Lists all doctors with specialization and fee |
| `cancel_appointment` | Cancels appointment and frees the slot |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| LLM | GPT-4o (OpenAI function-calling) |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Notifications | Slack Incoming Webhooks |
| Auth | JWT (role-based: patient / doctor) |

---

## Features

### Scenario 1 — Patient Appointment Booking
- Natural language booking: *"Book an appointment with Dr. Ahuja tomorrow morning"*
- AI parses intent, checks live availability, confirms slot, books in DB
- Google Calendar event created + Gmail confirmation sent to patient
- Multi-turn conversation — patient can say *"actually book 3 PM instead"* and the AI understands context

### Scenario 2 — Doctor Summary Reports
- Natural language queries: *"How many patients with fever this week?"*
- AI calls `get_doctor_summary` with correct period and symptom filter
- Summary rendered in chat + sent to doctor's Slack channel automatically
- Quick report buttons on dashboard for one-click reports

### Bonus Features Implemented
- Role-based JWT auth (patient vs doctor — separate UIs)
- Multi-turn conversation with session history per user
- Tool call badges shown in UI for transparency
- Appointment status sidebar (patient)
- Upcoming appointments panel (doctor)

---

## Project Structure

```
nidan/
├── backend/
│   ├── integrations/
│   │   ├── calendar.py       # Google Calendar API
│   │   ├── gmail.py          # Gmail confirmation emails
│   │   └── slack.py          # Slack Block Kit notifications
│   ├── models/
│   │   └── database.py       # SQLAlchemy models
│   ├── agent.py              # GPT-4o tool-calling loop + session history
│   ├── auth.py               # JWT auth + role guards
│   ├── main.py               # FastAPI routes
│   ├── mcp_tools.py          # MCP tool schemas + handlers
│   ├── schemas.py            # Pydantic models
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── components/
│       │   └── ChatWindow.jsx
│       ├── pages/
│       │   ├── LoginPage.jsx
│       │   ├── PatientPage.jsx
│       │   └── DoctorPage.jsx
│       ├── App.jsx
│       ├── AuthContext.jsx
│       └── api.js
│
└── README.md
```

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/nidan.git
cd nidan
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and fill in:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nidan_db
OPENAI_API_KEY=sk-your-openai-key

# Optional
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GMAIL_SENDER_EMAIL=...
```

### 3. Create database

```bash
psql -U postgres
CREATE DATABASE nidan_db;
\q
```

### 4. Run backend

```bash
uvicorn main:app --reload --port 8000
```

### 5. Seed sample data

```bash
# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:8000/seed -Method POST -UseBasicParsing

# Mac/Linux
curl -X POST http://localhost:8000/seed
```

### 6. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**

---

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Patient | patient@test.com | patient123 |
| Doctor | priya@clinic.com | doctor123 |

---

## Sample Prompts

### Patient
```
Show me all available doctors
Book an appointment with Dr. Ahuja tomorrow morning
Check Dr. Sharma's availability this Friday afternoon
Cancel my appointment
```

### Multi-turn example
```
User:  Check Dr. Ahuja's availability for tomorrow
AI:    Available slots: 9 AM, 10 AM, 11 AM, 2 PM...
User:  Book the 10 AM slot
AI:    Done! Appointment confirmed for tomorrow at 10:00 AM
```

### Doctor
```
How many patients do I have today?
How many appointments this week?
How many patients with fever this week?
Give me yesterday's summary
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/auth/register` | — | Register patient or doctor |
| POST | `/auth/login` | — | Login, returns JWT |
| GET | `/doctors` | — | List all doctors |
| GET | `/doctors/{id}/slots` | — | Available slots |
| POST | `/chat/patient` | Patient | Agentic chat — Scenario 1 |
| POST | `/chat/doctor` | Doctor | Agentic chat — Scenario 2 |
| POST | `/doctor/summary` | Doctor | Button-triggered summary |
| GET | `/appointments/mine` | Patient | Patient's appointments |
| GET | `/doctor/appointments` | Doctor | Doctor's schedule |
| DELETE | `/chat/session` | Any | Clear conversation session |
| POST | `/seed` | — | Seed demo data |

---


