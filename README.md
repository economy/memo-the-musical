# Memo: The Musical

A local-first hackathon spike that turns a spoken business-message ramble into structured,
music-ready Message DNA without generating music.

## Setup

1. Install Python 3.12+ and [uv](https://docs.astral.sh/uv/).
2. Copy `.env.example` to `.env` and add an OpenAI key for live realtime calls.
3. Run `uv sync`, then `task dev`.
4. Open `http://127.0.0.1:8000`.

The browser sends microphone audio directly to OpenAI over WebRTC. The API key and agent tools
remain on the server. Normal tests use injected fakes and need neither credentials nor network.

## Commands

- `task dev` — start the local FastAPI server
- `task test` — run the offline test suite
- `task check` — run Ruff, Pyright, and Pytest
- `task smoke` — start the app and verify its health endpoint
- `task live-smoke` — print whether a credentialed live spike can run

## Demo fallback

The intended 60-second demo is documented in `docs/prds/memo-the-musical.md`. If microphone
capture fails, use the same prepared text through the visibly labeled demo-transcript path. If
the network or Realtime API fails, use a visibly labeled replay of the last successful run.
