"""Minimal FastAPI application for the voice receptionist demo."""
from __future__ import annotations

import base64
import logging
import os
import warnings
from copy import deepcopy
from typing import Any
from uuid import uuid4

try:
    import absl.logging as absl_logging  # type: ignore
except ImportError:  # pragma: no cover
    absl_logging = None

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="ctranslate2",
)
warnings.filterwarnings(
    "ignore",
    message="Deprecated call to `pkg_resources.declare_namespace",
    category=DeprecationWarning,
    module="pkg_resources",
)

os.environ.setdefault("GRPC_VERBOSITY", "ERROR")
os.environ.setdefault("GRPC_TRACE", "")

if absl_logging is not None:
    try:
        absl_logging.set_verbosity(absl_logging.ERROR)
    except Exception:  # pragma: no cover
        pass

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from .core.config import settings
from .services.agent import SessionState, handle_turn
from .services.asr import transcribe_audio
from .services.llm import LLMUnavailableError, generate_reply, get_reply_source
from .services.session_store import session_store
from .services.tts import synthesize_speech

logger = logging.getLogger(__name__)

app = FastAPI(title="Rental Agent Demo API", version="0.1.0")

if settings.cors_allow_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

HTML_PAGE = """<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
    <title>Rental Voice Receptionist</title>
    <script src=\"https://cdn.tailwindcss.com\"></script>
</head>
<body class=\"min-h-screen bg-slate-950 text-slate-100\">
    <div class=\"border-b border-slate-800 bg-slate-900/80 backdrop-blur\">
        <div class=\"mx-auto flex max-w-5xl items-center justify-between px-6 py-4\">
            <div class=\"text-lg font-semibold\">Rental Voice Receptionist</div>
            <nav class=\"flex gap-4 text-sm text-slate-400\">
                <span class=\"text-white\">Call</span>
                <span class=\"text-slate-600\">Admin (coming soon)</span>
            </nav>
        </div>
    </div>

    <main class=\"mx-auto max-w-5xl px-6 py-8\">
        <div class=\"grid gap-6 lg:grid-cols-[2fr_1fr]\">
            <section class=\"rounded-2xl border border-slate-800 bg-slate-900/60 p-6\">
                <div class=\"flex flex-wrap items-start justify-between gap-4\">
                    <div>
                        <h2 class=\"text-xl font-semibold\">Call</h2>
                        <p id=\"status\" class=\"text-sm text-slate-400\">Start a call to begin.</p>
                    </div>
                    <button id=\"callButton\" class=\"rounded-full border border-emerald-400/60 px-4 py-2 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-400/10\">Start Call</button>
                </div>

                <div class=\"mt-6 space-y-5\">
                    <div class=\"rounded-xl border border-slate-800 bg-slate-950/50 p-5\">
                        <div class=\"flex items-center justify-between gap-4\">
                            <div>
                                <p class=\"text-sm text-slate-400\">Click-to-talk</p>
                                <p class=\"text-xs text-slate-500\">Tap once to start listening, tap again (or wait 15s) to send.</p>
                            </div>
                            <button id=\"recordButton\" class=\"min-w-[10rem] rounded-full bg-emerald-500 px-5 py-3 text-sm font-semibold text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40\" disabled>Start Listening</button>
                        </div>
                    </div>

                    <div class=\"rounded-xl border border-slate-800 bg-slate-950/50 p-5\">
                        <div class=\"flex items-center justify-between\">
                            <p class=\"text-sm text-slate-400\">Mic level</p>
                            <span id=\"levelValue\" class=\"text-xs text-slate-500\">0%</span>
                        </div>
                        <div class=\"mt-3 h-2 rounded-full bg-slate-800\">
                            <div id=\"levelBar\" class=\"h-full w-0 rounded-full bg-emerald-400 transition-[width]\" style=\"transition-duration:150ms;\"></div>
                        </div>
                    </div>

                    <div class=\"grid gap-4 lg:grid-cols-2\">
                        <div class=\"rounded-xl border border-slate-800 bg-slate-950/50 p-5\">
                            <p class=\"text-sm font-semibold text-slate-200\">You said</p>
                            <p id=\"transcript\" class=\"mt-2 min-h-[3rem] text-sm text-slate-400\">&nbsp;</p>
                        </div>
                        <div class=\"rounded-xl border border-slate-800 bg-slate-950/50 p-5\">
                            <p class=\"text-sm font-semibold text-slate-200\">Assistant replied</p>
                            <p id=\"reply\" class=\"mt-2 min-h-[3rem] text-sm text-slate-400\">&nbsp;</p>
                        </div>
                    </div>

                    <div class=\"rounded-xl border border-slate-800 bg-slate-950/50 p-5\">
                        <p class=\"text-sm font-semibold text-slate-200\">Conversation</p>
                        <div id=\"conversationLog\" class=\"mt-2 max-h-48 space-y-2 overflow-y-auto text-sm text-slate-400\">
                            <p class=\"text-xs text-slate-500\">Conversation will appear here after you start a call.</p>
                        </div>
                    </div>
                </div>
            </section>

            <aside class=\"space-y-5\">
                <section class=\"rounded-2xl border border-slate-800 bg-slate-900/60 p-6\">
                    <h2 class=\"text-lg font-semibold\">What to expect</h2>
                    <ul class=\"mt-4 space-y-3 text-sm text-slate-400\">
                        <li>• Audio is captured in 5–15 second bites.</li>
                        <li>• Whisper handles the transcription on CPU.</li>
                        <li>• Gemini responds using the seeded unit catalog.</li>
                        <li>• Edge TTS returns natural audio instantly.</li>
                    </ul>
                </section>

                <section class=\"rounded-2xl border border-slate-800 bg-slate-900/60 p-6\">
                    <h2 class=\"text-lg font-semibold\">Shortcuts</h2>
                    <p class=\"mt-2 text-sm text-slate-400\">Press the space bar to start and release to send.</p>
                </section>
            </aside>
        </div>

        <footer class=\"mt-12 border-t border-slate-900 pt-6 text-sm text-slate-500\">
            <p>Powered by faster-whisper, Gemini Flash, and Edge TTS. Built with Tailwind on FastAPI.</p>
        </footer>
    </main>

    <audio id=\"audioPlayer\" hidden></audio>

    <script>
        const recordButton = document.getElementById('recordButton');
        const callButton = document.getElementById('callButton');
        const statusEl = document.getElementById('status');
        const transcriptEl = document.getElementById('transcript');
        const replyEl = document.getElementById('reply');
        const conversationLogEl = document.getElementById('conversationLog');
        const audioEl = document.getElementById('audioPlayer');
        const levelBar = document.getElementById('levelBar');
        const levelValue = document.getElementById('levelValue');
        const MAX_RECORDING_MS = 15000;

        let mediaRecorder = null;
        let mediaStream = null;
        let chunks = [];
        let isRecording = false;
        let isCallActive = false;
        let monitorContext = null;
        let analyser = null;
        let dataArray = null;
        let rafId = null;
        let recordingTimeout = null;
        let sessionId = null;
        let conversation = [];

        function setStatus(message) {
            statusEl.textContent = message;
        }

        function updateConversationLog() {
            conversationLogEl.innerHTML = '';

            if (!conversation.length) {
                const placeholder = document.createElement('p');
                placeholder.className = 'text-xs text-slate-500';
                placeholder.textContent = 'Conversation will appear here after you start a call.';
                conversationLogEl.appendChild(placeholder);
                return;
            }

            const fragment = document.createDocumentFragment();
            conversation.forEach((turn) => {
                const wrapper = document.createElement('div');
                const speakerEl = document.createElement('span');
                speakerEl.className = 'font-semibold text-slate-200';
                speakerEl.textContent = turn.role === 'user' ? 'You:' : 'Assistant:';

                const contentEl = document.createElement('span');
                contentEl.className = 'text-slate-400';
                contentEl.textContent = ` ${turn.content}`;

                wrapper.appendChild(speakerEl);
                wrapper.appendChild(contentEl);
                fragment.appendChild(wrapper);
            });

            conversationLogEl.appendChild(fragment);
        }

        function resetTranscripts() {
            transcriptEl.innerHTML = '&nbsp;';
            replyEl.innerHTML = '&nbsp;';
        }

        function resetButton() {
            recordButton.disabled = !isCallActive;
            recordButton.textContent = 'Start Listening';
            recordButton.classList.remove('bg-emerald-400');
            recordButton.classList.add('bg-emerald-500');
        }

        function updateLevel() {
            if (!analyser || !dataArray) {
                return;
            }
            analyser.getByteTimeDomainData(dataArray);
            let sum = 0;
            for (let i = 0; i < dataArray.length; i += 1) {
                const value = dataArray[i] - 128;
                sum += value * value;
            }
            const rms = Math.sqrt(sum / dataArray.length) / 128;
            const percentage = Math.min(1, rms * 2) * 100;
            levelBar.style.width = `${percentage.toFixed(0)}%`;
            levelValue.textContent = `${percentage.toFixed(0)}%`;
            rafId = requestAnimationFrame(updateLevel);
        }

        function resetLevel() {
            levelBar.style.width = '0%';
            levelValue.textContent = '0%';
        }

        function requireActiveCall() {
            if (!isCallActive) {
                setStatus('Start a call before recording.');
                return false;
            }
            return true;
        }

        async function startCall() {
            if (isCallActive) {
                return;
            }

            sessionId = self.crypto?.randomUUID ? self.crypto.randomUUID() : Math.random().toString(36).slice(2);
            isCallActive = true;
            conversation = [];
            updateConversationLog();
            resetTranscripts();
            setStatus('Call started. Tap the mic when you are ready.');
            recordButton.disabled = false;
            callButton.textContent = 'End Call';
            callButton.classList.add('bg-emerald-500/10');
        }

        async function endCall() {
            if (!isCallActive) {
                return;
            }

            if (isRecording) {
                stopRecording();
            }

            recordButton.disabled = true;
            callButton.textContent = 'Start Call';
            callButton.classList.remove('bg-emerald-500/10');
            setStatus('Call ended. Start a new call to continue.');
            isCallActive = false;

            if (sessionId) {
                try {
                    await fetch('/api/session/reset', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ session_id: sessionId }),
                    });
                } catch (error) {
                    console.warn('Failed to reset server session:', error);
                }
            }

            sessionId = null;
            conversation = [];
            updateConversationLog();
            resetTranscripts();
        }

        async function startRecording() {
            if (!requireActiveCall() || isRecording) {
                return;
            }

            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

                const options = {};
                if (MediaRecorder.isTypeSupported('audio/webm')) {
                    options.mimeType = 'audio/webm';
                }

                mediaRecorder = new MediaRecorder(mediaStream, options);
                chunks = [];

                mediaRecorder.addEventListener('dataavailable', (event) => {
                    if (event.data && event.data.size > 0) {
                        chunks.push(event.data);
                    }
                });

                mediaRecorder.addEventListener('stop', async () => {
                    try {
                        if (!chunks.length) {
                            throw new Error('No audio data captured');
                        }

                        const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                        const wavBlob = await convertToWav(blob);
                        await submitAudio(wavBlob);
                    } catch (error) {
                        console.error(error);
                        setStatus('Recording failed. Please try again.');
                    } finally {
                        cleanupStream();
                        resetButton();
                        isRecording = false;
                    }
                });

                setupMonitor(mediaStream);

                mediaRecorder.start();
                isRecording = true;
                recordButton.textContent = 'Stop & Send';
                recordButton.classList.remove('bg-emerald-500');
                recordButton.classList.add('bg-emerald-400');
                setStatus('Listening... tap stop when you are done.');
                recordingTimeout = setTimeout(() => {
                    stopRecording();
                }, MAX_RECORDING_MS);
            } catch (error) {
                console.error(error);
                setStatus('Microphone access denied or unavailable.');
                cleanupStream();
                resetButton();
            }
        }

        function setupMonitor(stream) {
            resetLevel();
            try {
                monitorContext = new (window.AudioContext || window.webkitAudioContext)();
                const source = monitorContext.createMediaStreamSource(stream);
                analyser = monitorContext.createAnalyser();
                analyser.fftSize = 1024;
                const bufferLength = analyser.fftSize;
                dataArray = new Uint8Array(bufferLength);
                source.connect(analyser);
                rafId = requestAnimationFrame(updateLevel);
            } catch (error) {
                console.warn('Unable to initialise meter:', error);
                resetLevel();
            }
        }

        function stopRecording() {
            if (!isRecording || !mediaRecorder) {
                return;
            }
            setStatus('Processing...');
            recordButton.disabled = true;
            if (recordingTimeout) {
                clearTimeout(recordingTimeout);
                recordingTimeout = null;
            }
            mediaRecorder.stop();
        }

        function cleanupStream() {
            if (mediaStream) {
                mediaStream.getTracks().forEach((track) => track.stop());
                mediaStream = null;
            }
            if (rafId) {
                cancelAnimationFrame(rafId);
                rafId = null;
            }
            if (monitorContext) {
                monitorContext.close().catch(() => undefined);
                monitorContext = null;
            }
            analyser = null;
            dataArray = null;
            resetLevel();
            mediaRecorder = null;
            chunks = [];
            if (recordingTimeout) {
                clearTimeout(recordingTimeout);
                recordingTimeout = null;
            }
        }

        async function convertToWav(blob) {
            const arrayBuffer = await blob.arrayBuffer();
            const context = new (window.AudioContext || window.webkitAudioContext)();
            const audioBuffer = await context.decodeAudioData(arrayBuffer);
            const wavBuffer = audioBufferToWav(audioBuffer);
            await context.close();
            return new Blob([wavBuffer], { type: 'audio/wav' });
        }

        function audioBufferToWav(buffer) {
            const numberOfChannels = buffer.numberOfChannels;
            const sampleRate = buffer.sampleRate;
            const format = 1;
            const bitsPerSample = 16;

            let samples;
            if (numberOfChannels === 1) {
                samples = buffer.getChannelData(0);
            } else {
                const length = buffer.getChannelData(0).length;
                samples = new Float32Array(length);
                for (let channel = 0; channel < numberOfChannels; channel += 1) {
                    const channelData = buffer.getChannelData(channel);
                    for (let i = 0; i < length; i += 1) {
                        samples[i] += channelData[i];
                    }
                }
                for (let i = 0; i < samples.length; i += 1) {
                    samples[i] /= numberOfChannels;
                }
            }

            const byteRate = (sampleRate * bitsPerSample) / 8;
            const blockAlign = bitsPerSample / 8;
            const bufferLength = 44 + samples.length * 2;
            const arrayBuffer = new ArrayBuffer(bufferLength);
            const view = new DataView(arrayBuffer);

            function writeString(viewRef, offset, string) {
                for (let i = 0; i < string.length; i += 1) {
                    viewRef.setUint8(offset + i, string.charCodeAt(i));
                }
            }

            let offset = 0;
            writeString(view, offset, 'RIFF'); offset += 4;
            view.setUint32(offset, 36 + samples.length * 2, true); offset += 4;
            writeString(view, offset, 'WAVE'); offset += 4;
            writeString(view, offset, 'fmt '); offset += 4;
            view.setUint32(offset, 16, true); offset += 4;
            view.setUint16(offset, format, true); offset += 2;
            view.setUint16(offset, 1, true); offset += 2;
            view.setUint32(offset, sampleRate, true); offset += 4;
            view.setUint32(offset, byteRate, true); offset += 4;
            view.setUint16(offset, blockAlign, true); offset += 2;
            view.setUint16(offset, bitsPerSample, true); offset += 2;
            writeString(view, offset, 'data'); offset += 4;
            view.setUint32(offset, samples.length * 2, true); offset += 4;

            for (let i = 0; i < samples.length; i += 1) {
                let sample = Math.max(-1, Math.min(1, samples[i]));
                sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
                view.setInt16(offset, sample, true);
                offset += 2;
            }

            return arrayBuffer;
        }

        async function submitAudio(wavBlob) {
            setStatus('Sending audio...');
            const formData = new FormData();
            formData.append('audio', wavBlob, 'recording.wav');

            const endpoint = sessionId
                ? `/api/utterance?session_id=${encodeURIComponent(sessionId)}`
                : '/api/utterance';

            try {
                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData,
                });

                const transcript = response.headers.get('X-Transcript') || '';
                const reply = response.headers.get('X-Model-Reply') || '';
                const hadError = response.headers.get('X-Error') === 'true';
                const sessionHeader = response.headers.get('X-Session-Id');
                if (sessionHeader) {
                    sessionId = sessionHeader;
                }
                const stage = response.headers.get('X-Agent-Stage') || '';
                const completed = response.headers.get('X-Agent-Completed') === 'true';

                if (transcript) {
                    conversation.push({ role: 'user', content: transcript });
                }
                if (reply) {
                    conversation.push({ role: 'assistant', content: reply });
                }
                updateConversationLog();

                transcriptEl.textContent = transcript || '•';
                replyEl.textContent = reply || '•';

                const contentType = response.headers.get('Content-Type') || 'audio/mpeg';
                const buffer = await response.arrayBuffer();
                const audioBlob = new Blob([buffer], { type: contentType });
                const url = URL.createObjectURL(audioBlob);
                audioEl.src = url;
                try {
                    await audioEl.play();
                } catch (error) {
                    console.warn('Autoplay prevented:', error);
                }

                if (hadError) {
                    const reason = response.headers.get('X-Error-Reason');
                    if (reason === 'llm_unavailable') {
                        setStatus('Our LLM provider is unavailable right now. Please try again soon.');
                    } else {
                        setStatus('I could not process that clip. Please try again.');
                    }
                } else if (completed) {
                    setStatus('Viewing request noted. Let me know if you need anything else.');
                } else if (stage === 'gathering') {
                    setStatus('Collecting your preferences...');
                } else if (stage === 'recommending') {
                    setStatus('Reviewing matching listings for you...');
                } else if (stage === 'booking') {
                    setStatus('Grabbing booking details...');
                } else {
                    setStatus('Ready for your next clip.');
                }
            } catch (error) {
                console.error(error);
                setStatus('Network error while sending audio. Please try again.');
            }
        }

        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
            setStatus('Audio recording is not supported in this browser.');
            recordButton.disabled = true;
        }

        callButton.addEventListener('click', (event) => {
            event.preventDefault();
            if (isCallActive) {
                void endCall();
            } else {
                startCall();
            }
        });

        recordButton.addEventListener('click', (event) => {
            event.preventDefault();
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });

        document.addEventListener('keydown', (event) => {
            if (event.code === 'Space') {
                if (event.repeat) {
                    return;
                }
                event.preventDefault();
                if (isRecording) {
                    stopRecording();
                } else {
                    startRecording();
                }
            }
        });

        updateConversationLog();
    </script>
</body>
</html>
"""
@app.get("/", response_class=HTMLResponse, tags=["meta"])
async def index() -> HTMLResponse:
    """Serve the single-page demo UI."""

    return HTMLResponse(content=HTML_PAGE)


