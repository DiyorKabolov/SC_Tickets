from flask import Flask, request, render_template, jsonify
import sqlite3
from database import init_db, check_ticket
from pyngrok import ngrok

app = Flask(__name__)

init_db()

@app.route("/")
def index():
    return render_template("scan.html")

@app.route("/used", methods=["GET"])
def check():
    ticket_id = request.args.get("ticket_id")
    if not ticket_id:
        return "Ошибка: не передан ticket_id", 400
    result = check_ticket(ticket_id)
    print(result)
    return result
@app.route("/")
def showHTML():
    return render_template('scan.html')
if __name__ == "__main__":
    public_url = ngrok.connect(5000)
    print("URL:", public_url, app.run(host="0.0.0.0", port=5000))
