# interactive-cosmic-login

Interactive cosmic login screen with a React + Three.js frontend.

## What changed

- The login UI now lives in a Vite/React app under `src/`.
- The existing Three.js universe logic still powers the scene.
- The Flask app still provides the `/api/cosmic-fact` endpoint for the Wikipedia-backed fact card.

## Run it

```bash
npm install
npm run dev
```

If you want the backend fact endpoint available locally, run the Flask app in a second terminal as well:

```bash
python app.py
```

## Build

```bash
npm run build
```
