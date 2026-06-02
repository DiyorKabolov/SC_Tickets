import os
from pyngrok import ngrok
from app import create_app
from app.database import init_db


if __name__ == "__main__":
    app = create_app()
    init_db()

    host = os.getenv("FLASK_HOST", "127.0.0.1")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"

    if os.getenv("ENABLE_NGROK", "0") == "1":
        try:
            public_url = ngrok.connect(port)
            print("Public URL:", public_url)
        except Exception as e:
            print("Ngrok not connected:", e)

    app.run(host=host, port=port, debug=debug)
