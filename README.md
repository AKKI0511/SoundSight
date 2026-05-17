# SoundSight

A local AI app for Deaf and hard-of-hearing users — listens for important sounds and turns them into real-time visual alerts.

---

## Get Started

### macOS / Linux

```bash
git clone https://github.com/AKKI0511/SoundSight.git
cd SoundSight
chmod +x setup.sh run.sh
./setup.sh
./run.sh
```

Then open **http://localhost:3000**

---

### Windows

> ⚠️ **Cactus/Gemma 4 AI mode is not supported on Windows.** Use macOS or Linux for the full AI experience. Windows runs dummy mode only.

Requires [Git Bash](https://git-scm.com/downloads). Run all commands inside Git Bash.

```bash
git clone https://github.com/AKKI0511/SoundSight.git
cd SoundSight
chmod +x setup.sh run.sh
./setup.sh
./run.sh dummy
```

Then open **http://localhost:3000**

---

## Modes

| Mode | Command | What it does |
|------|---------|--------------|
| **Cactus** — macOS/Linux only | `./run.sh` | Uses Gemma 4 via Cactus for real AI audio detection |
| **Dummy** — all platforms | `./run.sh dummy` | Deterministic responses, no model download needed |

---

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Demo | `/demo` | Play built-in audio clips and watch alerts fire in real time |
| Live | `/live` | Use your microphone for live detection |
