"use client";

import { Pause, Play } from "lucide-react";
import { ProgressBar } from "@/components/ProgressBar";
import type { DemoClip } from "@/lib/demo-alerts";

type ClipSelectorProps = {
  clips: DemoClip[];
  selectedClipId: string;
  isPlaying: boolean;
  progress: number;
  onSelect: (clipId: string) => void;
  onToggle: (clip: DemoClip) => void;
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
    const isUnavailable = !selectedClip?.audio;
    const selectedProgress = selectedClip ? progress : 0;

    return (
      <section className="w-full min-w-0 rounded-2xl border border-white/10 bg-white/[0.04] p-2">
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
              className={`grid size-11 shrink-0 place-items-center rounded-full transition focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 ${
                isUnavailable
                  ? "cursor-not-allowed bg-white/10 text-slate-500"
                  : "bg-white text-slate-950 hover:bg-cyan-100"
              }`}
              aria-label={
                isUnavailable
                  ? `${selectedClip.clipName} unavailable`
                  : `${isPlaying ? "Pause" : "Play"} ${selectedClip.clipName}`
              }
              disabled={isUnavailable}
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
          <ProgressBar
            value={selectedClip?.id === selectedClipId ? selectedProgress : 0}
            active={isPlaying}
          />
        </div>
      </section>
    );
  }

  return (
    <section className={compact ? "space-y-2" : "space-y-2"}>
      <div className="space-y-2">
        {clips.map((clip) => {
          const isSelected = clip.id === selectedClipId;
          const isActive = isSelected && isPlaying;
          const isUnavailable = !clip.audio;

          return (
            <div
              key={clip.id}
              className={`rounded-2xl border transition ${
                compact ? "p-3" : "p-4"
              } ${
                isSelected
                  ? "border-cyan-200/40 bg-white/[0.065]"
                  : "border-white/10 bg-white/[0.035]"
              } ${isUnavailable ? "opacity-45" : "hover:border-white/20"}`}
            >
              <div className="flex items-center justify-between gap-4">
                <p
                  className={`min-w-0 truncate font-medium ${
                    compact ? "text-sm" : "text-base"
                  } ${isUnavailable ? "text-slate-500" : "text-white"}`}
                >
                  {clip.clipName}
                </p>
                <button
                  type="button"
                  className={`grid shrink-0 place-items-center rounded-full transition focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 ${
                    compact ? "size-9" : "size-10"
                  } ${
                    isUnavailable
                      ? "cursor-not-allowed bg-white/10 text-slate-500"
                      : "bg-white text-slate-950 hover:bg-cyan-100"
                  }`}
                  aria-label={
                    isUnavailable
                      ? `${clip.clipName} unavailable`
                      : `${isActive ? "Pause" : "Play"} ${clip.clipName}`
                  }
                  disabled={isUnavailable}
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
