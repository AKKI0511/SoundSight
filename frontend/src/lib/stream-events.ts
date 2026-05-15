import {
  getDemoClip,
  type LanguageCode,
  type ScheduledAlert,
  type StreamEvent,
} from "@/lib/demo-alerts";

type StreamEventsOptions = {
  clipId: string;
  language: LanguageCode;
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
  allowFallback?: boolean;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_SOUNDSIGHT_API_URL ?? "http://localhost:8000";
const BACKEND_CONNECT_TIMEOUT_MS = 1200;

export async function streamDemoEvents(
  options: StreamEventsOptions,
): Promise<void> {
  try {
    await streamBackendEvents(options);
  } catch (error) {
    if (options.signal.aborted || isAbortError(error)) {
      throw error;
    }

    if (options.allowFallback === false) {
      throw error;
    }

    await streamLocalFallbackEvents(options);
  }
}

async function streamBackendEvents({
  clipId,
  language,
  signal,
  onEvent,
}: StreamEventsOptions): Promise<void> {
  const backendAbort = createBackendAbort(signal);
  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/api/demo/stream-events`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/x-ndjson",
      },
      body: JSON.stringify({ clipId, language }),
      signal: backendAbort.signal,
    });
  } catch (error) {
    if (backendAbort.timedOut()) {
      throw new BackendUnavailableError();
    }

    throw error;
  }

  backendAbort.clearConnectTimeout();

  if (!response.ok) {
    backendAbort.cleanup();
    throw new Error(`Stream request failed with ${response.status}`);
  }

  if (!response.body) {
    backendAbort.cleanup();
    throw new Error("Stream response did not include a body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        emitNdjsonLine(line, onEvent);
      }
    }

    buffer += decoder.decode();
    emitNdjsonLine(buffer, onEvent);
  } finally {
    reader.releaseLock();
    backendAbort.cleanup();
  }
}

async function streamLocalFallbackEvents({
  clipId,
  signal,
  onEvent,
}: StreamEventsOptions): Promise<void> {
  const clip = getDemoClip(clipId);

  if (!clip) {
    throw new Error(`Unknown fallback clip: ${clipId}`);
  }

  const sessionId = `local_${getSessionToken()}`;
  let elapsedMs = 0;

  onEvent({
    type: "session_started",
    sessionId,
    clipId,
    timestampMs: 0,
  });

  for (const scheduledAlert of clip.localSchedule.alerts) {
    await waitUntil(scheduledAlert.startMs, elapsedMs, signal);
    elapsedMs = scheduledAlert.startMs;
    emitLocalAlertStart(sessionId, scheduledAlert, onEvent);

    await waitUntil(scheduledAlert.endMs, elapsedMs, signal);
    elapsedMs = scheduledAlert.endMs;
    onEvent({
      type: "alert_end",
      sessionId,
      eventId: scheduledAlert.eventId,
      timestampMs: scheduledAlert.endMs,
    });
  }

  await waitUntil(clip.localSchedule.doneMs, elapsedMs, signal);
  onEvent({
    type: "session_done",
    sessionId,
    timestampMs: clip.localSchedule.doneMs,
  });
}

function emitLocalAlertStart(
  sessionId: string,
  scheduledAlert: ScheduledAlert,
  onEvent: (event: StreamEvent) => void,
) {
  onEvent({
    type: "alert_start",
    sessionId,
    eventId: scheduledAlert.eventId,
    timestampMs: scheduledAlert.startMs,
    alert: scheduledAlert.alert,
  });
}

function emitNdjsonLine(
  line: string,
  onEvent: (event: StreamEvent) => void,
) {
  const trimmedLine = line.trim();

  if (!trimmedLine) {
    return;
  }

  onEvent(JSON.parse(trimmedLine) as StreamEvent);
}

function waitUntil(
  targetMs: number,
  elapsedMs: number,
  signal: AbortSignal,
): Promise<void> {
  return wait(Math.max(0, targetMs - elapsedMs), signal);
}

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(createAbortError());
      return;
    }

    const timeoutId = window.setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, ms);

    function abort() {
      window.clearTimeout(timeoutId);
      reject(createAbortError());
    }

    signal.addEventListener("abort", abort, { once: true });
  });
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function createAbortError(): DOMException {
  return new DOMException("Stream aborted", "AbortError");
}

function getSessionToken(): string {
  return globalThis.crypto?.randomUUID?.() ?? String(Date.now());
}

function createBackendAbort(signal: AbortSignal) {
  const controller = new AbortController();
  let didTimeOut = false;

  const timeoutId = window.setTimeout(() => {
    didTimeOut = true;
    controller.abort();
  }, BACKEND_CONNECT_TIMEOUT_MS);

  function abortFromCaller() {
    controller.abort();
  }

  signal.addEventListener("abort", abortFromCaller, { once: true });

  return {
    signal: controller.signal,
    timedOut: () => didTimeOut,
    clearConnectTimeout: () => window.clearTimeout(timeoutId),
    cleanup: () => {
      window.clearTimeout(timeoutId);
      signal.removeEventListener("abort", abortFromCaller);
    },
  };
}

class BackendUnavailableError extends Error {
  constructor() {
    super("Backend stream did not respond before fallback timeout");
    this.name = "BackendUnavailableError";
  }
}
