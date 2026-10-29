from collections.abc import Iterator

import pytest
import serial

from starter.serial_sensor import (
    bus_answers,
    open_loopback,
    parse_sensor_line,
    read_frames,
    read_line,
    send_line,
)


@pytest.fixture
def port() -> Iterator[serial.Serial]:
    # Independent of E1, so later exercise failures identify their own stubs.
    with serial.serial_for_url("loop://", timeout=0.01, write_timeout=0.5) as connection:
        yield connection


def _frame(payload: str) -> str:
    checksum = 0
    for byte in payload.encode("ascii"):
        checksum ^= byte
    return f"${payload}*{checksum:02X}"


@pytest.mark.parametrize("timeout", [0.0, 0.01, 0.05])
def test_e1_open_settings(timeout: float) -> None:
    with open_loopback(timeout) as connection:
        assert connection.is_open, "return an already open connection"
        assert connection.port == "loop://", "use the loopback URL handler"
        assert connection.timeout == timeout, "set the requested read timeout"
        assert connection.write_timeout == timeout, "bound writes as well as reads"
        assert (connection.baudrate, connection.bytesize, connection.parity, connection.stopbits) == (
            9600, 8, "N", 1
        ), "keep pySerial's default baud and framing"
    assert not connection.is_open, "the caller must be able to close the connection"


def test_e1_echo_bytes() -> None:
    with open_loopback(0.05) as connection:
        connection.write(b"CHASSIS\r\n")
        assert connection.read(9) == b"CHASSIS\r\n", "loopback should echo written bytes"


def test_e1_negative_timeout() -> None:
    with pytest.raises(ValueError):
        open_loopback(-0.1)


@pytest.mark.parametrize("text", ["STATUS?", "", "  CH2  "])
def test_e2_send_exact_bytes(port: serial.Serial, text: str) -> None:
    assert send_line(port, text) is None, "send_line should return None"
    expected = text.encode("ascii") + b"\r\n"
    assert port.read(len(expected)) == expected, "write ASCII followed by exactly one CRLF"
    assert port.in_waiting == 0, "do not append extra bytes"
    assert port.is_open, "the caller owns closing the port"


def test_e2_roundtrip_two_replies(port: serial.Serial) -> None:
    send_line(port, "STATUS?")
    send_line(port, "ID?")
    assert read_line(port) == "STATUS?", "read only the first complete reply"
    assert read_line(port) == "ID?", "leave the next reply for the next call"
    assert port.is_open, "reading must leave the connection open"


@pytest.mark.parametrize("raw, expected", [(b"  READY  \r\n", "  READY  "), (b"\r\n", "")])
def test_e2_read_preserves_payload(port: serial.Serial, raw: bytes, expected: str) -> None:
    port.write(raw)
    assert read_line(port) == expected, "remove only the final CRLF, preserving payload spaces"


def test_e2_silent_sensor_times_out(port: serial.Serial) -> None:
    with pytest.raises(TimeoutError):
        read_line(port)


@pytest.mark.parametrize("raw", [b"READY\n", b"partial", b"\xff\r\n"])
def test_e2_damaged_line(port: serial.Serial, raw: bytes) -> None:
    port.write(raw)
    with pytest.raises(ValueError):
        read_line(port)
    assert port.in_waiting == 0, "the damaged line has been consumed"


@pytest.mark.parametrize("text", ["STATUS?\n", "STATUS?\r", "A\r\nB", "TEMP=23\N{DEGREE SIGN}C"])
def test_e2_reject_invalid_command_before_write(port: serial.Serial, text: str) -> None:
    with pytest.raises(ValueError):
        send_line(port, text)
    assert port.in_waiting == 0, "invalid commands must not write any bytes"


def test_e3_known_checksum() -> None:
    result = parse_sensor_line("$TMP,23.5,PRS,101.2*02")
    assert result == {"TMP": 23.5, "PRS": 101.2}, "decode both sensor measurements"
    assert all(isinstance(value, float) for value in result.values()), "values must be floats"


@pytest.mark.parametrize("payload, expected", [
    ("TMP,-12.5", {"TMP": -12.5}),
    ("CH1,0,CH2,1e2,CH3,+3.25", {"CH1": 0.0, "CH2": 100.0, "CH3": 3.25}),
    ("tmp,1,TMP,2,tmp,3", {"tmp": 3.0, "TMP": 2.0}),
])
def test_e3_label_value_pairs(payload: str, expected: dict[str, float]) -> None:
    assert parse_sensor_line(_frame(payload)) == expected, f"incorrect measurements for {payload!r}"


def test_e3_lowercase_checksum() -> None:
    # XOR of TMP,23.5 is 7F; lowercase hex must also work.
    assert parse_sensor_line("$TMP,23.5*7f") == {"TMP": 23.5}, "accept lowercase hex digits"


