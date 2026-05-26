import uuid
import qrcode
import io
import base64
import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, session, send_file, jsonify
from database import (
    get_all_events_with_stats, get_event_by_id,
    save_ticket, get_user_tickets
)
from auth import login_required
from main import generate_ticket, OUTPUT_DIR

events = Blueprint("events", __name__)


def _is_ticket_expired(event_date_raw):
    if not event_date_raw:
        return False
    now = datetime.now()
    for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            event_dt = datetime.strptime(event_date_raw.strip(), fmt)
            return event_dt < now
        except ValueError:
            continue
    return False

# ───────────────────────── афиша ───────────────────────────────────

@events.route("/")
def index():
    # Fixes N+1: Single query for all events and counts
    all_events = get_all_events_with_stats()

    for event in all_events:
        event["available"] = event["capacity"] - event["sold"]
        event["is_full"] = event["available"] <= 0
        event["percent"] = round(event["sold"] / event["capacity"] * 100) if event["capacity"] else 0

    return render_template("index.html", events=all_events)

# ───────────────────────── страница события ─────────────────────────

@events.route("/event/<int:event_id>")
def event_page(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("events.index"))

    # Stats for the specific event
    from database import get_event_tickets_count
    sold = get_event_tickets_count(event_id)
    event["sold"] = sold
    event["available"] = event["capacity"] - sold
    event["is_full"] = event["available"] <= 0

    user_has_ticket = False
    if "user_id" in session:
        user_tickets = get_user_tickets(session["user_id"])
        user_has_ticket = any(t["event_id"] == event_id for t in user_tickets)

    return render_template("event.html",
                           event=event,
                           user_has_ticket=user_has_ticket)

# ───────────────────────── получить билет ──────────────────────────

@events.route("/event/<int:event_id>/buy", methods=["POST"])
@login_required
def buy_ticket(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("events.index"))

    user_tickets = get_user_tickets(session["user_id"])
    if any(t["event_id"] == event_id for t in user_tickets):
        flash("У вас уже есть билет на это мероприятие", "error")
        return redirect(url_for("events.event_page", event_id=event_id))

    ticket_id = str(uuid.uuid4())
    # Database handles capacity and race conditions in save_ticket
    success = save_ticket(ticket_id, user_id=session["user_id"], event_id=event_id)

    if not success:
        flash("К сожалению, билеты закончились", "error")
        return redirect(url_for("events.event_page", event_id=event_id))

    try:
        generate_ticket(ticket_id=ticket_id, event=event)
        flash("Билет успешно получен!", "success")
    except Exception as e:
        flash("Билет создан, но PDF не сгенерировался", "error")
        print(f"Ошибка генерации PDF: {e}")

    return redirect(url_for("events.cabinet"))

# ───────────────────────── личный кабинет ──────────────────────────

@events.route("/cabinet")
@login_required
def cabinet():
    tickets = get_user_tickets(session["user_id"])

    for ticket in tickets:
        # Generate QR code for display
        qr = qrcode.make(ticket["ticket_id"])
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        ticket["qr_base64"] = base64.b64encode(buffer.getvalue()).decode()

        # Date Parsing and Expiration check
        ticket["is_expired"] = _is_ticket_expired(ticket.get("event_date"))

    return render_template("cabinet.html", tickets=tickets)


@events.route("/cabinet/status")
@login_required
def cabinet_status():
    tickets = get_user_tickets(session["user_id"])
    payload = []
    for ticket in tickets:
        payload.append({
            "ticket_id": ticket["ticket_id"],
            "used": bool(ticket["used"]),
            "is_expired": _is_ticket_expired(ticket.get("event_date")),
        })
    return jsonify({"tickets": payload})

# ───────────────────────── скачать PDF ─────────────────────────────

@events.route("/ticket/<ticket_id>/pdf")
@login_required
def download_ticket(ticket_id):
    user_tickets = get_user_tickets(session["user_id"])
    ticket = next((t for t in user_tickets if t["ticket_id"] == ticket_id), None)

    if ticket is None:
        flash("Билет не найден", "error")
        return redirect(url_for("events.cabinet"))

    # Caching check in generate_ticket automatically handles existence
    event = get_event_by_id(ticket["event_id"]) if ticket["event_id"] else None
    pdf_path = generate_ticket(ticket_id=ticket_id, event=event)

    return send_file(pdf_path, as_attachment=True,
                     download_name=f"ticket_{ticket_id[:8]}.pdf")
