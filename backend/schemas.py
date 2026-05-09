from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    patient = "patient"
    doctor = "doctor"


class AppointmentStatus(str, Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    rescheduled = "rescheduled"


# ── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int
    full_name: str


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    phone: Optional[str]

    class Config:
        from_attributes = True


# ── Doctor ──────────────────────────────────────────────────────────────────

class DoctorProfile(BaseModel):
    id: int
    user_id: int
    specialization: str
    qualification: Optional[str]
    experience_years: int
    consultation_fee: float
    bio: Optional[str]
    full_name: str
    email: str

    class Config:
        from_attributes = True


class AvailabilitySlotOut(BaseModel):
    id: int
    slot_datetime: datetime
    duration_minutes: int
    is_available: bool

    class Config:
        from_attributes = True


# ── Appointments ─────────────────────────────────────────────────────────────

class AppointmentCreate(BaseModel):
    doctor_id: int
    slot_id: Optional[int] = None
    scheduled_at: datetime
    reason: Optional[str] = None
    symptoms: Optional[str] = None


class AppointmentOut(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    scheduled_at: datetime
    status: str
    reason: Optional[str]
    symptoms: Optional[str]
    notes: Optional[str]
    google_event_id: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Chat / Agent ─────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    tool_calls_made: List[str] = []
    appointment_booked: Optional[AppointmentOut] = None


# ── Doctor Summary ───────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    query: str
    doctor_id: Optional[int] = None  # if None, infer from JWT


class SummaryResponse(BaseModel):
    summary: str
    notification_sent: bool
    notification_channel: str
