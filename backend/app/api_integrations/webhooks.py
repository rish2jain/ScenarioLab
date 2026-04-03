"""Webhook management for third-party integrations."""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.api_integrations.database import (
    ensure_tables,
    webhook_repo,
)

logger = logging.getLogger(__name__)

# Event types that can trigger webhooks
WEBHOOK_EVENT_TYPES = [
    "simulation_started",
    "simulation_completed",
    "simulation_failed",
    "report_generated",
]


class Webhook(BaseModel):
    """A registered webhook."""

    webhook_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    events: list[str]  # Events to listen for
    api_key_id: str  # Associated API key
    active: bool = True
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    last_triggered_at: str | None = None
    failure_count: int = 0
    metadata: dict[str, Any] = {}


class WebhookPayload(BaseModel):
    """Payload sent to webhook endpoints."""

    event_type: str
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    webhook_id: str
    data: dict[str, Any]
    signature: str | None = None


class WebhookDelivery(BaseModel):
    """Record of a webhook delivery attempt."""

    delivery_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    webhook_id: str
    event_type: str
    url: str
    status_code: int | None
    success: bool
    error_message: str | None = None
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    response_time_ms: float | None = None


class WebhookManager:
    """Manages webhook registrations and deliveries.

    Uses SQLite persistence with in-memory cache for performance.
    """

    def __init__(self):
        self._webhooks: dict[str, Webhook] = {}
        self._deliveries: list[WebhookDelivery] = []
        self._http_client: httpx.AsyncClient | None = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_loaded(self) -> None:
        """Ensure webhooks are loaded from database."""
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            try:
                await ensure_tables()
                webhooks = await webhook_repo.list_all()
                for wh_data in webhooks:
                    webhook = Webhook(**wh_data)
                    self._webhooks[webhook.webhook_id] = webhook
                # Load recent deliveries
                deliveries = await webhook_repo.list_deliveries(limit=100)
                for del_data in deliveries:
                    delivery = WebhookDelivery(**del_data)
                    self._deliveries.append(delivery)
                self._initialized = True
                logger.info(
                    f"Loaded {len(self._webhooks)} webhooks from database"
                )
            except Exception as e:
                logger.warning(f"Failed to load webhooks from DB: {e}")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def register_webhook(
        self,
        url: str,
        events: list[str],
        api_key_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> Webhook:
        """Register a new webhook.

        Args:
            url: The URL to POST to
            events: List of event types to subscribe to
            api_key_id: The API key ID that owns this webhook
            metadata: Optional additional metadata

        Returns:
            The registered Webhook

        Raises:
            ValueError: If URL or events are invalid
        """
        # Validate events
        invalid_events = [
            e for e in events if e not in WEBHOOK_EVENT_TYPES
        ]
        if invalid_events:
            raise ValueError(
                f"Invalid event types: {invalid_events}. "
                f"Valid types: {WEBHOOK_EVENT_TYPES}"
            )

        if not url.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")

        webhook = Webhook(
            url=url,
            events=events,
            api_key_id=api_key_id,
            metadata=metadata or {},
        )

        self._webhooks[webhook.webhook_id] = webhook

        # Persist to database (async fire-and-forget)
        asyncio.create_task(self._save_webhook(webhook))

        logger.info(
            f"Registered webhook {webhook.webhook_id} "
            f"for events: {events}"
        )
        return webhook

    async def _save_webhook(self, webhook: Webhook) -> None:
        """Save webhook to database."""
        try:
            await webhook_repo.save(webhook.model_dump())
        except Exception as e:
            logger.warning(f"Failed to persist webhook to DB: {e}")

    async def list_webhooks(
        self, api_key_id: str | None = None
    ) -> list[Webhook]:
        """List webhooks, optionally filtered by API key.

        Args:
            api_key_id: Optional API key ID to filter by

        Returns:
            List of Webhook objects
        """
        await self._ensure_loaded()
        if api_key_id:
            return [
                w for w in self._webhooks.values()
                if w.api_key_id == api_key_id
            ]
        return list(self._webhooks.values())

    async def get_webhook(self, webhook_id: str) -> Webhook | None:
        """Get a specific webhook by ID.

        Args:
            webhook_id: The webhook ID

        Returns:
            Webhook or None
        """
        await self._ensure_loaded()
        return self._webhooks.get(webhook_id)

    def delete_webhook(self, webhook_id: str) -> bool:
        """Delete a webhook.

        Args:
            webhook_id: The webhook ID to delete

        Returns:
            True if deleted, False if not found
        """
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            # Delete from database (async fire-and-forget)
            asyncio.create_task(webhook_repo.delete(webhook_id))
            logger.info(f"Deleted webhook {webhook_id}")
            return True
        return False

    async def fire_webhook(
        self,
        event_type: str,
        payload: dict[str, Any],
    ) -> list[WebhookDelivery]:
        """Fire a webhook event to all subscribed endpoints.

        Args:
            event_type: The type of event
            payload: The event data

        Returns:
            List of WebhookDelivery records
        """
        await self._ensure_loaded()
        deliveries = []

        # Find webhooks subscribed to this event
        matching_webhooks = [
            w for w in self._webhooks.values()
            if w.active and event_type in w.events
        ]

        if not matching_webhooks:
            logger.debug(f"No webhooks subscribed to {event_type}")
            return deliveries

        # Fire all webhooks concurrently
        tasks = [
            self._deliver_webhook(webhook, event_type, payload)
            for webhook in matching_webhooks
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for webhook, result in zip(matching_webhooks, results):
            if isinstance(result, WebhookDelivery):
                deliveries.append(result)
                self._deliveries.append(result)
                # Save delivery to database
                asyncio.create_task(
                    self._save_delivery_and_update_stats(
                        webhook, result
                    )
                )
            else:
                # Log exception
                logger.error(
                    f"Webhook delivery error for "
                    f"{webhook.webhook_id}: {result}"
                )
                # Create failed delivery record
                delivery = WebhookDelivery(
                    webhook_id=webhook.webhook_id,
                    event_type=event_type,
                    url=webhook.url,
                    status_code=None,
                    success=False,
                    error_message=str(result),
                )
                deliveries.append(delivery)
                self._deliveries.append(delivery)
                # Save delivery to database
                asyncio.create_task(
                    self._save_delivery_and_update_stats(
                        webhook, delivery
                    )
                )

        return deliveries

    async def _save_delivery_and_update_stats(
        self, webhook: Webhook, delivery: WebhookDelivery
    ) -> None:
        """Save delivery to database and update webhook stats."""
        try:
            await webhook_repo.save_delivery(delivery.model_dump())
            await webhook_repo.update_webhook_stats(
                webhook.webhook_id,
                last_triggered_at=delivery.timestamp,
                increment_failure=not delivery.success,
            )
        except Exception as e:
            logger.warning(f"Failed to save delivery to DB: {e}")

    async def _deliver_webhook(
        self,
        webhook: Webhook,
        event_type: str,
        data: dict[str, Any],
    ) -> WebhookDelivery:
        """Deliver a webhook to a single endpoint.

        Args:
            webhook: The webhook to deliver to
            event_type: The event type
            data: The event data

        Returns:
            WebhookDelivery record
        """
        import time

        payload = WebhookPayload(
            event_type=event_type,
            webhook_id=webhook.webhook_id,
            data=data,
        )

        start_time = time.time()
        status_code = None
        error_message = None
        success = False

        try:
            client = await self._get_client()

            response = await client.post(
                webhook.url,
                content=payload.model_dump_json(),
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Event": event_type,
                    "X-Webhook-ID": webhook.webhook_id,
                },
            )

            status_code = response.status_code
            success = 200 <= status_code < 300

            if not success:
                error_message = f"HTTP {status_code}: {response.text[:200]}"

        except httpx.TimeoutException:
            error_message = "Request timed out"
        except httpx.RequestError as e:
            error_message = f"Request error: {str(e)}"
        except Exception as e:
            error_message = f"Unexpected error: {str(e)}"

        response_time = (time.time() - start_time) * 1000

        # Update webhook stats
        webhook.last_triggered_at = datetime.utcnow().isoformat()
        if not success:
            webhook.failure_count += 1

        delivery = WebhookDelivery(
            webhook_id=webhook.webhook_id,
            event_type=event_type,
            url=webhook.url,
            status_code=status_code,
            success=success,
            error_message=error_message,
            response_time_ms=response_time,
        )

        if success:
            logger.info(
                f"Webhook {webhook.webhook_id} delivered "
                f"{event_type} to {webhook.url} "
                f"({status_code}, {response_time:.0f}ms)"
            )
        else:
            logger.warning(
                f"Webhook {webhook.webhook_id} failed "
                f"{event_type} to {webhook.url}: {error_message}"
            )

        return delivery

    def get_delivery_history(
        self,
        webhook_id: str | None = None,
        limit: int = 100,
    ) -> list[WebhookDelivery]:
        """Get delivery history.

        Args:
            webhook_id: Optional webhook ID to filter by
            limit: Maximum number of records to return

        Returns:
            List of WebhookDelivery records
        """
        deliveries = self._deliveries
        if webhook_id:
            deliveries = [d for d in deliveries if d.webhook_id == webhook_id]

        return deliveries[-limit:]


# Global webhook manager instance
webhook_manager = WebhookManager()
