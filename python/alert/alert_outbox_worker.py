import time
import random
import logging
from typing import Optional
from alert.outbox_models import OutboxRepository, AlertStatus
from alert.telegram_adapter import TelegramAdapter
from alert.rate_limiter import RateLimiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertOutboxWorker:
    def __init__(self, 
                 repository: OutboxRepository, 
                 adapter: TelegramAdapter, 
                 rate_limiter: RateLimiter,
                 max_retries: int = 5,
                 base_delay: float = 1.0):
        self.repository = repository
        self.adapter = adapter
        self.rate_limiter = rate_limiter
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.running = False

    def start(self, poll_interval: float = 2.0):
        self.running = True
        logger.info("Starting AlertOutboxWorker...")
        while self.running:
            self._process_outbox()
            time.sleep(poll_interval)

    def stop(self):
        self.running = False

    def _process_outbox(self):
        events = self.repository.get_pending_events(limit=50)
        for event in events:
            if not self.running:
                break
                
            self.rate_limiter.wait_if_needed(event.destination)
            
            # Format message
            msg = self.adapter.format_scan_result(event.payload)
            
            # Send message
            success, retry_after, response = self.adapter.send_message(event.destination, msg)
            
            if success:
                self.repository.update_event_status(
                    event.alert_id, 
                    AlertStatus.SENT, 
                    event.retry_count, 
                    0
                )
                logger.info(f"Successfully sent alert_id {event.alert_id}")
            else:
                self._handle_failure(event, retry_after, response)

    def _handle_failure(self, event, retry_after: int, response: dict):
        new_retry_count = event.retry_count + 1
        
        if new_retry_count >= self.max_retries:
            # Move to Dead Letter Queue (FAILED)
            self.repository.update_event_status(
                event.alert_id,
                AlertStatus.FAILED,
                new_retry_count,
                0
            )
            logger.error(f"Alert {event.alert_id} failed after {self.max_retries} retries. Moved to FAILED.")
            return

        # Calculate backoff
        if retry_after > 0:
            # Respect Telegram's 429 retry_after explicitly
            delay = retry_after
        else:
            # Exponential backoff with random jitter
            delay = (self.base_delay * (2 ** event.retry_count)) + random.uniform(0, 1)

        next_retry_at = int(time.time() + delay)
        
        self.repository.update_event_status(
            event.alert_id,
            AlertStatus.RETRYING,
            new_retry_count,
            next_retry_at
        )
        logger.warning(f"Failed to send alert {event.alert_id}. Retrying at {next_retry_at} (delay: {delay:.2f}s)")
