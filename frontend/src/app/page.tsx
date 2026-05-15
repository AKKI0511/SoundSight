"use client";

import { useMemo, useRef, useState } from "react";
import { ClipSelector } from "@/components/ClipSelector";
import { LanguageSelector } from "@/components/LanguageSelector";
import { PhoneEmulator } from "@/components/PhoneEmulator";
import {
  playableDemoClips,
  type LanguageCode,
  type PlayableDemoClip,
} from "@/lib/demo-alerts";

export default function Home() {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [selectedClipId, setSelectedClipId] = useState(
    playableDemoClips[0]?.id ?? "",
  );
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const selectedClip = useMemo(
    () =>
      playableDemoClips.find((clip) => clip.id === selectedClipId) ??
      playableDemoClips[0]!,
    [selectedClipId],
  );

  const progress = duration > 0 ? currentTime / duration : 0;
  const isInEventWindow =
    isPlaying &&
    progress >= selectedClip.eventWindow.startRatio &&
    progress <= selectedClip.eventWindow.endRatio;
  const visibleAlert = isInEventWindow ? selectedClip : null;

  function resetAudioForClip(clip: PlayableDemoClip) {
    const audio = audioRef.current;

    if (audio) {
      audio.pause();
      audio.src = clip.audio.src;
      audio.currentTime = 0;
      audio.load();
    }

    setSelectedClipId(clip.id);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
  }

  function handleSelectClip(clipId: string) {
    const nextClip = playableDemoClips.find((clip) => clip.id === clipId);

    if (!nextClip || nextClip.id === selectedClip.id) {
      return;
    }

    resetAudioForClip(nextClip);
  }

  async function handleToggleClip(clip: PlayableDemoClip) {
    const audio = audioRef.current;

    if (!audio) {
      return;
    }

    if (clip.id === selectedClip.id && isPlaying) {
      audio.pause();
      return;
    }

    if (clip.id !== selectedClip.id) {
      audio.pause();
      audio.src = clip.audio.src;
      audio.currentTime = 0;
      audio.load();
      setSelectedClipId(clip.id);
      setCurrentTime(0);
      setDuration(0);
    }

    try {
      await audio.play();
    } catch {
      setIsPlaying(false);
    }
  }

  return (
    <main className="h-dvh overflow-hidden bg-[#030507] text-white lg:min-h-screen">
      <audio
        ref={audioRef}
        preload="metadata"
        src={selectedClip.audio.src}
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
        onEnded={(event) => {
          event.currentTarget.currentTime = 0;
          setCurrentTime(0);
          setIsPlaying(false);
        }}
      />

      <div className="flex h-full w-full min-w-0 max-w-full flex-col overflow-hidden lg:mx-auto lg:min-h-screen lg:max-w-6xl lg:px-8 lg:py-8">
        <header className="hidden items-center justify-between gap-4 lg:flex">
          <div className="text-sm font-semibold uppercase tracking-[0.24em] text-cyan-100">
            SoundSight
          </div>
          <LanguageSelector value={language} onChange={setLanguage} />
        </header>

        <div className="w-screen max-w-screen min-w-0 shrink-0 space-y-2 overflow-hidden px-3 pb-3 pt-3 lg:hidden">
          <div className="flex min-w-0 justify-end">
            <LanguageSelector value={language} onChange={setLanguage} />
          </div>
          <ClipSelector
            clips={playableDemoClips}
            selectedClipId={selectedClip.id}
            isPlaying={isPlaying}
            progress={progress}
            onSelect={handleSelectClip}
            onToggle={handleToggleClip}
            compact
          />
        </div>

        <section className="flex min-h-0 flex-1 lg:grid lg:items-center lg:gap-16 lg:py-0 lg:grid-cols-[340px_minmax(0,1fr)]">
          <div className="hidden lg:block">
            <ClipSelector
              clips={playableDemoClips}
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
