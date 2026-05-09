"""
MCP Tool Registry
-----------------
Each tool is defined as an OpenAI-compatible function schema + a Python handler.
The agent (agent.py) passes these schemas to GPT-4o's `tools` param and
calls the matching handler when the model requests a tool invocation.
"""

import json
from datetime import datetime, timedelta
from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import func


from models.database import (
    User, Doctor, AvailabilitySlot, Appointment,
    AppointmentStatus
)




# ── Tool schemas (OpenAI function-calling format) ────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "check_doctor_availability",
            "description": (
                "Check available appointment slots for a doctor. "
                "Use when the patient wants to see availability or book an appointment. "
                "Can search by doctor name or specialization."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {
                        "type": "string",
                        "description": "Full or partial name of the doctor, e.g. 'Dr. Ahuja' or 'Ahuja'",
                    },
                    "specialization": {
                        "type": "string",
                        "description": "Medical specialization, e.g. 'cardiologist', 'dermatologist'",
                    },
                    "date_str": {
                        "type": "string",
                        "description": (
                            "Date in YYYY-MM-DD format, or natural words like "
                            "'today', 'tomorrow', 'friday', 'this week'"
                        ),
                    },
                    "time_preference": {
                        "type": "string",
                        "description": "Time preference: 'morning', 'afternoon', 'evening', or a specific time like '3 PM'",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book a confirmed appointment for the patient with a specific doctor at a specific slot. "
                "Only call this after the patient has confirmed they want to book."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_id": {
                        "type": "integer",
                        "description": "The availability slot ID returned by check_doctor_availability",
                    },
                    "doctor_id": {
                        "type": "integer",
                        "description": "Doctor's ID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for visit / symptoms mentioned by the patient",
                    },
                },
                "required": ["slot_id", "doctor_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_summary",
            "description": (
                "Get a statistical summary/report for a doctor about their appointments. "
                "Use for queries like 'how many patients today', 'appointments this week', "
                "'patients with fever', 'yesterday's count', etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id": {
                        "type": "integer",
                        "description": "The doctor's ID",
                    },
                    "period": {
                        "type": "string",
                        "enum": ["today", "yesterday", "tomorrow", "this_week", "last_week", "this_month"],
                        "description": "Time period for the summary",
                    },
                    "filter_symptom": {
                        "type": "string",
                        "description": "Filter by symptom keyword, e.g. 'fever', 'diabetes', 'cold'",
                    },
                },
                "required": ["doctor_id", "period"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_doctors",
            "description": "List all available doctors, optionally filtered by specialization.",
            "parameters": {
                "type": "object",
                "properties": {
                    "specialization": {
                        "type": "string",
                        "description": "Filter by specialization keyword",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_appointment",
            "description": "Cancel an existing appointment by appointment ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {
                        "type": "integer",
                        "description": "ID of the appointment to cancel",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for cancellation",
                    },
                },
                "required": ["appointment_id"],
            },
        },
    },
]


# ── Helper: resolve date string to a date range ──────────────────────────────
def _resolve_date_range(date_str: str | None) -> tuple[datetime, datetime]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if not date_str:
        return today_start, today_start + timedelta(days=7)

    ds = date_str.lower().strip()

    if ds == "today":
        return today_start, today_start + timedelta(days=1)
    if ds == "tomorrow":
        d = today_start + timedelta(days=1)
        return d, d + timedelta(days=1)
    if ds == "yesterday":
        d = today_start - timedelta(days=1)
        return d, d + timedelta(days=1)
    if ds in ("this week", "this_week"):
        return today_start, today_start + timedelta(days=7)
    if ds in ("last week", "last_week"):
        return today_start - timedelta(days=7), today_start
    if ds == "this_month":
        return today_start.replace(day=1), today_start + timedelta(days=30)

    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    if ds in days:
        target_dow = days.index(ds)
        current_dow = now.weekday()
        delta = (target_dow - current_dow) % 7 or 7
        d = today_start + timedelta(days=delta)
        return d, d + timedelta(days=1)

    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d, d + timedelta(days=1)
    except ValueError:
        return today_start, today_start + timedelta(days=7)


