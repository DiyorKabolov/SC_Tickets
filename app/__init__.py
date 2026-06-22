import os
from datetime import timedelta
from flask import Flask, request, jsonify, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()
csrf = CSRFProtect()


def pluralize(n, one, few, many):
    if 11 <= n % 100 <= 19:
        return many
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return few
    return many


def create_app():
    template_folder = os.path.join(os.path.dirname(__file__), "..", "templates")
    static_folder = os.path.join(os.path.dirname(__file__), "..", "static")
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        secret_key = "dev-sc-tickets-secret-key-change-me"
        print("Warning: SECRET_KEY is not set. Using a development fallback key.")

    app.secret_key = secret_key
    app.permanent_session_lifetime = timedelta(days=30)
    app.config["SESSION_REFRESH_EACH_REQUEST"] = True
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "0") == "1"
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH", str(25 * 1024 * 1024)))
    app.config["WTF_CSRF_HEADERS"] = ["X-CSRFToken", "X-CSRF-Token"]

    csrf.init_app(app)

    from app.auth import auth, admin_required
    from app.events import events
    from app.admin import admin

    app.register_blueprint(auth)
    app.register_blueprint(events)
    app.register_blueprint(admin)
    app.template_filter("pluralize")(pluralize)

    @app.route("/used", methods=["POST"])
    @admin_required
    def check():
        payload = request.get_json(silent=True) or request.form
        ticket_id = (payload.get("ticket_id") or "").strip()
        if not ticket_id:
            return jsonify({"ok": False, "message": "Не передан ticket_id"}), 400

        from app.database import check_ticket
        result = check_ticket(ticket_id)
        return jsonify(result)

    @app.errorhandler(400)
    def handle_csrf_error(e):
        if "csrf" in str(e).lower():
            flash("Сессия истекла или форма невалидна. Попробуйте ещё раз.", "error")
            return redirect(request.referrer or url_for("events.index"))
        return "Bad Request", 400

    return app
