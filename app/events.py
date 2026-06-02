import uuid
import qrcode
import io
import base64
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, session, send_file, jsonify, request
from flask_wtf.csrf import generate_csrf
from app.database import (
    get_all_events_with_stats, get_event_by_id,
    save_ticket, get_user_tickets, is_event_expired,
    parse_event_datetime, get_event_categories, get_event_locations
)
from app.auth import login_required
from app.ticket import generate_ticket

events = Blueprint("events", __name__)


def _is_ticket_expired(event_date_raw):
    return is_event_expired(event_date_raw)

# ---------------------------------------- афиша ----------------------------------------

@events.route("/")
def index():
    events_list = get_all_events_with_stats()
    for event in events_list:
        event["available"] = event["capacity"] - event.get("sold", 0)
        event["is_full"] = event["available"] <= 0
        event["percent"] = round(event.get("sold", 0) / event["capacity"] * 100) if event["capacity"] else 0

    categories = get_event_categories()
    locations = get_event_locations()
    return render_template("index.html", events=events_list, categories=categories, locations=locations)

@events.route("/spa")
@events.route("/spa-react")
def react_spa():
    # Redirect SPA routes back to the Jinja-based frontend
    return redirect(url_for("events.index"))


# ---------------------------------------- страница события ----------------------------------------

@events.route("/event/<int:event_id>")
def event_page(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("events.index"))

    # Stats for the specific event
    from app.database import get_event_tickets_count
    sold = get_event_tickets_count(event_id)
    event["sold"] = sold
    event["available"] = event["capacity"] - sold
    event["is_full"] = event["available"] <= 0

    return render_template("event.html", event=event)

# ---------------------------------------- получить билет ----------------------------------------

@events.route("/event/<int:event_id>/buy", methods=["POST"])
@login_required
def buy_ticket(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("events.index"))

    ticket_id = str(uuid.uuid4())
    result = save_ticket(ticket_id, user_id=session["user_id"], event_id=event_id)

    if result == "full":
        flash("К сожалению, билеты закончились", "error")
        return redirect(url_for("events.event_page", event_id=event_id))
    if result != "success":
        flash("Не удалось создать билет. Попробуйте ещё раз.", "error")
        return redirect(url_for("events.event_page", event_id=event_id))

    try:
        generate_ticket(ticket_id=ticket_id, event=event)
        flash("Билет успешно получен!", "success")
    except Exception as e:
        flash("Билет создан, но PDF не сгенерировался", "error")
        print(f"Ошибка генерации PDF: {e}")

    return redirect(url_for("events.cabinet"))

# ---------------------------------------- личный кабинет ----------------------------------------

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

# ---------------------------------------- скачать PDF ----------------------------------------

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


# ----------------------------- SPA + API ---------------------------------



@events.route("/api/events", methods=["GET"])
def api_get_events():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    date_filter = request.args.get("date", "all").strip().lower()

    filters = {}
    if q:
        filters["q"] = q
    if category and category.lower() != "all":
        filters["category"] = category
    if location and location.lower() != "all":
        filters["location"] = location

    events_list = get_all_events_with_stats(filters)
    payload = []
    for event in events_list:
        dt = parse_event_datetime(event.get("date"))
        event["datetime"] = dt.isoformat() if dt else None
        event["available"] = event["capacity"] - event.get("sold", 0)
        event["is_full"] = event["available"] <= 0
        event["percent"] = round(event.get("sold", 0) / event["capacity"] * 100) if event["capacity"] else 0
        cover = event.get("cover_image")
        if cover:
            try:
                event["cover_url"] = url_for("static", filename=f"event_covers/{cover}")
            except Exception:
                event["cover_url"] = None
        else:
            event["cover_url"] = None
        payload.append(event)

    return jsonify({"events": payload})


@events.route('/api/csrf', methods=['GET'])
def api_csrf():
    try:
        token = generate_csrf()
        return jsonify({'csrf_token': token})
    except Exception:
        return jsonify({'csrf_token': None}), 500



 
@events.route("/api/events", methods=["POST"])
def api_create_event():
    # import admin_required and savers lazily to avoid circular imports
    from app.auth import admin_required as _admin_required
    from functools import wraps

    # wrap actual handler to enforce admin check
    def handler():
        values = {
            'title': request.form.get('title', '').strip(),
            'description': request.form.get('description', '').strip(),
            'date': request.form.get('date', '').strip(),
            'location': request.form.get('location', '').strip(),
            'category': request.form.get('category', '').strip(),
            'capacity': request.form.get('capacity', '100').strip(),
            'card_bg': request.form.get('card_bg', '#fdfdf5').strip(),
            'card_accent': request.form.get('card_accent', '#a898e0').strip(),
            'card_text': request.form.get('card_text', '#2a2a2a').strip(),
        }

        if not values['title'] or not values['date']:
            return jsonify({'ok': False, 'message': 'Название и дата обязательны'}), 400
        if parse_event_datetime(values['date']) is None:
            return jsonify({'ok': False, 'message': 'Неверный формат даты'}), 400

        try:
            capacity = int(values['capacity'])
            if capacity <= 0:
                raise ValueError
        except ValueError:
            return jsonify({'ok': False, 'message': 'Вместимость должна быть положительным числом'}), 400

        template_file = request.files.get('ticket_template')
        cover_file = request.files.get('cover_image')

        # savers live in admin module
        from app.admin import _save_ticket_template, _save_cover_image

        ticket_template = None
        if template_file and template_file.filename:
            ticket_template = _save_ticket_template(template_file)

        cover_image = None
        if cover_file and cover_file.filename:
            cover_image = _save_cover_image(cover_file)

        event_id = create_event(values['title'], values['description'], values['date'],
                                values['location'], values['category'], capacity,
                                values['card_bg'], values['card_accent'], values['card_text'],
                                ticket_template, cover_image)

        ev = get_event_by_id(event_id)
        return jsonify({'ok': True, 'event': ev}), 201

    # apply admin_required wrapper
    wrapped = _admin_required(handler)
    return wrapped()

