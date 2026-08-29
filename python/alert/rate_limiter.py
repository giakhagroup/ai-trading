import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, global_limit_per_sec: float = 30.0, chat_limit_per_sec: float = 1.0):
        self.global_limit = global_limit_per_sec
        self.chat_limit = chat_limit_per_sec
        self.last_global_send = 0.0
        self.last_chat_sends = defaultdict(float)

    def wait_if_needed(self, chat_id: str):
        now = time.time()

        # Global wait
        time_since_global = now - self.last_global_send
        global_wait = max(0.0, (1.0 / self.global_limit) - time_since_global)

        # Chat-specific wait
        time_since_chat = now - self.last_chat_sends[chat_id]
        chat_wait = max(0.0, (1.0 / self.chat_limit) - time_since_chat)

        wait_time = max(global_wait, chat_wait)
        if wait_time > 0:
            time.sleep(wait_time)

        now = time.time()
        self.last_global_send = now
        self.last_chat_sends[chat_id] = now
