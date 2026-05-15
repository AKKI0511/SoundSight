"use client";

import { languages, type LanguageCode } from "@/lib/demo-alerts";

type LanguageSelectorProps = {
  value: LanguageCode;
  onChange: (language: LanguageCode) => void;
};

export function LanguageSelector({ value, onChange }: LanguageSelectorProps) {
  return (
    <div
      className="grid shrink-0 grid-cols-3 overflow-hidden rounded-full border border-white/10 bg-white/[0.035] p-1"
      style={{ width: 104 }}
      role="group"
      aria-label="Alert language"
    >
      {languages.map((language) => {
        const isSelected = value === language.code;

        return (
          <button
            key={language.code}
            type="button"
            aria-pressed={isSelected}
            className={`h-8 min-w-8 rounded-full px-2 text-xs font-semibold transition sm:min-w-10 sm:px-3 ${
              isSelected
                ? "bg-white text-slate-950"
                : "text-slate-400 hover:text-white"
            }`}
            onClick={() => onChange(language.code)}
            title={language.label}
          >
            {language.shortLabel}
          </button>
        );
      })}
    </div>
  );
}
