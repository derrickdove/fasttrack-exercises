"""Provided instrument substitute; no hardware or network connection is used."""


class FakeInstrument:
    """Reply to queries from a script and record write commands in order."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = dict(replies)
        self.writes: list[str] = []

    def query(self, command: str) -> str:
        """Return the scripted reply; unknown commands raise KeyError."""
        return self.replies[command]

    def write(self, command: str) -> None:
        """Append a command to writes without changing the scripted replies."""
        self.writes.append(command)
