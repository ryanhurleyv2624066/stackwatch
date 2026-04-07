"""CLI entry point for stackwatch.

Provides the main command-line interface for monitoring AWS CloudFormation
stack events in real-time.
"""

import sys
import click
from typing import Optional

from stackwatch import __version__


@click.group()
@click.version_option(version=__version__, prog_name="stackwatch")
def cli() -> None:
    """stackwatch — Monitor AWS CloudFormation stack events in real-time.

    Watch stack deployments, filter events by status or resource type,
    and get alerted when stacks reach terminal states.
    """
    pass


@cli.command()
@click.argument("stack_name")
@click.option(
    "--region",
    "-r",
    default=None,
    envvar="AWS_DEFAULT_REGION",
    help="AWS region (defaults to AWS_DEFAULT_REGION or profile default).",
)
@click.option(
    "--profile",
    "-p",
    default=None,
    envvar="AWS_PROFILE",
    help="AWS CLI profile to use.",
)
@click.option(
    "--filter",
    "-f",
    "status_filter",
    multiple=True,
    metavar="STATUS",
    help="Only show events matching this status (repeatable). "
         "E.g. --filter FAILED --filter ROLLBACK_IN_PROGRESS",
)
@click.option(
    "--poll-interval",
    default=5,
    show_default=True,
    type=click.IntRange(1, 60),
    help="Seconds between polling for new events.",
)
@click.option(
    "--tail",
    "-t",
    is_flag=True,
    default=False,
    help="Continue watching even after the stack reaches a terminal state.",
)
@click.option(
    "--no-color",
    is_flag=True,
    default=False,
    envvar="NO_COLOR",
    help="Disable colored output.",
)
@click.option(
    "--alert-sns",
    default=None,
    metavar="TOPIC_ARN",
    help="Send an SNS alert when the stack reaches a terminal state.",
)
def watch(
    stack_name: str,
    region: Optional[str],
    profile: Optional[str],
    status_filter: tuple,
    poll_interval: int,
    tail: bool,
    no_color: bool,
    alert_sns: Optional[str],
) -> None:
    """Watch real-time events for STACK_NAME.

    Polls CloudFormation for new stack events and prints them as they arrive.
    Exits automatically when the stack reaches a terminal state unless --tail
    is specified.

    \b
    Examples:
      stackwatch watch my-app-stack
      stackwatch watch my-app-stack --region us-west-2 --filter FAILED
      stackwatch watch my-app-stack --poll-interval 10 --tail
    """
    # Lazy import to keep startup fast
    from stackwatch.watcher import StackWatcher

    watcher = StackWatcher(
        stack_name=stack_name,
        region=region,
        profile=profile,
        status_filter=list(status_filter),
        poll_interval=poll_interval,
        tail=tail,
        use_color=not no_color,
        alert_sns_arn=alert_sns,
    )

    try:
        exit_code = watcher.run()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        click.echo("\nInterrupted.", err=True)
        sys.exit(130)


def main() -> None:
    """Package entry point."""
    cli()


if __name__ == "__main__":
    main()
