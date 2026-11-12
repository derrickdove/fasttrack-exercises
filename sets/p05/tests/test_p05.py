"""Gentle checks for the eleven classes-from-zero exercises."""

from dataclasses import is_dataclass

import pytest

from starter.objects import (
    Channel,
    DataReading,
    EventCount,
    EventLog,
    FakeLink,
    PowerSwitch,
    Reading,
    StationError,
    count_passing,
    object_answers,
)


def _require_attributes(instance: object, call: str, *attributes: str) -> None:
    for attribute in attributes:
        assert hasattr(instance, attribute), (
            f"{call}: expected attribute {attribute!r}, but it is missing. "
            f"Store it in __init__ with self.{attribute} = ..."
        )


def _result_message(call: str, expected: object, got: object) -> str:
    message = f"{call}: expected {expected!r}, got {got!r}."
    if got is None:
        message += " your function returned None: did you forget `return`?"
    return message + " Return the result; printing it does not return it."


@pytest.mark.parametrize("name, value", [("supply", 5.0), ("load", 0.2), ("offset", -1.0)])
def test_e1_stores_name_and_value(name: str, value: float) -> None:
    reading = Reading(name, value)
    _require_attributes(reading, f"Reading({name!r}, {value!r})", "name", "value")
    assert reading.name == name, (
        f"Reading({name!r}, {value!r}).name: expected {name!r}, got {reading.name!r}"
    )
    assert reading.value == value, (
        f"Reading({name!r}, {value!r}).value: expected {value!r}, got {reading.value!r}"
    )


@pytest.mark.parametrize(
    "value, low, high, expected",
    [(5.0, 4.5, 5.5, True), (4.5, 4.5, 5.5, True), (5.5, 4.5, 5.5, True),
     (4.0, 4.5, 5.5, False), (6.0, 4.5, 5.5, False), (0.0, 0.0, 0.0, True)],
)
def test_e2_checks_inclusive_limits(value: float, low: float, high: float, expected: bool) -> None:
    reading = Reading("supply", value)
    _require_attributes(reading, f"Reading('supply', {value!r})", "name", "value")
    got = reading.within(low, high)
    call = f"Reading('supply', {value!r}).within({low!r}, {high!r})"
    assert got is expected, _result_message(call, expected, got)
    _require_attributes(reading, call, "name", "value")
    assert (reading.name, reading.value) == ("supply", value), (
        f"{call}: expected unchanged name/value {('supply', value)!r}, "
        f"got {(reading.name, reading.value)!r}"
    )


def test_e3_starts_at_zero_and_remembers_calls() -> None:
    events = EventCount()
    _require_attributes(events, "EventCount()", "count")
    assert events.count == 0, f"EventCount().count: expected 0, got {events.count!r}"
    for expected in (1, 2, 3):
        got = events.record()
        assert got is None, f"record() call {expected}: expected None, got {got!r}"
        _require_attributes(events, f"record() call {expected}", "count")
        assert events.count == expected, (
            f"record() after {expected} calls: expected count {expected}, got {events.count!r}"
        )


def test_e3_counters_start_independently() -> None:
    first = EventCount()
    _require_attributes(first, "EventCount()", "count")
    first.record()
    second = EventCount()
    _require_attributes(second, "second EventCount()", "count")
    assert second.count == 0, (
        f"EventCount() after another counter recorded: expected count 0, got {second.count!r}"
    )


def test_e4_logs_have_separate_lists_and_keep_order() -> None:
    first = EventLog()
    second = EventLog()
    _require_attributes(first, "first EventLog()", "messages")
    _require_attributes(second, "second EventLog()", "messages")
    assert first.messages == [], f"EventLog().messages: expected [], got {first.messages!r}"
    assert second.messages == [], f"second EventLog().messages: expected [], got {second.messages!r}"
    assert first.messages is not second.messages, (
        f"two EventLog() calls: expected separate lists, got the same list {first.messages!r}"
    )
    for text in ("started", "ready", "ready"):
        _require_attributes(first, "first.add(text)", "messages")
        got = first.add(text)
        assert got is None, f"first.add({text!r}): expected None, got {got!r}"
    _require_attributes(first, "first.add calls", "messages")
    assert first.messages == ["started", "ready", "ready"], (
        f"first.add('started'), add('ready'), add('ready'): expected messages "
        f"['started', 'ready', 'ready'], got {first.messages!r}"
    )
    got = second.add("finished")
    assert got is None, f"second.add('finished'): expected None, got {got!r}"
    _require_attributes(second, "second.add('finished')", "messages")
    assert second.messages == ["finished"], (
        f"second.add('finished'): expected only ['finished'], got {second.messages!r}"
    )
    _require_attributes(first, "second.add('finished')", "messages")
    assert first.messages == ["started", "ready", "ready"], (
        f"second.add('finished'): expected first log unchanged as ['started', 'ready', 'ready'], "
        f"got {first.messages!r}"
    )


