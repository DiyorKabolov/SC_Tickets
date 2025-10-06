import sqlite3
from flask import jsonify

DB_PATH = "tickets.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def save_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO tickets (ticket_id) VALUES (?)", (ticket_id,))
    conn.commit()
    conn.close()

def check_ticket(ticket_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT used FROM tickets WHERE ticket_id = ?", (ticket_id,))
    result = cursor.fetchone()
    if result is None:
        conn.close()
        return jsonify({"ok": False, "message": "❌ Билет не найден"})

    if result[0] == 1:
        conn.close()
        return jsonify({"ok": False, "message": "🚫 Билет уже использован"})


    # Если найден и не использован — помечаем как использованный
    cursor.execute("UPDATE tickets SET used = 1 WHERE ticket_id = ?", (ticket_id,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message": "✅ Билет действителен"})