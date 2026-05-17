#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
CACTUS_REPO="${SOUNDSIGHT_CACTUS_REPO:-$HOME/cactus}"
CACTUS_MODEL="${SOUNDSIGHT_CACTUS_MODEL:-google/gemma-4-E2B-it}"

platform="unknown"
platform_label="unknown"

info() {
  printf "\n[SoundSight] %s\n" "$*"
}

warn() {
  printf "\n[SoundSight warning] %s\n" "$*" >&2
}

error() {
  printf "\n[SoundSight error] %s\n" "$*" >&2
}

detect_platform() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || printf "unknown")"

  case "$uname_s" in
    Darwin*)
      platform="macos"
      platform_label="macOS"
      ;;
    Linux*)
      if grep -qiE "(microsoft|wsl)" /proc/version 2>/dev/null; then
        platform="linux_wsl"
        platform_label="Linux (WSL)"
      else
        platform="linux"
        platform_label="Linux"
      fi
      ;;
    MINGW*|MSYS*|CYGWIN*)
      platform="windows"
      platform_label="native Windows / Git Bash"
      ;;
    *)
      platform="unknown"
      platform_label="$uname_s"
      ;;
  esac
}

install_instruction() {
  local tool="$1"

  case "$platform:$tool" in
    macos:python3|macos:python)
      printf "  python3: brew install python\n"
      ;;
    linux:python3|linux:python|linux_wsl:python3|linux_wsl:python)
      printf "  python3: sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip\n"
      ;;
    windows:python3|windows:python)
      printf "  python: winget install Python.Python.3.12\n"
      ;;
    macos:uv|linux:uv|linux_wsl:uv)
      printf "  uv: curl -LsSf https://astral.sh/uv/install.sh | sh\n"
      ;;
    windows:uv)
      printf "  uv: powershell -ExecutionPolicy ByPass -c \"irm https://astral.sh/uv/install.ps1 | iex\"\n"
      ;;
    macos:node|macos:npm)
      printf "  node/npm: brew install node\n"
      ;;
    linux:node|linux:npm|linux_wsl:node|linux_wsl:npm)
      printf "  node/npm: curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs\n"
      ;;
    windows:node|windows:npm)
      printf "  node/npm: winget install OpenJS.NodeJS.LTS\n"
      ;;
    macos:ffmpeg)
      printf "  ffmpeg: brew install ffmpeg\n"
      ;;
    linux:ffmpeg|linux_wsl:ffmpeg)
      printf "  ffmpeg: sudo apt-get update && sudo apt-get install -y ffmpeg\n"
      ;;
    windows:ffmpeg)
      printf "  ffmpeg: winget install Gyan.FFmpeg\n"
      ;;
    macos:git)
      printf "  git: brew install git\n"
      ;;
    linux:git|linux_wsl:git)
      printf "  git: sudo apt-get update && sudo apt-get install -y git\n"
      ;;
    windows:git)
      printf "  git: winget install Git.Git\n"
      ;;
    *)
      printf "  %s: install %s and make sure it is on PATH\n" "$tool" "$tool"
      ;;
  esac
}

check_required_tools() {
  local required_tools=(uv node npm ffmpeg git)
  local missing_tools=()
  local tool

  if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
    missing_tools+=("python")
  fi

  for tool in "${required_tools[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing_tools+=("$tool")
    fi
  done

  if [ "${#missing_tools[@]}" -eq 0 ]; then
    info "All required tools are available."
    return 0
  fi

  error "Missing required tool(s): ${missing_tools[*]}"
  printf "\nInstall the missing tool(s), restart your terminal, then rerun ./setup.sh:\n" >&2
  for tool in "${missing_tools[@]}"; do
    install_instruction "$tool" >&2
  done
  exit 1
}

warn_cactus_prerequisites() {
  if [ "$platform" = "macos" ]; then
    if ! xcode-select -p >/dev/null 2>&1; then
      warn "Cactus builds may need Xcode Command Line Tools: xcode-select --install"
    fi
    if ! command -v cmake >/dev/null 2>&1; then
      warn "Cactus builds may need CMake: brew install cmake"
    fi
  elif [ "$platform" = "linux" ] || [ "$platform" = "linux_wsl" ]; then
    local missing_cactus_tools=()
    local tool
    for tool in cmake cc c++; do
      if ! command -v "$tool" >/dev/null 2>&1; then
        missing_cactus_tools+=("$tool")
      fi
    done
    if [ "${#missing_cactus_tools[@]}" -gt 0 ]; then
      warn "Cactus build tools may be missing (${missing_cactus_tools[*]}). On Ubuntu/Debian: sudo apt-get update && sudo apt-get install -y cmake build-essential libcurl4-openssl-dev libclang-dev"
    fi
  fi
}

