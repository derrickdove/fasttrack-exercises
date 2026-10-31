"""Contracts for the interview-style bench power supply driver."""
from decimal import Decimal
from pathlib import Path
import re
import runpy
import subprocess
import sys

import pyvisa
import pytest

from starter.psu import Psu, ResourceLike, ResourceManagerLike


class FakeResource:
    """Record communication settings, commands, replies and cleanup order."""

    def __init__(self) -> None:
        self.timeout = 0.0
        self.read_termination: str | None = None
        self.write_termination: str | None = None
        self.replies = {"MEAS:VOLT?": "12.034", "MEAS:CURR?": "0.512"}
        self.writes: list[str] = []
        self.queries: list[str] = []
        self.events: list[str] = []
        self.close_count = 0
        self.fail_off = False
        self.fail_close = False

    def write(self, message: str) -> int:
        self.writes.append(message)
        self.events.append(message)
        if message == "OUTP 0" and self.fail_off:
            raise OSError("output-off failed")
        return len(message)

    def read(self) -> str:
        raise AssertionError("use query for a measurement")

    def query(self, message: str) -> str:
        self.queries.append(message)
        return self.replies[message]

    def close(self) -> None:
        self.close_count += 1
        self.events.append("close")
        if self.fail_close:
            raise OSError("resource-close failed")


