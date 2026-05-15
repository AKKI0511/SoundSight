"use client";

import { Pause, Play } from "lucide-react";
import { ProgressBar } from "@/components/ProgressBar";
import type { PlayableDemoClip } from "@/lib/demo-alerts";

type ClipSelectorProps = {
  clips: PlayableDemoClip[];
  selectedClipId: string;
  isPlaying: boolean;
  progress: number;
  onSelect: (clipId: string) => void;
  onToggle: (clip: PlayableDemoClip) => void;
  compact?: boolean;
};

export function ClipSelector({
  clips,
  selectedClipId,
  isPlaying,
  progress,
  onSelect,
  onToggle,
  compact = false,
}: ClipSelectorProps) {
  const selectedClip = clips.find((clip) => clip.id === selectedClipId) ?? clips[0];

  if (compact) {
    const selectedProgress = selectedClip?.id === selectedClipId ? progress : 0;

    return (
      <section
        className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-2"
        style={{
          maxWidth: "calc(100vw - 1.5rem)",
          width: "calc(100vw - 1.5rem)",
        }}
      >
        <div
          className="grid min-w-0 items-center gap-2"
          style={{ gridTemplateColumns: "minmax(0, 1fr) 44px" }}
        >
          <div className="min-w-0 flex-1">
            <select
              className="h-11 w-full min-w-0 appearance-none truncate rounded-xl border border-white/10 bg-black/40 px-3 text-sm font-medium text-white outline-none"
              aria-label="Audio clip"
              value={selectedClipId}
              onChange={(event) => onSelect(event.target.value)}
            >
              {clips.map((clip) => (
                <option key={clip.id} value={clip.id}>
                  {clip.clipName}
                </option>
              ))}
            </select>
          </div>
          {selectedClip ? (
            <button
              type="button"
              className="grid size-11 shrink-0 place-items-center rounded-full bg-white text-slate-950 transition hover:bg-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
              aria-label={`${isPlaying ? "Pause" : "Play"} ${selectedClip.clipName}`}
              onClick={() => onToggle(selectedClip)}
            >
              {isPlaying ? (
                <Pause className="size-4" aria-hidden="true" />
              ) : (
                <Play className="size-4 fill-current" aria-hidden="true" />
              )}
            </button>
          ) : null}
        </div>
        <div className="mt-2">
          <ProgressBar value={selectedProgress} active={isPlaying} />
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium uppercase tracking-[0.18em] text-slate-500">
        Audio clips
      </h2>
      <div className="space-y-2">
        {clips.map((clip) => {
          const isSelected = clip.id === selectedClipId;
          const isActive = isSelected && isPlaying;

          return (
            <div
              key={clip.id}
              className={`rounded-2xl border p-4 transition ${
                isSelected
                  ? "border-cyan-200/40 bg-white/[0.065]"
                  : "border-white/10 bg-white/[0.035]"
              }`}
            >
              <div className="flex items-center justify-between gap-4">
                <p className="min-w-0 truncate text-base font-medium text-white">
                  {clip.clipName}
                </p>
                <button
                  type="button"
                  className="grid size-10 shrink-0 place-items-center rounded-full bg-white text-slate-950 transition hover:bg-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
                  aria-label={`${isActive ? "Pause" : "Play"} ${clip.clipName}`}
                  onClick={() => onToggle(clip)}
                >
                  {isActive ? (
                    <Pause className="size-4" aria-hidden="true" />
                  ) : (
                    <Play className="size-4 fill-current" aria-hidden="true" />
                  )}
                </button>
              </div>
              <div className="mt-4">
                <ProgressBar value={isSelected ? progress : 0} active={isActive} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
