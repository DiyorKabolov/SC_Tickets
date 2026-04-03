import sqlite3
import hashlib
import os

DB_PATH = "tickets.db"
print("DB path:", os.path.abspath(DB_PATH))


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                is_verified INTEGER DEFAULT 0,
                verify_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                location TEXT,
                capacity INTEGER DEFAULT 100,
                card_bg TEXT DEFAULT '#fdfdf5',
                card_accent TEXT DEFAULT '#a898e0',
                card_text TEXT DEFAULT '#2a2a2a',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                event_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (event_id) REFERENCES events(id)
            )
        """)

        # Добавляем колонки если БД уже существует без них
        for col, default in [
            ("card_bg", "'#fdfdf5'"),
            ("card_accent", "'#a898e0'"),
            ("card_text", "'#2a2a2a'"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT DEFAULT {default}")
            except sqlite3.OperationalError:
                pass  # колонка уже есть

        conn.commit()
    finally:
        conn.close()


# ── Users ──────────────────────────────────────────

def hash_password(password):
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password, stored_hash):
    salt, hashed = stored_hash.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == hashed


def create_user(username, email, password, role="user"):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (username, email, hash_password(password), role)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_all_users():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def set_verify_token(user_id, token):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verify_token=? WHERE id=?", (token, user_id))
        conn.commit()
    finally:
        conn.close()


def verify_email_token(user_id, code):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT verify_token FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        if row is None or row["verify_token"] != code:
            return False
        cursor.execute("UPDATE users SET is_verified=1, verify_token=NULL WHERE id=?", (user_id,))
        conn.commit()
        return True
    finally:
        conn.close()


# ── Events ─────────────────────────────────────────

def create_event(title, description, date, location, capacity,
                 card_bg="#fdfdf5", card_accent="#a898e0", card_text="#2a2a2a"):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, date, location, capacity,
                                card_bg, card_accent, card_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, date, location, capacity,
              card_bg, card_accent, card_text))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_events():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events ORDER BY date ASC")
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_event_by_id(event_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_event_tickets_count(event_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event_id,))
        return cursor.fetchone()[0]
    finally:
        conn.close()


def update_event(event_id, title, description, date, location, capacity,
                 card_bg="#fdfdf5", card_accent="#a898e0", card_text="#2a2a2a"):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET title=?, description=?, date=?, location=?, capacity=?,
                card_bg=?, card_accent=?, card_text=?
            WHERE id=?
        """, (title, description, date, location, capacity,
              card_bg, card_accent, card_text, event_id))
        conn.commit()
    finally:
        conn.close()


# ── Tickets ────────────────────────────────────────

def save_ticket(ticket_id, user_id=None, event_id=None):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO tickets (ticket_id, user_id, event_id) VALUES (?, ?, ?)",
            (ticket_id, user_id, event_id)
        )
        conn.commit()
    finally:
        conn.close()


def get_user_tickets(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, e.title as event_title, e.date as event_date,
                   e.location as event_location,
                   e.card_bg, e.card_accent, e.card_text
            FROM tickets t
            LEFT JOIN events e ON t.event_id = e.id
            WHERE t.user_id = ?
            ORDER BY t.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_all_tickets():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username, u.email, e.title as event_title
            FROM tickets t
            LEFT JOIN users u ON t.user_id = u.id
            LEFT JOIN events e ON t.event_id = e.id
            ORDER BY t.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def check_ticket(ticket_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT used FROM tickets WHERE ticket_id = ?", (ticket_id,))
        result = cursor.fetchone()

        if result is None:
            return {"ok": False, "message": "Билет не найден"}
        if result[0] == 1:
            return {"ok": False, "message": "Билет уже использован"}

        cursor.execute("UPDATE tickets SET used = 1 WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        return {"ok": True, "message": "Билет действителен"}
    finally:
        conn.close()


# ── Admin stats ────────────────────────────────────

def get_stats():
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        users_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM events")
        events_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets")
        tickets_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE used = 1")
        scanned_count = cursor.fetchone()[0]
        return {
            "users": users_count,
            "events": events_count,
            "tickets": tickets_count,
            "scanned": scanned_count,
        }
    finally:
        conn.close()


def set_user_role(user_id, role):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        conn.commit()
    finally:
        conn.close()


def verify_user(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None


def delete_user(user_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET user_id=NULL WHERE user_id=?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()