export type LanguageCode = "en" | "hi" | "es";

export type IconKey = "siren" | "fire" | "attention" | "door" | "speech";

export type LocalizedAlertCopy = {
  alertText: string;
  actionText: string;
};

export type DemoAudio = {
  src: string;
  label: string;
};

export type EventWindow = {
  startRatio: number;
  endRatio: number;
};

export type DemoClip = {
  id: string;
  clipName: string;
  icon: IconKey;
  audio?: DemoAudio;
  eventWindow: EventWindow;
  image?: {
    src: string;
    alt: string;
  };
  translations: Record<LanguageCode, LocalizedAlertCopy>;
};

export type PlayableDemoClip = DemoClip & {
  audio: DemoAudio;
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

export const demoClips: DemoClip[] = [
  {
    id: "emergency-vehicle",
    clipName: "Emergency siren",
    icon: "siren",
    audio: {
      src: "/demo-assets/audio/ambulance-siren.mp3",
      label: "Emergency siren",
    },
    eventWindow: {
      startRatio: 0.34,
      endRatio: 0.78,
    },
    image: {
      src: "/demo-assets/images/siren.png",
      alt: "Red emergency light",
    },
    translations: {
      en: {
        alertText: "Emergency vehicle nearby.",
        actionText: "Look around now.",
      },
      hi: {
        alertText: "आपातकालीन वाहन पास है।",
        actionText: "अभी आसपास देखें।",
      },
      es: {
        alertText: "Vehículo de emergencia cerca.",
        actionText: "Mira alrededor ahora.",
      },
    },
  },
  {
    id: "smoke-fire-alarm",
    clipName: "Fire alarm",
    icon: "fire",
    audio: {
      src: "/demo-assets/audio/fire-alarm.mp3",
      label: "Fire alarm",
    },
    eventWindow: {
      startRatio: 0.22,
      endRatio: 0.82,
    },
    image: {
      src: "/demo-assets/images/smoke-detector.svg",
      alt: "Smoke detector alarm",
    },
    translations: {
      en: {
        alertText: "Fire alarm detected.",
        actionText: "Move to safety.",
      },
      hi: {
        alertText: "आग का अलार्म मिला।",
        actionText: "सुरक्षित जगह जाएं।",
      },
      es: {
        alertText: "Alarma de incendio detectada.",
        actionText: "Ve a un lugar seguro.",
      },
    },
  },
  {
    id: "attention-outdoors",
    clipName: "Someone calling you",
    icon: "attention",
    eventWindow: {
      startRatio: 0.4,
      endRatio: 0.8,
    },
    image: {
      src: "/demo-assets/images/attention.png",
      alt: "Person raising a hand",
    },
    translations: {
      en: {
        alertText: "Someone wants your attention.",
        actionText: "Look around safely.",
      },
      hi: {
        alertText: "कोई आपका ध्यान चाहता है।",
        actionText: "सुरक्षित होकर देखें।",
      },
      es: {
        alertText: "Alguien llama tu atención.",
        actionText: "Mira con cuidado.",
      },
    },
  },
  {
    id: "door-knock",
    clipName: "Door knock",
    icon: "door",
    eventWindow: {
      startRatio: 0.35,
      endRatio: 0.75,
    },
    image: {
      src: "/demo-assets/images/door-knock.svg",
      alt: "Hand knocking on a door",
    },
    translations: {
      en: {
        alertText: "Someone is at the door.",
        actionText: "Check the entrance.",
      },
      hi: {
        alertText: "दरवाजे पर कोई है।",
        actionText: "दरवाजा देखें।",
      },
      es: {
        alertText: "Hay alguien en la puerta.",
        actionText: "Revisa la entrada.",
      },
    },
  },
  {
    id: "indoor-address",
    clipName: "Name called",
    icon: "speech",
    eventWindow: {
      startRatio: 0.38,
      endRatio: 0.78,
    },
    image: {
      src: "/demo-assets/images/indoor-address.svg",
      alt: "Person near a doorway",
    },
    translations: {
      en: {
        alertText: "Someone may be speaking to you.",
        actionText: "Look up safely.",
      },
      hi: {
        alertText: "कोई आपसे बात कर रहा है।",
        actionText: "सुरक्षित होकर देखें।",
      },
      es: {
        alertText: "Alguien puede hablarte.",
        actionText: "Mira con cuidado.",
      },
    },
  },
];

export const playableDemoClips = demoClips.filter(
  (clip): clip is PlayableDemoClip => Boolean(clip.audio),
);
