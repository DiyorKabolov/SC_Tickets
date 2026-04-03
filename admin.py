from flask import Blueprint, render_template, redirect, url_for, flash, request
from database import (
    get_all_events, get_event_by_id, create_event, update_event,
    get_all_users, get_all_tickets, get_stats,
    get_event_tickets_count, delete_user
)
from auth import admin_required

admin = Blueprint("admin", __name__, url_prefix="/admin")

# ───────────────────────── дашборд ─────────────────────────────────

@admin.route("/")
@admin_required
def dashboard():
    stats = get_stats()
    events = get_all_events()

    for event in events:
        sold = get_event_tickets_count(event["id"])
        event["sold"] = sold
        event["percent"] = round(sold / event["capacity"] * 100) if event["capacity"] else 0

    return render_template("admin/dashboard.html", stats=stats, events=events)

# ───────────────────────── мероприятия ─────────────────────────────

@admin.route("/events")
@admin_required
def events_list():
    events = get_all_events()
    for event in events:
        sold = get_event_tickets_count(event["id"])
        event["sold"] = sold
        event["available"] = event["capacity"] - sold
    return render_template("admin/events.html", events=events)


@admin.route("/events/create", methods=["GET", "POST"])
@admin_required
def event_create():
    if request.method == "POST":
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        date        = request.form.get("date", "").strip()
        location    = request.form.get("location", "").strip()
        capacity    = request.form.get("capacity", "100").strip()
        card_bg     = request.form.get("card_bg", "#fdfdf5").strip()
        card_accent = request.form.get("card_accent", "#a898e0").strip()
        card_text   = request.form.get("card_text", "#2a2a2a").strip()

        if not all([title, date]):
            flash("Название и дата обязательны", "error")
        else:
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                flash("Вместимость должна быть положительным числом", "error")
                return render_template("admin/event_form.html", event=None)

            create_event(title, description, date, location, capacity,
                         card_bg, card_accent, card_text)
            flash(f"Мероприятие «{title}» создано", "success")
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
        title       = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        date        = request.form.get("date", "").strip()
        location    = request.form.get("location", "").strip()
        capacity    = request.form.get("capacity", "100").strip()
        card_bg     = request.form.get("card_bg", "#fdfdf5").strip()
        card_accent = request.form.get("card_accent", "#a898e0").strip()
        card_text   = request.form.get("card_text", "#2a2a2a").strip()

        if not all([title, date]):
            flash("Название и дата обязательны", "error")
        else:
            try:
                capacity = int(capacity)
                if capacity <= 0:
                    raise ValueError
            except ValueError:
                flash("Вместимость должна быть положительным числом", "error")
                return render_template("admin/event_form.html", event=event)

            update_event(event_id, title, description, date, location, capacity,
                         card_bg, card_accent, card_text)
            flash("Мероприятие обновлено", "success")
            return redirect(url_for("admin.events_list"))

    return render_template("admin/event_form.html", event=event)

# ───────────────────────── пользователи ────────────────────────────

@admin.route("/users")
@admin_required
def users_list():
    users = get_all_users()
    return render_template("admin/users.html", users=users)


@admin.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    from database import get_user_by_id, set_user_role
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
    tickets = get_all_tickets()
    return render_template("admin/tickets.html", tickets=tickets)


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