

from mcp.server.fastmcp import FastMCP
from datetime import datetime, timedelta
from typing import Optional
import json

# Global db session injected at startup from main.py
_db_session = None

def set_db(db):
    global _db_session
    _db_session = db

def get_db():
    return _db_session


mcp = FastMCP(
    "Nidan MCP Server",
    streamable_http_path="/",
    instructions="""
    You are the Nidan medical appointment assistant.
    Use these tools to help patients book appointments and doctors get summaries.
    Never ask for doctor_id — it is always injected automatically.
    """
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _resolve_date_range(date_str: Optional[str]) -> tuple:
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


def _filter_by_time_preference(slots, pref: Optional[str]):
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
        else:
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
    return filtered or slots


# ── MCP Tools ─────────────────────────────────────────────────────────────────

@mcp.tool()
def list_doctors(specialization: Optional[str] = None) -> str:
    """
    List all available doctors in the system.
    Optionally filter by medical specialization (e.g. cardiologist, dermatologist).
    Returns doctor IDs, names, specializations, experience and fees.
    """
    from models.database import Doctor, User
    db = get_db()

    query = db.query(Doctor).join(User)
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
        ]
    })


@mcp.tool()
def check_doctor_availability(
    doctor_name: Optional[str] = None,
    specialization: Optional[str] = None,
    date_str: Optional[str] = None,
    time_preference: Optional[str] = None,
) -> str:
    """
    Check available appointment slots for a doctor.
    Use when patient wants to see availability or book an appointment.
    Search by doctor name (e.g. 'Dr. Ahuja') or specialization (e.g. 'cardiologist').
    date_str can be: 'today', 'tomorrow', 'friday', 'YYYY-MM-DD', or 'this week'.
    time_preference can be: 'morning', 'afternoon', 'evening', or '3 PM'.
    """
    from models.database import Doctor, User, AvailabilitySlot
    db = get_db()

    start_dt, end_dt = _resolve_date_range(date_str)

    query = db.query(Doctor).join(User)
    if doctor_name:
        query = query.filter(User.full_name.ilike(f"%{doctor_name}%"))
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))

    doctors = query.all()

    if not doctors:
        return json.dumps({
            "status": "not_found",
            "message": f"No doctor found matching '{doctor_name or specialization}'. Use list_doctors to see all."
        })

    results = []
    for doc in doctors:
        slots = db.query(AvailabilitySlot).filter(
            AvailabilitySlot.doctor_id == doc.id,
            AvailabilitySlot.is_available == True,
            AvailabilitySlot.slot_datetime >= start_dt,
            AvailabilitySlot.slot_datetime < end_dt,
        ).order_by(AvailabilitySlot.slot_datetime).all()

        slots = _filter_by_time_preference(slots, time_preference)

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
                for s in slots[:8]
            ],
        })

    return json.dumps({"status": "success", "doctors": results})


@mcp.tool()
def book_appointment(
    slot_id: int,
    doctor_id: int,
    patient_id: int,
    reason: Optional[str] = "General consultation",
) -> str:
    """
    Book a confirmed appointment for the patient.
    Only call this after patient has confirmed they want to book a specific slot.
    Requires slot_id and doctor_id from check_doctor_availability results.
    patient_id is automatically provided by the system.
    """
    from models.database import Doctor, User, AvailabilitySlot, Appointment, AppointmentStatus
    db = get_db()

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
    slot.is_available = False
    db.commit()
    db.refresh(appointment)

    return json.dumps({
        "status": "success",
        "appointment_id": appointment.id,
        "doctor": doctor.user.full_name,
        "specialization": doctor.specialization,
        "scheduled_at": slot.slot_datetime.strftime("%Y-%m-%d %H:%M"),
        "duration_minutes": slot.duration_minutes,
        "reason": reason,
    })


@mcp.tool()
def get_doctor_summary(
    doctor_id: int,
    period: str,
    filter_symptom: Optional[str] = None,
) -> str:
    """
    Get appointment statistics summary for a doctor.
    period must be one of: today, yesterday, tomorrow, this_week, last_week, this_month.
    Optionally filter by symptom keyword (e.g. 'fever', 'diabetes').
    doctor_id is automatically injected — never ask the user for it.
    """
    from models.database import Appointment, AppointmentStatus
    db = get_db()

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
        symptom_count = base_q.filter(
            Appointment.reason.ilike(f"%{filter_symptom}%")
        ).count()
        result["symptom_filter"] = filter_symptom
        result["symptom_count"] = symptom_count

    return json.dumps(result)


@mcp.tool()
def cancel_appointment(
    appointment_id: int,
    patient_id: int,
    reason: Optional[str] = "Cancelled by patient",
) -> str:
    """
    Cancel an existing appointment by appointment ID.
    patient_id is automatically provided by the system.
    """
    from models.database import Appointment, AppointmentStatus, AvailabilitySlot
    db = get_db()

    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient_id,
    ).first()

    if not appt:
        return json.dumps({"status": "error", "message": "Appointment not found or not yours."})

    if appt.status == AppointmentStatus.cancelled:
        return json.dumps({"status": "error", "message": "Already cancelled."})

    appt.status = AppointmentStatus.cancelled
    appt.notes = f"Cancelled: {reason}"

    if appt.slot_id:
        slot = db.query(AvailabilitySlot).filter(AvailabilitySlot.id == appt.slot_id).first()
        if slot:
            slot.is_available = True

    db.commit()
    return json.dumps({
        "status": "success",
        "message": f"Appointment #{appointment_id} cancelled successfully.",
    })
