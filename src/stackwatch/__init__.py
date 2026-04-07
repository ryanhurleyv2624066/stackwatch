"""stackwatch — Real-time AWS CloudFormation stack event monitor."""

__version__ = "0.1.0"
__author__ = "stackwatch contributors"
__description__ = "Monitor AWS CloudFormation stack events in real-time with filtered output and alerting."


def get_version() -> str:
    """Return the current version of stackwatch.

    Returns:
        str: The version string in PEP 440 format (e.g. ``"0.1.0"``).

    Example::

        >>> import stackwatch
        >>> stackwatch.get_version()
        '0.1.0'
    """
    return __version__
