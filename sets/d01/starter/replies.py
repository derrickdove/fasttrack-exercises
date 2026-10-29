"""Translate instrument replies and prepare a voltage command."""

import math


def parse_idn(reply: str) -> dict[str, str]:
    """Return four stripped identification fields; reject a different field count."""
    raise NotImplementedError("E1: Split the identification reply into four named fields")


def parse_reading(text: str) -> float:
    """Convert a numeric reply with float(); map positive 9.9e37 to infinity."""
    raise NotImplementedError("E2: Convert a reading and recognize the overload value")


def format_setpoint(volts: float) -> str:
    """Format a finite voltage from 0 through 30 as VOLT with three decimals."""
    raise NotImplementedError("E3: Check the voltage limits and format three decimals")


def split_channels(text: str) -> list[int]:
    """Expand a nonempty (@...) list of positive channels and ascending ranges."""
    raise NotImplementedError("E4: Validate the channel list and expand its ranges")
