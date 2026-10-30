"""Deterministic station safety checks: no hardware or real waiting."""
import pytest

from starter.safety import OutputGuard, ramp_voltage, retry, with_deadline


class FakePSU:
    def __init__(self) -> None:
        self.events: list[tuple[object, ...]] = []
        self.off_errors: dict[int, BaseException] = {}
        self.write_error: BaseException | None = None
        self.fail_at: float | None = None

    def output(self, ch: int, on: bool) -> None:
        self.events.append(("output", ch, on))
        if not on and ch in self.off_errors:
            raise self.off_errors[ch]

    def set_voltage(self, ch: int, voltage: float) -> None:
        self.events.append(("voltage", ch, voltage))
        if voltage == self.fail_at and self.write_error is not None:
            raise self.write_error


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []
        self.clock_calls = 0

    def clock(self) -> float:
        self.clock_calls += 1
        assert self.clock_calls <= 100, "polling must stop at the deadline"
        return self.now

    def sleep(self, seconds: float) -> None:
        assert 0 < seconds <= 0.01, "sleep must be positive and at most 0.01 s"
        self.sleeps.append(seconds)
        self.now += seconds


@pytest.fixture
def psu() -> FakePSU:
    return FakePSU()


def test_e1_entry_and_normal_exit(psu: FakePSU) -> None:
    guard = OutputGuard(psu, [2, 1])
    assert psu.events == [], "construction must not touch the supply"
    with guard as entered:
        assert entered is guard, "with ... as must receive the guard"
        assert psu.events == [], "entry must not enable or disable outputs"
        psu.events.append(("measurement",))
    assert psu.events == [("measurement",), ("output", 2, False), ("output", 1, False)]


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_e1_preserves_block_error_and_continues_cleanup(psu: FakePSU, cleanup_fails: bool) -> None:
    original = OSError("measurement failed")
    if cleanup_fails:
        psu.off_errors[2] = RuntimeError("channel 2 shutdown failed")
    guard = OutputGuard(psu, [2, 1])
    with pytest.raises(OSError) as caught:
        with guard:
            raise original
    assert caught.value is original, "the measurement error must survive failed cleanup"
    assert psu.events == [("output", 2, False), ("output", 1, False)]


def test_e1_reports_first_cleanup_error_after_attempting_all(psu: FakePSU) -> None:
    first = OSError("first shutdown failure")
    psu.off_errors = {3: first, 2: RuntimeError("second failure")}
    guard = OutputGuard(psu, [3, 2, 1])
    with pytest.raises(OSError) as caught:
        with guard:
            pass
    assert caught.value is first
    assert psu.events == [("output", 3, False), ("output", 2, False), ("output", 1, False)]


@pytest.mark.parametrize("channels", [[], [1, 1], [3, 1]])
def test_e1_snapshots_channels_and_keeps_duplicates(psu: FakePSU, channels: list[int]) -> None:
    expected = [("output", ch, False) for ch in channels]
    guard = OutputGuard(psu, channels)
    channels.append(99)
    with guard:
        pass
    assert psu.events == expected, "cleanup must use the original channel sequence"


def test_e1_handles_operator_interrupt(psu: FakePSU) -> None:
    original = KeyboardInterrupt("operator stop")
    psu.off_errors[1] = KeyboardInterrupt("shutdown interrupted")
    guard = OutputGuard(psu, [1, 2])
    with pytest.raises(KeyboardInterrupt) as caught:
        with guard:
            raise original
    assert caught.value is original
    assert psu.events == [("output", 1, False), ("output", 2, False)]


@pytest.mark.parametrize("result", [0, None, False, "ready"])
def test_e2_forwards_arguments_result_and_metadata(result: object) -> None:
    sleeps: list[float] = []
    calls: list[tuple[int, str]] = []

    def read_status(ch: int, *, mode: str) -> object:
        """Read the station status."""
        calls.append((ch, mode))
        return result

    wrapped = retry(3, (OSError,), sleep=sleeps.append)(read_status)
    assert wrapped(2, mode="quick") is result, "a falsey result is still a successful call"
    assert calls == [(2, "quick")]
    assert sleeps == []
    assert wrapped.__name__ == read_status.__name__
    assert wrapped.__doc__ == read_status.__doc__
    assert getattr(wrapped, "__wrapped__", None) is read_status, "use functools.wraps"


@pytest.mark.parametrize("delay", [0.0, 0.2])
def test_e2_retries_matching_errors_and_sleeps_between(delay: float) -> None:
    events: list[tuple[object, ...]] = []
    attempts = 0

    def read_status() -> str:
        nonlocal attempts
        attempts += 1
        events.append(("read", attempts))
        if attempts == 1:
            raise ConnectionError("temporary connection failure")
        if attempts == 2:
            raise ValueError("temporary incomplete response")
        return "ready"

    def sleep(seconds: float) -> None:
        events.append(("sleep", seconds))

    wrapped = retry(4, (OSError, ValueError), delay_s=delay, sleep=sleep)(read_status)
    assert wrapped() == "ready"
    assert events == [("read", 1), ("sleep", delay), ("read", 2), ("sleep", delay), ("read", 3)]


