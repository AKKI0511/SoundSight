export type LanguageCode = "en" | "hi" | "es";

export type AlertTier = "emergency" | "social" | "ambient";

export type IconKey = "siren" | "fire" | "attention" | "door" | "speech";

export type AlertTranslation = {
  alert_text: string;
  action: string;
};

export type StreamAlert = {
  sound_type: string;
  tier: AlertTier;
  image_key: string;
  alert_text: string;
  action: string;
  translations: Record<Exclude<LanguageCode, "en">, AlertTranslation>;
  haptic: string;
  confidence: number;
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
      type: "session_done";
      sessionId: string;
      timestampMs: number;
    };

export type DemoAudio = {
  src: string;
  label: string;
};

export type DemoImage = {
  src: string;
  alt: string;
};

export type ScheduledAlert = {
  eventId: string;
  startMs: number;
  endMs: number;
  alert: StreamAlert;
};

export type DemoClip = {
  id: string;
  clipName: string;
  icon: IconKey;
  imageKey: string;
  audio?: DemoAudio;
  localSchedule: {
    doneMs: number;
    alerts: ScheduledAlert[];
  };
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
  door_knock: "door",
  indoor_address: "speech",
};

const alerts = {
  emergencyVehicle: makeAlert({
    sound_type: "emergency_vehicle",
    tier: "emergency",
    image_key: "emergency_vehicle",
    alert_text: "Emergency vehicle nearby.",
    action: "Look around now.",
    hi: {
      alert_text:
        "\u0906\u092a\u093e\u0924\u0915\u093e\u0932\u0940\u0928 \u0935\u093e\u0939\u0928 \u092a\u093e\u0938 \u0939\u0948\u0964",
      action:
        "\u0905\u092d\u0940 \u0906\u0938\u092a\u093e\u0938 \u0926\u0947\u0916\u0947\u0902\u0964",
    },
    es: {
      alert_text: "Veh\u00edculo de emergencia cerca.",
      action: "Mira alrededor ahora.",
    },
    haptic: "SOS vibration",
    confidence: 0.95,
  }),
  fireAlarm: makeAlert({
    sound_type: "fire_alarm",
    tier: "emergency",
    image_key: "fire_alarm",
    alert_text: "Fire alarm detected.",
    action: "Move to safety now.",
    hi: {
      alert_text:
        "\u0906\u0917 \u0915\u093e \u0905\u0932\u093e\u0930\u094d\u092e \u092e\u093f\u0932\u093e\u0964",
      action:
        "\u0905\u092d\u0940 \u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u091c\u0917\u0939 \u091c\u093e\u090f\u0902\u0964",
    },
    es: {
      alert_text: "Alarma de incendio detectada.",
      action: "Ve a un lugar seguro ahora.",
    },
    haptic: "SOS vibration",
    confidence: 0.94,
  }),
  attentionOutdoors: makeAlert({
    sound_type: "attention_outdoors",
    tier: "social",
    image_key: "attention_outdoors",
    alert_text: "Someone wants your attention.",
    action: "Look around safely.",
    hi: {
      alert_text:
        "\u0915\u094b\u0908 \u0906\u092a\u0915\u093e \u0927\u094d\u092f\u093e\u0928 \u091a\u093e\u0939\u0924\u093e \u0939\u0948\u0964",
      action:
        "\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b\u0915\u0930 \u0926\u0947\u0916\u0947\u0902\u0964",
    },
    es: {
      alert_text: "Alguien llama tu atenci\u00f3n.",
      action: "Mira con cuidado.",
    },
    haptic: "Two short pulses",
    confidence: 0.88,
  }),
  doorKnock: makeAlert({
    sound_type: "door_knock",
    tier: "social",
    image_key: "door_knock",
    alert_text: "Someone is at the door.",
    action: "Check the entrance.",
    hi: {
      alert_text:
        "\u0926\u0930\u0935\u093e\u091c\u0947 \u092a\u0930 \u0915\u094b\u0908 \u0939\u0948\u0964",
      action:
        "\u0926\u0930\u0935\u093e\u091c\u093e \u0926\u0947\u0916\u0947\u0902\u0964",
    },
    es: {
      alert_text: "Hay alguien en la puerta.",
      action: "Revisa la entrada.",
    },
    haptic: "Two short pulses",
    confidence: 0.9,
  }),
  indoorAddress: makeAlert({
    sound_type: "indoor_address",
    tier: "social",
    image_key: "indoor_address",
    alert_text: "Someone may be speaking to you.",
    action: "Look up safely.",
    hi: {
      alert_text:
        "\u0915\u094b\u0908 \u0906\u092a\u0938\u0947 \u092c\u093e\u0924 \u0915\u0930 \u0930\u0939\u093e \u0939\u0948\u0964",
      action:
        "\u0938\u0941\u0930\u0915\u094d\u0937\u093f\u0924 \u0939\u094b\u0915\u0930 \u0926\u0947\u0916\u0947\u0902\u0964",
    },
    es: {
      alert_text: "Alguien puede hablarte.",
      action: "Mira con cuidado.",
    },
    haptic: "Two short pulses",
    confidence: 0.86,
  }),
};

