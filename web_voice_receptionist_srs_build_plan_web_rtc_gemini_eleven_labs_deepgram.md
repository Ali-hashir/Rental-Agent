# Minimal SRS: Web Voice Demo (Mic → ASR → LLM → TTS)

## 1) Goal
Show a working web demo where a visitor clicks **Call**, speaks, the app transcribes, asks an LLM, converts the reply to audio, and plays it back. No phone, no DB, no booking. Turn‑taking only.

## 2) Scope (MVP)
**In**: single‑page web UI, push‑to‑talk audio capture, transcription, LLM answer, TTS playback, on‑screen transcript.
**Out**: barge‑in, WebRTC rooms, calendars, leads, dashboards, policies, auth, CRM.

## 3) Flow
1. User clicks **Hold to talk** → mic records 5–15 s chunk.
2. Browser uploads WAV/PCM to backend.
3. Backend runs ASR → text.
4. Backend runs LLM on text + a short system prompt.
5. Backend runs TTS on LLM text → WAV/MP3.
6. Browser plays audio and shows transcript.

Latency target: ≤ 2 s for 5 s utterance on a mid laptop.

## 4) Tech choices (simple and close to your past stack)
- **Frontend**: React + Vite. Use MediaRecorder to capture 16 kHz mono WAV.
- **Backend**: FastAPI (Python 3.11). Single process.
- **ASR (no extra subscription)**: `faster-whisper` small model on CPU. Good enough for a demo.
- **LLM**: Gemini 2.5 Flash‑Lite via API key.
- **TTS**: ElevenLabs streaming or plain synth API.

> You can swap ASR to Deepgram later without changing the API.

## 5) API (one endpoint)
### POST `/api/utterance`
- **Request**: `multipart/form-data` with field `audio` (WAV/PCM) and optional `session_id`.
- **Response 200**: binary audio (MP3 or WAV) with headers:
  - `X-Transcript`: final ASR text
  - `X-Model-Reply`: LLM text (for debugging)

If you prefer JSON, return `{ transcript, reply_text, audio_base64 }` instead. Keep one format; binary is simpler to play.

### GET `/api/health`
- 200 `{ status: "ok" }`

## 6) System prompt (keep tiny)
```
You are a polite apartment receptionist. Be brief. If the user asks about rent or beds, answer with short plain sentences. If you do not know a number, say you don’t know. Do not ask for payment. One or two sentences only.
```

## 7) Demo data (hard‑coded)
Embed a tiny catalog in code for believable answers:
```
UNITS = [
  {"title":"2BR Clifton","rent":120000,"beds":2,"area":"Clifton","notes":"Sea view"},
  {"title":"1BR Gulshan","rent":65000,"beds":1,"area":"Gulshan","notes":"Near park"}
]
```
LLM may read this list and pick the closest.

## 8) Backend sketch (Copilot expands)
- `/api/utterance` steps:
  1) Read audio → temp WAV
  2) `faster_whisper.transcribe()` → `transcript`
  3) `gemini.generate(transcript, UNITS)` → `reply_text`
  4) `elevenlabs.tts(reply_text)` → bytes
  5) Return audio bytes. Add headers for transcript and reply.

Error handling: on any failure, return a short apology audio like “Sorry, I could not process that.”

## 9) Frontend sketch (Copilot expands)
- Button: **Hold to talk** (press = start `MediaRecorder`; release = stop and upload)
- Show: “You said: …” under the button
- Play: create `Audio()` from response bytes and `audio.play()`
- Minimal CSS. No state management lib needed.

## 10) Env vars
- `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`

## 11) Install and run
- Python deps: `fastapi uvicorn pydantic faster-whisper google-generativeai requests python-multipart`
- Node deps: `vite react react-dom`
- Run backend: `uvicorn api.main:app --reload --port 8000`
- Run web: `npm run dev`

## 12) Test cases
- User asks: “Any 2 bedroom in Clifton under 130k?” → reply mentions “2BR Clifton 120k”.
- User asks: “What is your name?” → short polite answer.
- Bad audio → returns a short error audio.

## 13) Definition of done
- Single page runs locally. Click‑talk‑reply loop works.
- Two seeded units referenced correctly. No DB.
- End‑to‑end under 2 s for short queries on a dev laptop.
- Code fits in two folders: `/web` and `/api`.

## 14) Next step after demo (optional)
- Swap ASR to Deepgram streaming.
- Add streaming TTS for faster first phoneme.
- Add barge‑in and continuous conversation.

