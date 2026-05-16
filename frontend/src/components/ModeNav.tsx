"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type ModeNavProps = {
  className?: string;
};

const modes = [
  { href: "/live", label: "Live", id: "live" },
  { href: "/demo", label: "Demo", id: "demo" },
] as const;

export function ModeNav({ className = "" }: ModeNavProps) {
  const pathname = usePathname();
  const activeMode = pathname.startsWith("/live") ? "live" : "demo";

  return (
    <nav
      className={`grid grid-cols-2 overflow-hidden rounded-full border border-white/10 bg-white/[0.035] p-1 ${className}`}
      aria-label="Mode"
    >
      {modes.map((mode) => {
        const isActive = activeMode === mode.id;

        return (
          <Link
            key={mode.id}
            href={mode.href}
            aria-current={isActive ? "page" : undefined}
            className={`grid h-8 min-w-16 place-items-center rounded-full px-3 text-xs font-semibold transition ${
              isActive
                ? "bg-white text-slate-950"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {mode.label}
          </Link>
        );
      })}
    </nav>
  );
}
