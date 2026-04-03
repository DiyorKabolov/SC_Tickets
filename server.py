from flask import Flask, request, jsonify
from database import init_db, check_ticket
from auth import auth
from events import events
from admin import admin
from pyngrok import ngrok
import os
from datetime import timedelta

app = Flask(__name__)

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

# Секретный ключ для сессий — обязательно замени на свой!
app.secret_key = os.environ.get("SECRET_KEY", "11235813")
app.permanent_session_lifetime = timedelta(days=30)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# ───────────────────── регистрация Blueprint'ов ─────────────────────
app.register_blueprint(auth)
app.register_blueprint(events)
app.register_blueprint(admin)

# ───────────────────── API сканера ──────────────────────────────────
@app.route("/used", methods=["GET"])
def check():
    ticket_id = request.args.get("ticket_id")
    if not ticket_id:
        return "Ошибка: не передан ticket_id", 400
    result = check_ticket(ticket_id)
    print(result)
    return jsonify(result)

# ────────────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    public_url = ngrok.connect(5000)
    print("URL:", public_url)
    app.run(host="0.0.0.0", port=5000)