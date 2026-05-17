export type LanguageCode = "en" | "hi" | "es";

export type AlertTier = "emergency" | "social" | "ambient" | "none";

export type IconKey =
  | "siren"
  | "fire"
  | "attention"
  | "door"
  | "speech"
  | "baby";

export type StreamAlert = {
  sound_type: string;
  tier: AlertTier;
  image_key: string;
  alert_text: string;
  action: string;
  haptic: string;
  confidence: number;
  language: LanguageCode;
};

export type StreamAnalysis = StreamAlert & {
  should_alert: boolean;
};

export type StreamEvent =
  | {
      type: "session_started";
      sessionId: string;
      clipId: string;
      timestampMs: number;
    }
  | {
      type: "alert_start";
      sessionId: string;
      eventId: string;
      timestampMs: number;
      alert: StreamAlert;
    }
  | {
      type: "alert_end";
      sessionId: string;
      eventId: string;
      timestampMs: number;
    }
  | {
      type: "engine_log";
      sessionId: string;
      timestampMs: number;
      [key: string]: unknown;
    }
  | {
      type: "candidate_start";
      sessionId: string;
      candidateId: string;
      timestampMs: number;
      [key: string]: unknown;
    }
  | {
      type: "candidate_update";
      sessionId: string;
      candidateId: string;
      timestampMs: number;
      [key: string]: unknown;
    }
  | {
      type: "model_call";
      sessionId: string;
      candidateId: string;
      source: "dummy" | "cactus";
      model?: string | null;
      timestampMs: number;
      clipId: string;
      language: LanguageCode;
      reason: string;
      windowStartMs: number;
      windowEndMs: number;
      candidateType: string;
      candidateConfidence: number;
    }
  | {
      type: "model_result";
      sessionId: string;
      candidateId: string;
      source: "dummy" | "cactus";
      model?: string | null;
      timestampMs: number;
      clipId: string;
      analysis: StreamAnalysis;
    }
  | {
      type: "model_error";
      sessionId: string;
      candidateId: string;
      source: "dummy" | "cactus";
      model?: string | null;
      timestampMs: number;
      clipId: string;
      message: string;
    }
  | {
      type: "session_done";
      sessionId: string;
      timestampMs: number;
    }
  | {
      type: "error";
      sessionId: string;
      clipId: string;
      timestampMs: number;
      code: string;
      message: string;
    };

export type DemoAudio = {
  src: string;
  label: string;
};

export type DemoImage = {
  src: string;
  alt: string;
};

export type DemoClip = {
  id: string;
  clipName: string;
  icon: IconKey;
  imageKey: string;
  audio?: DemoAudio;
};

export type LocalizedAlertCopy = {
  alertText: string;
  actionText: string;
};

export const languages: Array<{
  code: LanguageCode;
  label: string;
  shortLabel: string;
}> = [
  { code: "en", label: "English", shortLabel: "EN" },
  { code: "hi", label: "Hindi", shortLabel: "HI" },
  { code: "es", label: "Spanish", shortLabel: "ES" },
];

export const alertImagesByKey: Record<string, DemoImage> = {
  emergency_vehicle: {
    src: "/demo-assets/images/siren.png",
    alt: "Red emergency light",
  },
  fire_alarm: {
    src: "/demo-assets/images/smoke-detector.svg",
    alt: "Smoke detector alarm",
  },
  attention_outdoors: {
    src: "/demo-assets/images/attention.png",
    alt: "Person raising a hand",
  },
  baby_crying: {
    src: "/demo-assets/images/crying-baby.svg",
    alt: "Crying baby",
  },
  door_knock: {
    src: "/demo-assets/images/door-knock.svg",
    alt: "Hand knocking on a door",
  },
  indoor_address: {
    src: "/demo-assets/images/indoor-address.svg",
    alt: "Person near a doorway",
  },
};

export const iconByImageKey: Record<string, IconKey> = {
  emergency_vehicle: "siren",
  fire_alarm: "fire",
  attention_outdoors: "attention",
  baby_crying: "baby",
  door_knock: "door",
  indoor_address: "speech",
};

export const demoClips: DemoClip[] = [
  {
    id: "emergency_vehicle",
    clipName: "Ambulance",
    icon: "siren",
    imageKey: "emergency_vehicle",
    audio: {
      src: "/demo-assets/audio/ambulance-siren.mp3",
      label: "Ambulance",
    },
  },
  {
    id: "fire_alarm",
    clipName: "Fire alarm",
    icon: "fire",
    imageKey: "fire_alarm",
    audio: {
      src: "/demo-assets/audio/fire-alarm.mp3",
      label: "Fire alarm",
    },
  },
  {
    id: "attention_outdoors",
    clipName: "Baby crying",
    icon: "baby",
    imageKey: "baby_crying",
    audio: {
      src: "/demo-assets/audio/baby-crying.mp3",
      label: "Baby crying",
    },
  },
];

export function getLocalizedAlertCopy(alert: StreamAlert): LocalizedAlertCopy {
  return {
    alertText: alert.alert_text,
    actionText: alert.action,
  };
}
