import os
import re
import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request
from werkzeug.utils import secure_filename
from app.database import (
    get_all_events_with_stats, get_event_by_id, create_event, update_event,
    get_all_users, get_tickets_grouped_by_event, get_stats,
    get_event_tickets_count, delete_event, delete_user, parse_event_datetime
)
from app.auth import admin_required

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "assets", "ticket_templates"))
os.makedirs(TEMPLATE_DIR, exist_ok=True)

admin = Blueprint("admin", __name__, url_prefix="/admin")
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _allowed_template(filename):
    return filename.lower().endswith(".pdf")


def _save_ticket_template(file):
    if not file or not file.filename:
        return None
    filename = secure_filename(file.filename)
    if not _allowed_template(filename):
        return None
    target_name = f"{uuid.uuid4().hex}_{filename}"
    target_path = os.path.join(TEMPLATE_DIR, target_name)
    file.save(target_path)
    return target_name


def _delete_ticket_template(filename):
    if not filename:
        return
    try:
        os.remove(os.path.join(TEMPLATE_DIR, filename))
    except OSError:
        pass


def _normalize_color(value, fallback):
    value = (value or "").strip()
    return value if HEX_COLOR_RE.match(value) else fallback


def _event_form_values():
    return {
        "title": request.form.get("title", "").strip(),
        "description": request.form.get("description", "").strip(),
        "date": request.form.get("date", "").strip(),
        "location": request.form.get("location", "").strip(),
        "capacity": request.form.get("capacity", "100").strip(),
        "card_bg": _normalize_color(request.form.get("card_bg"), "#fdfdf5"),
        "card_accent": _normalize_color(request.form.get("card_accent"), "#a898e0"),
        "card_text": _normalize_color(request.form.get("card_text"), "#2a2a2a"),
        "ticket_template": request.form.get("ticket_template", "").strip(),
    }

# ───────────────────────── дашборд ─────────────────────────────────

@admin.route("/")
@admin_required
def dashboard():
    stats = get_stats()
    # Optimized: single query for all events and their ticket counts
    events = get_all_events_with_stats()

    for event in events:
        event["percent"] = round(event["sold"] / event["capacity"] * 100) if event["capacity"] else 0

    return render_template("admin/dashboard.html", stats=stats, events=events)

# ───────────────────────── мероприятия ─────────────────────────────

@admin.route("/events")
@admin_required
def events_list():
    events = get_all_events_with_stats()
    for event in events:
        event["available"] = event["capacity"] - event["sold"]
    return render_template("admin/events.html", events=events)


@admin.route("/events/create", methods=["GET", "POST"])
@admin_required
def event_create():
    if request.method == "POST":
        values = _event_form_values()
        template_file = request.files.get("ticket_template")

        if not all([values["title"], values["date"]]):
            flash("Название и дата обязательны", "error")
        elif parse_event_datetime(values["date"]) is None:
            flash("Дата должна быть в формате 2026-05-30 19:00 или 30.05.2026 19:00", "error")
            return render_template("admin/event_form.html", event=values)
        else:
            try:
                capacity = int(values["capacity"])
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                flash("Вместимость должна быть положительным числом", "error")
                return render_template("admin/event_form.html", event=values)

            ticket_template = None
            if template_file and template_file.filename:
                ticket_template = _save_ticket_template(template_file)
                if ticket_template is None:
                    flash("Загрузите корректный PDF-файл шаблона билета", "error")
                    return render_template("admin/event_form.html", event=values)

            create_event(values["title"], values["description"], values["date"], values["location"], capacity,
                         values["card_bg"], values["card_accent"], values["card_text"], ticket_template)
            flash(f"Мероприятие «{values['title']}» создано", "success")
            return redirect(url_for("admin.events_list"))

    return render_template("admin/event_form.html", event=None)


@admin.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@admin_required
def event_edit(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("admin.events_list"))

    if request.method == "POST":
        values = _event_form_values()
        values["id"] = event_id
        values["ticket_template"] = event.get("ticket_template")
        template_file = request.files.get("ticket_template")

        if not all([values["title"], values["date"]]):
            flash("Название и дата обязательны", "error")
        elif parse_event_datetime(values["date"]) is None:
            flash("Дата должна быть в формате 2026-05-30 19:00 или 30.05.2026 19:00", "error")
            return render_template("admin/event_form.html", event=values)
        else:
            try:
                capacity = int(values["capacity"])
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                flash("Вместимость должна быть положительным числом", "error")
                return render_template("admin/event_form.html", event=values)

            ticket_template = event.get("ticket_template")
            if template_file and template_file.filename:
                new_template = _save_ticket_template(template_file)
                if new_template is None:
                    flash("Загрузите корректный PDF-файл шаблона билета", "error")
                    return render_template("admin/event_form.html", event=values)
                _delete_ticket_template(ticket_template)
                ticket_template = new_template

            update_event(event_id, values["title"], values["description"], values["date"], values["location"], capacity,
                         values["card_bg"], values["card_accent"], values["card_text"], ticket_template)
            flash("Мероприятие обновлено", "success")
            return redirect(url_for("admin.events_list"))

    return render_template("admin/event_form.html", event=event)


@admin.route("/events/<int:event_id>/delete", methods=["POST"])
@admin_required
def event_delete(event_id):
    event = get_event_by_id(event_id)
    if event is None:
        flash("Мероприятие не найдено", "error")
        return redirect(url_for("admin.events_list"))

    tickets_count = get_event_tickets_count(event_id)
    delete_event(event_id)
    flash(f"Мероприятие «{event['title']}» удалено. Билетов удалено: {tickets_count}", "success")
    return redirect(url_for("admin.events_list"))

# ───────────────────────── пользователи ────────────────────────────

@admin.route("/users")
@admin_required
def users_list():
    users = get_all_users()
    return render_template("admin/users.html", users=users)


@admin.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    from app.database import get_user_by_id, set_user_role
    from flask import session as sess

    if user_id == sess["user_id"]:
        flash("Нельзя изменить свою роль", "error")
        return redirect(url_for("admin.users_list"))

    user = get_user_by_id(user_id)
    if user is None:
        flash("Пользователь не найден", "error")
        return redirect(url_for("admin.users_list"))

    new_role = "user" if user["role"] == "admin" else "admin"
    set_user_role(user_id, new_role)
    flash(f"{user['username']}: роль изменена на «{new_role}»", "success")
    return redirect(url_for("admin.users_list"))

# ───────────────────────── билеты ──────────────────────────────────

@admin.route("/tickets")
@admin_required
def tickets_list():
    ticket_groups = get_tickets_grouped_by_event()
    tickets_count = sum(group["total_tickets"] for group in ticket_groups)
    return render_template("admin/tickets.html",
                           ticket_groups=ticket_groups,
                           tickets_count=tickets_count)


@admin.route("/scan")
@admin_required
def scan():
    return render_template("scan.html")


@admin.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user_route(user_id):
    from flask import session as sess

    if user_id == sess["user_id"]:
        flash("Нельзя удалить себя", "error")
        return redirect(url_for("admin.users_list"))

    delete_user(user_id)
    flash("Пользователь удалён", "success")
    return redirect(url_for("admin.users_list"))