def _filter_by_time_preference(slots, pref: str | None):
    if not pref:
        return slots
    pref = pref.lower()
    filtered = []
    for s in slots:
        h = s.slot_datetime.hour
        if "morning" in pref and 6 <= h < 12:
            filtered.append(s)
        elif "afternoon" in pref and 12 <= h < 17:
            filtered.append(s)
        elif "evening" in pref and 17 <= h < 21:
            filtered.append(s)
        elif "night" in pref and (h >= 21 or h < 6):
            filtered.append(s)
        else:
            # try specific time like "3 pm", "15:00"
            try:
                import re
                m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", pref)
                if m:
                    hour = int(m.group(1))
                    ampm = m.group(3)
                    if ampm == "pm" and hour != 12:
                        hour += 12
                    if ampm == "am" and hour == 12:
                        hour = 0
                    if abs(h - hour) <= 1:
                        filtered.append(s)
            except Exception:
                filtered.append(s)
    return filtered or slots  # fallback to all if nothing matches


# ── Tool Handlers ─────────────────────────────────────────────────────────────

def handle_check_doctor_availability(args: dict, db: Session, patient_id: int = None) -> str:
    doctor_name = args.get("doctor_name", "")
    specialization = args.get("specialization", "")
    date_str = args.get("date_str")
    time_pref = args.get("time_preference")

    start_dt, end_dt = _resolve_date_range(date_str)

    # Find matching doctors
    query = db.query(Doctor).join(User, Doctor.user_id == User.id)

    if doctor_name:
        query = query.filter(User.full_name.ilike(f"%{doctor_name}%"))
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))

    doctors = query.all()

    if not doctors:
        return json.dumps({
            "status": "not_found",
            "message": f"No doctor found matching '{doctor_name or specialization}'. Use list_doctors to see available doctors."
        })

    results = []
    for doc in doctors:
        slots = db.query(AvailabilitySlot).filter(
            AvailabilitySlot.doctor_id == doc.id,
            AvailabilitySlot.is_available == True,
            AvailabilitySlot.slot_datetime >= start_dt,
            AvailabilitySlot.slot_datetime < end_dt,
        ).order_by(AvailabilitySlot.slot_datetime).all()

        slots = _filter_by_time_preference(slots, time_pref)

        results.append({
            "doctor_id": doc.id,
            "doctor_name": doc.user.full_name,
            "specialization": doc.specialization,
            "consultation_fee": doc.consultation_fee,
            "available_slots": [
                {
                    "slot_id": s.id,
                    "datetime": s.slot_datetime.strftime("%Y-%m-%d %H:%M"),
                    "duration_minutes": s.duration_minutes,
                }
                for s in slots[:8]  # cap at 8 slots per doctor
            ],
        })

    return json.dumps({"status": "success", "doctors": results})


def handle_book_appointment(
    args: dict, db: Session, patient_id: int,
    calendar_service=None, gmail_service=None
) -> str:
    slot_id = args.get("slot_id")
    doctor_id = args.get("doctor_id")
    reason = args.get("reason", "General consultation")

    slot = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.id == slot_id,
        AvailabilitySlot.is_available == True,
    ).first()

    if not slot:
        return json.dumps({"status": "error", "message": "Slot not available or already booked."})

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    patient = db.query(User).filter(User.id == patient_id).first()

    if not doctor or not patient:
        return json.dumps({"status": "error", "message": "Doctor or patient not found."})

    # Create appointment
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        slot_id=slot_id,
        scheduled_at=slot.slot_datetime,
        status=AppointmentStatus.scheduled,
        reason=reason,
        created_at=datetime.utcnow(),
    )
    db.add(appointment)

    # Mark slot unavailable
    slot.is_available = False
    db.flush()

    google_event_id = None

    # Google Calendar integration
    if calendar_service:
        try:
            from integrations.calendar import create_calendar_event
            google_event_id = create_calendar_event(
                service=calendar_service,
                title=f"Appointment: {patient.full_name} with {doctor.user.full_name}",
                start_dt=slot.slot_datetime,
                duration_minutes=slot.duration_minutes,
                description=f"Reason: {reason}\nPatient: {patient.email}",
                attendees=[patient.email, doctor.user.email],
            )
            appointment.google_event_id = google_event_id
        except Exception as e:
            pass  # don't fail booking if Calendar fails

    db.commit()
    db.refresh(appointment)

    # Gmail confirmation to patient
    if gmail_service:
        try:
            from integrations.gmail import send_confirmation_email
            send_confirmation_email(
                service=gmail_service,
                to_email=patient.email,
                patient_name=patient.full_name,
                doctor_name=doctor.user.full_name,
                appointment_dt=slot.slot_datetime,
                reason=reason,
            )
        except Exception:
            pass

    return json.dumps({
        "status": "success",
        "appointment_id": appointment.id,
        "doctor": doctor.user.full_name,
        "specialization": doctor.specialization,
        "scheduled_at": slot.slot_datetime.strftime("%Y-%m-%d %H:%M"),
        "duration_minutes": slot.duration_minutes,
        "reason": reason,
        "confirmation_email_sent": gmail_service is not None,
        "calendar_event_created": google_event_id is not None,
    })


