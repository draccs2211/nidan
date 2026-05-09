"""
Agent
-----
Wraps GPT-4o tool-calling with:
  - In-memory conversation history per session (multi-turn support)
  - MCP tool dispatch loop
  - Role-aware system prompts (patient vs doctor)
"""

import os
import json
import uuid
from typing import Optional
from openai import OpenAI
from sqlalchemy.orm import Session

from mcp_tools import TOOL_SCHEMAS, dispatch_tool

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# session_id -> list of messages
_conversation_store: dict[str, list[dict]] = {}

PATIENT_SYSTEM_PROMPT = """You are a helpful medical appointment assistant for a doctor clinic system.

You help patients:
- Check doctor availability
- Book appointments
- Cancel or reschedule appointments
- Answer questions about available doctors

Guidelines:
- Always confirm details (doctor, date/time, reason) before calling book_appointment
- Be warm and concise
- If a doctor is not found, suggest using list_doctors to see all available doctors
- After booking, summarize: doctor name, date/time, reason, and mention email confirmation
- Support multi-turn: remember what was discussed earlier in the conversation
- Today's date context will be provided in the first message
"""

DOCTOR_SYSTEM_PROMPT = """You are an intelligent medical assistant for doctors.

You help doctors get summaries and stats about their appointments.

CRITICAL RULES:
- NEVER ask the user for their doctor_id. It is automatically injected by the system.
- When asked anything about appointments, patients, or schedules, IMMEDIATELY call get_doctor_summary.
- Do not ask any clarifying questions before calling the tool.
- Just call the tool directly with the period that matches the user's query.

Period mapping:
- "today" → period: "today"
- "tomorrow" → period: "tomorrow"  
- "yesterday" → period: "yesterday"
- "this week" → period: "this_week"
- "last week" → period: "last_week"

After getting results, present them clearly in a readable format.
"""

def _get_or_create_session(session_id: Optional[str], role: str) -> tuple[str, list[dict]]:
    if session_id and session_id in _conversation_store:
        return session_id, _conversation_store[session_id]

    new_id = session_id or str(uuid.uuid4())
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")

    system_prompt = PATIENT_SYSTEM_PROMPT if role == "patient" else DOCTOR_SYSTEM_PROMPT
    history = [
        {"role": "system", "content": f"{system_prompt}\n\nToday is {today}."}
    ]
    _conversation_store[new_id] = history
    return new_id, history


def run_agent(
    user_message: str,
    session_id: Optional[str],
    role: str,
    db: Session,
    patient_id: int = None,
    doctor_id: int = None,
    calendar_service=None,
    gmail_service=None,
) -> dict:
    """
    Run one turn of the agent.
    Returns: { reply, session_id, tool_calls_made, booked_appointment_id }
    """
    session_id, history = _get_or_create_session(session_id, role)

    history.append({"role": "user", "content": user_message})

    tool_calls_made = []
    booked_appointment_id = None
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )

        msg = response.choices[0].message

        # No tool call → final answer
        if not msg.tool_calls:
            reply = msg.content or ""
            history.append({"role": "assistant", "content": reply})
            break

        # Append assistant message with tool_calls
        history.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ],
        })

        # Execute each requested tool
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            tool_calls_made.append(fn_name)

            _, result = dispatch_tool(
                tool_name=fn_name,
                args=fn_args,
                db=db,
                patient_id=patient_id,
                doctor_id=doctor_id,
                calendar_service=calendar_service,
                gmail_service=gmail_service,
            )

            # Track bookings
            if fn_name == "book_appointment":
                try:
                    parsed = json.loads(result)
                    if parsed.get("status") == "success":
                        booked_appointment_id = parsed.get("appointment_id")
                except Exception:
                    pass

            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result,
            })

    else:
        # Hit max rounds without a final reply
        reply = "I've processed your request. Is there anything else I can help you with?"
        history.append({"role": "assistant", "content": reply})

    # Keep history bounded (system + last 30 messages)
    if len(history) > 32:
        _conversation_store[session_id] = [history[0]] + history[-30:]

    return {
        "reply": reply,
        "session_id": session_id,
        "tool_calls_made": tool_calls_made,
        "booked_appointment_id": booked_appointment_id,
    }


def clear_session(session_id: str):
    _conversation_store.pop(session_id, None)


def get_session_history(session_id: str) -> list[dict]:
    return _conversation_store.get(session_id, [])
