import {
  type LanguageCode,
  type StreamEvent,
} from "@/lib/demo-alerts";

type DemoStreamEventsOptions = {
  clipId: string;
  language: LanguageCode;
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
};

type LiveWindowEventsOptions = {
  audio: Blob;
  language: LanguageCode;
  sessionId: string;
  signal: AbortSignal;
  onEvent: (event: StreamEvent) => void;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_SOUNDSIGHT_API_URL ?? "http://127.0.0.1:8000";
const BACKEND_CONNECT_TIMEOUT_MS = 10_000;
const FIRST_STREAM_CHUNK_TIMEOUT_MS = 2_500;

export async function streamDemoEvents(
  options: DemoStreamEventsOptions,
): Promise<void> {
  await streamBackendEvents(options);
}

export async function streamLiveWindowEvents({
  audio,
  language,
  sessionId,
  signal,
  onEvent,
}: LiveWindowEventsOptions): Promise<void> {
  const formData = new FormData();
  formData.append("audio", audio, liveWindowFileName(audio.type));
  formData.append("language", language);
  formData.append("sessionId", sessionId);

  const response = await fetch(`${API_BASE_URL}/api/live/process-window`, {
    method: "POST",
    headers: {
      Accept: "application/x-ndjson",
    },
    body: formData,
    signal,
  });

  await readNdjsonResponse(response, onEvent);
}

async function streamBackendEvents({
  clipId,
  language,
  signal,
  onEvent,
}: DemoStreamEventsOptions): Promise<void> {
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

  try {
    await readNdjsonResponse(response, onEvent);
  } finally {
    backendAbort.cleanup();
  }
}

async function readNdjsonResponse(
  response: Response,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  if (!response.ok) {
    throw new Error(`Stream request failed with ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Stream response did not include a body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let didReadChunk = false;

  try {
    while (true) {
      const readResult = didReadChunk
        ? await reader.read()
        : await readFirstChunk(reader);

      const { done, value } = readResult;

      if (done) {
        break;
      }

      didReadChunk = true;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        emitNdjsonLine(line, onEvent);
      }
    }

    buffer += decoder.decode();
    emitNdjsonLine(buffer, onEvent);
  } catch (error) {
    try {
      await reader.cancel();
    } catch {
      // The stream may already be closed by the browser or server.
    }
    throw error;
  } finally {
    reader.releaseLock();
  }
}

async function readFirstChunk(
  reader: ReadableStreamDefaultReader<Uint8Array>,
): Promise<ReadableStreamReadResult<Uint8Array>> {
  let timeoutId: number | undefined;

  try {
    const readResult = await Promise.race([
      reader.read(),
      new Promise<never>((_, reject) => {
        timeoutId = window.setTimeout(
          () => reject(new BackendUnavailableError()),
          FIRST_STREAM_CHUNK_TIMEOUT_MS,
        );
      }),
    ]);

    return readResult;
  } finally {
    if (timeoutId !== undefined) {
      window.clearTimeout(timeoutId);
    }
  }
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
    super("Backend stream did not respond before connection timeout");
    this.name = "BackendUnavailableError";
  }
}

function liveWindowFileName(mimeType: string): string {
  if (mimeType.includes("mp4")) {
    return "live-window.mp4";
  }

  if (mimeType.includes("ogg") || mimeType.includes("opus")) {
    return "live-window.ogg";
  }

  if (mimeType.includes("wav")) {
    return "live-window.wav";
  }

  return "live-window.webm";
}
