import pytest

from starter.units.guard import require_bool, typing_answers


@pytest.mark.parametrize("value", [True, False])
def test_e5_accepts_exact_bools(value: bool) -> None:
    assert require_bool("enable", value) is value, "Return the original bool unchanged"


@pytest.mark.parametrize("name", ["enable", "output_enabled"])
@pytest.mark.parametrize("value", [0, 1, "1", None, 1.0, 2, [], {}])
def test_e5_rejects_other_types(name: str, value: object) -> None:
    with pytest.raises(TypeError) as caught:
        require_bool(name, value)
    message = str(caught.value)
    assert name in message, "Name the rejected argument in the TypeError message"
    assert type(value).__name__ in message, "Name the received type in the TypeError message"


def test_e5_q1_static_and_dynamic_typing() -> None:
    answers = typing_answers()
    assert isinstance(answers, dict) and set(answers) == {"Q1", "Q2", "Q3", "Q4"}, (
        "Return exactly Q1 through Q4; reread E5 Part B and the typing introduction"
    )
    if answers.get("Q1") != "B":
        pytest.fail("Q1: Reread typing introduction, type hints versus runtime behavior", pytrace=False)


def test_e5_q2_hints_at_a_driver_call() -> None:
    if typing_answers().get("Q2") != "C":
        pytest.fail("Q2: Reread typing introduction, runtime enforcement of annotations", pytrace=False)


def test_e5_q3_when_mypy_runs() -> None:
    if typing_answers().get("Q3") != "A":
        pytest.fail("Q3: Reread mypy Getting started, A quick intro to type hints", pytrace=False)


def test_e5_q4_output_state_api() -> None:
    if typing_answers().get("Q4") != "D":
        pytest.fail("Q4: Reread E5 Part A and mypy Getting started, A quick intro to type hints", pytrace=False)
