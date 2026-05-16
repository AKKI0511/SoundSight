import type { AlertTier, StreamAlert } from "@/lib/demo-alerts";

export type ActiveAlert = {
  key: string;
  eventId: string;
  sessionId: string;
  sequence: number;
  alert: StreamAlert;
};

const tierPriority: Record<AlertTier, number> = {
  emergency: 3,
  social: 2,
  ambient: 1,
  none: 0,
};

export function alertKey(sessionId: string, eventId: string): string {
  return `${sessionId}:${eventId}`;
}

export function chooseVisibleAlert(alerts: ActiveAlert[]): ActiveAlert | null {
  return alerts.reduce<ActiveAlert | null>((visibleAlert, alert) => {
    if (!visibleAlert) {
      return alert;
    }

    const alertPriority = tierPriority[alert.alert.tier];
    const visiblePriority = tierPriority[visibleAlert.alert.tier];

    if (alertPriority > visiblePriority) {
      return alert;
    }

    if (
      alertPriority === visiblePriority &&
      alert.sequence > visibleAlert.sequence
    ) {
      return alert;
    }

    return visibleAlert;
  }, null);
}
