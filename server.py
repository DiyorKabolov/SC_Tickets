from flask import Flask, request, jsonify, flash, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from database import init_db, check_ticket
from auth import auth
from events import events
from admin import admin
from pyngrok import ngrok
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Секретный ключ для сессий (должен быть задан до CSRFProtect)
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-production")
app.permanent_session_lifetime = timedelta(days=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

csrf = CSRFProtect(app)

@app.template_filter('pluralize')
def pluralize(n, one, few, many):
    if 11 <= n % 100 <= 19:
        return many
    r = n % 10
    if r == 1:
        return one
    if 2 <= r <= 4:
        return few
    return many

# ───────────────────── регистрация Blueprint'ов ─────────────────────
app.register_blueprint(auth)
app.register_blueprint(events)
app.register_blueprint(admin)

# ───────────────────── API сканера ──────────────────────────────────
@app.route("/used", methods=["GET"])
@csrf.exempt
def check():
    ticket_id = request.args.get("ticket_id")
    if not ticket_id:
        return "Ошибка: не передан ticket_id", 400
    result = check_ticket(ticket_id)
    print(result)
    return jsonify(result)

@app.errorhandler(400)
def handle_csrf_error(e):
    if "csrf" in str(e).lower():
        flash("Сессия истекла или форма невалидна. Попробуйте ещё раз.", "error")
        return redirect(request.referrer or url_for("events.index"))
    return "Bad Request", 400

# ────────────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    # ngrok connect (optional/conditional)
    try:
        public_url = ngrok.connect(5000)
        print("Public URL:", public_url)
    except Exception as e:
        print("Ngrok not connected:", e)

    app.run(host="0.0.0.0", port=5000, debug=True)