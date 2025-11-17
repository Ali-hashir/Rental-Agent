# Rental Voice Demo API

This FastAPI service implements the minimal push-to-talk loop for the leasing receptionist demo:

1. Receive a short microphone clip via `POST /api/utterance`.
2. Transcribe the audio with **faster-whisper** (CPU).
3. Ask **Gemini Flash** for a brief, catalog-aware reply.
4. Convert the reply to audio with **Edge TTS** and stream it back to the browser.

The service also exposes `GET /api/health` for smoke checks.

## Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env` alongside this file and add your Gemini key:

```bash
GEMINI_API_KEY=your-google-ai-api-key
```

Optional tweaks live in `app/core/config.py` (voice name, Whisper model size, etc.).

### Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Tests

```bash
pytest
```

## API contract

`POST /api/utterance`

- Request: `multipart/form-data` with a single `audio` field (WAV/PCM).
- Response: binary audio (MP3) with the following headers:
	- `X-Transcript` – transcription returned by Whisper
	- `X-Model-Reply` – text supplied to TTS
	- `X-Error: true` – present when a fallback apology clip is returned

`GET /api/health`

- Response: `{"status": "ok"}`
