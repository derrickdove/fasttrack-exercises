"""E10: Write three regressions using the supplied offline recording fake."""
from starter import check54 as station


class FakeStation:
    """Supplied fake: record reads and output calls without touching hardware."""

    def __init__(self, status: int, age_s: float) -> None:
        self.status = status
        self.age_s = age_s
        self.events: list[tuple[object, ...]] = []

    def read_interlock(self) -> tuple[int, float]:
        self.events.append(("read",))
        return self.status, self.age_s

    def enable_output(self, on: bool) -> None:
        self.events.append(("enable", on))


def test_e10_fresh() -> None:
    """E10: Check fresh input, returned reasons and exact event order."""
    raise NotImplementedError("E10: write the fresh regression")


def test_e10_stale() -> None:
    """E10: Check stale input, returned reasons and exact event order."""
    raise NotImplementedError("E10: write the stale regression")


def test_e10_faulted() -> None:
    """E10: Check faulted input, returned reasons and exact event order."""
    raise NotImplementedError("E10: write the faulted regression")
