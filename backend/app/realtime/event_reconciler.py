from dataclasses import dataclass

from app.schemas import AlertAnalysis, AlertEndEvent, AlertStartEvent, StreamEvent


@dataclass
class EventReconciler:
    session_id: str
    active_sound_type: str | None = None
    active_event_id: str | None = None
    alert_count: int = 0

    def reconcile(self, analysis: AlertAnalysis, *, timestamp_ms: int) -> list[StreamEvent]:
        if analysis.should_alert:
            return self._reconcile_alert(analysis, timestamp_ms=timestamp_ms)
        return self._reconcile_no_alert(timestamp_ms=timestamp_ms)

    def finish(self, *, timestamp_ms: int) -> list[StreamEvent]:
        if self.active_event_id is None:
            return []

        event_id = self.active_event_id
        self.active_sound_type = None
        self.active_event_id = None
        return [
            AlertEndEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=timestamp_ms,
            )
        ]

    def _reconcile_alert(
        self,
        analysis: AlertAnalysis,
        *,
        timestamp_ms: int,
    ) -> list[StreamEvent]:
        if self.active_sound_type == analysis.sound_type:
            return []

        self.alert_count += 1
        event_id = f"{analysis.sound_type}_{self.alert_count}"
        self.active_sound_type = analysis.sound_type
        self.active_event_id = event_id
        return [
            AlertStartEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=timestamp_ms,
                alert=analysis.to_alert_payload(),
            )
        ]

    def _reconcile_no_alert(self, *, timestamp_ms: int) -> list[StreamEvent]:
        if self.active_event_id is None:
            return []

        event_id = self.active_event_id
        self.active_sound_type = None
        self.active_event_id = None
        return [
            AlertEndEvent(
                session_id=self.session_id,
                event_id=event_id,
                timestamp_ms=timestamp_ms,
            )
        ]
