# SoundSight

A mobile-first local AI app for Deaf and hard-of-hearing users that listens for important sounds and turns them into visual alerts.

## Project Layout

- `frontend/`: Next.js TypeScript UI and phone emulator.
- `backend/`: FastAPI Python backend managed with `uv`.
- `supporting-data-images-audio/`: demo audio and image assets.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the backend at `http://localhost:8000` by default. To change it:

```bash
NEXT_PUBLIC_SOUNDSIGHT_API_URL=http://localhost:8000 npm run dev
```

## Backend Setup

```bash
cd backend
uv sync
```

Run the backend in deterministic dummy mode:

```bash
SOUNDSIGHT_MODEL_MODE=dummy uv run uvicorn main:app --reload --port 8000
```

On Windows PowerShell:

```powershell
$env:SOUNDSIGHT_MODEL_MODE="dummy"
uv run uvicorn main:app --reload --port 8000
```

Dummy mode is the default when `SOUNDSIGHT_MODEL_MODE` is unset.

## Cactus/Gemma 4 Mode

Cactus mode uses the official Cactus Python FFI bindings and Gemma 4 native audio support. It is expected to be tested on macOS or Linux, not native Windows.

Official Cactus references:

- [Cactus Python SDK](https://docs.cactuscompute.com/latest/python/)
- [Cactus Quickstart](https://docs.cactuscompute.com/latest/docs/quickstart/)
- [Gemma 4 on Cactus](https://docs.cactuscompute.com/latest/blog/gemma4/)

Install and build Cactus from source:

```bash
git clone https://github.com/cactus-compute/cactus ~/cactus
cd ~/cactus
source ./setup
cactus build --python
cactus download google/gemma-4-E2B-it
```

Linux may also need the packages listed by Cactus:

```bash
sudo apt-get install python3 python3-venv python3-pip cmake build-essential libcurl4-openssl-dev
```

Required SoundSight environment variables for Cactus mode:

```bash
export SOUNDSIGHT_MODEL_MODE=cactus
export SOUNDSIGHT_CACTUS_REPO="$HOME/cactus"
export SOUNDSIGHT_CACTUS_MODEL="google/gemma-4-E2B-it"
export SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it"
```

`SOUNDSIGHT_CACTUS_MODEL_PATH` can be omitted if the Cactus `src.downloads.ensure_model` helper is available; SoundSight will try to resolve/download `SOUNDSIGHT_CACTUS_MODEL`.

Optional Cactus variables:

- `SOUNDSIGHT_CACTUS_MODEL`: defaults to `google/gemma-4-E2B-it`.
- `SOUNDSIGHT_CACTUS_MODEL_PATH`: local weights directory, preferred for predictable startup.
- `SOUNDSIGHT_CACTUS_REPO`: Cactus checkout path; SoundSight adds `<repo>/python` to `sys.path`.

## Smoke Test Cactus Audio

From `backend/` on macOS/Linux:

```bash
uv sync
export SOUNDSIGHT_MODEL_MODE=cactus
export SOUNDSIGHT_CACTUS_REPO="$HOME/cactus"
export SOUNDSIGHT_CACTUS_MODEL="google/gemma-4-E2B-it"
export SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it"
uv run python smoke_test_cactus_audio.py
```

The smoke test loads a demo fire-alarm clip, calls Cactus/Gemma 4 once, prints the raw Cactus envelope, prints the raw model response, prints parsed JSON, and ends with `PASS` or `FAIL`.

## Run Backend And Frontend Together

Terminal 1:

```bash
cd backend
SOUNDSIGHT_MODEL_MODE=cactus \
SOUNDSIGHT_CACTUS_REPO="$HOME/cactus" \
SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it" \
uv run uvicorn main:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm run dev
```

Open the frontend, play a demo clip, and watch the phone emulator.

To verify the UI is using real Cactus output:

1. Open browser DevTools and inspect the `POST /api/demo/stream-events` response.
2. Confirm the NDJSON stream contains `model_call` with `"source":"cactus"`.
3. Confirm the stream contains `model_result` with `"source":"cactus"` and a parsed `analysis.alert`.
4. Confirm the following `alert_start.alert.alert_text` matches the cue shown in the phone emulator.

You can also inspect the stream directly:

```bash
curl -N \
  -H "Content-Type: application/json" \
  -H "Accept: application/x-ndjson" \
  -d '{"clipId":"fire_alarm","language":"en"}' \
  http://localhost:8000/api/demo/stream-events
```

## Audio Report

Run the detector report in dummy mode:

```bash
SOUNDSIGHT_MODEL_MODE=dummy uv run python report_audio.py
```

Run the detector report in Cactus mode:

```bash
SOUNDSIGHT_MODEL_MODE=cactus \
SOUNDSIGHT_CACTUS_REPO="$HOME/cactus" \
SOUNDSIGHT_CACTUS_MODEL_PATH="$HOME/cactus/weights/gemma-4-e2b-it" \
uv run python report_audio.py
```

The report includes model source, model name/path, model calls, model results, and model errors.

## Streaming API

The main endpoint is unchanged:

```http
POST /api/demo/stream-events
Accept: application/x-ndjson
Content-Type: application/json

{"clipId":"fire_alarm","language":"en"}
```

The stream may include:

- `model_call`
- `model_result`
- `model_error`
- `alert_start`
- `alert_end`

In explicit Cactus mode, Cactus import/runtime/parser failures emit `model_error` and a safe no-alert `model_result`; SoundSight does not silently replace failed Cactus calls with dummy alerts.
