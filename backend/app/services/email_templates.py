"""HTML e-mails in the look of the web app (MUI theme: blue #1565c0, Inter/Roboto, 8px radius).

Mail clients ignore <style> blocks and modern CSS, so the layout uses tables and
inline styles only; images (the QR ticket) are attached inline and referenced by cid.
"""

from dataclasses import dataclass
from html import escape

PRIMARY = "#1565c0"
PRIMARY_DARK = "#0d47a1"
PAGE_BG = "#f5f5f5"
CARD_BG = "#ffffff"
INK = "#1f2937"
MUTED = "#6b7280"
LINE = "#e5e7eb"
FONT = "Inter, Roboto, 'Segoe UI', Helvetica, Arial, sans-serif"
MONO = "'Roboto Mono', Consolas, 'Courier New', monospace"

# Chip shown above the event, like the status chips in the app: label, text, background.
STATUS_CHIPS = {
    "REGISTRATION_CONFIRMED": ("Confirmed", "#1b5e20", "#e8f5e9"),
    "WAITLIST_PROMOTED": ("Confirmed", "#1b5e20", "#e8f5e9"),
    "REGISTRATION_WAITLISTED": ("Waitlist", "#8a4b00", "#fff3e0"),
    "EVENT_REMINDER": ("Starting soon", PRIMARY_DARK, "#e3f2fd"),
    "EVENT_UPDATED": ("Updated", PRIMARY_DARK, "#e3f2fd"),
    "EVENT_CANCELLED": ("Cancelled", "#b71c1c", "#ffebee"),
    "EVENT_ANNOUNCEMENT": ("Announcement", "#4a148c", "#f3e5f5"),
    "FEEDBACK_REQUESTED": ("Feedback", "#4a148c", "#f3e5f5"),
    "TASK_ASSIGNED": ("New task", "#4a148c", "#f3e5f5"),
}


@dataclass
class EventInfo:
    title: str
    when: str
    location: str
    organization: str | None
    url: str


@dataclass
class TicketInfo:
    code: str  # short, human-readable reference (first part of the ticket id)
    qr_cid: str  # Content-ID of the inline QR image, without angle brackets
    url: str


def _button(label: str, url: str) -> str:
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto">
  <tr><td align="center" bgcolor="{PRIMARY}" style="border-radius:8px">
    <a href="{escape(url)}" style="display:inline-block;padding:12px 28px;font:600 15px/1.2 {FONT};
       color:#ffffff;text-decoration:none;border-radius:8px;letter-spacing:.2px">{escape(label)}</a>
  </td></tr>
</table>"""


def _detail_row(label: str, value: str) -> str:
    return f"""
<tr>
  <td style="padding:6px 0;width:92px;vertical-align:top;font:600 12px/1.5 {FONT};color:{MUTED};
      text-transform:uppercase;letter-spacing:.6px">{escape(label)}</td>
  <td style="padding:6px 0;font:15px/1.5 {FONT};color:{INK}">{escape(value)}</td>
</tr>"""


def render_notification_html(
    *,
    notification_type: str,
    title: str,
    message: str,
    app_url: str,
    event: EventInfo | None = None,
    ticket: TicketInfo | None = None,
) -> str:
    chip = STATUS_CHIPS.get(notification_type)
    chip_html = (
        f"""<span style="display:inline-block;padding:3px 10px;border-radius:999px;
            font:600 12px/1.6 {FONT};color:{chip[1]};background:{chip[2]}">{escape(chip[0])}</span>"""
        if chip
        else ""
    )

    event_html = ""
    if event is not None:
        rows = _detail_row("When", event.when) + _detail_row("Where", event.location)
        if event.organization:
            rows += _detail_row("Organizer", event.organization)
        event_html = f"""
<tr><td style="padding:0 32px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="border:1px solid {LINE};border-radius:8px">
    <tr><td style="padding:18px 20px 6px">
      {chip_html}
      <div style="margin-top:10px;font:700 20px/1.3 {FONT};color:{INK}">{escape(event.title)}</div>
    </td></tr>
    <tr><td style="padding:4px 20px 14px">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0">{rows}</table>
    </td></tr>
  </table>
</td></tr>"""

    ticket_html = ""
    if ticket is not None:
        ticket_html = f"""
<tr><td style="padding:24px 32px 0">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="background:#fafbfd;border:1px solid {LINE};border-radius:8px">
    <tr><td style="padding:14px 20px;font:600 12px/1.4 {FONT};color:{MUTED};
        text-transform:uppercase;letter-spacing:.8px">Your ticket
      <span style="float:right;font:600 13px/1.4 {MONO};color:{INK};letter-spacing:1px">#{escape(ticket.code)}</span>
    </td></tr>
    <tr><td style="border-top:2px dashed {LINE};padding:22px 20px 8px" align="center">
      <img src="cid:{escape(ticket.qr_cid)}" width="220" height="220" alt="QR ticket"
           style="display:block;width:220px;height:220px;border:0">
    </td></tr>
    <tr><td align="center" style="padding:6px 20px 20px;font:14px/1.5 {FONT};color:{MUTED}">
      Show this QR code at the entrance.<br>Organizers scan it to check you in.
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:24px 32px 0">{_button("Open ticket in the app", ticket.url)}</td></tr>"""
    elif event is not None:
        ticket_html = f"""<tr><td style="padding:24px 32px 0">{_button("Open event", event.url)}</td></tr>"""

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title></head>
<body style="margin:0;padding:0;background:{PAGE_BG}">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{PAGE_BG}">
<tr><td align="center" style="padding:24px 12px">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
         style="max-width:560px;background:{CARD_BG};border-radius:8px;overflow:hidden;
                box-shadow:0 1px 3px rgba(0,0,0,.12)">
    <tr><td bgcolor="{PRIMARY}" style="padding:18px 32px">
      <a href="{escape(app_url)}" style="font:700 20px/1.2 {FONT};color:#ffffff;text-decoration:none">UBB Events</a>
      <div style="font:13px/1.4 {FONT};color:#cfe0f5;margin-top:2px">Student organization events at Babeș-Bolyai University</div>
    </td></tr>
    <tr><td style="padding:28px 32px 20px">
      <div style="font:700 22px/1.3 {FONT};color:{INK}">{escape(title)}</div>
      <p style="margin:10px 0 0;font:15px/1.6 {FONT};color:{INK}">{escape(message)}</p>
    </td></tr>
    {event_html}
    {ticket_html}
    <tr><td style="padding:28px 32px 26px">
      <div style="border-top:1px solid {LINE};padding-top:16px;font:12px/1.6 {FONT};color:{MUTED}">
        You receive this e-mail because of your activity on
        <a href="{escape(app_url)}" style="color:{PRIMARY};text-decoration:none">UBB Events</a>.
        All your notifications are also in the app.
      </div>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>"""
