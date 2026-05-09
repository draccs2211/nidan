import os
import contextlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from models.database import get_db, create_tables, User, Doctor, AvailabilitySlot, Appointment
from schemas import (
    UserCreate, UserLogin, Token, ChatRequest, ChatResponse,
    SummaryRequest, SummaryResponse, AppointmentOut,
)
from auth import hash_password, verify_password, create_access_token, get_current_user, require_role
from agent import run_agent, clear_session, get_session_history
from integrations.slack import send_doctor_summary_to_slack
from mcp_server import mcp

from dotenv import load_dotenv
load_dotenv()


# ── Lifespan: starts DB + MCP session manager ────────────────────────────────

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    print("Database tables created/verified.")
    print("MCP Server mounted at /mcp")
    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title="Nidan — Agentic Doctor Appointment AI",
    description="MCP-powered agentic appointment system using GPT-4o + proper MCP protocol",
    version="2.0.0",
    lifespan=lifespan,
)

# Mount MCP server — exposes /mcp with tools/list and tools/call
app.mount("/mcp", mcp.streamable_http_app())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:5173"), "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=Token)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()

    if payload.role == "doctor":
        doctor = Doctor(
            user_id=user.id,
            specialization="General Medicine",
            experience_years=0,
            consultation_fee=500.0,
        )
        db.add(doctor)

    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
    )


@app.post("/auth/login", response_model=Token)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
    )


# ── Doctors ───────────────────────────────────────────────────────────────────

