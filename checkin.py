"""Session/file check-in settings, pure decisions, and SMTP/practice delivery."""

from datetime import date, timedelta
from email.message import EmailMessage
import json
import os
from pathlib import Path
import smtplib
import ssl
import tempfile

STATE_PATH = Path(__file__).resolve().parent / "state" / "checkin_state.json"
STAGES = (("reminder_1", 150), ("reminder_2", 165), ("send_map", 180))
STAGE_LABELS = {
    "reminder_1": "Reminder 1", "reminder_2": "Reminder 2", "send_map": "Sent",
}
SMTP_KEYS = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD")
PDF_FILENAME = "Family_Wealth_Map.pdf"


def _date(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def decide(state, today):
    """Return one action without changing state or reading the clock/files/env.

    Dates may be ISO strings or date objects. The caller supplies the appropriate
    real or simulation stages_sent list.
    """
    paused_until = state.get("paused_until")
    if paused_until and today < _date(paused_until):
        return "paused"
    if not state.get("automatic_enabled", True):
        return "none"
    sent = state.get("stages_sent", [])
    if "send_map" in sent:
        return "none"
    days = (today - _date(state["last_check_in"])).days
    for stage, threshold in STAGES:
        if stage in sent:
            continue
        if days < threshold:
            return "none"
        if stage == "send_map":
            reminder_date = state.get("sent_on", {}).get("reminder_2")
            if not reminder_date or (today - _date(reminder_date)).days < 7:
                return "none"
        return stage
    return "none"


def next_stage(state, today):
    """Return the next eligible stage and its due date, allowing for a pause."""
    sent = state.get("stages_sent", [])
    if "send_map" in sent:
        return None, None
    if not state.get("automatic_enabled", True):
        return None, None
    last = _date(state["last_check_in"])
    paused_until = _date(state.get("paused_until"))
    resume = paused_until if paused_until and paused_until > today else None
    for stage, threshold in STAGES:
        if stage in sent:
            continue
        due = last + timedelta(days=threshold)
        if stage == "send_map":
            reminder_date = state.get("sent_on", {}).get("reminder_2")
            if not reminder_date:
                return stage, None
            due = max(due, _date(reminder_date) + timedelta(days=7))
        return stage, max(due, resume) if resume else due
    return None, None


def public_demo_enabled():
    """Default to a safe public demo; only an explicit false enables private mode."""
    return os.environ.get("PUBLIC_DEMO", "true").strip().lower() != "false"


def _initial_state(today, *, demo=False):
    return {
        "family_member_email": "meera@example.com" if demo else "",
        "owner_email": "arjun@example.com" if demo else "",
        "last_check_in": today.isoformat(), "paused_until": None,
        "stages_sent": [], "sent_on": {}, "automatic_enabled": False,
        "simulation": {"stages_sent": [], "sent_on": {}},
    }


def load_state(today, path=STATE_PATH, *, session_state=None):
    if public_demo_enabled():
        if session_state is None:
            raise ValueError("Public demo settings need a browser session.")
        return session_state.setdefault("checkin_settings_state", _initial_state(today, demo=True))
    path = Path(path)
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8")) or _initial_state(today)
        state.setdefault("automatic_enabled", False)
        state.setdefault("sent_on", {})
        state.setdefault("simulation", {"stages_sent": []})
        state["simulation"].setdefault("sent_on", {})
        return state
    state = _initial_state(today)
    save_state(state, path)
    return state


def save_state(state, path=STATE_PATH, *, session_state=None):
    """Persist settings and delivery dates, never PDF bytes or a PDF password."""
    if public_demo_enabled():
        if session_state is None:
            raise ValueError("Public demo settings need a browser session.")
        session_state["checkin_settings_state"] = state
        return
    path = Path(path)
    payload = {
        key: state[key] for key in (
            "family_member_email", "owner_email", "last_check_in",
            "paused_until", "stages_sent",
        )
    }
    payload["automatic_enabled"] = state.get("automatic_enabled", False)
    payload["sent_on"] = state.get("sent_on", {})
    payload["simulation"] = {
        "stages_sent": state["simulation"]["stages_sent"],
        "sent_on": state["simulation"].get("sent_on", {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, encoding="utf-8", delete=False,
        ) as output:
            temporary = Path(output.name)
            json.dump(payload, output, indent=2)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def smtp_configured():
    return not public_demo_enabled() and all(os.environ.get(key) for key in SMTP_KEYS)


def make_email(action, state, pdf=None, *, manual=False):
    """Compose emails without accepting or interpolating a PDF password."""
    if action == "send_map" and not pdf:
        raise ValueError("Create your map first in step 1.")
    owner_email = state["owner_email"].strip()
    if not owner_email:
        raise ValueError("Add your email in step 2 first.")
    message = EmailMessage()
    message["From"] = owner_email
    if action == "reminder_1":
        recipient = owner_email
        subject = "Family Wealth Navigator: please check in"
        body = "Please open the app and click I'm OK.\n\nYour family check-in is due."
    elif action == "reminder_2":
        recipient = owner_email
        subject = "Second reminder: your family check-in is overdue"
        body = (
            "Please open the app and click I'm OK as soon as possible.\n\n"
            "This is your final reminder. After 180 days without a check-in "
            "and at least 7 days after this reminder, your encrypted Family "
            "Wealth Map may be sent to your family member."
        )
    elif action == "send_map":
        recipient = state["family_member_email"].strip()
        if not recipient:
            raise ValueError("Add your family member's email in step 2 first.")
        subject = "Your encrypted Family Wealth Map"
        reason = (
            "The owner chose to share this guide with you now."
            if manual else
            "You received this because the owner has not checked in for at least 180 days."
        )
        body = (
            f"{reason}\n\n"
            "The attached Family Wealth Map is a practical guide to finding "
            "and accessing the family's holdings when the owner is unavailable.\n\n"
            "The PDF is encrypted. Its password was shared separately "
            "and is not included in this email."
        )
    else:
        raise ValueError("This action does not send an email.")
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)
    if action == "send_map":
        message.add_attachment(
            pdf, maintype="application", subtype="pdf", filename=PDF_FILENAME,
        )
    return message


def deliver_email(message, *, simulate=False):
    """Return dry-run details or send with SMTP; failures never become dry-runs."""
    attachments = list(message.iter_attachments())
    preview = {
        "to": str(message["To"]), "subject": str(message["Subject"]),
        "body": message.get_body(preferencelist=("plain",)).get_content(),
        "attachment_name": attachments[0].get_filename() if attachments else None,
    }
    if public_demo_enabled() or simulate or not smtp_configured():
        return {"mode": "dry-run", **preview}
    try:
        port = int(os.environ["SMTP_PORT"])
    except ValueError:
        raise ValueError("Email sending isn't set up correctly. Check the email port setting.") from None
    context = ssl.create_default_context()
    host = os.environ["SMTP_HOST"]
    if port == 465:
        connection = smtplib.SMTP_SSL(host, port, timeout=30, context=context)
    else:
        connection = smtplib.SMTP(host, port, timeout=30)
    with connection as smtp:
        if port != 465:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
        smtp.login(os.environ["SMTP_USER"], os.environ["SMTP_PASSWORD"])
        if smtp.send_message(message):
            raise smtplib.SMTPException("Not all recipients accepted the email.")
    return {"mode": "SMTP", **preview}