@pytest.mark.parametrize("times", [1, 3])
def test_e2_exhaustion_preserves_last_error(times: int) -> None:
    errors = [OSError(f"instrument failure {number}") for number in range(times)]
    attempts = 0
    sleeps: list[float] = []

    def read_status() -> str:
        nonlocal attempts
        error = errors[attempts]
        attempts += 1
        raise error

    wrapped = retry(times, (OSError,), 0.1, sleeps.append)(read_status)
    with pytest.raises(OSError) as caught:
        wrapped()
    assert caught.value is errors[-1]
    assert attempts == times, "times includes the first attempt"
    assert sleeps == [0.1] * (times - 1), "never sleep after the final failure"


@pytest.mark.parametrize("scenario", ["unlisted", "empty", "sleep_error"])
def test_e2_unlisted_errors_and_sleep_errors_propagate(scenario: str) -> None:
    original = OSError("offline")
    sleep_error = RuntimeError("timer failed")
    attempts = 0
    sleeps: list[float] = []

    def read_status() -> str:
        nonlocal attempts
        attempts += 1
        raise original

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        raise sleep_error

    errors = (OSError,) if scenario == "sleep_error" else ((ValueError,) if scenario == "unlisted" else ())
    wrapped = retry(3, errors, 0.2, sleep)(read_status)
    expected = sleep_error if scenario == "sleep_error" else original
    with pytest.raises(type(expected)) as caught:
        wrapped()
    assert caught.value is expected
    assert attempts == 1
    assert sleeps == ([0.2] if scenario == "sleep_error" else [])


def test_e2_attempt_budget_resets_each_invocation() -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    def read_status() -> str:
        calls.append(1)
        if len(calls) % 2:
            raise OSError("busy")
        return "ready"

    wrapped = retry(2, (OSError,), sleep=sleeps.append)(read_status)
    assert wrapped() == "ready"
    assert wrapped() == "ready", "each operator request gets its own budget"
    assert len(calls) == 4
    assert sleeps == [0, 0]


@pytest.mark.parametrize("times,delay", [(0, 0), (-1, 0), (1, -0.1)])
def test_e2_rejects_invalid_settings_at_factory_call(times: int, delay: float) -> None:
    with pytest.raises(ValueError):
        retry(times, (OSError,), delay)


@pytest.mark.parametrize("result", [True, "ready", {"ready": True}])
def test_e3_checks_immediately_even_with_zero_timeout(result: object) -> None:
    timer = FakeTime()
    calls: list[int] = []

    def read_ready() -> object:
        calls.append(1)
        return result

    assert with_deadline(read_ready, 0, timer.clock, timer.sleep) is result
    assert calls == [1]
    assert timer.sleeps == []


def test_e3_polls_falsey_values_until_exact_truthy_result() -> None:
    timer = FakeTime()
    timer.now = 50.0
    ready = {"channel": 2}
    answers = iter([None, 0, [], ready])
    starts: list[float] = []

    def read_ready() -> object:
        starts.append(timer.now)
        return next(answers)

    assert with_deadline(read_ready, 0.1, timer.clock, timer.sleep) is ready
    assert starts == pytest.approx([50, 50.01, 50.02, 50.03])
    assert timer.sleeps == [0.01, 0.01, 0.01]


@pytest.mark.parametrize("timeout,starts,sleeps", [
    (0.0, [0.0], []),
    (0.005, [0.0], [0.005]),
    (0.025, [0.0, 0.01, 0.02], [0.01, 0.01, 0.005]),
])
def test_e3_deadline_is_fixed_and_sleep_is_clamped(
    timeout: float, starts: list[float], sleeps: list[float]
) -> None:
    timer = FakeTime()
    actual_starts: list[float] = []

    def not_ready() -> bool:
        actual_starts.append(timer.now)
        assert len(actual_starts) <= 5, "deadline must not restart after each poll"
        return False

    with pytest.raises(TimeoutError):
        with_deadline(not_ready, timeout, timer.clock, timer.sleep)
    assert actual_starts == pytest.approx(starts), "do not poll at or beyond the deadline"
    assert timer.sleeps == pytest.approx(sleeps)
    assert timer.now == pytest.approx(timeout)


