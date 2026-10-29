"""Deterministic reproductions of the four operator reports; no hardware or sleeps."""

from collections.abc import Callable

import pytest

from starter.flaky_driver import (
    missing_samples,
    powered_sample,
    query_voltage,
    voltage_in_volts,
)


@pytest.mark.parametrize("reply, expected", [("500 mV", 0.5), ("2500 mV", 2.5), ("0 mV", 0.0)])
def test_e1_millivolt_symptom(reply: str, expected: float) -> None:
    got = voltage_in_volts(reply)
    assert got == pytest.approx(expected), f"{reply!r} must be converted to volts, got {got}"


@pytest.mark.parametrize("reply, expected", [("5.0 V", 5.0), (" \t1.2e1 V\r\n", 12.0), ("-2 mV", -0.002)])
def test_e1_preserves_volts_and_whitespace(reply: str, expected: float) -> None:
    assert voltage_in_volts(reply) == pytest.approx(expected), "parse the number and its exact unit"


@pytest.mark.parametrize("reply", ["", "500", "500 mV extra", "abc V", "2 A", "2 MV", "2 v"])
def test_e1_rejects_malformed_reply(reply: str) -> None:
    with pytest.raises(ValueError):
        voltage_in_volts(reply)


@pytest.mark.parametrize("reply", ["nan V", "inf mV", "-inf V", "1e999 V"])
def test_e1_rejects_nonfinite_measurements(reply: str) -> None:
    with pytest.raises(ValueError):
        voltage_in_volts(reply)


@pytest.fixture
def instrument_exchange() -> tuple[Callable[[str, float | None], str], list[tuple[str, float | None]]]:
    calls: list[tuple[str, float | None]] = []

    def exchange(command: str, timeout_s: float | None) -> str:
        calls.append((command, timeout_s))
        return "500 mV\n"

    return exchange, calls


def test_e2_default_timeout_and_raw_reply(instrument_exchange) -> None:
    exchange, calls = instrument_exchange
    assert query_voltage(exchange) == "500 mV\n", "return the raw reply unchanged"
    assert calls == [("MEAS:VOLT?", 0.25)], "one query must carry the datasheet timeout"


@pytest.mark.parametrize("timeout_s", [0.08, 2.0])
def test_e2_caller_timeout(instrument_exchange, timeout_s: float) -> None:
    exchange, calls = instrument_exchange
    query_voltage(exchange, timeout_s)
    assert calls == [("MEAS:VOLT?", timeout_s)], "forward the caller's timeout without replacing it"


def test_e2_silent_supply_is_bounded_without_retry() -> None:
    calls: list[tuple[str, float | None]] = []
    failure = TimeoutError("no instrument response")

    def silent_exchange(command: str, timeout_s: float | None) -> str:
        calls.append((command, timeout_s))
        # Fail immediately instead of letting legacy code hang this test process.
        assert timeout_s is not None and 0 < timeout_s < float("inf"), "unbounded instrument wait"
        raise failure

    with pytest.raises(TimeoutError) as caught:
        query_voltage(silent_exchange, 0.1)
    assert caught.value is failure, "preserve the transport's original timeout exception"
    assert calls == [("MEAS:VOLT?", 0.1)], "do not hide a timeout by retrying"


@pytest.mark.parametrize("timeout_s", [0.0, -0.1, float("nan"), float("inf"), -float("inf")])
def test_e2_invalid_timeout_does_not_touch_instrument(instrument_exchange, timeout_s: float) -> None:
    exchange, calls = instrument_exchange
    with pytest.raises(ValueError):
        query_voltage(exchange, timeout_s)
    assert calls == [], "validate the timeout before sending a command"


@pytest.mark.parametrize("counters, expected", [([], 0), ([42], 0), ([4, 5, 6], 0), ([4, 8, 10], 4)])
def test_e3_normal_stream(counters: list[int], expected: int) -> None:
    original = counters.copy()
    assert missing_samples(counters) == expected, f"wrong missing count for {counters}"
    assert counters == original, "the station's captured counters must stay unchanged"


@pytest.mark.parametrize("counters, expected", [([255, 0, 1], 0), ([254, 1], 2), ([254, 1, 1, 4], 4)])
def test_e3_wraparound_symptom(counters: list[int], expected: int) -> None:
    assert missing_samples(counters) == expected, f"count gaps across zero in {counters}"


@pytest.mark.parametrize("counters, modulus, expected", [([7, 7, 0, 2], 8, 1), ([1, 0, 1, 0], 2, 0), ([3, 3], 8, 0)])
def test_e3_duplicates_and_custom_modulus(counters: list[int], modulus: int, expected: int) -> None:
    assert missing_samples(counters, modulus) == expected, "duplicates are not missing samples"


@pytest.mark.parametrize("counters, modulus", [([], 1), ([0], 0), ([], -1), ([-1], 256), ([256], 256), ([8], 8)])
def test_e3_rejects_invalid_counter_configuration(counters: list[int], modulus: int) -> None:
    with pytest.raises(ValueError):
        missing_samples(counters, modulus)


def test_e4_success_has_exact_command_order() -> None:
    events: list[str] = []

    def sample() -> float:
        events.append("sample")
        return 4.98

    assert powered_sample(events.append, sample) == 4.98, "return the sample result unchanged"
    assert events == ["OUTP ON", "sample", "OUTP OFF"], "disable after exactly one sample"


@pytest.mark.parametrize("error_type", [ValueError, TimeoutError])
def test_e4_failed_sample_still_turns_output_off(error_type: type[Exception]) -> None:
    events: list[str] = []
    failure = error_type("measurement failed")

    def sample() -> float:
        events.append("sample")
        raise failure

    with pytest.raises(error_type) as caught:
        powered_sample(events.append, sample)
    assert caught.value is failure, "cleanup must preserve the original measurement exception"
    assert events == ["OUTP ON", "sample", "OUTP OFF"], "exception path must disable the supply"


def test_e4_enable_failure_also_attempts_output_off() -> None:
    events: list[str] = []
    failure = OSError("enable acknowledgement lost")

    def write(command: str) -> None:
        events.append(command)
        if command == "OUTP ON":
            raise failure

    def sample() -> float:
        pytest.fail("do not sample after enabling raises")

    with pytest.raises(OSError) as caught:
        powered_sample(write, sample)
    assert caught.value is failure, "preserve the original enabling exception"
    assert events == ["OUTP ON", "OUTP OFF"], "an uncertain enable needs an off attempt"


def test_e4_operator_cancellation_still_turns_output_off() -> None:
    events: list[str] = []
    failure = KeyboardInterrupt("operator cancelled")

    def sample() -> float:
        events.append("sample")
        raise failure

    with pytest.raises(KeyboardInterrupt) as caught:
        powered_sample(events.append, sample)
    assert caught.value is failure, "do not swallow operator cancellation"
    assert events == ["OUTP ON", "sample", "OUTP OFF"], "cleanup also runs on cancellation"
