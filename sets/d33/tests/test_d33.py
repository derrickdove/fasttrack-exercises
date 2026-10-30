"""Station tools run as Python children so the same checks work on Linux and Windows."""
from pathlib import Path
import signal
import subprocess
import sys

import pytest

from starter import procs
from starter.procs import GracefulStop, exit_code_meaning, run_tool, supervise


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("print('supply ready')", (0, "supply ready\n", "")),
        (
            "import sys; print('CH2'); print('overcurrent', file=sys.stderr); sys.exit(2)",
            (2, "CH2\n", "overcurrent\n"),
        ),
        ("pass", (0, "", "")),
    ],
)
def test_e1_capture_exit_code_and_both_streams(source, expected):
    got = run_tool([sys.executable, "-c", source], timeout=2.0)
    assert got == expected, f"tool output must be preserved exactly: expected {expected!r}, got {got!r}"


def test_e1_arguments_are_passed_literally():
    label = "station A; echo WRONG & $CHASSIS"
    cmd = [sys.executable, "-c", "import sys; print(sys.argv[1])", label]
    original = cmd.copy()
    got = run_tool(cmd, timeout=2.0)
    assert got == (0, label + "\n", ""), "station labels must remain one literal argument"
    assert cmd == original, "run_tool must not rewrite the caller's argument list"


def test_e1_timeout_uses_run_capture_and_discards_partial_output(monkeypatch):
    cmd = [sys.executable, "-c", "print('starting check')"]
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        assert args == cmd, "forward the command as a list"
        assert kwargs.get("capture_output") is True, "capture stdout and stderr"
        assert kwargs.get("text") is True, "return strings, not bytes"
        assert kwargs.get("timeout") == 0.05, "forward the caller's timeout"
        assert kwargs.get("shell", False) is False, "do not interpret station arguments in a shell"
        assert kwargs.get("check", False) is False, "nonzero codes are results, not exceptions"
        raise subprocess.TimeoutExpired(args, 0.05, output=b"partial", stderr=b"diagnostic")

    monkeypatch.setattr(subprocess, "run", fake_run)
    got = run_tool(cmd, timeout=0.05)
    assert got == (-9, "", "timeout"), f"discard partial timeout output; got {got!r}"
    assert len(calls) == 1, "E1 runs a tool once; E4 owns retries"


def test_e1_real_child_timeout():
    # Even a learner who omits the timeout gets a bounded child, not an endless loop.
    cmd = [sys.executable, "-c", "import time; time.sleep(0.2)"]
    got = run_tool(cmd, timeout=0.01)
    assert got == (-9, "", "timeout"), f"a timed-out tool needs the station timeout marker, got {got!r}"


