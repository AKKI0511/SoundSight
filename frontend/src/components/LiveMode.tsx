"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LanguageSelector } from "@/components/LanguageSelector";
import { MinimalAlert } from "@/components/MinimalAlert";
import { ModeNav } from "@/components/ModeNav";
import {
  alertKey,
  chooseVisibleAlert,
  type ActiveAlert,
} from "@/lib/alert-events";
import type { LanguageCode, StreamEvent } from "@/lib/demo-alerts";
import { streamLiveWindowEvents } from "@/lib/stream-events";

const LIVE_WINDOW_MS = 4_000;
const LIVE_WINDOW_INTERVAL_MS = 2_000;
const RECORDER_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4",
  "audio/ogg;codecs=opus",
];

export function LiveMode() {
  const streamRef = useRef<MediaStream | null>(null);
  const recordersRef = useRef<Set<MediaRecorder>>(new Set());
  const timeoutIdsRef = useRef<Set<number>>(new Set());
  const fetchControllersRef = useRef<Set<AbortController>>(new Set());
  const intervalIdRef = useRef<number | null>(null);
  const runIdRef = useRef(0);
  const windowIndexRef = useRef(0);
  const sessionBaseRef = useRef("");
  const alertSequenceRef = useRef(0);
  const startPendingRef = useRef(false);
  const languageRef = useRef<LanguageCode>("en");

  const [language, setLanguage] = useState<LanguageCode>("en");
  const [isListening, setIsListening] = useState(false);
  const [micBlocked, setMicBlocked] = useState(false);
  const [processingCount, setProcessingCount] = useState(0);
  const [activeAlerts, setActiveAlerts] = useState<ActiveAlert[]>([]);

  const visibleAlert = useMemo(
    () => chooseVisibleAlert(activeAlerts)?.alert ?? null,
    [activeAlerts],
  );
  const statusLabel = micBlocked
    ? "mic blocked"
    : isListening
      ? processingCount > 0
        ? "processing"
        : "listening"
      : null;

  useEffect(() => {
    languageRef.current = language;
  }, [language]);

  const applyLiveEvent = useCallback((event: StreamEvent) => {
    switch (event.type) {
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
    }
  }, []);

  const sendLiveWindow = useCallback(
    (audio: Blob, sessionId: string, runId: number) => {
      const controller = new AbortController();
      fetchControllersRef.current.add(controller);
      setProcessingCount((count) => count + 1);

      void streamLiveWindowEvents({
        audio,
        sessionId,
        language: languageRef.current,
        signal: controller.signal,
        onEvent: (event) => {
          if (runIdRef.current === runId && !controller.signal.aborted) {
            applyLiveEvent(event);
          }
        },
      })
        .catch((error: unknown) => {
          if (!controller.signal.aborted) {
            console.warn("SoundSight live window failed", error);
          }
        })
        .finally(() => {
          fetchControllersRef.current.delete(controller);
          setProcessingCount((count) => Math.max(0, count - 1));
        });
    },
    [applyLiveEvent],
  );

  const startRecorderWindow = useCallback(
    (runId: number) => {
      const stream = streamRef.current;
      if (!stream || runIdRef.current !== runId) {
        return;
      }

      if (typeof MediaRecorder === "undefined") {
        setMicBlocked(true);
        return;
      }

      const mimeType = preferredRecorderMimeType();
      let recorder: MediaRecorder;

      try {
        recorder = new MediaRecorder(
          stream,
          mimeType ? { mimeType } : undefined,
        );
      } catch {
        setMicBlocked(true);
        return;
      }

      const chunks: BlobPart[] = [];
      const windowIndex = windowIndexRef.current + 1;
      windowIndexRef.current = windowIndex;
      const sessionId = `${sessionBaseRef.current}_${windowIndex}`;
      let timeoutId: number | null = null;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        recordersRef.current.delete(recorder);
        if (timeoutId !== null) {
          timeoutIdsRef.current.delete(timeoutId);
        }

        if (runIdRef.current !== runId || chunks.length === 0) {
          return;
        }

        const audio = new Blob(chunks, {
          type: recorder.mimeType || mimeType || "audio/webm",
        });
        if (audio.size > 0) {
          sendLiveWindow(audio, sessionId, runId);
        }
      };

      recordersRef.current.add(recorder);

      try {
        recorder.start();
      } catch {
        recordersRef.current.delete(recorder);
        setMicBlocked(true);
        return;
      }

      timeoutId = window.setTimeout(() => {
        if (timeoutId !== null) {
          timeoutIdsRef.current.delete(timeoutId);
        }
        if (recorder.state !== "inactive") {
          recorder.stop();
        }
      }, LIVE_WINDOW_MS);
      timeoutIdsRef.current.add(timeoutId);
    },
    [sendLiveWindow],
  );

  const stopLiveSession = useCallback(() => {
    runIdRef.current += 1;
    startPendingRef.current = false;

    if (intervalIdRef.current !== null) {
      window.clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }

    for (const timeoutId of timeoutIdsRef.current) {
      window.clearTimeout(timeoutId);
    }
    timeoutIdsRef.current.clear();

    for (const recorder of recordersRef.current) {
      if (recorder.state !== "inactive") {
        recorder.stop();
      }
    }
    recordersRef.current.clear();

    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    for (const controller of fetchControllersRef.current) {
      controller.abort();
    }
    fetchControllersRef.current.clear();

    alertSequenceRef.current = 0;
    windowIndexRef.current = 0;
    setActiveAlerts([]);
    setProcessingCount(0);
    setIsListening(false);
  }, []);

  const startListening = useCallback(async () => {
    if (isListening || startPendingRef.current) {
      return;
    }

    startPendingRef.current = true;
    setMicBlocked(false);
    setActiveAlerts([]);
    setProcessingCount(0);
    alertSequenceRef.current = 0;
    windowIndexRef.current = 0;
    sessionBaseRef.current = `live_${sessionToken()}`;

    let stream: MediaStream;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone capture is unavailable.");
      }

      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
        },
      });
    } catch {
      startPendingRef.current = false;
      setMicBlocked(true);
      setIsListening(false);
      return;
    }

    const runId = runIdRef.current + 1;
    runIdRef.current = runId;
    streamRef.current = stream;
    setIsListening(true);
    startPendingRef.current = false;

    startRecorderWindow(runId);
    intervalIdRef.current = window.setInterval(() => {
      startRecorderWindow(runId);
    }, LIVE_WINDOW_INTERVAL_MS);
  }, [isListening, startRecorderWindow]);

  useEffect(() => {
    return () => {
      stopLiveSession();
    };
  }, [stopLiveSession]);

  return (
    <main className="relative h-dvh overflow-hidden bg-[#030507] text-white">
      <header className="pointer-events-none absolute inset-x-0 top-0 z-20 flex items-start justify-between gap-3 p-3 sm:p-5">
        <div className="pointer-events-auto hidden text-sm font-semibold uppercase tracking-[0.24em] text-cyan-100 sm:block">
          SoundSight
        </div>
        <div className="pointer-events-auto mx-auto sm:absolute sm:left-1/2 sm:-translate-x-1/2">
          <ModeNav />
        </div>
        <div className="pointer-events-auto">
          <LanguageSelector value={language} onChange={setLanguage} />
        </div>
      </header>

      <section className="flex h-full w-full items-center justify-center">
        {visibleAlert ? (
          <MinimalAlert alert={visibleAlert} language={language} />
        ) : null}
      </section>

      {statusLabel ? (
        <div
          className="absolute bottom-24 left-1/2 z-20 -translate-x-1/2 text-xs font-semibold uppercase tracking-[0.24em] text-slate-500"
          aria-live="polite"
        >
          {statusLabel}
        </div>
      ) : null}

      <button
        type="button"
        className="absolute bottom-8 left-1/2 z-20 h-12 min-w-40 -translate-x-1/2 rounded-full bg-white px-5 text-sm font-semibold text-slate-950 shadow-[0_18px_50px_rgba(0,0,0,0.4)] transition hover:bg-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
        onClick={isListening ? stopLiveSession : startListening}
      >
        {isListening ? "Stop Listening" : "Start Listening"}
      </button>
    </main>
  );
}

function preferredRecorderMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") {
    return undefined;
  }

  return RECORDER_MIME_TYPES.find((mimeType) =>
    MediaRecorder.isTypeSupported(mimeType),
  );
}

function sessionToken(): string {
  return globalThis.crypto?.randomUUID?.() ?? String(Date.now());
}