@pytest.mark.parametrize("number", [1, 4, 20])
def test_e5_accepts_positive_channels(number: int) -> None:
    channel = Channel(number)
    _require_attributes(channel, f"Channel({number})", "number")
    assert channel.number == number, (
        f"Channel({number}).number: expected {number}, got {channel.number!r}"
    )


@pytest.mark.parametrize("number", [0, -1, -4])
def test_e5_rejects_channels_below_one(number: int) -> None:
    try:
        got = Channel(number)
    except ValueError:
        return
    assert False, f"Channel({number}): expected ValueError, got an object {got!r} without an error"


def test_e6_pair_adds_to_existing_count() -> None:
    events = EventCount()
    _require_attributes(events, "EventCount()", "count")
    events.record()
    for expected in (3, 5):
        _require_attributes(events, "before record_pair()", "count")
        got = events.record_pair()
        assert got is None, f"record_pair(): expected None, got {got!r}"
        _require_attributes(events, "record_pair()", "count")
        assert events.count == expected, (
            f"record_pair() on a used counter: expected count {expected}, got {events.count!r}"
        )


def test_e6_pair_calls_record_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    events = EventCount()
    _require_attributes(events, "EventCount()", "count")
    calls: list[str] = []
    original_record = events.record

    def tracked_record() -> None:
        calls.append("record")
        original_record()

    monkeypatch.setattr(events, "record", tracked_record)
    got = events.record_pair()
    assert got is None, f"record_pair() with tracked record: expected None, got {got!r}"
    assert calls == ["record", "record"], (
        f"record_pair(): expected two self.record() calls, got {calls!r}"
    )


@pytest.mark.parametrize("message, channel", [("No answer", 3), ("Wrong mode", 1)])
def test_e7_error_keeps_channel_message_and_parent_args(message: str, channel: int) -> None:
    error = StationError(message, channel)
    call = f"StationError({message!r}, {channel!r})"
    assert isinstance(error, Exception), f"{call}: expected an Exception, got {type(error).__name__}"
    _require_attributes(error, call, "channel")
    assert error.channel == channel, (
        f"{call}.channel: expected {channel!r}, got {error.channel!r}"
    )
    assert error.args == (message,), (
        f"{call}.args: expected {(message,)!r}, got {error.args!r}. "
        "Call super().__init__(message) to initialize Exception with only the message."
    )
    assert str(error) == message, (
        f"str({call}): expected {message!r}, got {str(error)!r}. "
        "Keep Exception's string behavior after calling super().__init__(message)."
    )


def test_e8_uses_supplied_link_without_sending_at_setup() -> None:
    link = FakeLink()
    switch = PowerSwitch(link)
    _require_attributes(switch, "PowerSwitch(link)", "link")
    assert switch.link is link, (
        f"PowerSwitch(link).link: expected supplied link {link!r}, got {switch.link!r}"
    )
    assert link.sent == [], f"PowerSwitch(link): expected no commands, got {link.sent!r}"


@pytest.mark.parametrize("on_first", [True, False])
def test_e8_sends_exact_commands_including_repeats(on_first: bool) -> None:
    class TrackedLink(FakeLink):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def send(self, command: str) -> None:
            self.calls = self.calls + 1
            super().send(command)

    link = TrackedLink()
    switch = PowerSwitch(link)
    _require_attributes(switch, "PowerSwitch(link)", "link")
    if on_first:
        operations = [switch.turn_on, switch.turn_off, switch.turn_off, switch.turn_on]
        expected = ["OUTP 1", "OUTP 0", "OUTP 0", "OUTP 1"]
    else:
        operations = [switch.turn_off, switch.turn_on, switch.turn_on, switch.turn_off]
        expected = ["OUTP 0", "OUTP 1", "OUTP 1", "OUTP 0"]
    for operation in operations:
        got = operation()
        assert got is None, f"{operation.__name__}(): expected None, got {got!r}"
    assert link.sent == expected, (
        f"PowerSwitch calls {[operation.__name__ for operation in operations]!r}: "
        f"expected commands {expected!r}, got {link.sent!r}"
    )
    assert link.calls == 4, (
        f"four PowerSwitch calls: expected four link.send calls, got {link.calls!r}"
    )


