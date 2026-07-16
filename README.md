# Truck Driver ELD Log

Full-stack app (Django + React) that plans a property-carrying trip and generates
the driver's **Hours-of-Service** daily log sheets. Enter current / pickup / dropoff
locations and cycle hours used; get a route map with stops and rests, plus filled-in
ELD log grids — one per day, with the 11-hour, 14-hour, 30-minute-break, and
70-hour/8-day rules enforced.

The engine implements the FMCSA Hours-of-Service rules for property-carrying
drivers (49 CFR Part 395).

## Repo layout

```
backend/     Django + DRF API, the pure-Python HOS engine, and routing client
frontend/    React (Vite) app: trip form, Leaflet map, SVG log sheets
```

## Prerequisites

- Python 3.12+, Node 20+
- A free **OpenRouteService** API key (geocoding + directions):
  https://openrouteservice.org/dev/#/signup — needed for live routing.

## Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # if venv lacks pip: see note below
cp .env.example .env                      # then set ORS_API_KEY
python manage.py runserver                # http://localhost:8000 (no DB / no migrate)
```

The API is **stateless** — it computes each plan on demand and stores nothing, so
there is no database or migrations.

Run the tests (HOS engine + planner + API, incl. the FMCSA "John Doe" oracle):

```bash
cd backend && python manage.py test tests
```

> Note: if `python -m venv` reports `ensurepip is not available`, either install
> `python3-venv`, or bootstrap pip into the venv:
> `python -m venv --without-pip .venv && curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python`

### API

| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/health/` | liveness check |
| GET  | `/api/geocode/autocomplete/?text=` | location type-ahead (ORS proxy) |
| POST | `/api/plan/` | plan a trip; returns the route + per-day logs (stateless) |

Without `ORS_API_KEY`, `/plan/` and `/autocomplete/` return `503` with a clear
message; `/health/` still works.

## Frontend

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173 (proxies /api -> :8000)
```

Preview the map + logs **without an API key** using the bundled sample payload:
open http://localhost:5173/?demo=1

## Deployment

Config lives in the repo: [`render.yaml`](render.yaml) (backend) and
[`frontend/vercel.json`](frontend/vercel.json) (SPA). The backend is stateless — no
database to provision.

**Backend → Render.** In the Render dashboard: *New + → Blueprint*, connect this repo.
The blueprint provisions the web service, generates `SECRET_KEY`, and sets `DEBUG=False`.
After the first deploy, set the two secrets on the service: `ORS_API_KEY` and
`CORS_ALLOWED_ORIGINS` (your Vercel URL). `collectstatic` runs in the build command.

**Frontend → Vercel.** *New Project*, import this repo, set **Root Directory =
`frontend`** (Vite is auto-detected). Add one env var:

```
VITE_API_BASE=https://<your-render-service>.onrender.com
```

`api.js` prefixes requests with `VITE_API_BASE` in production (it's inlined at build
time, so redeploy after changing it); in dev, Vite proxies `/api` to `:8000` instead.

**Order:** deploy Render first → copy its URL into Vercel's `VITE_API_BASE` → deploy
Vercel → copy the Vercel URL into Render's `CORS_ALLOWED_ORIGINS`.
