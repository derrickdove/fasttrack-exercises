"""Friendly checks for the first values and text helpers."""

import pytest

from starter.basics import (
    channel_label,
    clean_operator,
    error_answers,
    first_character,
    last_character,
    millivolts_to_volts,
    model_prefix,
    parse_channel,
    parse_voltage,
    reading_field,
    reading_value,
    serial_length,
    station_label,
    status_message,
)


def test_e1_returns_fixed_label() -> None:
    for _ in range(2):
        got = station_label()
        message = f"station_label(): expected 'STATION READY', got {got!r}. "
        assert got is not None, message + "your function returned None: did you forget `return`? print() only displays text."
        assert got == "STATION READY", message + "Return the label; do not print it."


@pytest.mark.parametrize(
    "millivolts, expected",
    [(5000.0, 5.0), (250.0, 0.25), (0.0, 0.0), (3300.0, 3.3)],
)
def test_e2_converts_millivolts(millivolts: float, expected: float) -> None:
    got = millivolts_to_volts(millivolts)
    message = f"millivolts_to_volts({millivolts!r}): expected float {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert isinstance(got, float), message + "Division with / produces a float."
    assert got == expected, message + "There are 1000 millivolts in one volt."


@pytest.mark.parametrize(
    "channel, volts, expected",
    [(3, 5.0, "CH3: 5.0 V"), (1, 4.98, "CH1: 4.98 V"),
     (12, 0.0, "CH12: 0.0 V"), (7, 2.5, "CH7: 2.5 V")],
)
def test_e3_builds_channel_label(channel: int, volts: float, expected: str) -> None:
    got = channel_label(channel, volts)
    message = f"channel_label({channel!r}, {volts!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`? print() only displays text."
    assert got == expected, message + "Return the f-string, with the shown spaces."


@pytest.mark.parametrize(
    "entry, expected",
    [("  sam  ", "SAM"), ("Lee", "LEE"), (" ann wu ", "ANN WU"),
     ("  Jo Taylor ", "JO TAYLOR")],
)
def test_e4_cleans_operator_entry(entry: str, expected: str) -> None:
    got = clean_operator(entry)
    message = f"clean_operator({entry!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert got == expected, message + "Use the result of strip(), then upper()."


@pytest.mark.parametrize("serial, expected", [("AB12", 4), ("K7", 2), ("M73Q9", 5)])
def test_e5_serial_length(serial: str, expected: int) -> None:
    got = serial_length(serial)
    message = f"serial_length({serial!r}): expected int {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert type(got) is int, message + "len() returns an integer count."
    assert got == expected, message + "Count the characters, not their index positions."


@pytest.mark.parametrize("serial, expected", [("AB12", "A"), ("K7", "K"), ("M73Q9", "M")])
def test_e6_first_character(serial: str, expected: str) -> None:
    got = first_character(serial)
    message = f"first_character({serial!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert got == expected, message + "The first position is index zero."


@pytest.mark.parametrize("serial, expected", [("AB12", "2"), ("K7", "7"), ("M73Q9", "9")])
def test_e6_last_character(serial: str, expected: str) -> None:
    got = last_character(serial)
    message = f"last_character({serial!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert got == expected, message + "Use the last position and keep it as text."


@pytest.mark.parametrize(
    "model, expected", [("DMM6500", "DMM"), ("PSU300", "PSU"), ("ABC", "ABC"), ("Scope7", "Sco")],
)
def test_e7_slices_model_prefix(model: str, expected: str) -> None:
    got = model_prefix(model)
    message = f"model_prefix({model!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert got == expected, message + "The slice stop is left out; keep the original case."


@pytest.mark.parametrize(
    "reply, expected",
    [("CH3,4.98,V", "4.98"), ("CH1,0.0,V", "0.0"),
     ("CH12,12.5,V", "12.5"), ("CH7,2.25,V", "2.25")],
)
def test_e8_picks_reading_text(reply: str, expected: str) -> None:
    got = reading_field(reply)
    message = f"reading_field({reply!r}): expected text {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert got == expected, message + "Pick the second field and leave it as text."


@pytest.mark.parametrize("text, expected", [("3", 3), ("12", 12), ("7", 7)])
def test_e9_converts_channel_text(text: str, expected: int) -> None:
    got = parse_channel(text)
    message = f"parse_channel({text!r}): expected int {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert type(got) is int, message + "Use int() for the whole channel number."
    assert got == expected, message + "Return the converted number."


@pytest.mark.parametrize("text, expected", [("4.98", 4.98), ("5", 5.0), ("0.0", 0.0), ("2.25", 2.25)])
def test_e9_converts_voltage_text(text: str, expected: float) -> None:
    got = parse_voltage(text)
    message = f"parse_voltage({text!r}): expected float {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert isinstance(got, float), message + "Use float(), even when the text has no decimal point."
    assert got == expected, message + "Return the converted number."


@pytest.mark.parametrize(
    "reply, expected",
    [("CH3=4.98\n", 4.98), ("CH1=0.0\n", 0.0), ("CH12=5\n", 5.0), ("CH7=2.25\n", 2.25)],
)
def test_e10_reads_full_reply(reply: str, expected: float) -> None:
    got = reading_value(reply)
    message = f"reading_value({reply!r}): expected float {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`?"
    assert isinstance(got, float), message + "Convert the selected reading text with float()."
    assert got == expected, message + "Select the reading after the equals sign."


@pytest.mark.parametrize(
    "channel, millivolts, expected",
    [(3, 4980.0, "CH3: 4.98 V"), (1, 5000.0, "CH1: 5.0 V"),
     (12, 0.0, "CH12: 0.0 V"), (7, 250.0, "CH7: 0.25 V")],
)
def test_e11_combines_conversion_and_label(channel: int, millivolts: float, expected: str) -> None:
    got = status_message(channel, millivolts)
    message = f"status_message({channel!r}, {millivolts!r}): expected {expected!r}, got {got!r}. "
    assert got is not None, message + "your function returned None: did you forget `return`? print() only displays text."
    assert got == expected, message + "Convert to volts before building the one-line message."


_ERROR_ANSWERS = {"Q1": "A", "Q2": "C", "Q3": "B"}


@pytest.mark.parametrize(
    "question, hint",
    [("Q1", "Reread E12's NameError definition and compare the two variable names."),
     ("Q2", "Reread E12's TypeError definition and the rule for +."),
     ("Q3", "Reread the indentation explanation in How this works.")],
    ids=["Q1", "Q2", "Q3"],
)
def test_e12_reads_error_messages(question: str, hint: str) -> None:
    answers = error_answers()
    message = f"error_answers(): expected a dictionary of Q1, Q2 and Q3 option letters, got {answers!r}. "
    assert answers is not None, message + "your function returned None: did you forget `return`?"
    assert isinstance(answers, dict), message + "Use the dictionary shape in the practice example."
    assert set(answers) == {"Q1", "Q2", "Q3"}, message + "Return exactly those three keys."
    correct = answers.get(question) == _ERROR_ANSWERS[question]
    assert correct, (
        f"error_answers()[{question!r}]: expected the correct uppercase option letter "
        f"for {question}, got {answers.get(question)!r}. {hint}"
    )
