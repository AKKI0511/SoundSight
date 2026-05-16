"use client";

import { LanguageSelector } from "@/components/LanguageSelector";
import { ModeNav } from "@/components/ModeNav";
import type { LanguageCode } from "@/lib/demo-alerts";

type GlobalNavProps = {
  language: LanguageCode;
  onLanguageChange: (language: LanguageCode) => void;
  className?: string;
};

export function GlobalNav({
  language,
  onLanguageChange,
  className = "",
}: GlobalNavProps) {
  return (
    <header
      className={`relative z-20 w-full shrink-0 border-b border-white/8 bg-[#030507]/95 px-3 py-3 text-white backdrop-blur sm:px-5 ${className}`}
    >
      <div className="mx-auto grid w-full max-w-6xl grid-cols-[minmax(0,1fr)_auto] items-center gap-2 sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)]">
        <div className="min-w-0 truncate text-sm font-semibold uppercase tracking-[0.18em] text-cyan-100 sm:tracking-[0.24em]">
          SoundSight
        </div>

        <div className="order-3 col-span-2 flex min-w-0 justify-center sm:order-none sm:col-span-1">
          <ModeNav />
        </div>

        <div className="flex min-w-0 justify-end">
          <LanguageSelector value={language} onChange={onLanguageChange} />
        </div>
      </div>
    </header>
  );
}
