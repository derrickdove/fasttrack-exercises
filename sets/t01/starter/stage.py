"""Questions and simulations for a test station's XY positioning stage."""


def question_answers() -> dict[str, str]:
    """Return Q1 through Q4 option letters for the clarification quiz."""
    raise NotImplementedError("E1: Choose the useful clarifying questions")


def commands_ok(command: str) -> bool:
    """Return whether every character is L, R or F; accept empty text."""
    raise NotImplementedError("E2: Check every command character")


def run_once(command: str) -> tuple[int, int, int]:
    """Return x, y and heading index after one pass from the origin facing north."""
    raise NotImplementedError("E3: Track position and heading through one pass")


def is_valid(command: str) -> bool:
    """Return whether repetition stays bounded; reject other characters."""
    raise NotImplementedError("E4: Reject bad characters and simulate four passes")


def reasoning_answers() -> dict[str, str]:
    """Return Q1 through Q5 option letters for the explanation quiz."""
    raise NotImplementedError("E5: Explain the routes, work and missing return")
