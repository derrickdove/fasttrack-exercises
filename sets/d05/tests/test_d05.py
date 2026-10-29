from unittest.mock import Mock

import pytest

from starter.errors import (
    InstrumentError,
    InstrumentTimeout,
    drain_errors,
    parse_error_reply,
    safe_measure,
)


@pytest.mark.parametrize("message", ["CH1 did not answer", ""])
def test_e1_timeout_details(message: str) -> None:
    error = InstrumentTimeout(message)
    assert isinstance(error, Exception), "A timeout must be an exception"
    assert error.message == message, "Preserve the timeout message"
    assert str(error) == message, "Timeout text should be the original message"
    assert error.args == (message,), "Initialize the parent Exception too"


@pytest.mark.parametrize(
    ("code", "message"),
    [(-113, "Undefined header"), (0, "No error"), (25, ""), (-222, "CH1, overload")],
)
def test_e1_instrument_error_details(code: int, message: str) -> None:
    error = InstrumentError(code, message)
    assert error.code == code and isinstance(error.code, int), "Keep the integer code"
    assert error.message == message, "Preserve the instrument's message"
    assert str(error) == f"instrument error {code}: {message}", "Use the exact error format"
    assert error.args == (code, message), "Initialize the parent with both arguments"


def test_e1_instrument_error_can_be_caught() -> None:
    error = InstrumentError(-113, "Undefined header")
    with pytest.raises(InstrumentError) as caught:
        raise error
    assert caught.value is error, "Raising should preserve the exception object"


def test_e1_timeout_can_be_caught_separately() -> None:
    error = InstrumentTimeout("No reply")
    assert not isinstance(error, InstrumentError), "Timeout and instrument error are separate types"
    with pytest.raises(InstrumentTimeout) as caught:
        raise error
    assert caught.value is error, "Catch the same timeout object"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ('-113,"Undefined header"', (-113, "Undefined header")),
        ('+0,"No error"', (0, "No error")),
        ('17,"CH2 limit"', (17, "CH2 limit")),
        ('-0,"Clear"', (0, "Clear")),
        ('0012,"Leading zeros"', (12, "Leading zeros")),
    ],
)
def test_e2_valid_codes(reply: str, expected: tuple[int, str]) -> None:
    got = parse_error_reply(reply)
    assert got == expected, f"For reply {reply!r}, expected {expected!r}, got {got!r}"
    assert isinstance(got, tuple), "Return a tuple, not a list"
    assert isinstance(got[0], int), "Convert the code to an integer"


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        (' \t-222,"CH1, overload"\r\n', (-222, "CH1, overload")),
        ('0,""', (0, "")),
        ('7,"  Keep spaces  "', (7, "  Keep spaces  ")),
        ('8,"\u00b5A range"', (8, "\u00b5A range")),
    ],
)
def test_e2_message_and_outer_whitespace(reply: str, expected: tuple[int, str]) -> None:
    assert parse_error_reply(reply) == expected, "Keep message contents and strip only outside"


@pytest.mark.parametrize(
    "reply",
    [
        '', 'No error', ',"missing code"', '+,"missing digits"', '--1,"bad sign"',
        '1.0,"float"', '1_0,"underscore"', '\u0661,"non-ASCII"', '1 ,"space"',
        '+ 1,"space"', '1, "space"', '1,unquoted', '1,"unfinished',
        '1,"done"trailing', '1,"inner"quote"', '1,"a""b"',
        '1,"line\nbreak"', '1,"line\rbreak"',
    ],
)
def test_e2_malformed_reply_raises_value_error(reply: str) -> None:
    with pytest.raises(ValueError):
        parse_error_reply(reply)


@pytest.mark.parametrize("reply", ['0,"first","second"', '0,"ok",', '0,,"ok"'])
def test_e2_extra_fields_are_not_valid_messages(reply: str) -> None:
    with pytest.raises(ValueError):
        parse_error_reply(reply)


def test_e3_keeps_nonzero_errors_in_order() -> None:
    query = Mock(side_effect=[
        '-113,"Undefined header"', '5,"CH1, overload"',
        '-113,"Undefined header"', '+0,"No error"',
    ])
    got = drain_errors(query)
    expected = [(-113, "Undefined header"), (5, "CH1, overload"), (-113, "Undefined header")]
    assert got == expected, "Keep all nonzero replies in order, including duplicates"
    assert query.call_count == 4, "Read through the first zero and stop"
    assert all(call.args == ("SYST:ERR?",) and not call.kwargs for call in query.call_args_list), (
        "Every read must send exactly SYST:ERR?"
    )


def test_e3_empty_queue_stops_immediately() -> None:
    query = Mock(side_effect=['+0,"No error"', '-113,"Do not read this"'])
    assert drain_errors(query, max_reads=1) == [], "Exclude the zero reply"
    query.assert_called_once_with("SYST:ERR?")


