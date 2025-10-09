# 1. Project overview
A web-only voice receptionist for apartment rentals. A visitor clicks Call on the website. A real-time call starts in the browser. The agent listens, understands, queries your listings, quotes prices, books viewings, and sends follow-ups. No phone network.

**Primary goal:** Human-like, low-latency, full-duplex voice conversation that is grounded in your database.

**Target stack:**
- Transport: WebRTC in browser. Optionally LiveKit Cloud.
- ASR: Deepgram streaming.
- TTS: ElevenLabs streaming.
- LLM: Gemini 2.5 Flash-Lite. OpenAI is an option.
- Backend: FastAPI.
- Data: Postgres. Redis for session state.

---
# 2. Scope
## 2.1 In scope
- Real-time bidirectional audio in the browser.
- Live captions and conversation transcript.
- Search listings by filters.
- Quote monthly rent, deposits, fees, utilities, rules.
- Offer viewing time slots and book.
- Human handoff button to request a call back.
- Admin dashboard for calls, transcripts, leads, and appointments.

## 2.2 Out of scope (MVP)
- Payments on call.
- Send summary by SMS or email.
- Phone numbers and PSTN calls.
- Multilingual beyond English.

---
# 3. Users and stories
**Visitor**
- As a visitor, I press Call to speak to the agent in the page.
- As a visitor, I ask for a 2 bed under a budget and get matching units.
- As a visitor, I can interrupt the agent by speaking.
- As a visitor, I can book a viewing at a suggested time.
- As a visitor, I can receive a recap by SMS or email.

**Leasing team**
- As staff, I can see leads, calls, summaries, and bookings.
- As staff, I can mark outcomes and add notes.

---
# 4. Functional requirements with acceptance criteria
FR1. Web call
- Start, maintain, and end a WebRTC call in the page.
- AC: Call starts under 2 seconds on a typical connection.
- AC: Round-trip latency p95 under 600 ms during speech turns.

FR2. Live ASR captions
- Show partial and final captions.
- AC: Partial captions appear within 300 ms of user speech.

FR3. Natural voice replies
- Stream ElevenLabs TTS in real time.
- AC: First audio chunk within 400 ms after LLM token starts.

FR4. Barge-in
- Stop TTS immediately when the user begins speaking.
- AC: TTS stops within 150 ms of VAD trigger.

FR5. Grounded answers
- Quote numbers only from DB or configured policy.
- AC: No price is returned if not present in DB. Agent asks to clarify or offers to follow up.

FR6. Listing search
- Filters: location, min-max rent, beds, baths, furnished, date, amenities.
- AC: First page returns under 300 ms for 10k units indexed.

FR7. Booking
- Show available slots. Create appointment and send confirm.
- AC: Double booking prevented. Calendar holds created.

FR8. Follow-up
- Send recap by SMS or email with links.
- AC: Delivery confirmation stored.

FR9. Admin dashboard
- List calls, transcripts, leads, bookings. Search by date, status.
- AC: Page loads in under 2 seconds for 1k records.

FR10. Privacy and consent
- Show a short consent banner for recording.
- AC: Do not store audio if user declines. Store only minimal metadata.

---
# 5. Non-functional requirements
- Latency: p95 under 600 ms per turn. p50 under 350 ms.
- Availability: 99.5 percent monthly.
- Data retention: transcripts 90 days in MVP. Configurable.
- Security: HTTPS only. JWT session for admin. No card data.
- Observability: structured logs, metrics, and traces for each turn.

---
# 6. System architecture
**Components**
- Web app: React with WebRTC client, captions, transcript, and UI for results and booking.
- RTC gateway: FastAPI service for signaling and optional LiveKit token. Media routed over WebRTC to ASR and TTS.
- Agent service: LLM orchestration, retrieval, tool routing, policy enforcement.
- Data services: Postgres, Redis.
- Integrations: Deepgram streaming, ElevenLabs streaming, Gmail or SendGrid, SMS provider, Google Calendar or Calendly.

**Data flow**
1. Browser gets mic via getUserMedia.
2. Browser establishes WebRTC with backend and sends audio frames.
3. Backend streams to Deepgram. Partial transcripts stream back to UI.
4. Agent runs LLM over rolling context. Agent calls tools for search and booking.
5. Agent streams reply text to ElevenLabs. TTS audio streams back over WebRTC.
6. Barge-in stops TTS when VAD detects user speech.