def handle_get_doctor_summary(args: dict, db: Session) -> str:
    doctor_id = args.get("doctor_id")
    period = args.get("period", "today")
    filter_symptom = args.get("filter_symptom", "")

    start_dt, end_dt = _resolve_date_range(period)

    base_q = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.scheduled_at >= start_dt,
        Appointment.scheduled_at < end_dt,
    )

    total = base_q.count()
    scheduled = base_q.filter(Appointment.status == AppointmentStatus.scheduled).count()
    completed = base_q.filter(Appointment.status == AppointmentStatus.completed).count()
    cancelled = base_q.filter(Appointment.status == AppointmentStatus.cancelled).count()

    symptom_count = 0
    if filter_symptom:
        symptom_count = base_q.filter(
            Appointment.symptoms.ilike(f"%{filter_symptom}%") |
            Appointment.reason.ilike(f"%{filter_symptom}%")
        ).count()

    # Upcoming slots count
    now = datetime.now()
    upcoming = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.scheduled_at >= now,
        Appointment.scheduled_at < end_dt,
        Appointment.status == AppointmentStatus.scheduled,
    ).count()

    result = {
        "status": "success",
        "period": period,
        "total_appointments": total,
        "scheduled": scheduled,
        "completed": completed,
        "cancelled": cancelled,
        "upcoming_in_period": upcoming,
    }

    if filter_symptom:
        result["symptom_filter"] = filter_symptom
        result["symptom_count"] = symptom_count

    return json.dumps(result)


def handle_list_doctors(args: dict, db: Session) -> str:
    specialization = args.get("specialization", "")

    query = db.query(Doctor).join(User, Doctor.user_id == User.id)
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))

    doctors = query.all()
    return json.dumps({
        "status": "success",
        "doctors": [
            {
                "doctor_id": d.id,
                "name": d.user.full_name,
                "specialization": d.specialization,
                "experience_years": d.experience_years,
                "consultation_fee": d.consultation_fee,
            }
            for d in doctors
        ],
    })


def handle_cancel_appointment(args: dict, db: Session, patient_id: int) -> str:
    appointment_id = args.get("appointment_id")
    reason = args.get("reason", "Cancelled by patient")

    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient_id,
    ).first()

    if not appt:
        return json.dumps({"status": "error", "message": "Appointment not found or not yours."})

    if appt.status == AppointmentStatus.cancelled:
        return json.dumps({"status": "error", "message": "Appointment already cancelled."})

    appt.status = AppointmentStatus.cancelled
    appt.notes = f"Cancelled: {reason}"

    # Free the slot
    if appt.slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == appt.slot_id).first()
        if slot:
            slot.is_available = True

    db.commit()
    return json.dumps({
        "status": "success",
        "message": f"Appointment #{appointment_id} cancelled successfully.",
    })


# ── Dispatcher ────────────────────────────────────────────────────────────────

def dispatch_tool(
    tool_name: str,
    args: dict,
    db: Session,
    patient_id: int = None,
    doctor_id: int = None,
    calendar_service=None,
    gmail_service=None,
) -> tuple[str, str]:
    """
    Calls the right handler and returns (tool_name, result_json).
    """
    if tool_name == "check_doctor_availability":
        result = handle_check_doctor_availability(args, db, patient_id)
    elif tool_name == "book_appointment":
        result = handle_book_appointment(args, db, patient_id, calendar_service, gmail_service)
    elif tool_name == "get_doctor_summary":
        if doctor_id and "doctor_id" not in args:
            args["doctor_id"] = doctor_id
        result = handle_get_doctor_summary(args, db)
    elif tool_name == "list_doctors":
        result = handle_list_doctors(args, db)
    elif tool_name == "cancel_appointment":
        result = handle_cancel_appointment(args, db, patient_id)
    else:
        result = json.dumps({"status": "error", "message": f"Unknown tool: {tool_name}"})

    return tool_name, result