@pytest.mark.parametrize("budget", [1, 3])
def test_e3_budget_includes_final_zero_and_caps_nonzero_reads(budget: int) -> None:
    # Check the successful boundary before checking the same budget's failure path.
    ending_in_zero = Mock(side_effect=['-1,"Fault"'] * (budget - 1) + ['0,"Clear"'])
    assert drain_errors(ending_in_zero, budget) == [(-1, "Fault")] * (budget - 1)
    assert ending_in_zero.call_count == budget, "Zero on the last allowed read succeeds"
    never_clear = Mock(return_value='-1,"Fault"')
    with pytest.raises(RuntimeError):
        drain_errors(never_clear, budget)
    assert never_clear.call_count == budget, "Stop exactly at max_reads without probing again"


def test_e3_default_budget_is_twenty_reads() -> None:
    ending_in_zero = Mock(side_effect=['-2,"Busy"'] * 19 + ['0,"Clear"'])
    assert drain_errors(ending_in_zero) == [(-2, "Busy")] * 19
    assert ending_in_zero.call_count == 20, "Default budget must allow 20 reads"
    never_clear = Mock(return_value='-2,"Busy"')
    with pytest.raises(RuntimeError):
        drain_errors(never_clear)
    assert never_clear.call_count == 20, "The default must stop after 20 reads"


@pytest.mark.parametrize("budget", [0, -1, -20])
def test_e3_invalid_budget_never_queries(budget: int) -> None:
    query = Mock(return_value='0,"Clear"')
    with pytest.raises(ValueError):
        drain_errors(query, budget)
    query.assert_not_called()


def test_e3_bad_reply_and_query_failure_propagate_immediately() -> None:
    malformed = Mock(side_effect=['-1,"Fault"', 'broken reply', '0,"Clear"'])
    with pytest.raises(ValueError):
        drain_errors(malformed)
    assert malformed.call_count == 2, "Do not read past a malformed reply"
    failure = OSError("Instrument disconnected")
    disconnected = Mock(side_effect=['-1,"Fault"', failure, '0,"Clear"'])
    with pytest.raises(OSError) as caught:
        drain_errors(disconnected)
    assert caught.value is failure, "Propagate the original query exception"
    assert disconnected.call_count == 2, "Do not retry a failed query"


@pytest.mark.parametrize("value", [3.25, 0.0, -0.125])
def test_e4_first_success_stops(value: float) -> None:
    measure = Mock(return_value=value)
    assert safe_measure(measure, retries=3) == value, "Return successful values unchanged"
    measure.assert_called_once_with()


@pytest.mark.parametrize("retries", [1, 2, 4])
def test_e4_success_on_final_allowed_attempt(retries: int) -> None:
    failures = [InstrumentTimeout(f"Attempt {number}") for number in range(retries)]
    measure = Mock(side_effect=failures + [2.5])
    assert safe_measure(measure, retries) == 2.5, "Allow the initial call plus all extra attempts"
    assert measure.call_count == retries + 1, "Each timeout consumes one retry"
    assert all(call.args == () and not call.kwargs for call in measure.call_args_list), (
        "Call measure with no arguments"
    )


@pytest.mark.parametrize("retries", [0, 1, 3])
def test_e4_exhaustion_raises_last_timeout_object(retries: int) -> None:
    failures = [InstrumentTimeout(f"Attempt {number}") for number in range(retries + 1)]
    measure = Mock(side_effect=failures)
    with pytest.raises(InstrumentTimeout) as caught:
        safe_measure(measure, retries)
    assert caught.value is failures[-1], "Re-raise the last timeout, without wrapping or replacing it"
    assert measure.call_count == retries + 1, "Do not exceed the extra-attempt budget"


@pytest.mark.parametrize("after_timeout", [False, True])
@pytest.mark.parametrize("kind", [ValueError, OSError, InstrumentError])
def test_e4_other_failures_propagate_without_retry(kind: type[Exception], after_timeout: bool) -> None:
    failure = InstrumentError(-113, "Bad command") if kind is InstrumentError else kind("Disconnected")
    events = [InstrumentTimeout("First attempt")] if after_timeout else []
    measure = Mock(side_effect=[*events, failure, 3.25])
    with pytest.raises(kind) as caught:
        safe_measure(measure, retries=5)
    assert caught.value is failure, "Preserve non-timeout failures"
    assert measure.call_count == (2 if after_timeout else 1), "Retry only timeouts"


@pytest.mark.parametrize("retries", [-1, -5])
def test_e4_negative_retries_never_measures(retries: int) -> None:
    measure = Mock(return_value=2.5)
    with pytest.raises(ValueError):
        safe_measure(measure, retries)
    measure.assert_not_called()


def test_e4_timeout_subclass_is_retryable() -> None:
    class ChannelTimeout(InstrumentTimeout):
        pass

    failure = ChannelTimeout("CH2 did not answer")
    measure = Mock(side_effect=[failure, 1.25])
    assert safe_measure(measure, retries=1) == 1.25, "Retry timeout subclasses too"
    assert measure.call_count == 2