export const demoClips: DemoClip[] = [
  {
    id: "emergency_vehicle",
    clipName: "Emergency siren",
    icon: "siren",
    imageKey: "emergency_vehicle",
    audio: {
      src: "/demo-assets/audio/ambulance-siren.mp3",
      label: "Emergency siren",
    },
    localSchedule: {
      doneMs: 12500,
      alerts: [
        {
          eventId: "emergency_vehicle_1",
          startMs: 2800,
          endMs: 9700,
          alert: alerts.emergencyVehicle,
        },
      ],
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
    localSchedule: {
      doneMs: 12000,
      alerts: [
        {
          eventId: "fire_alarm_1",
          startMs: 2800,
          endMs: 9300,
          alert: alerts.fireAlarm,
        },
      ],
    },
  },
  {
    id: "attention_outdoors",
    clipName: "Someone getting attention",
    icon: "attention",
    imageKey: "attention_outdoors",
    localSchedule: {
      doneMs: 9000,
      alerts: [
        {
          eventId: "attention_outdoors_1",
          startMs: 2600,
          endMs: 7000,
          alert: alerts.attentionOutdoors,
        },
      ],
    },
  },
  {
    id: "door_knock",
    clipName: "Door knock",
    icon: "door",
    imageKey: "door_knock",
    localSchedule: {
      doneMs: 8500,
      alerts: [
        {
          eventId: "door_knock_1",
          startMs: 2500,
          endMs: 6600,
          alert: alerts.doorKnock,
        },
      ],
    },
  },
  {
    id: "indoor_address",
    clipName: "Name called indoors",
    icon: "speech",
    imageKey: "indoor_address",
    localSchedule: {
      doneMs: 9000,
      alerts: [
        {
          eventId: "indoor_address_1",
          startMs: 2600,
          endMs: 7000,
          alert: alerts.indoorAddress,
        },
      ],
    },
  },
];

export function getDemoClip(clipId: string): DemoClip | undefined {
  return demoClips.find((clip) => clip.id === clipId);
}

export function getLocalizedAlertCopy(
  alert: StreamAlert,
  language: LanguageCode,
): LocalizedAlertCopy {
  if (language === "en") {
    return {
      alertText: alert.alert_text,
      actionText: alert.action,
    };
  }

  const translation = alert.translations[language];

  return {
    alertText: translation?.alert_text ?? alert.alert_text,
    actionText: translation?.action ?? alert.action,
  };
}

function makeAlert({
  hi,
  es,
  ...alert
}: Omit<StreamAlert, "translations"> & {
  hi: AlertTranslation;
  es: AlertTranslation;
}): StreamAlert {
  return {
    ...alert,
    translations: {
      hi,
      es,
    },
  };
}
