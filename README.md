# NIDAN — Agentic Doctor Appointment System

> Full-stack agentic AI application for intelligent doctor appointment booking and patient-doctor communication.

---

## Overview

NIDAN is an agentic AI system that handles doctor appointment scheduling through natural language. Patients and doctors interact via a conversational interface powered by GPT-4o tool-calling, which autonomously checks availability, books appointments, sends confirmations, and notifies relevant parties — all without manual coordination.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite) + Tailwind CSS |
| Backend | FastAPI (Python) |
| AI Agent | GPT-4o with Tool Calling |
| Protocol | MCP (Model Context Protocol) |
| Database | PostgreSQL |
| Calendar | Google Calendar API |
| Notifications | Gmail + Slack |

---

## Architecture

```
React (Vite)
├── POST /chat/patient  ──►  FastAPI
└── POST /chat/doctor   ──►  FastAPI
                                └──► GPT-4o (tool-calling)
                                        ├── check_doctor_availability  ──► PostgreSQL
                                        ├── book_appointment           ──► PostgreSQL
                                        ├── send_confirmation          ──► Gmail
                                        ├── add_to_calendar            ──► Google Calendar
                                        └── notify_doctor              ──► Slack
```

---

## Features

- **Conversational Booking** — Patients describe their symptoms/needs in natural language; the agent handles the rest
- **Agentic Tool Calling** — GPT-4o autonomously calls backend tools to check slots, book, and confirm
- **Dual Interface** — Separate chat flows for patients and doctors
- **Calendar Integration** — Appointments auto-added to Google Calendar
- **Multi-channel Notifications** — Confirmation via Gmail; doctor alerts via Slack
- **MCP Protocol** — Structured tool communication between agent and backend services

---

## Project Structure

```
nidan/
├── backend/
│   ├── agent.py          # GPT-4o agentic logic + tool orchestration
│   ├── auth.py           # Authentication
│   ├── main.py           # FastAPI app + route definitions
│   ├── mcp_tools.py      # MCP tool definitions
│   ├── schemas.py        # Pydantic models
│   ├── models/           # Database models
│   ├── integrations/     # Google Calendar, Gmail, Slack clients
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL
- OpenAI API key
- Google Cloud project (Calendar + Gmail APIs enabled)
- Slack Bot token

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # Fill in your credentials
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

```env
OPENAI_API_KEY=your_openai_key
DATABASE_URL=postgresql://user:password@localhost:5432/nidan
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_channel_id
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat/patient` | Patient conversation with AI agent |
| POST | `/chat/doctor` | Doctor-side conversation interface |

---

## License

MIT License — feel free to use and modify.

---

## Author

**Divyansh Maurya**
- GitHub: [@draccs2211](https://github.com/draccs2211)
- LinkedIn: [divyanshmaurya-42a25735b](https://linkedin.com/in/divyanshmaurya-42a25735b)
