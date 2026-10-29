from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from starter.review6 import (
    create_app,
    decode_status,
    excursion_counts,
    parse_command,
    parse_error_reply,
    setup_order,
    scan_current,
)


@pytest.mark.parametrize("extra, expected", [([], False), (["--dry-run"], True)])
def test_e1_run_flag(extra: list[str], expected: bool) -> None:
    args = parse_command(["run", "--station", "bench-2", *extra])
    assert (args.command, args.station, args.dry_run) == ("run", "bench-2", expected)
    assert type(args.dry_run) is bool, "dry_run must be a Boolean"


def test_e1_show_order_and_input(capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["show", "--instrument", "PSU_1", "--station", " bench 2 "]
    original = argv.copy()
    args = parse_command(argv)
    assert (args.command, args.station, args.instrument) == ("show", " bench 2 ", "PSU_1")
    assert argv == original, "parsing must not change the caller's argument list"
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", ""), "successful parsing should be quiet"


@pytest.mark.parametrize("argv", [
    [], ["run"], ["show", "--station", "A"], ["reset"],
    ["run", "--station", "A", "--unknown"],
    ["run", "--station"], ["show", "--instrument", "psu"],
])
def test_e1_reject_bad_arguments(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        parse_command(argv)
    assert error.value.code == 2, "argument errors use argparse exit code 2"
    captured = capsys.readouterr()
    assert captured.err, "argparse should explain the error on stderr"
    assert captured.out == "", "argument errors should not print to stdout"


@pytest.mark.parametrize("value, active", [
    (0, set()), (1, {"ready"}), (2, {"output_on"}),
    (8, {"overcurrent"}), (32, {"overtemperature"}),
    (9, {"ready", "overcurrent"}),
    (255, {"ready", "output_on", "overcurrent", "overtemperature"}),
])
def test_e2_status_flags(value: int, active: set[str]) -> None:
    expected = {key: key in active for key in ("ready", "output_on", "overcurrent", "overtemperature")}
    got = decode_status(value)
    assert got == expected, f"status {value}: expected {expected}, got {got}"
    assert all(type(flag) is bool for flag in got.values()), "return bools, not integer masks"


def test_e2_unused_bits() -> None:
    assert decode_status(0xD4) == {
        "ready": False, "output_on": False, "overcurrent": False, "overtemperature": False,
    }, "bits outside the four documented masks must be ignored"


@pytest.mark.parametrize("value", [-1, -256, 256, 1000])
def test_e2_reject_out_of_range(value: int) -> None:
    with pytest.raises(ValueError):
        decode_status(value)


@pytest.mark.parametrize("deps, expected", [
    ({}, []),
    ({"scope": [], "psu": [], "dmm": []}, ["dmm", "psu", "scope"]),
    ({"psu": [], "dmm": ["psu"], "scope": []}, ["psu", "dmm", "scope"]),
    ({"run": ["scope", "dmm"], "scope": ["psu"], "dmm": ["psu"], "psu": []},
     ["psu", "dmm", "scope", "run"]),
])
def test_e3_safe_order(deps: dict[str, list[str]], expected: list[str]) -> None:
    got = setup_order(deps)
    assert got == expected, f"for prerequisites {deps}, expected {expected}, got {got}"


def test_e3_duplicates_and_no_mutation() -> None:
    deps = {"dmm": ["psu", "psu"], "psu": []}
    original = deepcopy(deps)
    assert setup_order(deps) == ["psu", "dmm"], "duplicate prerequisites count once"
    assert deps == original, "do not consume the caller's lists while planning setup"
    assert setup_order(deps) == ["psu", "dmm"], "repeated calls should return the same plan"


def test_e3_unknown_before_cycle() -> None:
    deps = {"psu": ["z-missing", "a-missing"], "loop": ["loop"]}
    with pytest.raises(ValueError) as error:
        setup_order(deps)
    assert str(error.value) == "unknown prerequisite: a-missing"


@pytest.mark.parametrize("deps, message", [
    ({"psu": ["psu"]}, "cycle or blocked: psu"),
    ({"b": ["a"], "a": ["b"], "c": ["b"], "ready": []}, "cycle or blocked: a, b, c"),
])
def test_e3_cycles_name_blocked_instruments(deps: dict[str, list[str]], message: str) -> None:
    with pytest.raises(ValueError) as error:
        setup_order(deps)
    assert str(error.value) == message, "report all remaining IDs, excluding completed setup"


@pytest.mark.parametrize("reply, expected", [
    ('0,"No error"', (0, "No error")),
    (' -113, "Undefined header, CH2"\r\n', (-113, "Undefined header, CH2")),
    ('+7,   Output inhibited   ', (7, "Output inhibited")),
    ('2, "  Channel disabled  "', (2, "Channel disabled")),
])
def test_e4_parse_driver_reply(reply: str, expected: tuple[int, str]) -> None:
    got = parse_error_reply(reply)
    assert got == expected, f"reply {reply!r}: expected {expected!r}, got {got!r}"


def test_e4_preserve_message_contents() -> None:
    assert parse_error_reply('4,Overcurrent, channel 2, output off') == (4, "Overcurrent, channel 2, output off")
    assert parse_error_reply('5, Bad "VOLT" command') == (5, 'Bad "VOLT" command')
    assert parse_error_reply('6,"Bad "VOLT" command"') == (6, 'Bad "VOLT" command')


@pytest.mark.parametrize("reply", [
    "", "No error", "not-a-code,Fault", ",Fault", "1.5,Fault", "0x10,Fault",
    "0,", "0,   ", '0,""', '0,"   "', '0,"Fault', '0,Fault"', '0,"',
])
def test_e4_reject_malformed_reply(reply: str) -> None:
    with pytest.raises(ValueError):
        parse_error_reply(reply)


@pytest.fixture
def status_client() -> Iterator[TestClient]:
    with TestClient(create_app("bench-2", {"psu": 9, "dmm": 0})) as client:
        client.timeout = 1.0
        yield client


def test_e5_health(status_client: TestClient) -> None:
    response = status_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "station": "bench-2"}


@pytest.mark.parametrize("instrument, flags", [
    ("psu", {"ready": True, "output_on": False, "overcurrent": True, "overtemperature": False}),
    ("dmm", {"ready": False, "output_on": False, "overcurrent": False, "overtemperature": False}),
])
def test_e5_instrument_status(status_client: TestClient, instrument: str, flags: dict[str, bool]) -> None:
    response = status_client.get(f"/instruments/{instrument}")
    assert response.status_code == 200
    assert response.json() == {"instrument": instrument, "flags": flags}


def test_e5_unknown_instrument(status_client: TestClient) -> None:
    response = status_client.get("/instruments/scope")
    assert response.status_code == 404
    assert response.json() == {"detail": "unknown instrument: scope"}


def test_e5_copy_input_snapshot() -> None:
    statuses = {"psu": 1}
    app = create_app("A", statuses)
    statuses["psu"] = 32
    statuses["scope"] = 0
    with TestClient(app) as client:
        client.timeout = 1.0
        response = client.get("/instruments/psu")
        assert response.status_code == 200
        assert response.json()["flags"] == {
            "ready": True, "output_on": False, "overcurrent": False, "overtemperature": False,
        }, "the app must keep the register value from creation time"
        assert client.get("/instruments/scope").status_code == 404, "new caller entries must not appear"


def test_e5_independent_apps() -> None:
    first = create_app("A", {"psu": 2})
    second = create_app("B", {})
    assert first is not second, "create_app must return a fresh application"
    with TestClient(first) as client_a, TestClient(second) as client_b:
        client_a.timeout = client_b.timeout = 1.0
        assert client_a.get("/health").json() == {"ok": True, "station": "A"}
        assert client_b.get("/health").json() == {"ok": True, "station": "B"}
        assert client_a.get("/instruments/psu").json()["flags"]["output_on"] is True
        assert client_b.get("/instruments/psu").status_code == 404


@pytest.fixture
def alarm_csv(tmp_path: Path) -> Path:
    path = tmp_path / "alarms.csv"
    path.write_text(
        "channel,value\nrail,5.2\nrail,5.0\nrail,5.2\nsense,5.1\nsafe,4.0\nrail,4.9\n",
        encoding="utf-8",
    )
    return path


def test_e6_count_crossings_by_channel(alarm_csv: Path) -> None:
    original = alarm_csv.read_bytes()
    got = excursion_counts(alarm_csv, 5.0)
    assert got == {"rail": 2, "sense": 1}, "count every strict crossing; omit channels with none"
    assert alarm_csv.read_bytes() == original, "reviewing alarms must not rewrite the log"


def test_e6_csv_names_and_numeric_formats(tmp_path: Path) -> None:
    path = tmp_path / "quoted.csv"
    path.write_bytes(
        'channel,value\r\n"rail,backup",-1e-1\r\n\r\n'
        '"rail,backup",-0.2\r\n" température ", +1.0E+0 \r\n'
        'Rail,0\r\nrail,-1\r\n'.encode("utf-8")
    )
    assert excursion_counts(path, -0.2) == {
        "rail,backup": 1, " température ": 1, "Rail": 1,
    }, "honor CSV quotes, UTF-8, exact names, blank lines, and numeric conversion"


@pytest.mark.parametrize("rows", ["", "\n\n", "rail,5.0\nsense,4.0\n"])
def test_e6_no_crossings(tmp_path: Path, rows: str) -> None:
    path = tmp_path / "quiet.csv"
    path.write_text("channel,value\n" + rows, encoding="utf-8")
    assert excursion_counts(path, 5.0) == {}, "an empty or quiet log has no affected channels"


@pytest.mark.parametrize("rows", ["rail,offline\n", "rail,6.0\nsense,offline\n"])
def test_e6_invalid_numeric_text(tmp_path: Path, rows: str) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("channel,value\n" + rows, encoding="utf-8")
    with pytest.raises(ValueError):
        excursion_counts(path, 5.0)


def test_e6_missing_log(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        excursion_counts(tmp_path / "missing.csv", 5.0)


class FakeCurrentTransport:
    """Script replies and keep writes and queries together to check their order."""

    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = iter(replies)
        self.calls: list[tuple[str, str]] = []
        self.write_error: Exception | None = None

    def write(self, command: str) -> None:
        self.calls.append(("write", command))
        if command == "INST:NSEL 2" and self.write_error is not None:
            raise self.write_error

    def query(self, command: str) -> str:
        self.calls.append(("query", command))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def current_transport() -> FakeCurrentTransport:
    return FakeCurrentTransport(["0.2\n", " 1.5e-1 ", "0.25"])


def test_e7_scan_order_and_duplicates(current_transport: FakeCurrentTransport) -> None:
    channels = [3, 1, 3]
    assert scan_current(current_transport, channels) == [0.2, 0.15, 0.25], "return fresh readings in scan order"
    assert current_transport.calls == [
        ("write", "INST:NSEL 3"), ("query", "MEAS:CURR?"),
        ("write", "INST:NSEL 1"), ("query", "MEAS:CURR?"),
        ("write", "INST:NSEL 3"), ("query", "MEAS:CURR?"),
    ], "select then query for every occurrence, including repeated channels"
    assert channels == [3, 1, 3], "do not sort or consume the operator's list"


def test_e7_empty_scan(current_transport: FakeCurrentTransport) -> None:
    assert scan_current(current_transport, []) == [], "no selected channels means no readings"
    assert current_transport.calls == [], "an empty scan must not contact the instrument"


@pytest.mark.parametrize("channels", [[0], [4], [-1], [1, 4, 2], [3, 1, 0]])
def test_e7_validate_before_io(current_transport: FakeCurrentTransport, channels: list[int]) -> None:
    original = channels.copy()
    current_transport.calls.append(("write", "earlier command"))
    with pytest.raises(ValueError):
        scan_current(current_transport, channels)
    assert current_transport.calls == [("write", "earlier command")], "validate the whole request before any call"
    assert channels == original, "invalid requests must leave the channel list unchanged"


def test_e7_bad_reply_stops_scan() -> None:
    transport = FakeCurrentTransport(["0.1", "not a reading", "0.3"])
    with pytest.raises(ValueError):
        scan_current(transport, [1, 2, 3])
    assert transport.calls == [
        ("write", "INST:NSEL 1"), ("query", "MEAS:CURR?"),
        ("write", "INST:NSEL 2"), ("query", "MEAS:CURR?"),
    ], "a conversion error must stop before selecting the next channel"


@pytest.mark.parametrize("operation", ["write", "query"])
def test_e7_transport_error_stops_scan(operation: str) -> None:
    failure = TimeoutError("current scan timed out")
    transport = FakeCurrentTransport(["0.1", failure, "0.3"])
    if operation == "write":
        transport.write_error = failure
    with pytest.raises(TimeoutError) as error:
        scan_current(transport, [1, 2, 3])
    assert error.value is failure, "propagate the same transport exception object"
    expected = [
        ("write", "INST:NSEL 1"), ("query", "MEAS:CURR?"),
        ("write", "INST:NSEL 2"),
    ]
    if operation == "query":
        expected.append(("query", "MEAS:CURR?"))
    assert transport.calls == expected, "stop at the failed call without a retry or later commands"


def test_e7_repeated_scans_are_fresh() -> None:
    transport = FakeCurrentTransport(["0.0", "-0.05"])
    assert scan_current(transport, [2]) == [0.0], "zero is a valid current reading"
    assert scan_current(transport, [2]) == [-0.05], "a later scan must query again"
    assert transport.calls == [
        ("write", "INST:NSEL 2"), ("query", "MEAS:CURR?"),
        ("write", "INST:NSEL 2"), ("query", "MEAS:CURR?"),
    ], "each scan reselects and remeasures the channel"