---
# 7. Sequence descriptions
**Start call**
- Client: POST /rtc/token → get token.
- Client: create RTCPeerConnection and attach tracks.
- Server: on audio frames, forward to Deepgram. Emit partial captions.

**Search and quote**
- LLM detects intent → call search_listings.
- Backend queries Postgres with filters and returns ranked units.
- Agent summarizes and quotes rent, deposit, utilities, and rules.

**Booking**
- LLM calls list_slots → user picks → LLM calls book_viewing.
- Backend writes appointment, places calendar hold, sends confirm.

---
# 8. API contracts (Copilot-ready)
All responses JSON with snake_case keys. Auth: session cookie for web, JWT for admin API.

POST /api/rtc/token
- Body: { "room": "public", "user_id": "anon-uuid" }
- 200: { "token": "...", "expires_in": 3600 }

POST /api/agent/events
- Body: { "session_id": "uuid", "type": "vad_start|vad_end|tts_stop", "ts": "iso8601" }
- 204

POST /api/agent/tool/search_listings
- Body: { "filters": { "location": "string", "rent_min": 0, "rent_max": 0, "beds": 0, "baths": 0, "furnished": true, "amenities": ["parking","lift"], "available_from": "date" }, "limit": 20, "cursor": "optional" }
- 200: { "results": [ { "unit_id": "uuid", "property_id": "uuid", "title": "2BR at Clifton", "rent": 120000, "deposit": 240000, "baths": 2, "beds": 2, "sqft": 950, "furnished": false, "amenities": ["parking"], "address": "...", "images": ["url"], "available_from": "date" } ], "next_cursor": null }

POST /api/agent/tool/quote_total
- Body: { "unit_id": "uuid", "start_date": "date" }
- 200: { "rent": 120000, "deposit": 240000, "fees": [{"name":"application","amount":2000}], "utilities_included": ["water"], "notes": "Policy text" }

POST /api/agent/tool/list_slots
- Body: { "unit_id": "uuid", "days_ahead": 14 }
- 200: { "slots": [ {"start":"2025-10-12T10:00:00Z","end":"2025-10-12T10:30:00Z"} ] }

POST /api/agent/tool/book_viewing
- Body: { "unit_id": "uuid", "slot_start": "iso8601", "visitor": { "name": "string", "phone": "string", "email": "string" } }
- 200: { "appointment_id": "uuid", "calendar_event_url": "url" }

POST /api/agent/tool/send_followup
- Body: { "lead_id": "uuid", "channel": "sms|email" }
- 200: { "status": "sent" }

GET /api/admin/calls?from=&to=&q=
- 200: { "items": [ { "call_id":"uuid", "started_at":"iso", "duration_sec":120, "lead_id":"uuid", "outcome":"booked|info|abandoned" } ] }

GET /api/admin/calls/{call_id}
- 200: { "call": { "transcript": [ {"speaker":"user|agent","ts":"iso","text":"..."} ], "summary":"...", "metrics": {"avg_latency_ms":310,"barge_ins":2} } }

---
# 9. Data model
**Entities**
- properties(id, name, address, city, policies_json)
- units(id, property_id, title, beds, baths, sqft, rent, deposit, furnished, amenities, available_from, images)
- availability(unit_id, date_from, status)
- leads(id, name, phone, email, source, stage)
- appointments(id, lead_id, unit_id, slot_start, slot_end, status, calendar_url)
- calls(id, lead_id, started_at, duration_sec, outcome, transcript_uri, metrics_json)

