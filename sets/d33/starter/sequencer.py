"""State transitions and cleanup for a chassis test station."""

from collections.abc import Callable

Setup = Callable[[], None]
Run = Callable[[], bool]
Teardown = Callable[[], None]
Step = tuple[Setup, Run, Teardown]

# E1: fill in all seven states and their allowed destinations.
TRANSITIONS: dict[str, set[str]] = {}


def can_move(a: str, b: str) -> bool:
    """Return whether the station may move from a to b; unknown states are illegal."""
    raise NotImplementedError("E1: look up allowed destinations in TRANSITIONS")


class Sequencer:
    """Track a single station sequence and its visited states."""

    state: str
    history: list[str]

    def __init__(self) -> None:
        """Start in IDLE with a separate history list for this instance."""
        raise NotImplementedError("E2: initialize state and history")

    def move(self, to: str) -> None:
        """Record a legal move, or raise ValueError without changing anything."""
        raise NotImplementedError("E2: validate the move before updating state and history")


def run_steps(steps: list[Step]) -> tuple[str, list[str]]:
    """Run all setups, then measurements, then reverse cleanup; return state/history."""
    raise NotImplementedError("E3/E4: run callbacks and always finish registered cleanup")
