import uuid
import qrcode
import io
import base64
from flask import Blueprint, render_template, redirect, url_for, flash, session, send_file, jsonify
from app.database import (
    get_all_events_with_stats, get_event_by_id,
    save_ticket, get_user_tickets, is_event_expired
)
from app.auth import login_required
from app.ticket import generate_ticket

events = Blueprint("events", __name__)


def _is_ticket_expired(event_date_raw):
    return is_event_expired(event_date_raw)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ð°Ñ„Ð¸ÑˆÐ° â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@events.route("/")
def index():
    # Fixes N+1: Single query for all events and counts
    all_events = get_all_events_with_stats()

    for event in all_events:
        event["available"] = event["capacity"] - event["sold"]
        event["is_full"] = event["available"] <= 0
        event["percent"] = round(event["sold"] / event["capacity"] * 100) if event["capacity"] else 0

    return render_template("index.html", events=all_events)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ÑÑ‚Ñ€Ð°Ð½Ð¸Ñ†Ð° ÑÐ¾Ð±Ñ‹Ñ‚Ð¸Ñ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@events.route("/event/<int:event_id>")
def event_page(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("ÐœÐµÑ€Ð¾Ð¿Ñ€Ð¸ÑÑ‚Ð¸Ðµ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾", "error")
        return redirect(url_for("events.index"))

    # Stats for the specific event
    from app.database import get_event_tickets_count
    sold = get_event_tickets_count(event_id)
    event["sold"] = sold
    event["available"] = event["capacity"] - sold
    event["is_full"] = event["available"] <= 0

    return render_template("event.html", event=event)

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ð¿Ð¾Ð»ÑƒÑ‡Ð¸Ñ‚ÑŒ Ð±Ð¸Ð»ÐµÑ‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@events.route("/event/<int:event_id>/buy", methods=["POST"])
@login_required
def buy_ticket(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("ÐœÐµÑ€Ð¾Ð¿Ñ€Ð¸ÑÑ‚Ð¸Ðµ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½Ð¾", "error")
        return redirect(url_for("events.index"))

    ticket_id = str(uuid.uuid4())
    result = save_ticket(ticket_id, user_id=session["user_id"], event_id=event_id)

    if result == "full":
        flash("Ðš ÑÐ¾Ð¶Ð°Ð»ÐµÐ½Ð¸ÑŽ, Ð±Ð¸Ð»ÐµÑ‚Ñ‹ Ð·Ð°ÐºÐ¾Ð½Ñ‡Ð¸Ð»Ð¸ÑÑŒ", "error")
        return redirect(url_for("events.event_page", event_id=event_id))
    if result != "success":
        flash("ÐÐµ ÑƒÐ´Ð°Ð»Ð¾ÑÑŒ ÑÐ¾Ð·Ð´Ð°Ñ‚ÑŒ Ð±Ð¸Ð»ÐµÑ‚. ÐŸÐ¾Ð¿Ñ€Ð¾Ð±ÑƒÐ¹Ñ‚Ðµ ÐµÑ‰Ñ‘ Ñ€Ð°Ð·.", "error")
        return redirect(url_for("events.event_page", event_id=event_id))

    try:
        generate_ticket(ticket_id=ticket_id, event=event)
        flash("Ð‘Ð¸Ð»ÐµÑ‚ ÑƒÑÐ¿ÐµÑˆÐ½Ð¾ Ð¿Ð¾Ð»ÑƒÑ‡ÐµÐ½!", "success")
    except Exception as e:
        flash("Ð‘Ð¸Ð»ÐµÑ‚ ÑÐ¾Ð·Ð´Ð°Ð½, Ð½Ð¾ PDF Ð½Ðµ ÑÐ³ÐµÐ½ÐµÑ€Ð¸Ñ€Ð¾Ð²Ð°Ð»ÑÑ", "error")
        print(f"ÐžÑˆÐ¸Ð±ÐºÐ° Ð³ÐµÐ½ÐµÑ€Ð°Ñ†Ð¸Ð¸ PDF: {e}")

    return redirect(url_for("events.cabinet"))

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Ð»Ð¸Ñ‡Ð½Ñ‹Ð¹ ÐºÐ°Ð±Ð¸Ð½ÐµÑ‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


@events.route("/profile")
@login_required
def profile():
    tickets = get_user_tickets(session["user_id"])
    active_count = sum(1 for ticket in tickets if not ticket["used"] and not _is_ticket_expired(ticket.get("event_date")))
    used_count = sum(1 for ticket in tickets if ticket["used"])
    return render_template(
        "profile.html",
        tickets_count=len(tickets),
        active_count=active_count,
        used_count=used_count,
    )


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

# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ ÑÐºÐ°Ñ‡Ð°Ñ‚ÑŒ PDF â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@events.route("/ticket/<ticket_id>/pdf")
@login_required
def download_ticket(ticket_id):
    user_tickets = get_user_tickets(session["user_id"])
    ticket = next((t for t in user_tickets if t["ticket_id"] == ticket_id), None)

    if ticket is None:
        flash("Ð‘Ð¸Ð»ÐµÑ‚ Ð½Ðµ Ð½Ð°Ð¹Ð´ÐµÐ½", "error")
        return redirect(url_for("events.cabinet"))

    # Caching check in generate_ticket automatically handles existence
    event = get_event_by_id(ticket["event_id"]) if ticket["event_id"] else None
    pdf_path = generate_ticket(ticket_id=ticket_id, event=event)

    return send_file(pdf_path, as_attachment=True,
                     download_name=f"ticket_{ticket_id[:8]}.pdf")
