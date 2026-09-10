# Memo: The Musical

A local-first hackathon spike that turns a spoken business-message ramble into structured,
music-ready Message DNA without generating music.

## Setup

1. Install Python 3.12+ and [uv](https://docs.astral.sh/uv/).
2. Copy `.env.example` to `.env` and add an OpenAI key for live realtime calls.
3. Run `uv sync`, then `task dev`.
4. Open `http://127.0.0.1:8885`.

The browser sends microphone audio directly to OpenAI over WebRTC. The API key and agent tools
remain on the server. Normal tests use injected fakes and need neither credentials nor network.

## Commands

- `task dev` — start the local FastAPI server
- `task test` — run the offline test suite
- `task check` — run Ruff, Pyright, and Pytest
- `task smoke` — start the app and verify its health endpoint
- `task live-smoke` — print whether a credentialed live spike can run

## 60-second demo script

Use the presenter rail on the home page, or follow this exact sequence:

1. **0:00–0:07 — Hook:** “Business messages are boring. Catchy misinformation is worse. Memo is
   the safety preflight before a memo becomes music.”
2. **0:07–0:27 — Live voice:** Click **Start Voice Session** and say:
   “Make our security training reminder memorable. Everyone, including contractors, must complete
   LearnHub by Friday, October 16 at 5 PM Pacific. It takes about 12 minutes. Give it playful
   spy-movie energy, but never joke about phishing victims. Actually, correction: Thursday,
   October 15—not Friday. Don’t invent prizes.”
3. **0:27–0:36 — Follow-up:** When asked about teasing procrastination, answer: “Lightly tease
   procrastination, never individuals.”
4. **0:36–0:49 — Reveal:** Point to Message DNA: superseded Friday deadline, active Thursday
   deadline, Chorus, CTA, audience, vibe, guardrails, and unresolved LearnHub URL.
5. **0:49–0:55 — Persistence:** Reload the page and show the same project from SQLite.
6. **0:55–1:00 — Close:** “Memo doesn’t write the song. It makes sure the song knows what it is
   allowed to sing.”

## Fallback sequence

1. **Microphone fails:** Start a live session, click **Use Demo Transcript**. The badge stays
   **LIVE** and the exact prepared text is sent through the active Realtime data channel.
2. **Network or Realtime fails:** Click **Replay Last Run**. The badge switches to **REPLAY**
   and loads the pre-seeded completed `security-training-replay` project from SQLite. This is
   never presented as live.
3. **Last resort:** Manual editing remains outside this demo path.

The presenter rail can be hidden with one click during the talk track.
