import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


def get_gmail_service(token_info: dict):
    creds = Credentials(
        token=token_info["access_token"],
        refresh_token=token_info.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )
    return build("gmail", "v1", credentials=creds)


def send_confirmation_email(
    service,
    to_email: str,
    patient_name: str,
    doctor_name: str,
    appointment_dt: datetime,
    reason: str = "General consultation",
):
    sender = os.getenv("GMAIL_SENDER_EMAIL", "noreply@clinic.com")
    subject = f"Appointment Confirmed – {doctor_name}"

    dt_str = appointment_dt.strftime("%A, %B %d %Y at %I:%M %p")

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #e0e0e0; border-radius: 8px;">
      <h2 style="color: #2563eb;">Appointment Confirmed ✓</h2>
      <p>Dear <strong>{patient_name}</strong>,</p>
      <p>Your appointment has been successfully booked.</p>
      <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr>
          <td style="padding: 8px; background: #f9fafb; font-weight: bold; width: 40%;">Doctor</td>
          <td style="padding: 8px;">{doctor_name}</td>
        </tr>
        <tr>
          <td style="padding: 8px; background: #f9fafb; font-weight: bold;">Date & Time</td>
          <td style="padding: 8px;">{dt_str} IST</td>
        </tr>
        <tr>
          <td style="padding: 8px; background: #f9fafb; font-weight: bold;">Reason</td>
          <td style="padding: 8px;">{reason}</td>
        </tr>
      </table>
      <p style="color: #6b7280; font-size: 13px;">
        A Google Calendar invite has been sent separately. Please arrive 5 minutes early.
      </p>
      <p style="color: #6b7280; font-size: 13px;">— Clinic Appointment System</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        print(f"[Gmail] Confirmation sent to {to_email}")
    except Exception as e:
        print(f"[Gmail] Failed to send email: {e}")
