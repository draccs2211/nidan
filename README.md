# निदान — Nidan

> **Sahi waqt par, sahi doctor.**
> AI-powered doctor appointment and reporting system with proper MCP client-server architecture.

---

## Overview

Nidan is a full-stack agentic AI application built for the Full-Stack Developer Intern Assignment (Agentic AI with MCP). It demonstrates true agentic behavior where GPT-4o dynamically discovers and invokes MCP tools to fulfill user intents across multi-turn conversations.

**Two core scenarios:**

- **Patients** book doctor appointments using plain natural language
- **Doctors** query appointment data and receive AI-generated reports via Slack

---

## MCP Architecture

This implementation strictly follows the MCP specification:

```
┌─────────────────────────────────────────────────────────┐
│                    MCP CLIENT (agent.py)                 │
│                                                          │
│  1. session.list_tools()  →  dynamic tool discovery      │
│  2. GPT-4o decides which tool to call                    │
│  3. session.call_tool()   →  routed via MCP protocol     │
└──────────────────────┬──────────────────────────────────-┘
                       │  HTTP (Streamable HTTP Transport)
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  MCP SERVER (mcp_server.py)              │
│                                                          │
│  FastMCP — official MCP Python SDK                       │
│  Mounted at /mcp via ASGI                                │
│                                                          │
│  @mcp.tool() check_doctor_availability                   │
│  @mcp.tool() book_appointment                            │
│  @mcp.tool() get_doctor_summary                          │
│  @mcp.tool() list_doctors                                │
│  @mcp.tool() cancel_appointment                          │
└──────────────────────┬──────────────────────────────────-┘
                       │
                       ▼
              PostgreSQL Database
```

**MCP Requirements Satisfied:**

| Requirement | Implementation |
|-------------|---------------|
| MCP client-server protocol | `streamablehttp_client` transport in `agent.py` |
| Dynamic tool discovery at runtime | `session.list_tools()` called every request |
| No hardcoded tool schemas | Schemas fetched from MCP server at runtime |
| LLM-driven orchestration | GPT-4o decides tool calls — no if/else routing |
| Clear Client/Server/Tool separation | `agent.py` (client) / `mcp_server.py` (server) / `@mcp.tool()` (tools) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS |
| Backend | FastAPI, SQLAlchemy, Python 3.11 |
| Database | PostgreSQL |
| LLM | GPT-4o (OpenAI function-calling) |
| MCP | Official MCP Python SDK (`mcp`, `fastmcp`) |
| Calendar | Google Calendar API |
| Email | Gmail API |
| Notifications | Slack Incoming Webhooks |
| Auth | JWT — role-based (patient / doctor) |

---

## Features

### Scenario 1 — Patient Appointment Booking
- Natural language booking: *"Book an appointment with Dr. Ahuja tomorrow morning"*
- MCP client calls `tools/list` → discovers `check_doctor_availability` → calls it via MCP protocol
- Slot confirmed → `book_appointment` tool called → DB updated → Google Calendar event created → Gmail sent
- Full multi-turn context: *"Actually book 3 PM instead"* works without repeating intent

### Scenario 2 — Doctor Summary Reports
- Natural language: *"How many patients with fever this week?"*
- MCP client routes to `get_doctor_summary` with `period=this_week` and `filter_symptom=fever`
- Summary rendered in chat + pushed to Slack automatically
- Quick report buttons on dashboard for one-click reports

### Bonus Features
- Role-based JWT authentication (patient vs doctor — separate UIs)
- Multi-turn conversation with session history per user
- Tool call badges shown in UI for transparency
- Prompt history tracking
- Appointment sidebar (patient) and upcoming panel (doctor)

---

## Project Structure

```
nidan/
├── backend/
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── calendar.py       # Google Calendar API
│   │   ├── gmail.py          # Gmail patient confirmations
│   │   └── slack.py          # Slack doctor notifications
│   ├── models/
│   │   ├── __init__.py
│   │   └── database.py       # SQLAlchemy models
│   ├── agent.py              # MCP CLIENT — tools/list + session.call_tool()
│   ├── auth.py               # JWT auth + role guards
│   ├── main.py               # FastAPI app + MCP server mount + lifespan
│   ├── mcp_server.py         # MCP SERVER — FastMCP + @mcp.tool() decorators
│   ├── schemas.py            # Pydantic request/response models
│   ├── requirements.txt
│   └── .env.example
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
git clone https://github.com/draccs2211/nidan.git
cd nidan
```

### 2. Backend setup

```bash
cd backend
python -m venv venv

# Activate
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/nidan_db
OPENAI_API_KEY=sk-your-openai-key

# Optional integrations
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

Expected output:
```
Database tables created/verified.
MCP Server mounted at /mcp
[MCP Client] Discovered 5 tools via tools/list: ['list_doctors', 'check_doctor_availability', ...]
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
AI:    Available slots: 9 AM, 10 AM, 11 AM...
User:  Book the 10 AM slot
AI:    Confirmed — appointment booked for tomorrow at 10:00 AM
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
| GET/POST | `/mcp` | — | MCP server endpoint (tools/list, tools/call) |
| POST | `/chat/patient` | Patient | Agentic chat — Scenario 1 |
| POST | `/chat/doctor` | Doctor | Agentic chat — Scenario 2 |
| POST | `/doctor/summary` | Doctor | Button-triggered summary + Slack |
| GET | `/appointments/mine` | Patient | Patient's appointments |
| GET | `/doctor/appointments` | Doctor | Doctor's upcoming schedule |
| DELETE | `/chat/session` | Any | Clear conversation session |
| POST | `/seed` | — | Seed demo data |
| GET | `/health` | — | Health check |

---

## Demo

- **GitHub:** https://github.com/draccs2211/nidan
- **Demo Video:** https://youtu.be/QbxxRX4Q8uQ

---

*Built for Full-Stack Developer Intern Assignment — Agentic AI with MCP*
