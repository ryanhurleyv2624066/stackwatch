"""Alert handling for CloudFormation stack events.

Supports multiple notification channels including desktop notifications
and webhook-based alerts (e.g., Slack).
"""

import json
import logging
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# CloudFormation statuses considered failure states
FAILURE_STATUSES = {
    "CREATE_FAILED",
    "DELETE_FAILED",
    "ROLLBACK_FAILED",
    "ROLLBACK_COMPLETE",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_FAILED",
    "UPDATE_ROLLBACK_COMPLETE",
}

# Statuses considered successful terminal states
SUCCESS_STATUSES = {
    "CREATE_COMPLETE",
    "DELETE_COMPLETE",
    "UPDATE_COMPLETE",
    "IMPORT_COMPLETE",
}


@dataclass
class AlertEvent:
    """Represents a stack event that triggered an alert."""

    stack_name: str
    status: str
    resource_type: str
    logical_resource_id: str
    status_reason: Optional[str] = None

    @property
    def is_failure(self) -> bool:
        """Return True if this event represents a failure state."""
        return self.status in FAILURE_STATUSES

    @property
    def is_success(self) -> bool:
        """Return True if this event represents a successful terminal state."""
        return self.status in SUCCESS_STATUSES

    def to_message(self) -> str:
        """Format the event as a human-readable alert message."""
        emoji = "\u274c" if self.is_failure else "\u2705" if self.is_success else "\u2139\ufe0f"
        msg = (
            f"{emoji} *StackWatch Alert* — `{self.stack_name}`\n"
            f"Resource: `{self.logical_resource_id}` ({self.resource_type})\n"
            f"Status: `{self.status}`"
        )
        if self.status_reason:
            msg += f"\nReason: {self.status_reason}"
        return msg


class AlertManager:
    """Manages alert dispatch for stack events."""

    def __init__(
        self,
        slack_webhook_url: Optional[str] = None,
        notify_on_failure: bool = True,
        notify_on_success: bool = False,
        desktop_notify: bool = False,
    ):
        self.slack_webhook_url = slack_webhook_url
        self.notify_on_failure = notify_on_failure
        self.notify_on_success = notify_on_success
        self.desktop_notify = desktop_notify

    def should_alert(self, event: AlertEvent) -> bool:
        """Determine whether an alert should be dispatched for this event."""
        if self.notify_on_failure and event.is_failure:
            return True
        if self.notify_on_success and event.is_success:
            return True
        return False

    def dispatch(self, event: AlertEvent) -> None:
        """Dispatch alerts for a given event through all configured channels."""
        if not self.should_alert(event):
            return

        message = event.to_message()
        logger.debug("Dispatching alert for %s/%s", event.stack_name, event.status)

        if self.slack_webhook_url:
            self._send_slack(message)

        if self.desktop_notify:
            self._send_desktop(event)

    def _send_slack(self, message: str) -> None:
        """Post a message to a Slack incoming webhook."""
        payload = json.dumps({"text": message}).encode("utf-8")
        req = urllib.request.Request(
            self.slack_webhook_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    logger.warning("Slack webhook returned status %d", resp.status)
        except urllib.error.URLError as exc:
            logger.error("Failed to send Slack alert: %s", exc)

    def _send_desktop(self, event: AlertEvent) -> None:
        """Send a desktop notification using the 'notify-send' command (Linux/macOS)."""
        try:
            import subprocess  # noqa: PLC0415

            title = f"StackWatch: {event.stack_name}"
            body = f"{event.logical_resource_id} → {event.status}"
            if event.status_reason:
                body += f"\n{event.status_reason}"
            subprocess.run(
                ["notify-send", "--urgency", "critical" if event.is_failure else "normal", title, body],
                check=False,
                timeout=5,
            )
        except FileNotFoundError:
            logger.debug("notify-send not available; skipping desktop notification")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Desktop notification failed: %s", exc)
