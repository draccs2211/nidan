

import os
import json
import uuid
from typing import Optional
from openai import OpenAI
from sqlalchemy.orm import Session

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# In-memory conversation store: session_id -> message history
_conversation_store: dict[str, list[dict]] = {}

# Cached MCP tool schemas (populated via tools/list)
_mcp_tool_schemas: list[dict] = []

PATIENT_SYSTEM_PROMPT = """You are Nidan AI, a helpful medical appointment assistant.

You help patients:
- Check doctor availability
- Book appointments
- Cancel appointments
- List available doctors

RULES:
- Always confirm slot details before calling book_appointment
- Never ask for patient_id — it is injected automatically
- After booking, summarize: doctor, date/time, reason
- Support multi-turn context — remember previous messages
"""

DOCTOR_SYSTEM_PROMPT = """You are Nidan AI, an intelligent assistant for doctors.

You help doctors get appointment summaries and statistics.

CRITICAL RULES:
- NEVER ask for doctor_id — it is always injected automatically by the system
- When asked about appointments or patients, IMMEDIATELY call get_doctor_summary
- Do not ask clarifying questions before calling the tool
- Map the user query to correct period: today/tomorrow/yesterday/this_week/last_week
- Use filter_symptom for symptom-based queries like 'how many with fever'
"""


async def discover_tools_from_mcp() -> list[dict]:
    """
    Connect to MCP server and call tools/list to dynamically
    discover available tools at runtime.
    Returns OpenAI-compatible tool schemas.
    """
    global _mcp_tool_schemas

    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Dynamic tool discovery at runtime — tools/list call
                tools_result = await session.list_tools()

                schemas = []
                for tool in tools_result.tools:
                    schemas.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema if tool.inputSchema else {
                                "type": "object",
                                "properties": {}
                            },
                        }
                    })

                _mcp_tool_schemas = schemas
                print(f"[MCP Client] Discovered {len(schemas)} tools via tools/list: "
                      f"{[s['function']['name'] for s in schemas]}")
                return schemas

    except Exception as e:
        print(f"[MCP Client] tools/list failed: {e}. Using cached schemas.")
        return _mcp_tool_schemas


async def call_mcp_tool(tool_name: str, tool_args: dict) -> str:
    """
    Execute a tool through the MCP client-server protocol.
    Not a direct function call — goes through MCP transport layer.
    """
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async with streamablehttp_client("http://localhost:8000/mcp") as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, tool_args)

                if result.content:
                    for content_item in result.content:
                        if hasattr(content_item, 'text'):
                            return content_item.text

                return json.dumps({"status": "error", "message": "Empty result from MCP tool"})

    except Exception as e:
        print(f"[MCP Client] Tool call failed for {tool_name}: {e}")
        return json.dumps({"status": "error", "message": str(e)})


def _get_or_create_session(session_id: Optional[str], role: str) -> tuple[str, list[dict]]:
    if session_id and session_id in _conversation_store:
        return session_id, _conversation_store[session_id]

    new_id = session_id or str(uuid.uuid4())
    from datetime import datetime
    today = datetime.now().strftime("%A, %B %d, %Y")
    system_prompt = PATIENT_SYSTEM_PROMPT if role == "patient" else DOCTOR_SYSTEM_PROMPT

    history = [{"role": "system", "content": f"{system_prompt}\n\nToday is {today}."}]
    _conversation_store[new_id] = history
    return new_id, history


async def run_agent(
    user_message: str,
    session_id: Optional[str],
    role: str,
    db: Session,
    patient_id: int = None,
    doctor_id: int = None,
) -> dict:
    """
    Run one turn of the agent using MCP client-server protocol.
    - Discovers tools dynamically via tools/list
    - Routes all tool calls through MCP client
    - GPT-4o drives the orchestration
    """
    from mcp_server import set_db
    set_db(db)

    session_id, history = _get_or_create_session(session_id, role)
    history.append({"role": "user", "content": user_message})

    # Dynamically discover tools from MCP server at runtime
    tool_schemas = await discover_tools_from_mcp()

    tool_calls_made = []
    booked_appointment_id = None
    reply = ""
    MAX_TOOL_ROUNDS = 5

    for _ in range(MAX_TOOL_ROUNDS):
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=history,
            tools=tool_schemas if tool_schemas else None,
            tool_choice="auto" if tool_schemas else None,
        )

        msg = response.choices[0].message

        if not msg.tool_calls:
            reply = msg.content or ""
            history.append({"role": "assistant", "content": reply})
            break

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

        # Execute each tool through MCP client protocol
        for tc in msg.tool_calls:
            fn_name = tc.function.name
            try:
                fn_args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                fn_args = {}

            # Inject context automatically — LLM never needs to ask for these
            if fn_name == "book_appointment" and patient_id:
                fn_args["patient_id"] = patient_id
            if fn_name == "cancel_appointment" and patient_id:
                fn_args["patient_id"] = patient_id
            if fn_name == "get_doctor_summary" and doctor_id:
                if "doctor_id" not in fn_args:
                    fn_args["doctor_id"] = doctor_id

            tool_calls_made.append(fn_name)

            # Route through MCP client — proper protocol, not direct call
            result = await call_mcp_tool(fn_name, fn_args)

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
        reply = "I've processed your request. Is there anything else I can help you with?"
        history.append({"role": "assistant", "content": reply})

    # Keep history bounded to last 30 messages
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
