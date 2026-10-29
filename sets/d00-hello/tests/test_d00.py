import pytest

from starter.hello import station_greeting


@pytest.mark.parametrize("name", ["A1", "bench 2", ""])
def test_e1_greeting(name: str) -> None:
    expected = f"Hello from test station {name}"
    got = station_greeting(name)
    assert got == expected, f"for station {name!r} expected {expected!r}, got {got!r}"
