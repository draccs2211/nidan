from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, ForeignKey, Enum, Float
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import enum
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/doctor_appointment_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserRole(str, enum.Enum):
    patient = "patient"
    doctor = "doctor"


class AppointmentStatus(str, enum.Enum):
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"
    rescheduled = "rescheduled"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)

    # Relationships
    patient_appointments = relationship(
        "Appointment", back_populates="patient", foreign_keys="Appointment.patient_id"
    )
    doctor_profile = relationship("Doctor", back_populates="user", uselist=False)


class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialization = Column(String, nullable=False)
    qualification = Column(String, nullable=True)
    experience_years = Column(Integer, default=0)
    consultation_fee = Column(Float, default=0.0)
    bio = Column(Text, nullable=True)

    user = relationship("User", back_populates="doctor_profile")
    availability_slots = relationship("AvailabilitySlot", back_populates="doctor")
    appointments = relationship(
        "Appointment", back_populates="doctor", foreign_keys="Appointment.doctor_id"
    )


class AvailabilitySlot(Base):
    __tablename__ = "availability_slots"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_datetime = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    is_available = Column(Boolean, default=True)

    doctor = relationship("Doctor", back_populates="availability_slots")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    slot_id = Column(Integer, ForeignKey("availability_slots.id"), nullable=True)
    scheduled_at = Column(DateTime, nullable=False)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.scheduled)
    reason = Column(Text, nullable=True)
    symptoms = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    google_event_id = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=True)

    patient = relationship("User", back_populates="patient_appointments", foreign_keys=[patient_id])
    doctor = relationship("Doctor", back_populates="appointments", foreign_keys=[doctor_id])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    Base.metadata.create_all(bind=engine)
