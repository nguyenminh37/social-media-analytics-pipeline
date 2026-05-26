# Frontend

Small Next.js App Router dashboard for the existing YouTube serving API.

## Run locally

1. Start the Python backend from the repo root:

```bash
python3 -m serving_api.server
```

2. In `frontend/`, create the local env file:

```bash
cp .env.example .env.local
```

3. Install dependencies and run the frontend:

```bash
npm install
npm run dev
```

4. Open `http://localhost:3001`.

## Architecture

- Browser calls local Next.js Route Handlers under `src/app/api/**`
- Route Handlers proxy to `ANALYTICS_API_BASE_URL`
- UI components live in `src/components/dashboard`
- Shared client fetchers and response normalization live in `src/lib/api.ts`

## Default backend URL

```bash
ANALYTICS_API_BASE_URL=http://localhost:8081
```

## Default frontend port

The frontend uses port `3001` by default because the repo's Docker stack already reserves `3000` for Grafana.