def test_e1_missing_executable_propagates(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_tool([str(tmp_path / "missing-station-tool")], timeout=1.0)


@pytest.mark.parametrize("code, expected", [(0, "ok"), (1, "fail"), (2, "usage")])
def test_e2_station_codes(code, expected):
    got = exit_code_meaning(code)
    assert got == expected, f"exit code {code} should mean {expected!r}, got {got!r}"


@pytest.mark.parametrize("number", [1, 2, 9, 15, 37, 1000])
def test_e2_signal_encodings_agree(number):
    expected = f"killed by signal {number}"
    for code in (-number, 128 + number):
        got = exit_code_meaning(code)
        assert got == expected, f"decode signal convention for code {code}: got {got!r}"


@pytest.mark.parametrize("code", [3, 17, 127, 128])
def test_e2_other_codes_include_128(code):
    got = exit_code_meaning(code)
    assert got == f"exit {code}", f"ordinary code {code} must not be classified as a signal"


SIGNALS = [signal.SIGINT]
if hasattr(signal, "SIGTERM"):
    SIGNALS.append(signal.SIGTERM)


@pytest.fixture
def safe_signals():
    # Harmless baseline handlers keep incorrect learner code from terminating pytest.
    original = {sig: signal.getsignal(sig) for sig in SIGNALS}
    seen = []

    def baseline(signum, frame):
        seen.append(signum)

    try:
        for sig in SIGNALS:
            signal.signal(sig, baseline)
        yield baseline, seen
    finally:
        for sig, handler in original.items():
            signal.signal(sig, handler)


def test_e3_initial_flag_and_entered_object(safe_signals):
    stop = GracefulStop()
    assert stop.requested is False, "a new station stop monitor starts clear"
    with stop as entered:
        assert entered is stop, "__enter__ must return the monitor itself"
        assert entered.requested is False, "entering alone is not a stop request"
    assert stop.requested is False


@pytest.mark.parametrize("sig", SIGNALS, ids=lambda sig: sig.name)
def test_e3_signal_sets_flag_without_running_previous_handler(safe_signals, sig):
    _, seen = safe_signals
    with GracefulStop() as stop:
        signal.raise_signal(sig)
        assert stop.requested is True, f"{sig.name} must request a graceful station stop"
        signal.raise_signal(sig)
        assert stop.requested is True, "repeated stop signals leave the flag set"
        assert seen == [], "the old handler must not run while the monitor is active"
    assert stop.requested is True, "exiting preserves the last flag value"


@pytest.mark.parametrize("exceptional_exit", [False, True])
def test_e3_restores_exact_handlers_on_every_exit(safe_signals, exceptional_exit):
    baseline, _ = safe_signals
    stop = GracefulStop()
    if exceptional_exit:
        with pytest.raises(ValueError, match="station check failed"):
            with stop:
                raise ValueError("station check failed")
    else:
        with stop:
            pass
    for sig in SIGNALS:
        assert signal.getsignal(sig) is baseline, f"restore the exact prior {sig.name} handler"


def test_e3_sequential_reuse_resets_flag_and_saves_current_handlers(safe_signals):
    stop = GracefulStop()
    with stop:
        signal.raise_signal(signal.SIGINT)
        assert stop.requested is True
    previous_requests = []

    def replacement(signum, frame):
        previous_requests.append(signum)

    for sig in SIGNALS:
        signal.signal(sig, replacement)
    with stop:
        assert stop.requested is False, "a reused monitor starts a fresh check"
    for sig in SIGNALS:
        assert signal.getsignal(sig) is replacement, "save handlers on entry, not at construction"
    assert previous_requests == []


def test_e3_nested_instances_restore_outer_monitor(safe_signals):
    with GracefulStop() as outer:
        outer_handlers = {sig: signal.getsignal(sig) for sig in SIGNALS}
        with GracefulStop() as inner:
            signal.raise_signal(signal.SIGINT)
            assert inner.requested is True
            assert outer.requested is False, "only the active inner monitor handles this request"
        for sig in SIGNALS:
            assert signal.getsignal(sig) == outer_handlers[sig], "restore the outer monitor's handler"
        signal.raise_signal(signal.SIGINT)
        assert outer.requested is True, "the outer handler must work again after inner exit"


def counter_command(tmp_path: Path, failures: int) -> tuple[list[str], Path]:
    """A tool records each launch and succeeds after a fixed number of failures."""
    counter = tmp_path / "station attempts.txt"
    source = (
        "from pathlib import Path; import sys; "
        "p = Path(sys.argv[1]); "
        "n = int(p.read_text()) if p.exists() else 0; "
        "p.write_text(str(n + 1)); "
        "sys.exit(1 if n < int(sys.argv[2]) else 0)"
    )
    return [sys.executable, "-c", source, str(counter), str(failures)], counter


def test_e4_success_stops_after_one_real_launch(tmp_path):
    cmd, counter = counter_command(tmp_path, failures=0)
    got = supervise(cmd, restarts=3)
    assert got == [0], f"a successful station tool needs no restart, got {got!r}"
    assert counter.read_text() == "1", "do not launch extra attempts after success"


def test_e4_transient_failure_retries_then_stops(tmp_path):
    cmd, counter = counter_command(tmp_path, failures=2)
    original = cmd.copy()
    got = supervise(cmd, restarts=4)
    assert got == [1, 1, 0], f"record failures and final success in order, got {got!r}"
    assert counter.read_text() == "3", "stop as soon as the instrument tool succeeds"
    assert cmd == original, "restart the same command without rewriting its arguments"


@pytest.mark.parametrize("restarts", [0, 2])
def test_e4_budget_counts_additional_attempts(tmp_path, restarts):
    cmd, counter = counter_command(tmp_path, failures=99)
    got = supervise(cmd, restarts=restarts)
    assert got == [1] * (restarts + 1), f"{restarts} retries allow {restarts + 1} total attempts"
    assert counter.read_text() == str(restarts + 1), "the budget must match actual launches"


def test_e4_timeouts_and_other_nonzero_codes_are_retryable(monkeypatch):
    cmd = [sys.executable, "-c", "print('probe')"]
    outcomes = iter([-9, -15, 2, 0])
    calls = []

    def fake_tool(args, timeout):
        calls.append((args.copy(), timeout))
        assert len(calls) <= 4, "stop after the first successful attempt"
        return next(outcomes), "discard this output", "discard this diagnostic"

    monkeypatch.setattr(procs, "run_tool", fake_tool)
    got = supervise(cmd, restarts=7)
    assert got == [-9, -15, 2, 0], f"retry every nonzero result, including timeout: got {got!r}"
    assert calls == [(cmd, 5.0)] * 4, "reuse E1 with the same command and a five-second timeout"


@pytest.mark.parametrize("restarts", [-1, -3])
def test_e4_negative_budget_rejected_before_launch(monkeypatch, restarts):
    calls = []

    def fake_tool(args, timeout):
        calls.append(args)
        return 0, "", ""

    monkeypatch.setattr(procs, "run_tool", fake_tool)
    with pytest.raises(ValueError):
        supervise(["station-tool"], restarts=restarts)
    assert calls == [], "invalid retry budgets must not launch a station tool"


def test_e4_launch_error_propagates_without_retry(monkeypatch):
    calls = []

    def fake_tool(args, timeout):
        calls.append(args)
        raise FileNotFoundError("missing station checker")

    monkeypatch.setattr(procs, "run_tool", fake_tool)
    with pytest.raises(FileNotFoundError, match="missing station checker"):
        supervise(["missing-station-tool"], restarts=3)
    assert len(calls) == 1, "a launch error is not an exit code and must not be retried"