@pytest.mark.parametrize("line", ["$TMP,23.5,PRS,101.2*4F", "$TMP,23.5,PRS,101.3*02"])
def test_e3_reject_checksum_mismatch(line: str) -> None:
    with pytest.raises(ValueError):
        parse_sensor_line(line)


@pytest.mark.parametrize("line", [
    "", "TMP,20*67", "$TMP,20", "$TMP,20*67*67", "$TMP,20*7",
    "$TMP,20*067", "$TMP,20*GG", "$TMP,20*+A", "$TMP,20*67\r\n",
    "$T\N{DEGREE SIGN},20*00",
])
def test_e3_reject_malformed_envelope(line: str) -> None:
    with pytest.raises(ValueError):
        parse_sensor_line(line)


@pytest.mark.parametrize("payload", ["", "TMP", "TMP,20,PRS", ",20", "TMP,", "TMP,hot"])
def test_e3_reject_invalid_fields(payload: str) -> None:
    with pytest.raises(ValueError):
        parse_sensor_line(_frame(payload))


def test_e4_collect_and_leave_next_frame(port: serial.Serial) -> None:
    lines = [_frame("TMP,21"), _frame("PRS,102"), _frame("TMP,22")]
    port.write(("\r\n".join(lines) + "\r\n").encode("ascii"))
    assert read_frames(port, 2) == ([{"TMP": 21.0}, {"PRS": 102.0}], 0), "keep arrival order"
    assert port.readline() == (lines[2] + "\r\n").encode("ascii"), "stop at the requested count"
    assert port.is_open, "the caller still owns the connection"


def test_e4_skip_and_count_damaged_lines(port: serial.Serial) -> None:
    good = (_frame("TMP,23.5,PRS,101.2") + "\r\n").encode("ascii")
    malformed = (_frame("TMP,hot") + "\r\n").encode("ascii")
    port.write(b"$TMP,23.5,PRS,101.2*4F\r\n" + good + malformed
               + b"\xff\r\nwrong-ending\n\r\n" + good)
    expected = {"TMP": 23.5, "PRS": 101.2}
    assert read_frames(port, 2) == ([expected, expected], 5), "count each rejected line once"


def test_e4_zero_count_does_not_read(port: serial.Serial) -> None:
    port.write(b"untouched\r\n")
    assert read_frames(port, 0) == ([], 0), "zero requested frames needs no reads"
    assert port.readline() == b"untouched\r\n", "zero must preserve buffered bytes"


def test_e4_negative_count_does_not_read(port: serial.Serial) -> None:
    port.write(b"untouched\r\n")
    with pytest.raises(ValueError):
        read_frames(port, -1)
    assert port.readline() == b"untouched\r\n", "reject the count before reading"


@pytest.mark.parametrize("raw", [b"", b"bad\r\n", b"partial", b"$TMP,23.5,PRS,101.2*02\r\n"])
def test_e4_propagate_timeout_without_partial_result(port: serial.Serial, raw: bytes) -> None:
    if raw:
        port.write(raw)
    with pytest.raises(TimeoutError):
        read_frames(port, 2)


def test_e4_propagate_connection_failure(port: serial.Serial) -> None:
    port.close()
    with pytest.raises(serial.SerialException):
        read_frames(port, 1)


def test_e5_q1_asynchronous_bus() -> None:
    answers = bus_answers()
    assert isinstance(answers, dict), "Return a dictionary of question IDs and option letters"
    assert set(answers) == {"Q1", "Q2", "Q3", "Q4", "Q5"}, "Return exactly Q1 through Q5"
    if answers.get("Q1") != "C":
        pytest.fail("Q1: reread SparkFun Serial Communication, Synchronous vs. Asynchronous", pytrace=False)


def test_e5_q2_chip_select() -> None:
    if bus_answers().get("Q2") != "B":
        pytest.fail("Q2: reread SparkFun SPI, the chip-select signal discussion", pytrace=False)


def test_e5_q3_address_and_ack() -> None:
    if bus_answers().get("Q3") != "A":
        pytest.fail("Q3: reread SparkFun I2C, the address and ACK message discussion", pytrace=False)


def test_e5_q4_full_duplex() -> None:
    if bus_answers().get("Q4") != "B":
        pytest.fail("Q4: reread SparkFun Serial Communication, Half/Full-Duplex, and SPI data signals", pytrace=False)


def test_e5_q5_usb_adapter_and_baud() -> None:
    if bus_answers().get("Q5") != "C":
        pytest.fail("Q5: reread SparkFun Serial Communication, UARTs and Baud Rate", pytrace=False)
