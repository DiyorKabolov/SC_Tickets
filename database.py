import sqlite3
import bcrypt
import os
from datetime import datetime, timedelta, time
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFY_TOKEN_TTL_MINUTES = int(os.getenv("VERIFY_TOKEN_TTL_MINUTES", "10"))
VERIFY_MAX_ATTEMPTS = int(os.getenv("VERIFY_MAX_ATTEMPTS", "5"))
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
                verify_token_created_at TIMESTAMP,
                verify_attempts INTEGER DEFAULT 0,
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

        for col, definition in [
            ("verify_token_created_at", "TIMESTAMP"),
            ("verify_attempts", "INTEGER DEFAULT 0"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass

        cursor.execute("DROP INDEX IF EXISTS idx_tickets_user_event")
        conn.commit()


def parse_event_datetime(event_date_raw):
    if not event_date_raw:
        return None

    value = event_date_raw.strip()
    formats = (
        ("%Y-%m-%dT%H:%M", False),
        ("%Y-%m-%d %H:%M", False),
        ("%d.%m.%Y %H:%M", False),
        ("%d.%m.%Y", True),
        ("%Y-%m-%d", True),
    )

    for fmt, is_date_only in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if is_date_only:
                parsed = datetime.combine(parsed.date(), time.max)
            return parsed
        except ValueError:
            continue
    return None


def is_event_expired(event_date_raw):
    event_dt = parse_event_datetime(event_date_raw)
    return bool(event_dt and event_dt < datetime.now())

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
        cursor.execute("""
            UPDATE users
            SET verify_token=?, verify_token_created_at=CURRENT_TIMESTAMP, verify_attempts=0
            WHERE id=?
        """, (token, user_id))
        conn.commit()

def verify_email_token(user_id, code):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT verify_token, verify_token_created_at, verify_attempts
            FROM users
            WHERE id=?
        """, (user_id,))
        row = cursor.fetchone()
        if row is None or not row["verify_token"]:
            return False

        attempts = row["verify_attempts"] or 0
        if attempts >= VERIFY_MAX_ATTEMPTS:
            return False

        created_at = row["verify_token_created_at"]
        if created_at:
            created_dt = datetime.fromisoformat(str(created_at))
            if created_dt + timedelta(minutes=VERIFY_TOKEN_TTL_MINUTES) < datetime.now():
                return False

        if row["verify_token"] != code:
            cursor.execute("UPDATE users SET verify_attempts=verify_attempts + 1 WHERE id=?", (user_id,))
            conn.commit()
            return False

        cursor.execute("""
            UPDATE users
            SET is_verified=1, verify_token=NULL, verify_token_created_at=NULL, verify_attempts=0
            WHERE id=?
        """, (user_id,))
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

def delete_event(event_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tickets WHERE event_id = ?", (event_id,))
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        conn.commit()
        return cursor.rowcount > 0

# â”€â”€ Tickets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def save_ticket(ticket_id, user_id=None, event_id=None):
    with get_db() as conn:
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            cursor.execute("SELECT capacity FROM events WHERE id = ?", (event_id,))
            event = cursor.fetchone()
            if not event:
                conn.rollback()
                return "not_found"

            cursor.execute("SELECT COUNT(*) FROM tickets WHERE event_id = ?", (event_id,))
            sold = cursor.fetchone()[0]

            if sold >= event['capacity']:
                conn.rollback()
                return "full"

            cursor.execute(
                "INSERT INTO tickets (ticket_id, user_id, event_id) VALUES (?, ?, ?)",
                (ticket_id, user_id, event_id)
            )
            conn.commit()
            return "success"
        except sqlite3.IntegrityError:
            conn.rollback()
            return "error"
        except Exception:
            conn.rollback()
            return "error"


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

def get_tickets_grouped_by_event():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*,
                   COUNT(t.id) as total_tickets,
                   COALESCE(SUM(CASE WHEN t.used = 1 THEN 1 ELSE 0 END), 0) as used_tickets
            FROM events e
            LEFT JOIN tickets t ON e.id = t.event_id
            GROUP BY e.id
            ORDER BY e.date ASC
        """)
        groups = [dict(row) for row in cursor.fetchall()]
        groups_by_id = {}
        for group in groups:
            group["tickets"] = []
            group["unused_tickets"] = group["total_tickets"] - group["used_tickets"]
            groups_by_id[group["id"]] = group

        cursor.execute("""
            SELECT t.*, u.username, u.email, e.title as event_title
            FROM tickets t
            LEFT JOIN users u ON t.user_id = u.id
            LEFT JOIN events e ON t.event_id = e.id
            ORDER BY e.date ASC, t.created_at DESC
        """)
        orphan_group = None
        for row in cursor.fetchall():
            ticket = dict(row)
            group = groups_by_id.get(ticket["event_id"])
            if group is None:
                if orphan_group is None:
                    orphan_group = {
                        "id": None,
                        "title": "Без мероприятия",
                        "date": "—",
                        "location": "",
                        "capacity": 0,
                        "total_tickets": 0,
                        "used_tickets": 0,
                        "unused_tickets": 0,
                        "tickets": [],
                    }
                    groups.append(orphan_group)
                group = orphan_group

            group["tickets"].append(ticket)
            if group is orphan_group:
                group["total_tickets"] += 1
                group["used_tickets"] += 1 if ticket["used"] else 0
                group["unused_tickets"] = group["total_tickets"] - group["used_tickets"]

        return groups

def check_ticket(ticket_id):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")
            cursor.execute("""
                SELECT t.used, e.date AS event_date
                FROM tickets t
                LEFT JOIN events e ON t.event_id = e.id
                WHERE t.ticket_id = ?
            """, (ticket_id,))
            result = cursor.fetchone()

            if result is None:
                conn.rollback()
                return {"ok": False, "message": "Билет не найден"}
            if result["used"] == 1:
                conn.rollback()
                return {"ok": False, "message": "Билет уже использован"}
            if is_event_expired(result["event_date"]):
                conn.rollback()
                return {"ok": False, "message": "Билет просрочен"}

            cursor.execute("""
                UPDATE tickets
                SET used = 1
                WHERE ticket_id = ? AND used = 0
            """, (ticket_id,))
            if cursor.rowcount != 1:
                conn.rollback()
                return {"ok": False, "message": "Билет уже использован"}

            conn.commit()
            return {"ok": True, "message": "Билет действителен"}
        except Exception:
            conn.rollback()
            return {"ok": False, "message": "Ошибка проверки билета"}

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



