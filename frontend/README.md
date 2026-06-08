# AITutor Frontend

React 18 + TypeScript + Vite frontend for the AI Tutor learning platform.

## Setup (Windows — if `npm` is not recognized)

Node.js is bundled locally in `../.tools/node`. Use the helper scripts:

```powershell
cd frontend
.\setup.ps1          # adds local node/npm to PATH for this session
npm install          # first time only
copy .env.example .env
.\dev.ps1            # starts Vite on http://localhost:5173
```

Or install system-wide Node from https://nodejs.org (LTS), then:

```powershell
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Backend integration

The frontend wires to the real FastAPI backend at `VITE_API_URL` (default `http://localhost:8000`):

| Feature | Endpoint |
|---------|----------|
| Chat | `POST /tutor/chat` |
| Recommendations | `POST /tutor/recommend` |
| Profile | `GET /tutor/profile/{learner_id}` |
| Content catalog | `GET /tutor/content-items` (dev token) |

Auth, admin, and university course APIs use a **local platform layer** (`src/api/localPlatform.ts`) until backend routes exist.

Set `VITE_API_KEY` and `VITE_DEV_TOKEN` to match `agency/.env`.

## Scripts

- `npm run dev` — development server (port 5173)
- `npm run build` — production build
- `npm run preview` — preview production build
