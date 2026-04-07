"""Core CloudFormation stack event watcher module."""

import time
from datetime import datetime, timezone
from typing import Optional, Callable

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# Terminal color codes for event status highlighting
STATUS_COLORS = {
    "CREATE_COMPLETE": "\033[92m",       # Green
    "UPDATE_COMPLETE": "\033[92m",       # Green
    "DELETE_COMPLETE": "\033[92m",       # Green
    "CREATE_IN_PROGRESS": "\033[94m",   # Blue
    "UPDATE_IN_PROGRESS": "\033[94m",   # Blue
    "DELETE_IN_PROGRESS": "\033[94m",   # Blue
    "CREATE_FAILED": "\033[91m",        # Red
    "UPDATE_FAILED": "\033[91m",        # Red
    "DELETE_FAILED": "\033[91m",        # Red
    "ROLLBACK_IN_PROGRESS": "\033[93m", # Yellow
    "ROLLBACK_COMPLETE": "\033[93m",    # Yellow
    "ROLLBACK_FAILED": "\033[91m",      # Red
}
RESET_COLOR = "\033[0m"

# Terminal states that indicate the stack operation has finished
TERMINAL_STATES = {
    "CREATE_COMPLETE",
    "CREATE_FAILED",
    "DELETE_COMPLETE",
    "DELETE_FAILED",
    "ROLLBACK_COMPLETE",
    "ROLLBACK_FAILED",
    "UPDATE_COMPLETE",
    "UPDATE_FAILED",
    "UPDATE_ROLLBACK_COMPLETE",
    "UPDATE_ROLLBACK_FAILED",
}


class StackWatcher:
    """Watches CloudFormation stack events and streams them to a callback."""

    def __init__(
        self,
        stack_name: str,
        region: Optional[str] = None,
        profile: Optional[str] = None,
        poll_interval: float = 5.0,
        filter_status: Optional[list[str]] = None,
        no_color: bool = False,
    ):
        self.stack_name = stack_name
        self.poll_interval = poll_interval
        self.filter_status = [s.upper() for s in filter_status] if filter_status else []
        self.no_color = no_color

        session_kwargs = {}
        if profile:
            session_kwargs["profile_name"] = profile
        if region:
            session_kwargs["region_name"] = region

        session = boto3.Session(**session_kwargs)
        self.cf_client = session.client("cloudformation")
        self._seen_event_ids: set[str] = set()

    def _colorize(self, status: str, text: str) -> str:
        """Apply terminal color to text based on resource status."""
        if self.no_color:
            return text
        color = STATUS_COLORS.get(status, "")
        return f"{color}{text}{RESET_COLOR}" if color else text

    def _fetch_events(self) -> list[dict]:
        """Fetch all events for the stack, handling pagination."""
        events = []
        paginator = self.cf_client.get_paginator("describe_stack_events")
        for page in paginator.paginate(StackName=self.stack_name):
            events.extend(page.get("StackEvents", []))
        return events

    def _get_stack_status(self) -> str:
        """Return the current status of the CloudFormation stack."""
        response = self.cf_client.describe_stacks(StackName=self.stack_name)
        stacks = response.get("Stacks", [])
        if not stacks:
            raise ValueError(f"Stack '{self.stack_name}' not found.")
        return stacks[0]["StackStatus"]

    def format_event(self, event: dict) -> str:
        """Format a single stack event into a human-readable string."""
        timestamp = event["Timestamp"].astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        status = event.get("ResourceStatus", "UNKNOWN")
        resource_type = event.get("ResourceType", "")
        logical_id = event.get("LogicalResourceId", "")
        reason = event.get("ResourceStatusReason", "")

        status_str = self._colorize(status, f"{status:<30}")
        line = f"{timestamp}  {status_str}  {resource_type:<45}  {logical_id}"
        if reason:
            line += f"\n    → {reason}"
        return line

    def watch(
        self,
        on_event: Callable[[dict, str], None],
        stop_on_terminal: bool = True,
    ) -> None:
        """
        Poll for new stack events and invoke `on_event` for each new one.

        Args:
            on_event: Callback receiving (event_dict, formatted_string).
            stop_on_terminal: Stop polling when the stack reaches a terminal state.
        """
        try:
            # Seed seen events so we only report new ones going forward
            existing = self._fetch_events()
            self._seen_event_ids = {e["EventId"] for e in existing}
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ValidationError":
                raise ValueError(f"Stack '{self.stack_name}' does not exist.") from exc
            raise
        except NoCredentialsError as exc:
            raise RuntimeError(
                "AWS credentials not found. Configure via environment variables, "
                "~/.aws/credentials, or an IAM role."
            ) from exc

        while True:
            time.sleep(self.poll_interval)

            new_events = [
                e for e in reversed(self._fetch_events())
                if e["EventId"] not in self._seen_event_ids
            ]

            for event in new_events:
                self._seen_event_ids.add(event["EventId"])
                status = event.get("ResourceStatus", "")

                if self.filter_status and status not in self.filter_status:
                    continue

                formatted = self.format_event(event)
                on_event(event, formatted)

            if stop_on_terminal:
                try:
                    stack_status = self._get_stack_status()
                except ClientError:
                    break  # Stack may have been deleted
                if stack_status in TERMINAL_STATES:
                    break
