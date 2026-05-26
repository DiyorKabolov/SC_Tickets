import sqlite3
import bcrypt
import os
from datetime import datetime
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path_from_env = os.getenv("DB_PATH")
if db_path_from_env:
    DB_PATH = db_path_from_env if os.path.isabs(db_path_from_env) else os.path.join(BASE_DIR, db_path_from_env)
else:
    DB_PATH = os.path.join(BASE_DIR, "tickets.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
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

        # Add columns if DB exists without them
        for col, default in [
            ("card_bg", "'#fdfdf5'"),
            ("card_accent", "'#a898e0'"),
            ("card_text", "'#2a2a2a'"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE events ADD COLUMN {col} TEXT DEFAULT {default}")
            except sqlite3.OperationalError:
                pass
        conn.commit()

# â”€â”€ Users â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, stored_hash):
    try:
        return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
    except Exception:
        return False

def create_user(username, email, password, role="user"):
    with get_db() as conn:
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

def get_user_by_email(email):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_id(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_all_users():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC")
        return [dict(row) for row in cursor.fetchall()]

def set_verify_token(user_id, token):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET verify_token=? WHERE id=?", (token, user_id))
        conn.commit()

def verify_email_token(user_id, code):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT verify_token FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        if row is None or row["verify_token"] != code:
            return False
        cursor.execute("UPDATE users SET is_verified=1, verify_token=NULL WHERE id=?", (user_id,))
        conn.commit()
        return True

# â”€â”€ Events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def create_event(title, description, date, location, capacity,
                 card_bg="#fdfdf5", card_accent="#a898e0", card_text="#2a2a2a"):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (title, description, date, location, capacity,
                                card_bg, card_accent, card_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, description, date, location, capacity,
              card_bg, card_accent, card_text))
        conn.commit()
        return cursor.lastrowid

def get_all_events_with_stats():
    """Optimized: returns events with ticket counts in one query (Fixes N+1)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*, COUNT(t.id) as sold
            FROM events e
            LEFT JOIN tickets t ON e.id = t.event_id
            GROUP BY e.id
            ORDER BY e.date ASC
        """)
        return [dict(row) for row in cursor.fetchall()]

def get_event_by_id(event_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM events WHERE id = ?", (event_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_event_tickets_count(event_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event_id,))
        return cursor.fetchone()[0]

def update_event(event_id, title, description, date, location, capacity,
                 card_bg="#fdfdf5", card_accent="#a898e0", card_text="#2a2a2a"):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE events
            SET title=?, description=?, date=?, location=?, capacity=?,
                card_bg=?, card_accent=?, card_text=?
            WHERE id=?
        """, (title, description, date, location, capacity,
              card_bg, card_accent, card_text, event_id))
        conn.commit()

# â”€â”€ Tickets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_ticket(ticket_id, user_id=None, event_id=None):
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            # BEGIN IMMEDIATE locks the DB to prevent race conditions
            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("SELECT capacity FROM events WHERE id = ?", (event_id,))
            event = cursor.fetchone()
            if not event:
                conn.rollback()
                return False

            cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event_id,))
            sold = cursor.fetchone()[0]

            if sold >= event['capacity']:
                conn.rollback()
                return False

            cursor.execute(
                "INSERT OR IGNORE INTO tickets (ticket_id, user_id, event_id) VALUES (?, ?, ?)",
                (ticket_id, user_id, event_id)
            )
            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False


def get_user_tickets(user_id):
    with get_db() as conn:
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

def get_all_tickets():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, u.username, u.email, e.title as event_title
            FROM tickets t
            LEFT JOIN users u ON t.user_id = u.id
            LEFT JOIN events e ON t.event_id = e.id
            ORDER BY t.created_at DESC
        """)
        return [dict(row) for row in cursor.fetchall()]

def check_ticket(ticket_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.used, e.date AS event_date
            FROM tickets t
            LEFT JOIN events e ON t.event_id = e.id
            WHERE t.ticket_id = ?
        """, (ticket_id,))
        result = cursor.fetchone()

        if result is None:
            return {"ok": False, "message": "\u0411\u0438\u043b\u0435\u0442 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d"}
        if result[0] == 1:
            return {"ok": False, "message": "\u0411\u0438\u043b\u0435\u0442 \u0443\u0436\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d"}

        event_date = (result["event_date"] or "").strip()
        if event_date:
            now = datetime.now()
            parsed_dt = None
            for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%Y-%m-%d"):
                try:
                    parsed_dt = datetime.strptime(event_date, fmt)
                    break
                except ValueError:
                    continue
            if parsed_dt and parsed_dt < now:
                return {"ok": False, "message": "\u0411\u0438\u043b\u0435\u0442 \u043f\u0440\u043e\u0441\u0440\u043e\u0447\u0435\u043d"}

        cursor.execute("UPDATE tickets SET used = 1 WHERE ticket_id = ?", (ticket_id,))
        conn.commit()
        return {"ok": True, "message": "\u0411\u0438\u043b\u0435\u0442 \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u0442\u0435\u043b\u0435\u043d"}

# â”€â”€ Admin stats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def get_stats():
    with get_db() as conn:
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

def set_user_role(user_id, role):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        conn.commit()

def verify_user(email, password):
    user = get_user_by_email(email)
    if user and verify_password(password, user["password_hash"]):
        return user
    return None

def delete_user(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tickets SET user_id=NULL WHERE user_id=?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.commit()



