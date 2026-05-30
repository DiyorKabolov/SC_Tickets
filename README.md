# SC Tickets

Flask-приложение для выдачи бесплатных QR-билетов, админки мероприятий, PDF-билетов и сканирования входа.

## Быстрый запуск

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python server.py
```

Приложение по умолчанию запускается на `http://127.0.0.1:5000`.

## Важные настройки

- `SECRET_KEY` должен быть длинным случайным значением для постоянных сессий.
- `MAIL_FROM` и `MAIL_PASSWORD` нужны для отправки кодов подтверждения email.
- `FLASK_DEBUG=1` включайте только локально.
- `ENABLE_NGROK=1` включает публичный туннель ngrok при запуске.
- `SESSION_COOKIE_SECURE=1` включайте при работе через HTTPS.

## Админ

Создайте пользователя через интерфейс, затем назначьте роль:

```powershell
python make_admin.py user@example.com
```

Сканер доступен только администраторам по адресу `/admin/scan`.