**DDL (Postgres)**
```sql
create table properties (
  id uuid primary key,
  name text not null,
  address text not null,
  city text not null,
  policies_json jsonb default '{}'::jsonb
);

create table units (
  id uuid primary key,
  property_id uuid references properties(id) on delete cascade,
  title text not null,
  beds int not null,
  baths int not null,
  sqft int,
  rent int not null,
  deposit int,
  furnished boolean default false,
  amenities text[] default '{}',
  available_from date,
  images text[] default '{}'
);

create table availability (
  unit_id uuid references units(id) on delete cascade,
  date_from date not null,
  status text check (status in ('available','on_hold','rented')) not null,
  primary key (unit_id, date_from)
);

create table leads (
  id uuid primary key,
  name text,
  phone text,
  email text,
  source text,
  stage text check (stage in ('new','engaged','booked','lost')) default 'new'
);

create table appointments (
  id uuid primary key,
  lead_id uuid references leads(id) on delete set null,
  unit_id uuid references units(id) on delete cascade,
  slot_start timestamptz not null,
  slot_end timestamptz not null,
  status text check (status in ('scheduled','completed','canceled')) default 'scheduled',
  calendar_url text
);

create table calls (
  id uuid primary key,
  lead_id uuid references leads(id) on delete set null,
  started_at timestamptz not null default now(),
  duration_sec int,
  outcome text,
  transcript_uri text,
  metrics_json jsonb default '{}'::jsonb
);
```

---
# 10. LLM prompt and tool schema
**System prompt**
- You are a leasing receptionist on a website.
- Speak concisely and naturally.
- Never invent prices or policies. Only answer with DB or policy docs.
- If unsure, ask a short follow-up.
- Offer to book viewings and send summaries.
- Stop speaking when the user starts talking.

**Function signatures**
- search_listings(filters, limit, cursor)
- quote_total(unit_id, start_date)
- list_slots(unit_id, days_ahead)
- book_viewing(unit_id, slot_start, visitor)
- send_followup(lead_id, channel)

**Hallucination guard**
- If a numeric answer is requested and not found, return: "I do not have that number. I can check with a person and follow up."

---
# 11. Frontend spec
**Views**
- CallPanel: Call button, VU meter, captions, stop call.
- Results: cards of units with CTA to book.
- Booking: slot picker.
- Recap: send to SMS or email.
- Admin: Calls, Leads, Appointments.

**WebRTC client**
- Use insertable streams if needed for VAD.
- Auto-reconnect on ICE failure.
- Cancel TTS on VAD start.

**State**
- session_id, call_state, partial_caption, final_transcript[], results[], booking_state.

---
# 12. Realtime pipeline
- Capture 16 kHz mono PCM.
- Send to Deepgram streaming. Receive partial and final transcripts.
- Append partials to on-screen captions. Replace with final when committed.
- For replies, stream tokens to ElevenLabs. Push PCM chunks to WebRTC downlink.
- VAD triggers: on RMS threshold over 150 ms, send tts_stop event and cut the downlink source.

---
# 13. Configuration
**Env vars**
- DEEPGRAM_API_KEY
- ELEVENLABS_API_KEY
- GEMINI_API_KEY
- LIVEKIT_API_KEY, LIVEKIT_API_SECRET, LIVEKIT_URL (optional)
- DATABASE_URL
- REDIS_URL
- EMAIL_FROM, SENDGRID_API_KEY (or Gmail)
- SMS_PROVIDER_KEY (optional)

**Local workflow**
- Run the FastAPI backend with `uvicorn app.main:app --reload` from `apps/api`.
- Run the React frontend with `npm run dev` from `apps/web`.
- External dependencies (Neon Postgres, Redis if required) are accessed as managed services rather than containers.

---
# 14. Logging and metrics
- Per turn: asr_latency_ms, tts_start_ms, tts_total_ms, barge_in_count, llm_tokens_in, llm_tokens_out.
- Per call: duration, outcome, booked, abandonment, errors.
- PII scrubbing for logs.

---
# 15. Test plan
**Unit tests**
- Tools: search, quote, booking conflict.
- VAD: start and stop thresholds.

**Integration**
- WebRTC loop with mock ASR and TTS.
- Booking end to end with calendar.

**Load**
- 50 concurrent calls with 20 percent barge-in rate.

**Acceptance (Gherkin snippets)**
```
Feature: Book viewing by budget
  Scenario: User finds a 2BR under budget
    Given seeded units with rent and availability
    When the user asks for a 2 bedroom under 120000
    Then the agent lists up to 5 units with rent and availability
    And the user can pick a slot to book
```
```
Feature: Guard pricing
  Scenario: Price not in DB
    Given a unit without a deposit value
    When the user asks for deposit amount
    Then the agent says it does not have that number
    And offers to follow up by SMS or email
```

