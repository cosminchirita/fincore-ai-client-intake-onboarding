import logging
import os
import socket
import time

import httpx

from app.config import get_settings
from app.db import close_pool, open_pool
from app.repository import claim_outbox_events, complete_outbox_event, retry_outbox_event

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("fincore-outbox-worker")


def main() -> None:
    settings = get_settings()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    open_pool()
    try:
        with httpx.Client(timeout=15) as client:
            while True:
                events = claim_outbox_events(worker_id)
                if not events:
                    time.sleep(settings.outbox_poll_seconds)
                    continue
                for event in events:
                    try:
                        response = client.post(
                            settings.n8n_webhook_url,
                            json=event["payload"],
                            headers={
                                "X-Event-ID": str(event["id"]),
                                "X-Event-Type": event["event_type"],
                            },
                        )
                        response.raise_for_status()
                        complete_outbox_event(event["id"])
                    except Exception as exc:  # worker must retain and retry failed deliveries
                        logger.exception("Outbox delivery failed for %s", event["id"])
                        retry_outbox_event(event, str(exc))
    finally:
        close_pool()


if __name__ == "__main__":
    main()
