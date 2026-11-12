"""Small objects for a hardware test station."""

from dataclasses import dataclass


class Reading:
    """Keep a measurement's name and value together."""

    def __init__(self, name: str, value: float) -> None:
        """E1: Store the supplied name and value on this reading."""
        raise NotImplementedError("E1: Store name and value on self")

    def within(self, low: float, high: float) -> bool:
        """E2: Return whether this value is inside the inclusive limits."""
        raise NotImplementedError("E2: Compare self.value with both limits")


class EventCount:
    """Remember how many station events have happened."""

    def __init__(self) -> None:
        """E3: Start this counter at zero."""
        raise NotImplementedError("E3: Give this object a count starting at zero")

    def record(self) -> None:
        """E3: Increase this object's count by one."""
        raise NotImplementedError("E3: Add one to self.count")

    def record_pair(self) -> None:
        """E6: Record two events by calling record twice."""
        raise NotImplementedError("E6: Call self.record twice")


class EventLog:
    """Keep a separate message list for each station run."""

    def __init__(self) -> None:
        """E4: Create this object's empty messages list."""
        raise NotImplementedError("E4: Create an empty list inside __init__")

    def add(self, text: str) -> None:
        """E4: Append one message to this object's list."""
        raise NotImplementedError("E4: Append text to self.messages")


class Channel:
    """Keep a positive channel number."""

    def __init__(self, number: int) -> None:
        """E5: Reject numbers below one, then store the number."""
        raise NotImplementedError("E5: Reject a channel below one with ValueError")


class StationError(Exception):
    """Keep a station failure's message and channel together."""

    def __init__(self, message: str, channel: int) -> None:
        """E7: Store the channel and initialize the parent with the message."""
        raise NotImplementedError("E7: Store self.channel and call super().__init__(message)")


class FakeLink:
    """Record commands instead of sending them to hardware; already complete."""

    def __init__(self) -> None:
        """Create an empty command history for this link."""
        self.sent: list[str] = []

    def send(self, command: str) -> None:
        """Remember one command exactly as supplied."""
        self.sent.append(command)


class PowerSwitch:
    """Switch a power supply through the link handed to it."""

    def __init__(self, link: FakeLink) -> None:
        """E8: Store the supplied link without sending anything."""
        raise NotImplementedError("E8: Store the supplied link on self")

    def turn_on(self) -> None:
        """E8: Send the command that enables the supply output."""
        raise NotImplementedError("E8: Send OUTP 1 through self.link")

    def turn_off(self) -> None:
        """E8: Send the command that disables the supply output."""
        raise NotImplementedError("E8: Send OUTP 0 through self.link")


class DataReading:
    """E9: Replace the placeholder initializer with a dataclass and fields."""

    def __init__(self, name: str, value: float) -> None:
        """E9: Delete this whole method when adding the dataclass fields."""
        raise NotImplementedError("E9: Make DataReading a dataclass with name and value")


def count_passing(readings: list[Reading], low: float, high: float) -> int:
    """E10: Count readings whose within method returns True."""
    raise NotImplementedError("E10: Count the reading objects that pass their limits")


def object_answers() -> dict[str, str]:
    """E11: Map Q1, Q2 and Q3 to uppercase option letters from the README."""
    raise NotImplementedError("E11: Choose one answer for each object question")