---
# 16. Rollout plan
Week 1
- DB and tools. WebRTC signaling. Streaming ASR and captions.
- LLM prompt with tool calls. ElevenLabs streaming.
Week 2
- Booking integration. SMS and email summaries.
- Admin dashboard. Metrics. QA. Deploy.

---
# 17. ADRs
ADR-001: Web-only via WebRTC. Rationale: low latency, simpler UX. Alternative: Twilio phone. Not chosen.
ADR-002: Deepgram streaming ASR. Rationale: low latency and stable APIs. Alternative: Whisper server.
ADR-003: ElevenLabs streaming TTS. Rationale: most human voice. Alternative: model vendor TTS.
ADR-004: Gemini 2.5 Flash-Lite as LLM. Rationale: cost and speed. Alternative: OpenAI.

---
# 18. Risks and mitigations
- Network jitter increases latency. Mitigate with WebRTC jitter buffers and smaller TTS chunks.
- Hallucinated numbers. Mitigate with guards and DB checks.
- Double bookings. Mitigate with unique slot constraint and transactions.
- Privacy. Mitigate with consent banner and retention policy.

---
# 19. Cost notes (web-only)
- Deepgram: pay per audio minute.
- ElevenLabs: plan minutes plus overage per minute.
- LiveKit: participant minutes and agent minutes.
- LLM: token-based. Flash-Lite is cheap.

---
# 20. Repo layout and Copilot tasks
**Layout**
```
/README.md
/apps
  /web           # React + Vite
  /api           # FastAPI, agents, tools, rtc signaling
  /infra         # (removed; direct terminal workflow in use)

```

**Web tasks for Copilot**
1. Create a React CallPanel with a Call button, VU meter, captions area, and Stop button.
2. Implement WebRTC connect using a token from /api/rtc/token. Attach mic track. Handle ICE and reconnect.
3. Show partial captions from server over WebSocket. Replace with final on commit.
4. Render search results as cards with rent, beds, baths, furnished, and CTA.
5. Implement booking dialog with slot picker.

**API tasks for Copilot**
1. FastAPI app with /api/rtc/token, /api/agent/tool/* endpoints.
2. Deepgram streaming client that emits partial and final captions.
3. ElevenLabs streaming client that yields PCM frames.
4. Agent loop that buffers ASR, runs LLM with tool calling, streams TTS.
5. Postgres models and queries for listings and availability.
6. Booking API that enforces unique slot per unit.
7. Email and SMS senders with provider adapters.

**Comments to seed Copilot**
- Add docstrings that describe the turn-by-turn timing targets.
- Add type hints on all public functions.
- Add TODOs that reference the API contracts in section 8.

---
# 21. Example code stubs (for Copilot to expand)
**FastAPI router skeleton**
```python
# api/main.py
from fastapi import FastAPI, Depends
from routers import rtc, tools, admin

app = FastAPI()
app.include_router(rtc.router, prefix="/api/rtc")
app.include_router(tools.router, prefix="/api/agent/tool")
app.include_router(admin.router, prefix="/api/admin")
```

**Agent loop sketch**
```python
class AgentSession:
    def __init__(self, session_id, asr, tts, llm, tools):
        self.ctx = []  # rolling transcript turns
        self.speaking = False

    async def on_user_audio(self, pcm_chunk):
        text, is_final = await self.asr.feed(pcm_chunk)
        if text:
            yield {"type": "caption", "partial": not is_final, "text": text}
            if is_final:
                self.ctx.append({"speaker":"user","text":text})
                await self.reply()

    async def reply(self):
        plan = await self.llm.plan(self.ctx)
        for step in plan:
            if step["type"] == "tool":
                data = await self.tools.call(step["name"], step["args"])
                self.ctx.append({"speaker":"tool","name":step["name"],"data":data})
        async for audio in self.tts.stream(await self.llm.speak(self.ctx)):
            if self.detect_barge_in():
                await self.tts.stop()
                break
            yield {"type": "audio", "pcm": audio}
```

**Booking unique index**
```sql
create unique index uniq_unit_slot on appointments(unit_id, slot_start);
```

---
# 22. Definition of done
- Web call stable in Chrome and Safari.
- p95 latency under 600 ms on test network.
- Correct pricing and policies for seeded data.
- Booking prevents conflicts and sends a confirmation.
- Admin views show calls, leads, and bookings.
- Logs and metrics available. QA checklist passed.

