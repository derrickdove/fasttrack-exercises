"""Write station tests here; add the decorators described in the README."""
import pytest

from scpi import build_query, parse_error, parse_number, read_voltage


def test_e1_number_reply(reply: str, expected: float) -> None:
    """E1: Parametrize at least the six required voltage reply formats."""
    raise NotImplementedError("E1: add number cases and assert the parsed voltage")


def test_e2_error_reply(reply: str, expected: tuple[int, str]) -> None:
    """E2: Parametrize the four error replies with explicit readable ids."""
    raise NotImplementedError("E2: add named error cases and assert code and message")


def test_e3_station_sweep() -> None:
    """E3: Mark this slow and check voltage-query text for channels 1, 2, 3."""
    raise NotImplementedError("E3: mark the sweep slow and check each command")


def test_e4_overload_quirk() -> None:
    """E4: Expect ValueError for OVLD, with a strict reasoned xfail for FW-17."""
    raise NotImplementedError("E4: document FW-17 with xfail and test desired behavior")