def test_e8_switches_keep_their_own_links() -> None:
    first_link = FakeLink()
    second_link = FakeLink()
    first = PowerSwitch(first_link)
    second = PowerSwitch(second_link)
    _require_attributes(first, "PowerSwitch(first_link)", "link")
    _require_attributes(second, "PowerSwitch(second_link)", "link")
    first.turn_on()
    second.turn_off()
    assert first_link.sent == ["OUTP 1"], (
        f"first.turn_on(), second.turn_off(): expected first link ['OUTP 1'], got {first_link.sent!r}"
    )
    assert second_link.sent == ["OUTP 0"], (
        f"first.turn_on(), second.turn_off(): expected second link ['OUTP 0'], got {second_link.sent!r}"
    )


@pytest.mark.parametrize("name, value", [("supply", 5.0), ("load", 0.2)])
def test_e9_dataclass_keeps_the_same_fields(name: str, value: float) -> None:
    reading = DataReading(name, value)
    _require_attributes(reading, f"DataReading({name!r}, {value!r})", "name", "value")
    assert is_dataclass(reading), (
        f"DataReading({name!r}, {value!r}): expected a dataclass, got {type(reading).__name__} "
        "without dataclass behavior"
    )
    assert (reading.name, reading.value) == (name, value), (
        f"DataReading({name!r}, {value!r}): expected fields {(name, value)!r}, "
        f"got {(reading.name, reading.value)!r}"
    )


def test_e9_dataclass_compares_fields() -> None:
    first = DataReading("supply", 5.0)
    same = DataReading("supply", 5.0)
    _require_attributes(first, "first DataReading('supply', 5.0)", "name", "value")
    _require_attributes(same, "second DataReading('supply', 5.0)", "name", "value")
    assert first == same, (
        f"DataReading('supply', 5.0) == DataReading('supply', 5.0): expected True, got {first == same!r}"
    )
    other_name = DataReading("load", 5.0)
    other_value = DataReading("supply", 6.0)
    _require_attributes(other_name, "DataReading('load', 5.0)", "name", "value")
    _require_attributes(other_value, "DataReading('supply', 6.0)", "name", "value")
    assert first != other_name, (
        f"DataReading with supply vs load: expected unequal objects, got {first!r} and {other_name!r}"
    )
    assert first != other_value, (
        f"DataReading with 5.0 vs 6.0: expected unequal objects, got {first!r} and {other_value!r}"
    )


@pytest.mark.parametrize(
    "values, expected",
    [([5.0, 6.0], 1), ([4.5, 5.5], 2), ([4.0, 6.0], 0), ([], 0), ([5.0, 5.0, 5.0], 3)],
)
def test_e10_counts_objects_and_preserves_inputs(values: list[float], expected: int) -> None:
    readings = []
    for value in values:
        reading = Reading("supply", value)
        _require_attributes(reading, f"Reading('supply', {value!r})", "name", "value")
        readings.append(reading)
    before = readings.copy()
    got = count_passing(readings, 4.5, 5.5)
    call = f"count_passing(readings with values {values!r}, 4.5, 5.5)"
    assert got == expected, _result_message(call, expected, got)
    assert readings == before, f"{call}: expected original list {before!r}, got {readings!r}"
    actual_fields = []
    for reading in readings:
        _require_attributes(reading, call, "name", "value")
        actual_fields.append((reading.name, reading.value))
    expected_fields = []
    for value in values:
        expected_fields.append(("supply", value))
    assert actual_fields == expected_fields, (
        f"{call}: expected unchanged fields {expected_fields!r}, got {actual_fields!r}"
    )


@pytest.mark.parametrize(
    "question, expected, reread",
    [("Q1", "B", "E1: Python supplies self"),
     ("Q2", "C", "E2: the spelling of stored attribute names"),
     ("Q3", "A", "E6: parentheses run the method")],
    ids=["Q1", "Q2", "Q3"],
)
def test_e11_object_quiz(question: str, expected: str, reread: str) -> None:
    answers = object_answers()
    assert isinstance(answers, dict), _result_message("object_answers()", "an answer dictionary", answers)
    assert set(answers) == {"Q1", "Q2", "Q3"}, (
        f"object_answers(): expected exactly the keys Q1, Q2, Q3, got {list(answers)!r}"
    )
    got = answers.get(question)
    correct = got == expected
    assert correct, (
        f"object_answers()[{question!r}]: expected the correct uppercase option letter, "
        f"got {got!r}; reread {reread}."
        + (" your function returned None: did you forget `return`?" if got is None else "")
    )
