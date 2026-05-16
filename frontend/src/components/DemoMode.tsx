"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ClipSelector } from "@/components/ClipSelector";
import { GlobalNav } from "@/components/GlobalNav";
import { PhoneEmulator } from "@/components/PhoneEmulator";
import {
  demoClips,
  type DemoClip,
  type LanguageCode,
  type StreamEvent,
} from "@/lib/demo-alerts";
import {
  alertKey,
  chooseVisibleAlert,
  type ActiveAlert,
} from "@/lib/alert-events";
import { streamDemoEvents } from "@/lib/stream-events";

export function DemoMode() {
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
        const key = alertKey(event.sessionId, event.eventId);
        const sequence = alertSequenceRef.current;
        alertSequenceRef.current += 1;
        setActiveAlerts((alerts) => [
          ...alerts.filter((alert) => alert.key !== key),
          {
            key,
            eventId: event.eventId,
            sessionId: event.sessionId,
            sequence,
            alert: event.alert,
          },
        ]);
        break;
      }
      case "alert_end": {
        const key = alertKey(event.sessionId, event.eventId);
        setActiveAlerts((alerts) =>
          alerts.filter((alert) => alert.key !== key),
        );
        break;
      }
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
    <main className="flex h-dvh flex-col overflow-hidden bg-[#030507] text-white lg:min-h-screen">
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

      <GlobalNav language={language} onLanguageChange={setLanguage} />

      <div className="flex min-h-0 w-full min-w-0 max-w-full flex-1 flex-col overflow-hidden lg:mx-auto lg:max-w-6xl lg:px-8 lg:pb-8 lg:pt-6">
        <div className="w-full max-w-full min-w-0 shrink-0 space-y-2 overflow-hidden px-3 pb-3 pt-3 lg:hidden">
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
