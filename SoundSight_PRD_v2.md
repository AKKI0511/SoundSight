# SoundSight — Product Requirements Document
**Version:** 2.1  
**Hackathon:** Gemma 4 for Good (Kaggle) — Digital Equity & Inclusivity track  
**Submission deadline:** 18 May 2025  
**Team size:** 2  

---

## 1. One-line summary

SoundSight is a mobile-first, on-device AI app for Deaf, hard-of-hearing, and senior users that listens for important sounds and turns them into visual alerts — with a contextual illustration, multilingual text, and haptic feedback — using lightweight real-time detection plus Gemma 4 local reasoning.

---

## 2. The problem

Hearing is the ambient sense. Most of what happens around us is announced by sound before we see it — a knock at the door, a siren approaching, someone saying your name from behind.

For 1.5 billion people worldwide with some degree of hearing loss, these ambient cues are missed constantly. The gap is not just inconvenient; it is a safety risk and a daily source of social exclusion.

Existing tools address speech-to-text (captions) but not sound-to-meaning. No mainstream app tells a Deaf person that an emergency vehicle is nearby, that someone behind them is trying to get their attention, or that the smoke alarm in the next room has gone off.

**SoundSight addresses this gap.**

> Captions tell you *what was said.*  
> SoundSight tells you *what matters.*

---

## 3. Target users

### Primary — Deaf and hard-of-hearing people

- Approximately 430 million people globally have disabling hearing loss (WHO, 2024)
- Many are active smartphone users who manage daily life independently
- They understand the problem viscerally and will be the most vocal early adopters
- Built *for* this community first — not as an afterthought

### Secondary — Senior citizens with age-related hearing loss

- 1 in 3 people over 65 have significant hearing decline
- By 2050, 2.5 billion people globally will be aged 60+
- Most have not adopted assistive technology
- Strongest use-case: ageing in place independently, without a carer present
- Families of seniors are a co-audience — they want peace of mind

### Combined TAM

These two groups together represent over 500 million smartphone users globally who would benefit from an ambient sound awareness tool today, growing significantly with demographic ageing.

---

## 4. Core product concept

SoundSight runs on a mobile device. It listens passively in the background using the microphone, detects sounds that matter, sends relevant audio clips to Gemma 4 for reasoning, and surfaces the result as a visual alert card — with a corresponding haptic pattern.

The pipeline is:

```
Microphone audio
→ lightweight sound trigger (VAD / RMS spike detector)
→ rolling 3–5 second audio buffer captured
→ Gemma 4 reasons over the clip
→ alert classified by severity tier
→ visual card + haptic pattern shown to user
```

The key distinction: Gemma 4 is not doing transcription. It is doing **sound reasoning** — understanding what a sound means, who it might be directed at, what the user should do, and how urgently.

---

## 5. Alert severity tiers

Every sound alert in SoundSight maps to one of three severity tiers. Tier determines visual treatment, haptic pattern, and alert behaviour.

### Tier 1 — Emergency

**Definition:** Sounds that indicate immediate physical danger.  
**Visual:** Full-screen red alert, large text, stays on screen until dismissed.  
**Haptic:** Repeating long pulse (SOS-style pattern).  
**Dismissal:** Explicit tap required.

| Use case | Sound | Alert text example |
|---|---|---|
| Emergency vehicle | Siren, air horn | "Emergency vehicle nearby. Stay alert." |
| Smoke / fire alarm | Sustained beeping alarm | "Fire alarm detected. Check your surroundings immediately." |

### Tier 2 — Social

**Definition:** Sounds directed at the user socially — someone wants their attention.  
**Visual:** Prominent card overlay, medium size, persists for 8 seconds.  
**Haptic:** Two short pulses.  
**Dismissal:** Auto-dismisses or tap.

| Use case | Sound | Alert text example |
|---|---|---|
| Attention — outdoors | "Hey / excuse me / watch out" + name | "Someone is trying to get your attention. Look around." |
| Attention — indoors | Name called in room / office | "Someone may be addressing you. Look up when safe." |
| Door knock | Knock / doorbell | "Someone at the door." |

### Tier 3 — Ambient *(upcoming)*

**Definition:** Sounds that are informational, not urgent.  
**Visual:** Small notification card, bottom of screen.  
**Haptic:** Single short pulse.  
**Dismissal:** Auto-dismisses after 5 seconds.