install_backend_dependencies() {
  info "Installing backend dependencies with uv sync."
  cd "$BACKEND_DIR"
  uv sync
}

install_frontend_dependencies() {
  info "Installing frontend dependencies with npm install."
  cd "$FRONTEND_DIR"
  npm install
}

setup_cactus() {
  warn_cactus_prerequisites

  info "Setting up Cactus for Gemma 4 mode."
  info "Cactus repo: $CACTUS_REPO"
  info "Cactus model: $CACTUS_MODEL"

  if [ -d "$CACTUS_REPO/.git" ]; then
    info "Existing Cactus checkout found; updating when possible."
    if ! git -C "$CACTUS_REPO" fetch --tags --prune; then
      warn "Could not fetch Cactus updates. Continuing with the existing checkout."
    fi

    local branch
    branch="$(git -C "$CACTUS_REPO" branch --show-current 2>/dev/null || true)"
    if [ "$branch" = "main" ] || [ "$branch" = "master" ]; then
      if ! git -C "$CACTUS_REPO" pull --ff-only; then
        warn "Could not fast-forward the Cactus checkout. Continuing with the existing checkout."
      fi
    elif [ -n "$branch" ]; then
      warn "Cactus checkout is on branch '$branch'. Leaving it as-is."
    fi
  elif [ -e "$CACTUS_REPO" ]; then
    error "$CACTUS_REPO exists but is not a Cactus git checkout."
    return 1
  else
    git clone https://github.com/cactus-compute/cactus "$CACTUS_REPO"
  fi

  if [ ! -f "$CACTUS_REPO/setup" ]; then
    error "Cactus setup file not found at $CACTUS_REPO/setup."
    return 1
  fi

  cd "$CACTUS_REPO"
  # Official Cactus Python setup: source ./setup, build Python bindings, download weights.
  # shellcheck disable=SC1091
  source ./setup
  cactus build --python
  cactus download "$CACTUS_MODEL"
}

detect_platform

info "Detected OS: $platform_label"
if [ "$platform" = "windows" ]; then
  printf "\nCactus/Gemma 4 mode is not supported on native Windows. Use macOS/Linux for real model mode, or run ./run.sh dummy.\n"
fi
check_required_tools

install_backend_dependencies
install_frontend_dependencies

if [ "$platform" = "windows" ]; then
  warn "Skipping Cactus setup on native Windows."
  info "Setup complete for native Windows dummy/dev mode."
  exit 0
fi

if [ "$platform" != "macos" ] && [ "$platform" != "linux" ] && [ "$platform" != "linux_wsl" ]; then
  warn "Unsupported OS for automatic Cactus setup: $platform_label"
  printf "\nNext steps:\n"
  printf "  1. Install Cactus manually from https://docs.cactuscompute.com/latest/python/\n"
  printf "  2. Set SOUNDSIGHT_CACTUS_REPO to your Cactus checkout.\n"
  printf "  3. Run ./run.sh dummy if you only need dev fallback mode.\n"
  exit 1
fi

set +e
(
  set -Eeuo pipefail
  setup_cactus
)
cactus_status=$?
set -e

if [ "$cactus_status" -ne 0 ]; then
  warn "Cactus setup failed. Backend/frontend dependencies were installed, but real model mode is not ready."
  printf "\nNext steps:\n" >&2
  printf "  1. Review the Cactus error above.\n" >&2
  printf "  2. Install platform prerequisites from https://docs.cactuscompute.com/latest/docs/quickstart/\n" >&2
  printf "  3. Rerun ./setup.sh, or run ./run.sh dummy for deterministic fallback mode.\n" >&2
  exit "$cactus_status"
fi

info "Cactus setup complete."
info "Setup complete. Run ./run.sh for Cactus mode or ./run.sh dummy for fallback mode."
