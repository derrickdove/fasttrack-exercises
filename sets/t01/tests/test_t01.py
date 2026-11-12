import pytest

from starter.stage import (
    commands_ok,
    is_valid,
    question_answers,
    reasoning_answers,
    run_once,
)


@pytest.mark.parametrize(
    "question, expected, revisit",
    [
        ("Q1", "B", "E1: ask what other characters mean"),
        ("Q2", "A", "E1: ask which parts of the final state matter"),
        ("Q3", "C", "E1: ask what empty input means"),
        ("Q4", "B", "E1: ask about the input size"),
    ],
    ids=["Q1", "Q2", "Q3", "Q4"],
)
def test_e1_clarifying_questions(question: str, expected: str, revisit: str) -> None:
    got = question_answers()
    call = "question_answers()"
    assert got is not None, (
        f"{call}: expected a quiz dictionary, got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert isinstance(got, dict), f"{call}: expected a quiz dictionary, got {got!r}"
    keys = {"Q1", "Q2", "Q3", "Q4"}
    assert set(got) == keys, f"{call}: expected exactly keys Q1 through Q4, got {got!r}"
    # Report the chosen letter and a hint without giving away the correct letter.
    correct = got.get(question) == expected
    assert correct, (
        f"{call}, {question}: expected the correct uppercase option letter, "
        f"got {got.get(question)!r}; reread {revisit}."
    )


@pytest.mark.parametrize(
    "command, expected",
    [
        ("", True),
        ("L", True),
        ("R", True),
        ("F", True),
        ("LRF", True),
        ("FFRLLF", True),
        ("X", False),
        ("FLX", False),
        ("XLF", False),
        ("LXR", False),
        ("f", False),
        ("LR1", False),
    ],
)
def test_e2_command_alphabet(command: str, expected: bool) -> None:
    got = commands_ok(command)
    call = f"commands_ok({command!r})"
    assert got is not None, (
        f"{call}: expected {expected!r}, got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert got is expected, f"{call}: expected {expected!r}, got {got!r}"


@pytest.mark.parametrize(
    "command, expected",
    [
        ("", (0, 0, 0)),
        ("F", (0, 1, 0)),
        ("FF", (0, 2, 0)),
        ("L", (0, 0, 3)),
        ("R", (0, 0, 1)),
        ("LL", (0, 0, 2)),
        ("LLL", (0, 0, 1)),
        ("RRR", (0, 0, 3)),
        ("LLLL", (0, 0, 0)),
        ("RRRR", (0, 0, 0)),
        ("LRF", (0, 1, 0)),
        ("RFF", (2, 0, 1)),
        ("LF", (-1, 0, 3)),
        ("LLF", (0, -1, 2)),
        ("FRFLF", (1, 2, 0)),
        ("FLLF", (0, 0, 2)),
        ("FRFRFRFR", (0, 0, 0)),
    ],
)
def test_e3_one_pass(command: str, expected: tuple[int, int, int]) -> None:
    got = run_once(command)
    call = f"run_once({command!r})"
    assert got is not None, (
        f"{call}: expected {expected!r}, got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert got == expected, f"{call}: expected {expected!r}, got {got!r}"


def test_e3_each_call_starts_at_origin_facing_north() -> None:
    first = run_once("RF")
    assert first is not None, (
        "run_once('RF'): expected (1, 0, 1), got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert first == (1, 0, 1), f"run_once('RF'): expected (1, 0, 1), got {first!r}"
    second = run_once("F")
    assert second is not None, (
        "run_once('F'): expected (0, 1, 0), got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert second == (0, 1, 0), (
        f"run_once('F') after a previous call: expected a fresh (0, 1, 0), got {second!r}"
    )


@pytest.mark.parametrize(
    "command, expected",
    [
        ("", True),
        ("F", False),
        ("LRF", False),
        ("L", True),
        ("FLLF", True),
        ("LF", True),
        ("R", True),
        ("RF", True),
        ("FFLL", True),
        ("FF", False),
        ("FRFRFRFR", True),
        ("RFFL", False),
        ("LLLLF", False),
        ("FLLFLLF", False),
    ],
)
def test_e4_repeated_route(command: str, expected: bool) -> None:
    got = is_valid(command)
    call = f"is_valid({command!r})"
    assert got is not None, (
        f"{call}: expected {expected!r}, got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert got is expected, f"{call}: expected {expected!r}, got {got!r}"


@pytest.mark.parametrize("command", ["X", "FX", "XLF", "LXR", "f", "FLLFX"])
def test_e4_rejects_other_characters(command: str) -> None:
    try:
        got = is_valid(command)
    except ValueError:
        return
    assert got is not None, (
        f"is_valid({command!r}): expected ValueError, got None; "
        "your function returned None: did you forget `return`? Reject bad input with raise."
    )
    assert False, f"is_valid({command!r}): expected ValueError, got {got!r} instead"


@pytest.mark.parametrize(
    "question, expected, revisit",
    [
        ("Q1", "C", "E4: zero turn and a nonzero displacement"),
        ("Q2", "B", "E3: position is separate from heading"),
        ("Q3", "A", "E4: four rotated displacements cancel"),
        ("Q4", "C", "E5: a fixed number of scans is linear work"),
        ("Q5", "B", "How this works: return versus print"),
    ],
    ids=["Q1", "Q2", "Q3", "Q4", "Q5"],
)
def test_e5_explain_the_result(question: str, expected: str, revisit: str) -> None:
    got = reasoning_answers()
    call = "reasoning_answers()"
    assert got is not None, (
        f"{call}: expected a quiz dictionary, got None; "
        "your function returned None: did you forget `return`? Printing is not returning."
    )
    assert isinstance(got, dict), f"{call}: expected a quiz dictionary, got {got!r}"
    keys = {"Q1", "Q2", "Q3", "Q4", "Q5"}
    assert set(got) == keys, f"{call}: expected exactly keys Q1 through Q5, got {got!r}"
    correct = got.get(question) == expected
    assert correct, (
        f"{call}, {question}: expected the correct uppercase option letter, "
        f"got {got.get(question)!r}; reread {revisit}."
    )
