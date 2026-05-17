# SoundSight Backend

FastAPI backend for SoundSight audio windowing, model calls, and alert stream events.

## Layout

```text
backend/
  app/
    main.py
    config.py
    schemas.py
    audio/
      loader.py
      windowing.py
      detector.py
    model/
      gateway.py
      no_alert.py
      dummy_gateway.py
      cactus_gateway.py
    realtime/
      event_reconciler.py
      stream_runner.py
  scripts/
    report_audio.py
    smoke_test_cactus_audio.py
  reports/
```

## Environment

```bash
SOUNDSIGHT_MODEL_MODE=dummy | cactus
SOUNDSIGHT_TRIGGER_MODE=detector | interval
SOUNDSIGHT_INTERVAL_SECONDS=2.0
SOUNDSIGHT_CACTUS_REPO=/path/to/cactus
SOUNDSIGHT_CACTUS_MODEL=google/gemma-4-E2B-it
SOUNDSIGHT_CACTUS_MODEL_PATH=/path/to/gemma-4-weights
```

`dummy` is deterministic and is the default. `cactus` only calls Cactus/Gemma 4; import, model, completion, JSON, or validation failures emit `model_error` and a no-alert model result. There is no dummy fallback in cactus mode.

`detector` skips clear silence with basic energy/onset checks. `interval` calls the model every `SOUNDSIGHT_INTERVAL_SECONDS`.

## Setup

```powershell
cd backend
uv sync
```

## Run Dummy Mode

```powershell
cd backend
uv sync
$env:SOUNDSIGHT_MODEL_MODE="dummy"
$env:SOUNDSIGHT_TRIGGER_MODE="detector"
uv run uvicorn app.main:app --reload --port 8000
```

## Run Frontend

```powershell
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000` unless `NEXT_PUBLIC_SOUNDSIGHT_API_URL` is set.

## Reports And Smoke Tests

Dummy report:

```powershell
cd backend
$env:SOUNDSIGHT_MODEL_MODE="dummy"
uv run python scripts/report_audio.py
```

Cactus smoke test for macOS/Linux teammates:

```bash
cd backend
uv sync
export SOUNDSIGHT_MODEL_MODE=cactus
export SOUNDSIGHT_TRIGGER_MODE=detector
export SOUNDSIGHT_CACTUS_REPO="$HOME/cactus"
export SOUNDSIGHT_CACTUS_MODEL="google/gemma-4-E2B-it"
# optional:
export SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it"
uv run python scripts/smoke_test_cactus_audio.py
uv run uvicorn app.main:app --reload --port 8000
```

Native Windows is not expected to run Cactus mode because the Cactus Python bindings and Gemma 4 native audio runtime are intended for macOS/Linux in this setup.

## API

```http
POST /api/demo/stream-events
POST /api/live/process-window
```

The stream is NDJSON. Frontend-compatible event types include `model_call`, `model_result`, `model_error`, `alert_start`, `alert_end`, and `session_done`.

Alert payloads contain only the selected UI language:

```json
{
  "should_alert": true,
  "sound_type": "fire_alarm",
  "tier": "emergency",
  "alert_text": "Fire alarm detected.",
  "action": "Move to safety now.",
  "image_key": "fire_alarm",
  "haptic": "SOS vibration",
  "confidence": 0.91,
  "language": "en"
}
```
