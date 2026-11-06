# Research Brief Studio

Local React + TypeScript interface for the Research Brief API.

```powershell
npm install
npm run dev
```

The UI expects the backend at `http://127.0.0.1:8000`. Optionally set `VITE_API_URL` in a local `.env` to use a different API address. Never put the Groq key in the frontend.

`npm run build` type-checks and creates the static production build. The backend runs in mock mode by default, which is sufficient to review the UI and workflow shape.
