#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

platform="unknown"
backend_pid=""
frontend_pid=""
cleaned_up=0

info() {
  printf "\n[SoundSight] %s\n" "$*"
}

error() {
  printf "\n[SoundSight error] %s\n" "$*" >&2
}

usage() {
  cat <<'USAGE'
Usage:
  ./run.sh          # cactus mode
  ./run.sh cactus   # cactus mode
  ./run.sh dummy    # dummy mode
USAGE
}

detect_platform() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || printf "unknown")"

  case "$uname_s" in
    MINGW*|MSYS*|CYGWIN*)
      platform="windows"
      ;;
    Darwin*)
      platform="macos"
      ;;
    Linux*)
      platform="linux"
      ;;
    *)
      platform="unknown"
      ;;
  esac
}

stop_process() {
  local pid="$1"
  local name="$2"

  if [ -z "$pid" ]; then
    return 0
  fi

  if kill -0 "$pid" 2>/dev/null; then
    if command -v pkill >/dev/null 2>&1; then
      pkill -TERM -P "$pid" 2>/dev/null || true
    fi
    kill -TERM "$pid" 2>/dev/null || true
    sleep 1
  fi

  if kill -0 "$pid" 2>/dev/null; then
    if command -v pkill >/dev/null 2>&1; then
      pkill -KILL -P "$pid" 2>/dev/null || true
    fi
    kill -KILL "$pid" 2>/dev/null || true
  fi

  wait "$pid" 2>/dev/null || true
  printf "[SoundSight] Stopped %s.\n" "$name"
}

cleanup() {
  if [ "$cleaned_up" -eq 1 ]; then
    return 0
  fi
  cleaned_up=1

  printf "\n[SoundSight] Stopping SoundSight...\n"
  stop_process "$frontend_pid" "frontend"
  stop_process "$backend_pid" "backend"
}

handle_interrupt() {
  trap - INT TERM
  cleanup
  exit 130
}

process_is_running() {
  local pid="$1"
  local job_pid

  for job_pid in $(jobs -r -p); do
    if [ "$job_pid" = "$pid" ]; then
      return 0
    fi
  done

  return 1
}

collect_wait_status() {
  local pid="$1"
  local var_name="$2"
  local status

  set +e
  wait "$pid"
  status=$?
  set -e
  printf -v "$var_name" "%s" "$status"
}

require_command() {
  local command_name="$1"

  if ! command -v "$command_name" >/dev/null 2>&1; then
    error "$command_name is missing. Run ./setup.sh first."
    exit 1
  fi
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

if [ "$#" -gt 1 ]; then
  usage >&2
  exit 1
fi

mode="${1:-cactus}"
case "$mode" in
  cactus|dummy)
    ;;
  *)
    error "Unknown mode: $mode"
    usage >&2
    exit 1
    ;;
esac

detect_platform

if [ "$platform" = "windows" ] && [ "$mode" = "cactus" ]; then
  error "Cactus/Gemma 4 mode is not supported on native Windows. Use macOS/Linux for real model mode, or run ./run.sh dummy."
  exit 1
fi

require_command uv
require_command node
require_command npm
require_command ffmpeg

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  error "Backend dependencies are missing. Run ./setup.sh first."
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  error "Frontend dependencies are missing. Run ./setup.sh first."
  exit 1
fi

export SOUNDSIGHT_TRIGGER_MODE="${SOUNDSIGHT_TRIGGER_MODE:-detector}"

if [ "$mode" = "cactus" ]; then
  export SOUNDSIGHT_CACTUS_MODEL="${SOUNDSIGHT_CACTUS_MODEL:-google/gemma-4-E2B-it}"
  export SOUNDSIGHT_CACTUS_REPO="${SOUNDSIGHT_CACTUS_REPO:-$HOME/cactus}"

  if [ ! -d "$SOUNDSIGHT_CACTUS_REPO" ]; then
    error "Cactus is not set up at $SOUNDSIGHT_CACTUS_REPO. Run ./setup.sh first, or set SOUNDSIGHT_CACTUS_REPO to your Cactus checkout."
    exit 1
  fi

  if [ ! -d "$SOUNDSIGHT_CACTUS_REPO/python/src" ]; then
    error "Cactus Python bindings were not found under $SOUNDSIGHT_CACTUS_REPO/python/src. Run ./setup.sh first."
    exit 1
  fi
fi

trap cleanup EXIT
trap handle_interrupt INT TERM

info "Starting backend on http://localhost:8000."
(
  cd "$BACKEND_DIR"
  exec env SOUNDSIGHT_MODEL_MODE="$mode" uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
backend_pid=$!

info "Starting frontend on http://localhost:3000."
(
  cd "$FRONTEND_DIR"
  exec npm run dev -- --hostname 0.0.0.0
) &
frontend_pid=$!

sleep 2

if ! process_is_running "$backend_pid"; then
  collect_wait_status "$backend_pid" backend_status
  error "Backend stopped during startup with exit code $backend_status."
  exit "$backend_status"
fi

if ! process_is_running "$frontend_pid"; then
  collect_wait_status "$frontend_pid" frontend_status
  error "Frontend stopped during startup with exit code $frontend_status."
  exit "$frontend_status"
fi

printf "\nSoundSight is running\n"
printf "Open: http://localhost:3000\n"
printf "Backend: http://localhost:8000\n"
printf "Mode: %s\n" "$mode"
printf "Press Ctrl+C to stop\n\n"

while true; do
  if ! process_is_running "$backend_pid"; then
    collect_wait_status "$backend_pid" backend_status
    error "Backend stopped with exit code $backend_status. Stopping frontend."
    exit "$backend_status"
  fi

  if ! process_is_running "$frontend_pid"; then
    collect_wait_status "$frontend_pid" frontend_status
    error "Frontend stopped with exit code $frontend_status. Stopping backend."
    exit "$frontend_status"
  fi

  sleep 1
done