| Use case | Sound | Alert text example | Status |
|---|---|---|---|
| Baby / child crying | Infant cry | "A child may need attention nearby." | Upcoming v2 |
| Timer / appliance beep | Microwave, oven, washer | "A timer or appliance has completed." | Upcoming v2 |
| Phone ringing | Ringtone | "Your phone may be ringing." | Upcoming v2 |

---

## 6. Use cases — hackathon build scope

### Scenario A: On the move (street, transit, travel)

The user is outside — walking, commuting, in a market, at a station. Background noise is variable. The app is running in foreground with screen on or accessible.

**Use case A1 — Emergency vehicle or danger sound** *(Tier 1)*  
A siren, air horn, or loud danger sound is detected. Full-screen emergency alert fires immediately. This is the highest life-safety use case in the app. For a Deaf user crossing a road or cycling, this is the most critical alert the app can produce.

**Use case A2 — Someone trying to get your attention** *(Tier 2)*  
Someone says "hey", "excuse me", "watch out", or calls the user's name from behind or nearby. A social alert card appears with the cue: "Someone is trying to get your attention." The action prompt: "Look around when safe."

---

### Scenario B: Home and office

The user is indoors — at home alone, in a shared home, or at a desk in an office. The phone is nearby, possibly face-down or in a pocket.

**Use case B1 — Smoke or fire alarm** *(Tier 1)*  
A sustained alarm beep is detected. Full-screen emergency alert with strong haptic. Especially critical for seniors living alone, where an unheard alarm is a life-threatening gap. Shares the same Tier 1 visual and haptic treatment as the siren alert.

**Use case B2 — Door knock or doorbell** *(Tier 2)*  
A knock or doorbell is detected. A card appears: "Someone at the door." This is the highest daily-frequency use case in the home scenario. Simple, reliable, extremely easy to reproduce in a demo.

**Use case B3 — Someone addressing you in the room** *(Tier 2)*  
A colleague, family member, or housemate says the user's name or addresses them directly while they are at their desk or in another room. Same Gemma prompt logic as A2 — the indoor social-attention variant. Low marginal build effort; reuses the attention-detection pipeline.

---

### Upcoming use cases (not in hackathon build)

These are scoped for a post-hackathon v2. They are listed here to show the full product vision, and the baby cry scenario is included in the demo video narrative.

- **Baby / child crying** (Tier 3) — For Deaf parents; high emotional resonance for the product story
- **Timer / appliance beep** (Tier 3) — Kitchen independence for seniors
- **Transit / tannoy announcement** (Tier 2) — Station PA, bus stop; deprioritised due to demo audio reliability risk

---

## 7. Gemma 4 prompt design

Each use case maps to a structured Gemma 4 prompt. The model does not transcribe — it reasons. The prompt instructs Gemma to:

1. Identify what the sound is
2. Assess whether it is directed at the user
3. Assign a severity tier (Emergency / Social / Ambient)
4. Generate a short alert text (max 12 words)
5. Generate a short action prompt (max 8 words)
6. Generate a visual scene description for the alert illustration
7. Translate alert text and action into the user's preferred language

Example output schema:

```json
{
  "sound_type": "smoke_alarm",
  "tier": "emergency",
  "alert_text": "Fire alarm detected. Check your surroundings immediately.",
  "action": "Move to safety. Do not ignore.",
  "visual_description": "A red fire alarm on a white wall with flashing light and smoke nearby",
  "translations": {
    "hi": { "alert_text": "आग का अलार्म। तुरंत सुरक्षित स्थान पर जाएं।", "action": "अभी निकलें।" },
    "es": { "alert_text": "Alarma de incendio. Comprueba tu entorno.", "action": "Muévete a un lugar seguro." }
  },
  "confidence": 0.94
}
```

The structured JSON output drives the UI tier directly — no secondary classification step needed. The `visual_description` field is passed to an image generation step (see Section 9) and the `translations` field is used if the user has set a preferred language in settings.

### Multilingual support

A significant portion of Deaf and hard-of-hearing users globally are not native English speakers, and many have lower text literacy due to reduced access to audio-based language learning. Multilingual alerts are therefore not just a convenience — they are a core accessibility requirement.

