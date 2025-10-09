# Rental-Agent

Web-based rental leasing receptionist with a FastAPI backend and React frontend.

## Prerequisites

- Python 3.12+
- Node.js 20+
- Neon Postgres connection string saved to the project `.env`

## Initial setup

```powershell
# From the repository root
python -m venv apps/api/venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
apps\api\venv\Scripts\Activate.ps1
pip install -r apps/api/requirements.txt

cd ..\web
npm install
```

## Running the services

### Backend (FastAPI)

```powershell
Set-Location apps/api
apps\api\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

The API listens on `http://127.0.0.1:8000`.

### Frontend (React + Vite)

Open a second terminal:

```powershell
Set-Location apps/web
npm run dev
```

The UI is available at `http://127.0.0.1:5173`.

## Testing

```powershell
Set-Location apps/api
apps\api\venv\Scripts\Activate.ps1
pytest
```

## Repository layout

```
apps/
	api/   # FastAPI backend, agent services
	web/   # React frontend
```
