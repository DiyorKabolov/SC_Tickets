# SC-Tickets React SPA (Vite)

This folder contains a minimal Vite + React prototype used as the new frontend.

Quick start (requires Node.js and npm):

```bash
cd static/spa-react
npm install
npm run dev
```

Then open the dev server URL (shown by Vite), or visit the Flask route if serving static files:

- Dev: http://localhost:5173 (default Vite)
- Flask integration: http://127.0.0.1:5000/spa-react (serves `static/spa-react/index.html`)

Build for production:

```bash
npm run build
# optionally copy build output into Flask static serve location
# cp -r dist/* ../spa-react/  # (example)
```

Notes:
- The SPA fetches event data from `/api/events` and uses extracted design assets from `/static/design/` as fallbacks.
- To extract images from the provided PDF, run the Python script in the project root:

```bash
pip install -r requirements.txt
python scripts/extract_pdf_assets.py "SC-Tickets Полный Редизайн_removed.pdf"
```

Assets will appear in `static/design/`.