@app.head("/", tags=["meta"])
async def index_head() -> Response:
    """Fast health checks issue HEAD /; answer with 200 to avoid noisy 405s."""

    return Response(status_code=200)


FAVICON_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
)


@app.get("/api/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Simple liveness probe."""

    return {"status": "ok"}


@app.head("/api/health", tags=["meta"])
async def health_head() -> Response:
    """Allow HEAD for uptime monitors that only need the status code."""

    return Response(status_code=200)


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots() -> PlainTextResponse:
    """Serve a minimal robots.txt to avoid 404 noise."""

    return PlainTextResponse("User-agent: *\nDisallow:")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Return a tiny placeholder favicon."""

    return Response(content=FAVICON_BYTES, media_type="image/png")


@app.post("/api/session/reset", tags=["voice"])
async def reset_session(payload: dict[str, str] = Body(...)) -> dict[str, str]:
    """Clear the agent session state when a call ends."""

    session_id = payload.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    session_store.clear(session_id)
    return {"status": "cleared"}


@app.post("/api/utterance", tags=["voice"])
async def process_utterance(audio: UploadFile = File(...), session_id: str | None = None) -> Response:
    """Handle a single push-to-talk turn."""

    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Audio payload was empty")

    resolved_session_id = session_id or str(uuid4())
    existing_state = session_store.get(resolved_session_id)
    previous_state = deepcopy(existing_state) if existing_state is not None else None
    state = existing_state or SessionState(session_id=resolved_session_id)

    try:
        transcript = await transcribe_audio(audio_bytes)
        if not transcript:
            raise ValueError("Transcription returned empty text")

        agent_turn = handle_turn(state, transcript)

        reply_source = "unknown"
        try:
            reply_text = await generate_reply(transcript, agent_result=agent_turn, state=state)
            if not reply_text:
                reply_text = agent_turn.reply_text
                reply_source = "policy-template"
            else:
                reply_source = get_reply_source() or "unknown"
        except LLMUnavailableError:
            if previous_state is not None:
                session_store.save(previous_state)
            else:
                session_store.clear(resolved_session_id)
            raise
        except Exception as exc:  # noqa: BLE001 - degrade to templated reply
            logger.exception("LLM polishing failed, using policy template: %s", exc)
            reply_text = agent_turn.reply_text
            reply_source = "policy-template"

        if state.history and state.history[-1].get("role") == "assistant":
            state.history[-1]["content"] = reply_text

        session_store.save(state)

        audio_payload, media_type = await synthesize_speech(reply_text)

        headers: dict[str, Any] = {
            "X-Transcript": transcript,
            "X-Model-Reply": reply_text,
            "X-Session-Id": resolved_session_id,
            "X-LLM-Source": reply_source,
            "X-Agent-Stage": agent_turn.stage,
        }
        if agent_turn.listing:
            headers["X-Listing-Id"] = agent_turn.listing.id
        if agent_turn.completed:
            headers["X-Agent-Completed"] = "true"

        return Response(content=audio_payload, media_type=media_type, headers=headers)

    except LLMUnavailableError as exc:
        logger.exception("All Gemini models failed: %s", exc)
        apology = "Our language service is temporarily unavailable. Please try again shortly."
        fallback_audio, media_type = await synthesize_speech(apology)
        headers = {
            "X-Transcript": transcript if "transcript" in locals() else "",
            "X-Model-Reply": apology,
            "X-Error": "true",
            "X-Error-Reason": "llm_unavailable",
            "X-LLM-Source": "unavailable",
            "X-Session-Id": resolved_session_id,
        }
        return Response(content=fallback_audio, media_type=media_type, headers=headers, status_code=503)

    except Exception as exc:  # noqa: BLE001 - we want a single fallback path
        logger.exception("Failed processing utterance: %s", exc)
        apology = "Sorry, I could not process that."
        fallback_audio, media_type = await synthesize_speech(apology)
        if previous_state is not None:
            session_store.save(previous_state)
        else:
            session_store.clear(resolved_session_id)
        headers = {
            "X-Transcript": "",
            "X-Model-Reply": apology,
            "X-Error": "true",
            "X-LLM-Source": "error",
            "X-Error-Reason": "unknown",
            "X-Session-Id": resolved_session_id,
        }
        return Response(content=fallback_audio, media_type=media_type, headers=headers, status_code=500)