@app.get("/doctors")
def list_doctors(specialization: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(Doctor).join(User)
    if specialization:
        q = q.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    doctors = q.all()
    return [
        {
            "doctor_id": d.id,
            "name": d.user.full_name,
            "specialization": d.specialization,
            "experience_years": d.experience_years,
            "consultation_fee": d.consultation_fee,
            "bio": d.bio,
        }
        for d in doctors
    ]


@app.get("/doctors/{doctor_id}/slots")
def get_doctor_slots(doctor_id: int, db: Session = Depends(get_db)):
    now = datetime.now()
    slots = db.query(AvailabilitySlot).filter(
        AvailabilitySlot.doctor_id == doctor_id,
        AvailabilitySlot.is_available == True,
        AvailabilitySlot.slot_datetime >= now,
    ).order_by(AvailabilitySlot.slot_datetime).limit(20).all()

    return [
        {
            "slot_id": s.id,
            "datetime": s.slot_datetime.strftime("%Y-%m-%d %H:%M"),
            "duration_minutes": s.duration_minutes,
        }
        for s in slots
    ]


# ── Patient Chat ──────────────────────────────────────────────────────────────

@app.post("/chat/patient", response_model=ChatResponse)
async def patient_chat(
    req: ChatRequest,
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    result = await run_agent(
        user_message=req.message,
        session_id=req.session_id,
        role="patient",
        db=db,
        patient_id=current_user.id,
    )

    booked = None
    if result.get("booked_appointment_id"):
        appt = db.query(Appointment).filter(
            Appointment.id == result["booked_appointment_id"]
        ).first()
        if appt:
            booked = AppointmentOut.model_validate(appt)

    return ChatResponse(
        reply=result["reply"],
        session_id=result["session_id"],
        tool_calls_made=result["tool_calls_made"],
        appointment_booked=booked,
    )


# ── Doctor Chat ───────────────────────────────────────────────────────────────

@app.post("/chat/doctor", response_model=ChatResponse)
async def doctor_chat(
    req: ChatRequest,
    current_user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    result = await run_agent(
        user_message=req.message,
        session_id=req.session_id,
        role="doctor",
        db=db,
        doctor_id=doctor.id,
    )

    if "get_doctor_summary" in result.get("tool_calls_made", []):
        send_doctor_summary_to_slack(
            doctor_name=current_user.full_name,
            summary_text=result["reply"],
            period="queried",
        )

    return ChatResponse(
        reply=result["reply"],
        session_id=result["session_id"],
        tool_calls_made=result["tool_calls_made"],
    )


# ── Doctor Summary Button ─────────────────────────────────────────────────────

@app.post("/doctor/summary", response_model=SummaryResponse)
async def doctor_summary(
    req: SummaryRequest,
    current_user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    result = await run_agent(
        user_message=req.query,
        session_id=None,
        role="doctor",
        db=db,
        doctor_id=doctor.id,
    )

    notified = False
    if "get_doctor_summary" in result.get("tool_calls_made", []):
        notified = send_doctor_summary_to_slack(
            doctor_name=current_user.full_name,
            summary_text=result["reply"],
            period=req.query,
        )

    return SummaryResponse(
        summary=result["reply"],
        notification_sent=notified,
        notification_channel="Slack",
    )


# ── Appointments ──────────────────────────────────────────────────────────────

@app.get("/appointments/mine")
def my_appointments(
    current_user: User = Depends(require_role("patient")),
    db: Session = Depends(get_db),
):
    appts = db.query(Appointment).filter(
        Appointment.patient_id == current_user.id
    ).order_by(Appointment.scheduled_at.desc()).all()

    result = []
    for a in appts:
        doc = db.query(Doctor).filter(Doctor.id == a.doctor_id).first()
        result.append({
            "appointment_id": a.id,
            "doctor_name": doc.user.full_name if doc else "Unknown",
            "specialization": doc.specialization if doc else "",
            "scheduled_at": a.scheduled_at.strftime("%Y-%m-%d %H:%M"),
            "status": a.status,
            "reason": a.reason,
        })
    return result


@app.get("/doctor/appointments")
def doctor_appointments(
    current_user: User = Depends(require_role("doctor")),
    db: Session = Depends(get_db),
):
    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor profile not found.")

    now = datetime.now()
    appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.scheduled_at >= now - timedelta(days=1),
    ).order_by(Appointment.scheduled_at).all()

    result = []
    for a in appts:
        patient = db.query(User).filter(User.id == a.patient_id).first()
        result.append({
            "appointment_id": a.id,
            "patient_name": patient.full_name if patient else "Unknown",
            "patient_email": patient.email if patient else "",
            "scheduled_at": a.scheduled_at.strftime("%Y-%m-%d %H:%M"),
            "status": a.status,
            "reason": a.reason,
            "symptoms": a.symptoms,
        })
    return result


# ── Chat Session ──────────────────────────────────────────────────────────────

@app.get("/chat/history")
def chat_history(session_id: str, current_user: User = Depends(get_current_user)):
    history = get_session_history(session_id)
    return [m for m in history if m["role"] in ("user", "assistant")]


@app.delete("/chat/session")
def delete_session(session_id: str, current_user: User = Depends(get_current_user)):
    clear_session(session_id)
    return {"message": "Session cleared."}


# ── Seed Data ─────────────────────────────────────────────────────────────────

@app.post("/seed")
def seed_data(db: Session = Depends(get_db)):
    db.query(Appointment).delete()
    db.query(AvailabilitySlot).delete()
    db.query(Doctor).delete()
    db.query(User).delete()

    now = datetime.now()

    doctor_data = [
        ("Dr. Priya Ahuja",  "priya@clinic.com", "Cardiologist",    15, 800.0),
        ("Dr. Rahul Sharma", "rahul@clinic.com", "Dermatologist",    8, 600.0),
        ("Dr. Meena Gupta",  "meena@clinic.com", "General Medicine", 12, 400.0),
        ("Dr. Arjun Singh",  "arjun@clinic.com", "Orthopedic",       10, 700.0),
    ]

    for name, email, spec, exp, fee in doctor_data:
        user = User(
            email=email,
            hashed_password=hash_password("doctor123"),
            full_name=name,
            role="doctor",
            created_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

        doctor = Doctor(
            user_id=user.id,
            specialization=spec,
            experience_years=exp,
            consultation_fee=fee,
            bio=f"{exp} years of experience in {spec}.",
        )
        db.add(doctor)
        db.flush()

        for day_offset in range(7):
            for hour in [9, 10, 11, 14, 15, 16, 17]:
                slot_dt = (now + timedelta(days=day_offset)).replace(
                    hour=hour, minute=0, second=0, microsecond=0
                )
                db.add(AvailabilitySlot(
                    doctor_id=doctor.id,
                    slot_datetime=slot_dt,
                    duration_minutes=30,
                    is_available=True,
                ))

    patient = User(
        email="patient@test.com",
        hashed_password=hash_password("patient123"),
        full_name="Ravi Kumar",
        role="patient",
        created_at=datetime.utcnow(),
    )
    db.add(patient)
    db.commit()

    return {
        "message": "Seeded 4 doctors, 1 patient, 7x7 availability slots.",
        "patient_login": {"email": "patient@test.com", "password": "patient123"},
        "doctor_login": {"email": "priya@clinic.com", "password": "doctor123"},
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "Nidan Agentic AI", "mcp_endpoint": "/mcp"}
