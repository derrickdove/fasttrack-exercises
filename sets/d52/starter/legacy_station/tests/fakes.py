"""In-memory transport used by the existing station tests."""


class FakeTransport:
    """Reply from a dictionary and keep the exact communication history."""

    def __init__(self, replies: dict[str, str]) -> None:
        self.replies = dict(replies)
        self.writes: list[tuple[str, float]] = []
        self.queries: list[tuple[str, float]] = []

    def write(self, command: str, timeout_s: float) -> None:
        self.writes.append((command, timeout_s))

    def query(self, command: str, timeout_s: float) -> str:
        self.queries.append((command, timeout_s))
        return self.replies[command]