@pytest.mark.parametrize("source", ["fn", "clock", "sleep"])
def test_e3_dependency_errors_propagate_without_retry(source: str) -> None:
    timer = FakeTime()
    original = OSError(f"{source} failed")
    calls: list[str] = []

    def read_ready() -> bool:
        calls.append("fn")
        if source == "fn":
            raise original
        return False

    def clock() -> float:
        if source == "clock":
            raise original
        return timer.clock()

    def sleep(seconds: float) -> None:
        calls.append("sleep")
        raise original

    with pytest.raises(OSError) as caught:
        with_deadline(read_ready, 1, clock, sleep)
    assert caught.value is original
    assert calls == ([] if source == "clock" else ["fn"] if source == "fn" else ["fn", "sleep"])


def test_e3_rejects_negative_timeout_before_dependencies() -> None:
    calls: list[str] = []

    def dependency() -> float:
        calls.append("dependency")
        return 0.0

    with pytest.raises(ValueError):
        with_deadline(dependency, -1, clock=dependency)
    assert calls == []


def test_e3_accounts_for_time_in_poll_and_accepts_started_success() -> None:
    timer = FakeTime()
    calls: list[int] = []

    def slow_not_ready() -> bool:
        calls.append(1)
        timer.now += 0.5
        return False

    with pytest.raises(TimeoutError):
        with_deadline(slow_not_ready, 0.1, timer.clock, timer.sleep)
    assert calls == [1]
    assert timer.sleeps == []

    def slow_ready() -> str:
        timer.now += 0.5
        return "ready"

    assert with_deadline(slow_ready, 0.1, timer.clock, timer.sleep) == "ready"


@pytest.mark.parametrize("target,step,levels", [
    (5.0, 2.0, [2.0, 4.0, 5.0]),
    (4.0, 2.0, [2.0, 4.0]),
    (0.5, 2.0, [0.5]),
    (0.0, 1.0, []),
    (0.3, 0.1, [0.1, 0.2, 0.3]),
])
def test_e4_ramp_order_clamp_and_settle(
    psu: FakePSU, target: float, step: float, levels: list[float]
) -> None:
    def settle() -> None:
        psu.events.append(("settle",))

    assert ramp_voltage(psu, 2, target, step, settle) is None
    expected = [event for level in levels for event in [("voltage", 2, level), ("settle",)]]
    assert psu.events == expected, "each write needs one settle; success leaves output enabled"
    assert all(event[2] <= target for event in psu.events if event[0] == "voltage")


@pytest.mark.parametrize("source,fail_at", [("write", 2.0), ("write", 5.0), ("settle", 2.0), ("settle", 5.0)])
def test_e4_write_or_settle_failure_recovers_and_reraises(
    psu: FakePSU, source: str, fail_at: float
) -> None:
    original = OSError("ramp failed")
    if source == "write":
        psu.fail_at, psu.write_error = fail_at, original

    def settle() -> None:
        last_voltage = psu.events[-1][2]
        psu.events.append(("settle",))
        if source == "settle" and last_voltage == fail_at:
            raise original

    with pytest.raises(OSError) as caught:
        ramp_voltage(psu, 3, 5, 2, settle)
    assert caught.value is original
    expected: list[tuple[object, ...]] = []
    for level in [2.0, 4.0, 5.0]:
        expected.append(("voltage", 3, level))
        if source != "write" or level != fail_at:
            expected.append(("settle",))
        if level == fail_at:
            break
    expected.extend([("voltage", 3, 0.0), ("output", 3, False)])
    assert psu.events == expected, "stop the ramp and perform only the two cleanup commands"


@pytest.mark.parametrize("voltage_fails,off_fails", [(True, False), (False, True), (True, True)])
def test_e4_cleanup_failures_do_not_replace_original(
    psu: FakePSU, voltage_fails: bool, off_fails: bool
) -> None:
    original = ValueError("settling failed")
    if voltage_fails:
        psu.fail_at, psu.write_error = 0.0, OSError("reset failed")
    if off_fails:
        psu.off_errors[4] = RuntimeError("shutdown failed")

    def settle() -> None:
        raise original

    with pytest.raises(ValueError) as caught:
        ramp_voltage(psu, 4, 5, 2, settle)
    assert caught.value is original
    assert psu.events == [("voltage", 4, 2), ("voltage", 4, 0), ("output", 4, False)]


@pytest.mark.parametrize("target,step", [(-1, 1), (1, 0), (1, -1), (0, 0)])
def test_e4_invalid_inputs_do_not_touch_device(psu: FakePSU, target: float, step: float) -> None:
    calls: list[int] = []
    with pytest.raises(ValueError):
        ramp_voltage(psu, 1, target, step, lambda: calls.append(1))
    assert psu.events == [], "validation errors must not send commands"
    assert calls == []


def test_e4_operator_interrupt_also_recovers(psu: FakePSU) -> None:
    original = KeyboardInterrupt("operator stop")

    def settle() -> None:
        raise original

    with pytest.raises(KeyboardInterrupt) as caught:
        ramp_voltage(psu, 1, 1, 1, settle)
    assert caught.value is original
    assert psu.events == [("voltage", 1, 1), ("voltage", 1, 0), ("output", 1, False)]
