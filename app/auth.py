import secrets
from functools import wraps
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.database import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    set_verify_token,
    verify_email_token,
    verify_user,
)
from app.mail import send_verify_email


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


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlparse(request.host_url)
    test_url = urlparse(target)
    if not test_url.netloc and not test_url.scheme:
        return True
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def _save_session(user):
    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]


def _send_code(user_id, email, username):
    code = str(secrets.randbelow(900000) + 100000)
    set_verify_token(user_id, code)
    if not send_verify_email(email, username, code):
        raise RuntimeError("verification email was not sent")
    return code


auth = Blueprint("auth", __name__)


@auth.route("/register", methods=["GET", "POST"])
def register_page():
    if "user_id" in session:
        return redirect(url_for("events.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if not all([username, email, password, confirm]):
            flash("Заполните все поля", "error")
        elif len(password) < 8:
            flash("Пароль должен быть минимум 8 символов", "error")
        elif password != confirm:
            flash("Пароли не совпадают", "error")
        else:
            user_id = create_user(username, email, password)

            if user_id is None:
                existing = get_user_by_email(email)
                if existing and existing["is_verified"] == 0:
                    try:
                        _send_code(existing["id"], email, existing["username"])
                        session["pending_user_id"] = existing["id"]
                        flash("Аккаунт уже существует, но не подтверждён. Мы отправили новый код.", "success")
                        return redirect(url_for("auth.confirm_page"))
                    except Exception:
                        flash("Не удалось отправить письмо с кодом", "error")
                else:
                    flash("Email или имя уже заняты", "error")
            else:
                try:
                    _send_code(user_id, email, username)
                    session["pending_user_id"] = user_id
                    flash("Код подтверждения отправлен на почту", "success")
                    return redirect(url_for("auth.confirm_page"))
                except Exception:
                    flash("Аккаунт создан, но письмо не отправилось", "error")

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
        flash("Неверный код", "error")

    return render_template("confirm.html")


@auth.route("/login", methods=["GET", "POST"])
def login_page():
    if "user_id" in session:
        return redirect(url_for("events.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = verify_user(email, password)
        if user is None:
            flash("Неверный email или пароль", "error")
        elif user["is_verified"] == 0:
            try:
                _send_code(user["id"], user["email"], user["username"])
                session["pending_user_id"] = user["id"]
                flash("Подтвердите email, мы отправили новый код", "error")
                return redirect(url_for("auth.confirm_page"))
            except Exception:
                flash("Не удалось отправить код подтверждения", "error")
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
