import time
from typing import List, Optional
from alert.outbox_models import OutboxRepository, AlertEvent
from engine.scanner.scanner_types import ScanResult

class AlertPolicy:
    MIN_TOTAL_SCORE = 80
    MIN_TREND_SCORE = 80
    COOLDOWN_SECONDS = 4 * 3600
    SUMMARY_SIZE = 3
    RULE_VERSION = "v1.0"

    def __init__(self, outbox_repo: OutboxRepository):
        self.outbox_repo = outbox_repo

    def evaluate_and_emit(self, results: List[ScanResult], current_time: int = None) -> Optional[AlertEvent]:
        """
        Evaluates scan results and emits a summary AlertEvent if conditions are met.
        current_time should be in SECONDS.
        """
        if current_time is None:
            current_time = int(time.time())

        # Filter by quality, scores
        valid_candidates = []
        for r in results:
            if r.data_quality != "VALID":
                continue
            if getattr(r, 'total_score', 0) < self.MIN_TOTAL_SCORE:
                continue
            if getattr(r, 'trend_score', 0) < self.MIN_TREND_SCORE:
                continue
            valid_candidates.append(r)

        if not valid_candidates:
            return None

        # Sort by total score descending
        valid_candidates.sort(key=lambda x: getattr(x, 'total_score', 0), reverse=True)

        # Check cooldowns
        symbols_to_check = [c.symbol for c in valid_candidates]
        cooldowns = self.outbox_repo.get_cooldowns(symbols_to_check)
        
        final_list = []
        for c in valid_candidates:
            last_alert = cooldowns.get(c.symbol, 0)
            if last_alert == 0 or (current_time - last_alert) >= self.COOLDOWN_SECONDS:
                final_list.append(c)
            
            if len(final_list) == self.SUMMARY_SIZE:
                break

        if not final_list:
            return None

        # Create payload
        payload_items = []
        alerted_symbols = []
        for c in final_list:
            alerted_symbols.append(c.symbol)
            payload_items.append({
                "symbol": c.symbol,
                "total_score": getattr(c, 'total_score', 0),
                "trend_score": getattr(c, 'trend_score', 0),
                "momentum_score": getattr(c, 'momentum_score', 0),
                "mtf_score": getattr(c, 'mtf_score', 0),
                "trend": getattr(c, 'trend_state', 'UNKNOWN')
            })

        # Update cooldowns
        self.outbox_repo.update_cooldowns(alerted_symbols, current_time)

        # Generate idempotency key based on time chunk (e.g. 15 minute intervals)
        # We round down the timestamp to the nearest 15 minutes to avoid duplicates within that window
        interval_15m = (current_time // 900) * 900
        
        signal_id = f"alert:summary:vn30:15m:{interval_15m}:{self.RULE_VERSION}"

        event = AlertEvent(
            signal_id=signal_id,
            destination="TELEGRAM_SUMMARY",
            payload={"items": payload_items},
            created_at=current_time,
            rule_version=self.RULE_VERSION
        )

        # Try to add to outbox, will return False if duplicate
        self.outbox_repo.add_event(event)
        return event
