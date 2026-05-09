import os
import httpx
from datetime import datetime


SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")


def send_doctor_summary_to_slack(
    doctor_name: str,
    summary_text: str,
    period: str = "today",
    stats: dict = None,
) -> bool:
    """
    Send a rich Slack notification with the doctor's appointment summary.
    Uses Slack Block Kit for a clean formatted message.
    """
    if not SLACK_WEBHOOK_URL:
        print("[Slack] SLACK_WEBHOOK_URL not configured.")
        return False

    stats = stats or {}
    now_str = datetime.now().strftime("%B %d, %Y %I:%M %p")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Appointment Summary — {doctor_name}",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Period: *{period.replace('_', ' ').title()}* | Generated: {now_str}",
                }
            ],
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary_text},
        },
    ]

    # Add stats breakdown if available
    if stats:
        fields = []
        mapping = {
            "total_appointments": "Total",
            "scheduled": "Scheduled",
            "completed": "Completed",
            "cancelled": "Cancelled",
            "upcoming_in_period": "Upcoming",
        }
        for key, label in mapping.items():
            if key in stats:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{label}*\n{stats[key]}",
                })
        if fields:
            blocks.append({"type": "section", "fields": fields[:6]})

    if stats.get("symptom_filter"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔍 Patients with *{stats['symptom_filter']}*: {stats.get('symptom_count', 0)}",
            },
        })

    payload = {"blocks": blocks}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(SLACK_WEBHOOK_URL, json=payload)
            if resp.status_code == 200:
                print("[Slack] Notification sent.")
                return True
            else:
                print(f"[Slack] Failed: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        print(f"[Slack] Error: {e}")
        return False
