# SoundSight

A mobile-first local AI app for Deaf and hard-of-hearing users that listens for important sounds and turns them into visual alerts.

## Project Layout

- `frontend/`: Next.js TypeScript UI.
- `backend/`: FastAPI Python backend managed with `uv`.
- `supporting-data-images-audio/`: demo audio and image assets.

## Modes

### Demo Mode

Demo mode is available at `/` and `/demo`. It keeps the existing clip picker interface, plays local demo audio clips, and streams backend events from:

```http
POST /api/demo/stream-events
```

The frontend displays the alert payloads returned by the backend. Local hardcoded fallback alert schedules are not used.

### Live Mode

Live mode is available at `/live`. It requests browser microphone permission and uses `MediaRecorder`/`getUserMedia` to capture overlapping audio windows:

- each window records about 4 seconds of microphone audio
- a new window starts every 2 seconds while listening
- each completed window is uploaded as `multipart/form-data`
- the backend decides whether detector results should call the model

Live mode is not raw WebSocket streaming, WebRTC, or continuous frontend model calling yet.

Live windows are sent to:

```http
POST /api/live/process-window
Content-Type: multipart/form-data

audio=<file/blob>
language=en|hi|es
sessionId=<optional>
```

The endpoint returns NDJSON using the same event schema as Demo mode, including `session_started`, `engine_log`, `model_call`, `model_result`, `alert_start`, `alert_end`, `model_error`, and `session_done`.

## Run Locally

### Backend

Install dependencies:

```bash
cd backend
uv sync
```

Run in deterministic dummy mode on Windows PowerShell:

```powershell
cd backend
uv sync
$env:SOUNDSIGHT_MODEL_MODE="dummy"
$env:SOUNDSIGHT_TRIGGER_MODE="detector"
uv run uvicorn app.main:app --reload --port 8000
```

Dummy mode is the default when `SOUNDSIGHT_MODEL_MODE` is unset. Backend-specific instructions are in `backend/README.md`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000`. To change it:

```bash
NEXT_PUBLIC_SOUNDSIGHT_API_URL=http://localhost:8000 npm run dev
```

Open:

- Demo: `http://localhost:3000/` or `http://localhost:3000/demo`
- Live: `http://localhost:3000/live`

## Test Live Mode In Dummy Mode

1. Start the backend in dummy mode.
2. Start the frontend.
3. Open `http://localhost:3000/live`.
4. Click `Start Listening`.
5. Allow microphone permission.
6. Play or make a detectable sound near the microphone.
7. Confirm the live screen shows backend-generated alerts and clears when `alert_end` arrives.

You can also test the live endpoint with a known demo file:

```bash
cd backend
curl -N \
  -F "audio=@../supporting-data-images-audio/audio-clips/fire-alarm-414915.mp3" \
  -F "language=en" \
  http://localhost:8000/api/live/process-window
```

## Model Modes

SoundSight uses one model mode variable:

```bash
SOUNDSIGHT_MODEL_MODE=dummy | cactus
SOUNDSIGHT_TRIGGER_MODE=detector | interval
SOUNDSIGHT_INTERVAL_SECONDS=2.0
```

### Dummy Mode

Dummy mode is deterministic, works on Windows, and keeps all dummy alert payloads centralized in `backend/app/model/dummy_gateway.py`.

### Cactus Mode

Cactus mode is intended for macOS/Linux testing with the Cactus Python FFI bindings and Gemma 4 native audio support. It is not expected to run on native Windows.

Official Cactus references:

- [Cactus Python SDK](https://docs.cactuscompute.com/latest/python/)
- [Cactus Quickstart](https://docs.cactuscompute.com/latest/docs/quickstart/)
- [Gemma 4 on Cactus](https://docs.cactuscompute.com/latest/blog/gemma4/)

Example setup:

```bash
git clone https://github.com/cactus-compute/cactus ~/cactus
cd ~/cactus
source ./setup
cactus build --python
cactus download google/gemma-4-E2B-it
```

Linux may also need:

```bash
sudo apt-get install python3 python3-venv python3-pip cmake build-essential libcurl4-openssl-dev
```

Run SoundSight with Cactus:

```bash
cd backend
export SOUNDSIGHT_MODEL_MODE=cactus
export SOUNDSIGHT_TRIGGER_MODE=detector
export SOUNDSIGHT_CACTUS_REPO="$HOME/cactus"
export SOUNDSIGHT_CACTUS_MODEL="google/gemma-4-E2B-it"
export SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it"
uv run uvicorn app.main:app --reload --port 8000
```

`SOUNDSIGHT_CACTUS_MODEL_PATH` can be omitted if the Cactus `src.downloads.ensure_model` helper is available.

To verify Cactus integration on macOS/Linux:

```bash
cd backend
uv run python scripts/smoke_test_cactus_audio.py
```

Then run Demo or Live and inspect the NDJSON stream for `model_call` and `model_result` events with `"source":"cactus"`.
