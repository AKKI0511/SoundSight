import Image from "next/image";
import {
  DoorOpen,
  Flame,
  Hand,
  MessageCircle,
  Siren,
  type LucideIcon,
} from "lucide-react";
import {
  alertImagesByKey,
  getLocalizedAlertCopy,
  iconByImageKey,
  type IconKey,
  type LanguageCode,
  type StreamAlert,
} from "@/lib/demo-alerts";

type MinimalAlertProps = {
  alert: StreamAlert;
  language: LanguageCode;
};

const iconMap: Record<IconKey, LucideIcon> = {
  siren: Siren,
  fire: Flame,
  attention: Hand,
  door: DoorOpen,
  speech: MessageCircle,
};

export function MinimalAlert({ alert, language }: MinimalAlertProps) {
  const copy = getLocalizedAlertCopy(alert, language);
  const image = alertImagesByKey[alert.image_key];
  const iconKey = iconByImageKey[alert.image_key] ?? "speech";
  const FallbackIcon = iconMap[iconKey];

  return (
    <div className="flex h-full flex-col items-center justify-center px-7 text-center">
      <div className="grid size-44 place-items-center rounded-[2rem] bg-white/[0.06] ring-1 ring-white/10 sm:size-52">
        {image ? (
          <Image
            src={image.src}
            alt={image.alt}
            width={220}
            height={220}
            className="h-32 w-32 object-contain drop-shadow-2xl sm:h-40 sm:w-40"
            priority
          />
        ) : (
          <FallbackIcon className="size-24 text-cyan-100" aria-hidden="true" />
        )}
      </div>

      <p className="mt-10 text-3xl font-semibold leading-tight text-white">
        {copy.alertText}
      </p>
      <p className="mt-4 text-lg font-medium leading-snug text-cyan-100">
        {copy.actionText}
      </p>
    </div>
  );
}
