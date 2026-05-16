"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ClipSelector } from "@/components/ClipSelector";
import { LanguageSelector } from "@/components/LanguageSelector";
import { PhoneEmulator } from "@/components/PhoneEmulator";
import {
  demoClips,
  type AlertTier,
  type DemoClip,
  type LanguageCode,
  type StreamAlert,
  type StreamEvent,
} from "@/lib/demo-alerts";
import { streamDemoEvents } from "@/lib/stream-events";

type ActiveAlert = {
  eventId: string;
  sequence: number;
  alert: StreamAlert;
};

const tierPriority: Record<AlertTier, number> = {
  emergency: 3,
  social: 2,
  ambient: 1,
  none: 0,
};

export default function Home() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const streamControllerRef = useRef<AbortController | null>(null);
  const streamRunRef = useRef(0);
  const alertSequenceRef = useRef(0);

  const [language, setLanguage] = useState<LanguageCode>("en");
  const [selectedClipId, setSelectedClipId] = useState(
    demoClips[0]?.id ?? "",
  );
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [activeAlerts, setActiveAlerts] = useState<ActiveAlert[]>([]);

  const selectedClip = useMemo(
    () => demoClips.find((clip) => clip.id === selectedClipId) ?? demoClips[0]!,
    [selectedClipId],
  );

  const visibleAlert = useMemo(
    () => chooseVisibleAlert(activeAlerts)?.alert ?? null,
    [activeAlerts],
  );

  const progress = duration > 0 ? currentTime / duration : 0;

  const applyStreamEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
      case "session_started":
        alertSequenceRef.current = 0;
        setActiveAlerts([]);
        break;
      case "alert_start": {
        const sequence = alertSequenceRef.current;
        alertSequenceRef.current += 1;
        setActiveAlerts((alerts) => [
          ...alerts.filter((alert) => alert.eventId !== event.eventId),
          {
            eventId: event.eventId,
            sequence,
            alert: event.alert,
          },
        ]);
        break;
      }
      case "alert_end":
        setActiveAlerts((alerts) =>
          alerts.filter((alert) => alert.eventId !== event.eventId),
        );
        break;
      case "session_done":
        setActiveAlerts([]);
        break;
    }
  }, []);

  const stopAndReset = useCallback(() => {
    streamControllerRef.current?.abort();
    streamControllerRef.current = null;
    streamRunRef.current += 1;
    alertSequenceRef.current = 0;
    setActiveAlerts([]);

    const audio = audioRef.current;

    if (audio) {
      audio.pause();
      audio.currentTime = 0;
    }

    setCurrentTime(0);
    setIsPlaying(false);
  }, []);

  const startClip = useCallback(
    async (clip: DemoClip) => {
      if (!clip.audio) {
        return;
      }

      streamControllerRef.current?.abort();
      alertSequenceRef.current = 0;
      setActiveAlerts([]);
      setSelectedClipId(clip.id);
      setCurrentTime(0);
      setDuration(0);

      const audio = audioRef.current;

      if (!audio) {
        return;
      }

      audio.pause();
      audio.muted = false;
      audio.volume = 1;

      const nextSrc = new URL(clip.audio.src, window.location.href).href;
      const sourceChanged = audio.currentSrc !== nextSrc && audio.src !== nextSrc;

      if (sourceChanged) {
        audio.src = clip.audio.src;
        audio.load();
      }

      try {
        audio.currentTime = 0;
      } catch {
        // Some browsers reject seeking until metadata exists for a new source.
      }

      const controller = new AbortController();
      const runId = streamRunRef.current + 1;
      streamRunRef.current = runId;
      streamControllerRef.current = controller;

      try {
        await audio.play();
      } catch {
        if (
          streamRunRef.current === runId &&
          !controller.signal.aborted
        ) {
          controller.abort();
          streamControllerRef.current = null;
          setCurrentTime(0);
          setIsPlaying(false);
        }

        return;
      }

      if (streamRunRef.current !== runId || controller.signal.aborted) {
        return;
      }

      setIsPlaying(true);

      void streamDemoEvents({
        clipId: clip.id,
        language,
        signal: controller.signal,
        allowFallback: false,
        onEvent: (event) => {
          if (
            streamRunRef.current === runId &&
            !controller.signal.aborted
          ) {
            applyStreamEvent(event);
          }
        },
      })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) {
            console.warn("SoundSight stream ended unexpectedly", error);
          }
        })
        .finally(() => {
          if (streamRunRef.current === runId) {
            streamControllerRef.current = null;
          }
        });
    },
    [applyStreamEvent, language],
  );

  function handleToggleClip(clip: DemoClip) {
    if (!clip.audio) {
      return;
    }

    if (clip.id === selectedClip.id && isPlaying) {
      stopAndReset();
      return;
    }

    void startClip(clip);
  }

  function handleSelectClip(clipId: string) {
    const nextClip = demoClips.find((clip) => clip.id === clipId);

    if (!nextClip || nextClip.id === selectedClip.id) {
      return;
    }

    stopAndReset();
    setSelectedClipId(nextClip.id);
    setCurrentTime(0);
    setDuration(0);
  }

  useEffect(() => {
    return () => {
      streamControllerRef.current?.abort();
    };
  }, []);

  return (
    <main className="h-dvh overflow-hidden bg-[#030507] text-white lg:min-h-screen">
      <audio
        ref={audioRef}
        preload="metadata"
        src={selectedClip.audio?.src}
        onLoadedMetadata={(event) => {
          const nextDuration = event.currentTarget.duration;
          setDuration(Number.isFinite(nextDuration) ? nextDuration : 0);
        }}
        onTimeUpdate={(event) => {
          setCurrentTime(event.currentTarget.currentTime);
          const nextDuration = event.currentTarget.duration;
          if (Number.isFinite(nextDuration)) {
            setDuration(nextDuration);
          }
        }}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        onEnded={() => {
          stopAndReset();
        }}
      />

      <div className="flex h-full w-full min-w-0 max-w-full flex-col overflow-hidden lg:mx-auto lg:min-h-screen lg:max-w-6xl lg:px-8 lg:py-8">
        <header className="hidden items-center justify-between gap-4 lg:flex">
          <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-100">
            SoundSight
          </div>
          <LanguageSelector value={language} onChange={setLanguage} />
        </header>

        <div className="w-full max-w-full min-w-0 shrink-0 space-y-2 overflow-hidden px-3 pb-3 pt-3 lg:hidden">
          <div className="flex min-w-0 justify-end">
            <LanguageSelector value={language} onChange={setLanguage} />
          </div>
          <ClipSelector
            clips={demoClips}
            selectedClipId={selectedClip.id}
            isPlaying={isPlaying}
            progress={progress}
            onSelect={handleSelectClip}
            onToggle={handleToggleClip}
            compact
          />
        </div>

        <section className="flex min-h-0 flex-1 lg:grid lg:grid-cols-[340px_minmax(0,1fr)] lg:items-center lg:gap-16 lg:py-0">
          <div className="hidden lg:block">
            <ClipSelector
              clips={demoClips}
              selectedClipId={selectedClip.id}
              isPlaying={isPlaying}
              progress={progress}
              onSelect={handleSelectClip}
              onToggle={handleToggleClip}
            />
          </div>

          <PhoneEmulator
            alert={visibleAlert}
            language={language}
            isPlaying={isPlaying}
          />
        </section>
      </div>
    </main>
  );
}

function chooseVisibleAlert(alerts: ActiveAlert[]): ActiveAlert | null {
  return alerts.reduce<ActiveAlert | null>((visibleAlert, alert) => {
    if (!visibleAlert) {
      return alert;
    }

    const alertPriority = tierPriority[alert.alert.tier];
    const visiblePriority = tierPriority[visibleAlert.alert.tier];

    if (alertPriority > visiblePriority) {
      return alert;
    }

    if (
      alertPriority === visiblePriority &&
      alert.sequence > visibleAlert.sequence
    ) {
      return alert;
    }

    return visibleAlert;
  }, null);
}