**Supported languages at launch (hackathon):** English + 2 regional languages selectable in settings (suggested defaults: Hindi and Spanish, covering the two largest non-English user populations globally).

**How it works:** The user selects a preferred language on first launch. Gemma 4 returns alert text and action text in that language alongside English. The UI renders the preferred language as the primary display text.

**Gemma 4 advantage:** Unlike a static translation lookup, Gemma generates contextually appropriate phrasing in the target language — important for short urgent messages where literal translation can lose urgency.

---

## 8. App modes

### Live Awareness Mode (core feature)

The user taps **Start Listening**. The app runs the detection pipeline in the foreground. Alerts appear as they are triggered. Local alert history is maintained in session.

### Demo Clips Mode (hackathon reliability)

Five bundled audio clips — one per build use case. The user (or judge) taps a clip; the same full pipeline runs and produces the alert card. This ensures the judges can always see the AI reasoning clearly regardless of live room conditions.

### Upload Audio (nice to have, time-permitting)

User uploads an audio file. App processes it through the same pipeline and returns an alert card. Useful for testing and for the hackathon submission video.

---

## 9. UX requirements

### Alert card anatomy

Every alert card has four layers: a contextual illustration, a tier badge, alert text in the user's language, and an action prompt. Text literacy is not assumed.

```
┌─────────────────────────────────┐
│  🔴 EMERGENCY                   │  ← Tier badge (colour-coded, icon-led)
│                                 │
│  ┌───────────────────────────┐  │
│  │  [Contextual illustration] │  │  ← Generated visual (fire, siren, person etc.)
│  │   e.g. flashing red alarm  │  │    Large, unambiguous, icon-style
│  └───────────────────────────┘  │
│                                 │
│  आग का अलार्म।                  │  ← Alert text in user's preferred language
│  Fire alarm detected.           │    Secondary line in English (always shown)
│                                 │
│  → अभी निकलें।                  │  ← Action prompt (preferred language)
│    Move to safety now.          │    Secondary in English
│                                 │
│              [Dismiss]          │
└─────────────────────────────────┘
```

Tier 1: Full-screen red, white text, persistent, large illustration (top half of screen)
Tier 2: Card overlay, prominent, 8-second auto-dismiss, medium illustration
Tier 3: Small bottom card, 5-second auto-dismiss, small icon only

### Visual illustration

The illustration is the primary communication layer for users with low text literacy. It must convey the sound event unambiguously without words.

**Implementation approach:**

For the hackathon, a curated set of pre-generated illustrations is the most reliable path — one high-quality image per use case, generated ahead of time and bundled with the app. Each illustration is bold, high-contrast, and icon-like (not photographic) to ensure clarity at a glance.

| Use case | Illustration |
|---|---|
| Emergency vehicle / siren | Red and blue flashing lights, ambulance silhouette |
| Smoke / fire alarm | Red alarm disc on wall, smoke wisps, flashing |
| Someone getting attention (outdoor) | Person with raised hand, speech bubble, exclamation |
| Door knock | Raised fist knocking on a door |
| Someone addressing you (indoor) | Person facing viewer, pointing, speech bubble |
| Baby crying *(upcoming)* | Baby face with tears and sound waves |

**Production path (post-hackathon):** The `visual_description` field from Gemma 4's JSON output is passed to an on-device image generation model to produce dynamic, context-aware illustrations. This is the full Gemma 4 multimodal vision — noted in the submission as the v2 architecture.

### Senior-accessible mode

A settings toggle activates Senior Mode:
- Minimum font size 22pt
- High contrast (black on white / white on black)
- Simplified one-tap activation
- Alerts persist until explicitly dismissed (overrides tier defaults)

### Haptic patterns

| Tier | Pattern |
|---|---|
| Emergency | Long–long–long repeating (until dismiss) |
| Social | Short–short (double tap) |
| Ambient | Single short pulse |

---

## 10. Tech stack

### Recommended for hackathon

