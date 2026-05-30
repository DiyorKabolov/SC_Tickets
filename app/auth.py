import secrets
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from app.database import create_user, verify_user, get_user_by_id, set_verify_token, verify_email_token, get_user_by_email
from app.mail import send_verify_email
from urllib.parse import urlparse

# ───────────────────────── декораторы ──────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Войдите в аккаунт", "error")
            return redirect(url_for("auth.login_page"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Войдите в аккаунт", "error")
            return redirect(url_for("auth.login_page"))
        if session.get("role") != "admin":
            flash("Доступ запрещён", "error")
            return redirect(url_for("events.index"))
        return f(*args, **kwargs)
    return decorated

# ───────────────────────── вспомогательные ─────────────────────────

def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    # Relative paths (no netloc, no scheme) are safe
    # Absolute URLs are safe only if they point to the same host
    if not test_url.netloc and not test_url.scheme:
        return True
    return test_url.scheme in ('http', 'https') and \
           ref_url.netloc == test_url.netloc

def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)

def _save_session(user):
    session.permanent = True
    session["user_id"]  = user["id"]
    session["username"] = user["username"]
    session["role"]     = user["role"]

def _send_code(user_id, email, username):
    """Сгенерировать и отправить код. Возвращает True если успешно."""
    code = str(secrets.randbelow(900000) + 100000)
    set_verify_token(user_id, code)
    send_verify_email(email, username, code)
    return code

# ───────────────────────── роуты ───────────────────────────────────

auth = Blueprint("auth", __name__)

@auth.route("/register", methods=["GET", "POST"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("events.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            flash("Заполните все поля", "error")
        elif len(password) < 6:
            flash("Пароль минимум 6 символов", "error")
        elif password != confirm:
            flash("Пароли не совпадают", "error")
        else:
            user_id = create_user(username, email, password)

            if user_id is None:
                existing = get_user_by_email(email)
                if existing and existing["is_verified"] == 0:
                    try:
                        _send_code(existing["id"], email, existing["username"])
                        flash("Аккаунт уже существует но не подтверждён — отправили новый код", "success")
                    except Exception as e:
                        flash("Не удалось отправить письмо", "error")
                    session["pending_user_id"] = existing["id"]
                    return redirect(url_for("auth.confirm_page"))
                else:
                    flash("Email или имя уже заняты", "error")
            else:
                try:
                    _send_code(user_id, email, username)
                    flash("Код подтверждения отправлен на почту", "success")
                except Exception as e:
                    flash("Аккаунт создан, но письмо не отправилось", "error")
                session["pending_user_id"] = user_id
                return redirect(url_for("auth.confirm_page"))

    return render_template("register.html")


@auth.route("/confirm", methods=["GET", "POST"])
def confirm_page():
    user_id = session.get("pending_user_id")
    if not user_id:
        return redirect(url_for("auth.register_page"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if verify_email_token(user_id, code):
            session.pop("pending_user_id", None)
            user = get_user_by_id(user_id)
            _save_session(user)
            flash("Добро пожаловать!", "success")
            return redirect(url_for("events.index"))
        else:
            flash("Неверный код", "error")

    return render_template("confirm.html")

@auth.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("events.index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_user(email, password)
        if user is None:
            flash("Неверный email или пароль", "error")
        elif user["is_verified"] == 0:
            session["pending_user_id"] = user["id"]
            flash("Подтвердите email — отправили новый код", "error")
            try:
                _send_code(user["id"], user["email"], user["username"])
            except Exception as e:
                print(f"Error: {e}")
            return redirect(url_for("auth.confirm_page"))
        else:
            _save_session(user)
            next_url = request.args.get("next")
            if next_url and not is_safe_url(next_url):
                next_url = url_for("events.index")
            return redirect(next_url or url_for("events.index"))

    return render_template("login.html")


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))