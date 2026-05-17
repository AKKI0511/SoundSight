import { MinimalAlert } from "@/components/MinimalAlert";
import type { StreamAlert } from "@/lib/demo-alerts";

type PhoneEmulatorProps = {
  alert: StreamAlert | null;
  isPlaying: boolean;
  statusLabel?: string;
};

export function PhoneEmulator({
  alert,
  isPlaying,
  statusLabel,
}: PhoneEmulatorProps) {
  const visibleStatus = statusLabel ?? (isPlaying ? "listening" : "ready");

  return (
    <section className="flex min-h-0 w-full min-w-0 flex-1 lg:mx-auto lg:block lg:max-w-[380px] lg:flex-none">
      <div className="relative flex min-h-0 flex-1 overflow-hidden bg-[#030507] lg:block lg:h-[650px] lg:rounded-[3rem] lg:border lg:border-white/12 lg:bg-[#090b0f] lg:p-3 lg:shadow-[0_30px_100px_rgba(0,0,0,0.55)]">
        <div className="absolute left-1/2 top-5 z-10 hidden h-6 w-24 -translate-x-1/2 rounded-full bg-black lg:block" />
        <div className="relative flex min-h-0 w-full flex-1 items-center justify-center overflow-hidden bg-[#030507] lg:h-full lg:rounded-[2.35rem] lg:border lg:border-white/8">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-28 bg-gradient-to-b from-white/[0.045] to-transparent" />
          {alert ? (
            <MinimalAlert alert={alert} />
          ) : (
            <div className="flex flex-1 items-center justify-center">
              <div
                className="flex items-center gap-3 text-sm font-medium text-slate-500"
                aria-live="polite"
              >
                <span
                  className={`size-2 rounded-full ${
                    isPlaying ? "animate-pulse bg-cyan-200" : "bg-slate-700"
                  }`}
                />
                {visibleStatus}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