class FakeResourceManager:
    """An independent manager, deliberately falsey to check rm is None."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.resource = FakeResource()

    def __bool__(self) -> bool:
        return False

    def open_resource(self, resource_name: str) -> FakeResource:
        self.opened.append(resource_name)
        return self.resource


@pytest.fixture
def manager() -> FakeResourceManager:
    return FakeResourceManager()


def test_e5_open_settings_and_lazy_default(manager: FakeResourceManager,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[FakeResourceManager] = []

    def factory() -> FakeResourceManager:
        replacement = FakeResourceManager()
        created.append(replacement)
        return replacement

    monkeypatch.setattr(pyvisa, "ResourceManager", factory)
    # Loading the module itself must never try to connect to hardware.
    runpy.run_path(str(Path(__file__).parents[1] / "starter/psu.py"))
    assert created == [], "create the default manager only inside Psu construction"
    compatible: ResourceManagerLike = manager
    resource: ResourceLike = manager.resource
    Psu("10.2.3.4", 750, rm=compatible)
    assert created == [], "an injected manager must replace the default, even if falsey"
    assert manager.opened == ["TCPIP::10.2.3.4::INSTR"]
    assert (resource.timeout, resource.read_termination, resource.write_termination) == (750, "\n", "\n")
    assert manager.resource.writes == [] and manager.resource.queries == []
    Psu("192.0.2.8")
    assert len(created) == 1, "construct one default manager when rm is None"
    assert created[0].opened == ["TCPIP::192.0.2.8::INSTR"]
    assert created[0].resource.timeout == 2000
    assert created[0].resource.read_termination == created[0].resource.write_termination == "\n"


@pytest.mark.parametrize("bad", [0, -1, True, False, 1.5, "2000", None])
def test_e5_invalid_timeout_before_open(bad: object) -> None:
    manager = FakeResourceManager()
    # Establish the exercise's implementation before checking rejection paths.
    Psu("probe", rm=manager)
    manager.opened.clear()
    with pytest.raises(ValueError, match="timeout_ms"):
        Psu("192.0.2.1", bad, rm=manager)
    assert manager.opened == [], "reject timeout_ms before opening an instrument"


@pytest.mark.parametrize("method, command", [("read_voltage", "MEAS:VOLT?"),
                                            ("read_current", "MEAS:CURR?")])
def test_e5_queries_convert_and_report_bad_replies(method: str, command: str,
                                                   manager: FakeResourceManager) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    read = getattr(supply, method)
    for reply, expected in [(manager.resource.replies[command], 12.034 if method == "read_voltage" else 0.512),
                            (" -2.5e-3\n", -0.0025), ("0", 0.0)]:
        manager.resource.replies[command] = reply
        got = read()
        assert isinstance(got, float)
        assert got == pytest.approx(expected), f"wrong measurement for {reply!r}"
    for reply in ("OVERLOAD", "1.2 V", ""):
        manager.resource.replies[command] = reply
        with pytest.raises(ValueError) as caught:
            read()
        assert reply in str(caught.value), "invalid numeric replies must appear in the error"
    del manager.resource.replies[command]
    with pytest.raises(KeyError):
        read()
    assert manager.resource.queries == [command] * 7, "query exactly once on every call"
    assert manager.resource.writes == []


def test_e5_setpoints_format_and_reject_invalid_values(manager: FakeResourceManager) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    assert supply.set_voltage(12.0344) is None
    assert supply.set_current_limit(0.5126) is None
    assert supply.set_voltage(0) is None
    assert supply.set_current_limit(0) is None
    expected = ["VOLT 12.034", "CURR 0.513", "VOLT 0.000", "CURR 0.000"]
    assert manager.resource.writes == expected, "write exactly three decimal places"
    for setter in (supply.set_voltage, supply.set_current_limit):
        for invalid in (-0.0001, float("nan"), float("inf"), float("-inf")):
            with pytest.raises(ValueError):
                setter(invalid)
            assert manager.resource.writes == expected, f"reject {invalid!r} before writing or rounding"
    assert manager.resource.queries == []


def test_e5_output_requires_actual_bool(manager: FakeResourceManager) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    assert supply.enable_output(True) is None
    assert supply.enable_output(False) is None
    expected = ["OUTP 1", "OUTP 0"]
    assert manager.resource.writes == expected
    for bad in (0, 1, 2, "1", None, 1.0):
        with pytest.raises(TypeError):
            supply.enable_output(bad)
        assert manager.resource.writes == expected, f"reject {bad!r} before a write"
    assert manager.resource.queries == []


def test_e5_real_pyvisa_sim_voltage(tmp_path: Path) -> None:
    yaml = Path(__file__).parents[1] / "data/psu.yaml"
    manager = pyvisa.ResourceManager(f"{yaml}@sim")
    try:
        supply = Psu("192.168.1.100", rm=manager)
        assert supply.read_voltage() == pytest.approx(12.034)
    finally:
        manager.close()
    snippet = tmp_path / "injection.py"
    snippet.write_text(
        'import pyvisa\nfrom starter.psu import Psu\n'
        'manager = pyvisa.ResourceManager("dummy.yaml@sim")\n'
        'supply = Psu("192.168.1.100", rm=manager)\n'
        'configured = Psu.from_config("station.toml", rm=manager)\n',
        encoding="utf-8",
    )
    checked = subprocess.run(
        [sys.executable, "-m", "mypy", "--strict", "--cache-dir",
         str(tmp_path / "mypy_cache"), str(snippet)],
        cwd=Path(__file__).parents[1], capture_output=True, text=True, timeout=60,
    )
    assert checked.returncode == 0, checked.stdout + checked.stderr


@pytest.mark.parametrize("method, key, limit, expected", [
    ("set_voltage", "max_voltage", 12.0, ["VOLT 0.000", "VOLT 12.000"]),
    ("set_current_limit", "max_current", 0.5, ["CURR 0.000", "CURR 0.500"]),
])
def test_e6_limits_allow_boundary_and_reject_before_rounding(
    method: str, key: str, limit: float, expected: list[str], manager: FakeResourceManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Establish implementation before checking constructor rejection paths.
    Psu("probe", rm=manager)
    manager.opened.clear()
    monkeypatch.setattr(pyvisa, "ResourceManager", lambda: manager)
    for invalid in (-1.0, -0.0001, float("nan"), float("inf"), float("-inf")):
        for resource_manager in (manager, None):
            with pytest.raises(ValueError, match=key):
                Psu("192.0.2.1", rm=resource_manager, **{key: invalid})
            assert manager.opened == [], f"reject {key}={invalid!r} before opening hardware"
            assert manager.resource.writes == [] and manager.resource.queries == []
    supply = Psu("192.0.2.1", rm=manager, **{key: limit})
    setter = getattr(supply, method)
    setter(0)
    setter(limit)
    assert manager.resource.writes == expected
    with pytest.raises(ValueError) as caught:
        setter(limit + 0.0001)
    message = str(caught.value)
    numbers = re.findall(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", message)
    assert key in message and any(Decimal(number) == Decimal(str(limit)) for number in numbers), (
        "name the maximum and its value (any equivalent numeric spelling)"
    )
    assert manager.resource.writes == expected, "reject above-max requests before any write"
    for invalid in (-1.0, -0.0001, float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError):
            setter(invalid)
        assert manager.resource.writes == expected, "reject invalid setpoints with a configured maximum"
    assert manager.resource.queries == []
    zero = Psu("192.0.2.1", rm=manager, **{key: 0})
    getattr(zero, method)(0)
    with pytest.raises(ValueError, match=key):
        getattr(zero, method)(0.001)
    unlimited = Psu("192.0.2.1", rm=manager)
    getattr(unlimited, method)(100)
    assert manager.resource.writes[-1].endswith("100.000"), "None means no maximum"


def test_e6_config_defaults_limits_and_classmethod(tmp_path: Path, manager: FakeResourceManager) -> None:
    config = tmp_path / "station supply.toml"
    config.write_text('ip = "192.0.2.4"\n', encoding="utf-8")

    class StationPsu(Psu):
        pass

    supply = StationPsu.from_config(config, rm=manager)
    assert isinstance(supply, StationPsu), "a classmethod must construct cls"
    assert manager.opened == ["TCPIP::192.0.2.4::INSTR"]
    assert manager.resource.timeout == 2000
    supply.set_voltage(80)
    supply.set_current_limit(8)
    config.write_text('ip = "10.0.0.9"\ntimeout_ms = 1250\nmax_voltage = 12\nmax_current = 0.5\n', encoding="utf-8")
    supply = Psu.from_config(str(config), rm=manager)
    assert manager.opened[-1] == "TCPIP::10.0.0.9::INSTR"
    assert manager.resource.timeout == 1250
    supply.set_voltage(12)
    supply.set_current_limit(0.5)
    before = list(manager.resource.writes)
    for setter, key, value in [(supply.set_voltage, "max_voltage", 12.1),
                               (supply.set_current_limit, "max_current", 0.6)]:
        with pytest.raises(ValueError, match=key):
            setter(value)
    assert manager.resource.writes == before


@pytest.mark.parametrize("content, key", [
    ("", "ip"), ('ip = 12', "ip"), ('ip = true', "ip"),
    ('ip = ["10.0.0.1"]', "ip"),
    *[(f'ip = "10.0.0.1"\ntimeout_ms = {value}', "timeout_ms")
      for value in ('"2000"', '2.0', 'true', '0', '-1')],
    *[(f'ip = "10.0.0.1"\n{key} = {value}', key)
      for key in ("max_voltage", "max_current")
      for value in ('"12"', 'true', '[]', '-1', '-0.0001', 'nan', '+inf', '-inf')],
])
def test_e6_config_errors_name_key_before_open(content: str, key: str, tmp_path: Path,
                                               manager: FakeResourceManager) -> None:
    # Valid construction keeps an untouched starter failure as NotImplementedError.
    Psu("probe", rm=manager)
    manager.opened.clear()
    config = tmp_path / "bad.toml"
    config.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=key):
        Psu.from_config(config, rm=manager)
    assert manager.opened == [], "validate the whole config before opening hardware"
    assert manager.resource.writes == [] and manager.resource.queries == []


def test_e6_close_is_idempotent(manager: FakeResourceManager) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    assert supply.close() is None
    assert supply.close() is None
    assert manager.resource.close_count == 1, "close the resource only once"
    assert manager.resource.writes == [], "explicit close only closes the resource"


@pytest.mark.parametrize("raise_in_block", [False, True])
def test_e6_context_disables_then_closes(raise_in_block: bool, manager: FakeResourceManager) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    failure = RuntimeError("test step failed")

    def step() -> None:
        with supply as active:
            assert active is supply, "__enter__ returns the same supply"
            active.enable_output(True)
            if raise_in_block:
                raise failure

    if raise_in_block:
        with pytest.raises(RuntimeError) as caught:
            step()
        assert caught.value is failure, "preserve the original block exception"
    else:
        step()
    assert manager.resource.events == ["OUTP 1", "OUTP 0", "close"]
    supply.close()
    assert manager.resource.close_count == 1


@pytest.mark.parametrize("raise_in_block", [False, True])
@pytest.mark.parametrize("failure_stage", ["output-off", "resource-close"])
def test_e6_cleanup_failure_preserves_block_exception(
    raise_in_block: bool, failure_stage: str, manager: FakeResourceManager
) -> None:
    supply = Psu("192.0.2.1", rm=manager)
    manager.resource.fail_off = failure_stage == "output-off"
    manager.resource.fail_close = failure_stage == "resource-close"
    failure = RuntimeError("original test failure")
    with pytest.raises(RuntimeError if raise_in_block else OSError) as caught:
        with supply:
            if raise_in_block:
                raise failure
    if raise_in_block:
        assert caught.value is failure, "cleanup must not replace the block failure"
    else:
        assert f"{failure_stage} failed" in str(caught.value), "surface cleanup failure after a successful block"
    assert manager.resource.events == ["OUTP 0", "close"], "attempt output-off, then close, even if cleanup raises"
    supply.close()
    assert manager.resource.close_count == 1