| Layer | Choice | Notes |
|---|---|---|
| App framework | React Native | Cross-platform; Expo for fast setup |
| AI inference | Gemma 4 via API (cloud) | Primary path for hackathon demo |
| On-device inference | Cactus + Gemma 4 E2B | Aspirational architecture; demo as architecture slide |
| Audio capture | `expo-av` or `react-native-audio-record` | Rolling buffer with RMS trigger |
| Sound pre-filter | RMS energy spike + simple VAD | Prevents Gemma being called on silence |
| Haptics | `expo-haptics` | Supports custom vibration patterns |
| Multilingual output | Gemma 4 JSON (translations field) | EN + 2 languages; user sets preference on first launch |
| Alert illustrations | Pre-generated, bundled in app | One image per use case; bold, icon-style, high-contrast |
| Image generation (v2) | On-device image model | Driven by Gemma's `visual_description` field; post-hackathon |
| Storage | AsyncStorage / SQLite | Local alert history, no cloud sync |
| Demo clips | Bundled `.m4a` files | Pre-recorded, processed through real pipeline |

### Architecture note — on-device vs cloud

The production vision is fully on-device: audio never leaves the device, protecting conversational and environmental privacy. For the hackathon demo, the Gemma 4 API (cloud) is used to ensure reliable, fast inference. The on-device Cactus runtime is presented as the deployment architecture in the submission write-up and video.

### Pre-filter rationale

A raw RMS spike detector is fast but will false-positive heavily outdoors (wind, traffic). If time permits, a lightweight sound event classifier (e.g. YAMNet or similar) should be added as a pre-filter before invoking Gemma. This reduces unnecessary API calls and keeps the demo clean in noisy environments.

---

## 11. 4-day build plan

| Day | Focus | Owner split |
|---|---|---|
| Day 1 (15 May) | Repo, Expo setup, Gemma 4 API end-to-end working. One audio clip → one alert card on screen. | Person A: pipeline + Gemma prompt + JSON schema with translations field. Person B: alert card UI + tier styling + illustration slot. |
| Day 2 (16 May) | All 5 use cases wired with demo clips. Severity tier logic working. Bundled illustrations per use case. Multilingual toggle in settings. Alert history screen. Haptic patterns. | Person A: use cases + multilingual output. Person B: full UI, illustrations, Senior Mode toggle. |
| Day 3 (17 May) | Live Awareness Mode (mic → VAD → Gemma → alert). Polish. Bug fixes. Buffer day. Record demo clips. | Both: integration + stability. |
| Day 4 (18 May) | Demo video recording and edit. Submission write-up. Code freeze. Submit. | Person A: video narration + screen record. Person B: submission form + write-up. |

---

## 12. Demo video structure

**Working title:** *The World Without Sound*

**Narrative arc:**

1. POV scene: someone knocks — nothing heard, door missed
2. POV scene: siren approaching while crossing a road — no alert
3. POV scene: smoke alarm going off in another room — silence
4. Title card: *"1.5 billion people live this every day."*
5. Introduce SoundSight
6. Same three scenes — this time the app fires alerts
7. Show Live Awareness Mode working
8. Show Demo Clips (all 5 use cases) — show illustration + multilingual text switching
9. Show alert card anatomy — Emergency / Social / Ambient tier, illustration, language toggle
10. Mention baby cry and upcoming Tier 3 vision
11. Architecture slide: on-device, private, no audio to cloud
12. Close: *"SoundSight is not trying to make Deaf people hear. It is trying to make the hearing world visible."*

**Closing line:**  
*"You did not miss the video. You missed the sound."*

---

## 13. What SoundSight is not

- **Not a captioning app.** Live transcription exists (Google Live Transcribe, Apple Live Captions). SoundSight handles non-speech sounds and prioritises meaning over verbatim text.
- **Not a hearing aid.** It does not amplify sound. It interprets and surfaces events visually.
- **Not a cloud surveillance tool.** Audio is processed locally on device. No audio is stored or transmitted in the production architecture.

---

## 14. Hackathon submission checklist

- [ ] Working app with 5 use cases across 2 scenarios
- [ ] Demo Clips mode functional for all 5 use cases
- [ ] Three severity tiers visually distinct
- [ ] Alert card shows contextual illustration per use case
- [ ] Multilingual alert text working (EN + 2 languages)
- [ ] Language preference selectable in settings
- [ ] Haptic patterns implemented
- [ ] Alert history screen
- [ ] Senior Mode toggle
- [ ] Demo video (3–5 minutes)
- [ ] On-device / privacy architecture explained in video
- [ ] Submission write-up referencing Digital Equity & Inclusivity track
- [ ] Gemma 4 prompt design documented
