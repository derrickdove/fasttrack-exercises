import pytest

from starter.collections_basics import (
    ascending_readings,
    average_reading,
    channels_over_limit,
    collection_answers,
    count_statuses,
    largest_reading,
    last_reading,
    lookup_status,
    make_readings,
    reading_count,
    readings_above,
    record_channels,
    smallest_reading,
    sorted_channels,
    total_readings,
    unique_channels,
)


def _failure(call: str, expected: object, got: object) -> str:
    message = f"{call}: expected {expected!r}, got {got!r}."
    if got is None:
        message += (
            " your function returned None: did you forget `return`?"
            " Printing a result does not return it."
        )
    return message


@pytest.mark.parametrize(
    "first,second,third,expected",
    [
        (1.0, 2.0, 3.0, [1.0, 2.0, 3.0]),
        (0.0, 0.0, 4.5, [0.0, 0.0, 4.5]),
        (7.5, -2.0, 1.0, [7.5, -2.0, 1.0]),
    ],
)
def test_e1_append_readings(
    first: float, second: float, third: float, expected: list[float]
) -> None:
    got = make_readings(first, second, third)
    assert got == expected, _failure(
        f"make_readings({first!r}, {second!r}, {third!r})", expected, got
    )


@pytest.mark.parametrize("values,expected", [([2.5, 4.0, 3.0], 3.0), ([7.5], 7.5)])
def test_e2_last_reading(values: list[float], expected: float) -> None:
    before = values.copy()
    got = last_reading(values)
    call = f"last_reading({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize("values,expected", [([2.5, 4.0, 3.0], 3), ([7.5], 1), ([], 0)])
def test_e2_reading_count(values: list[float], expected: int) -> None:
    before = values.copy()
    got = reading_count(values)
    call = f"reading_count({before!r})"
    assert type(got) is int, _failure(call, "an int count (whole number)", got)
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize(
    "values,limit,expected",
    [
        ([7.0, 5.0, 6.0, 6.0, 4.0], 5.0, [7.0, 6.0, 6.0]),
        ([7.0, 6.0], 5.0, [7.0, 6.0]),
        ([1.0, 2.0], 3.0, []),
        ([-1.0, -3.0, 0.0], -2.0, [-1.0, 0.0]),
        ([], 5.0, []),
    ],
)
def test_e3_filter_readings(
    values: list[float], limit: float, expected: list[float]
) -> None:
    before = values.copy()
    got = readings_above(values, limit)
    call = f"readings_above({before!r}, {limit!r})"
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)
    assert got is not values, _failure(call, "a separate new list", got)


@pytest.mark.parametrize(
    "values,expected", [([3.0, 1.0, 2.0], 1.0), ([-2.0, 0.0, -2.0], -2.0), ([4.5], 4.5)]
)
def test_e4_smallest_reading(values: list[float], expected: float) -> None:
    before = values.copy()
    got = smallest_reading(values)
    call = f"smallest_reading({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize(
    "values,expected", [([3.0, 1.0, 2.0], 3.0), ([-2.0, 0.0, -2.0], 0.0), ([4.5], 4.5)]
)
def test_e4_largest_reading(values: list[float], expected: float) -> None:
    before = values.copy()
    got = largest_reading(values)
    call = f"largest_reading({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize(
    "values,expected", [([3.0, 1.0, 2.0], 6.0), ([-2.0, 0.0, -2.0], -4.0), ([4.5], 4.5)]
)
def test_e4_total_readings(values: list[float], expected: float) -> None:
    before = values.copy()
    got = total_readings(values)
    call = f"total_readings({before!r})"
    assert got == pytest.approx(expected), _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize(
    "values,expected",
    [([2.0, 5.0], 3.5), ([1.0, 1.0, 2.0], 4.0 / 3.0), ([-2.0, 2.0, 0.0], 0.0), ([4.5], 4.5)],
)
def test_e5_average_reading(values: list[float], expected: float) -> None:
    before = values.copy()
    got = average_reading(values)
    call = f"average_reading({before!r})"
    assert got == pytest.approx(expected), _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)


@pytest.mark.parametrize(
    "statuses,name,expected",
    [
        ({"BUS_V": "READY", "TEMP_C": "WAIT"}, "BUS_V", "READY"),
        ({"BUS_V": "READY", "TEMP_C": "WAIT"}, "TEMP_C", "WAIT"),
        ({"BUS_V": "READY"}, "READY", "UNKNOWN"),
        ({"BUS_V": "READY"}, "bus_v", "UNKNOWN"),
        ({}, "BUS_V", "UNKNOWN"),
    ],
)
def test_e6_lookup_status(statuses: dict[str, str], name: str, expected: str) -> None:
    before = statuses.copy()
    got = lookup_status(statuses, name)
    call = f"lookup_status({before!r}, {name!r})"
    assert got == expected, _failure(call, expected, got)
    assert statuses == before, _failure(f"input after {call}", before, statuses)


@pytest.mark.parametrize(
    "statuses,expected",
    [
        (["PASS", "FAIL", "PASS"], {"PASS": 2, "FAIL": 1}),
        (["READY", "READY"], {"READY": 2}),
        (["PASS", "FAIL", "WAIT", "FAIL", "PASS"], {"PASS": 2, "FAIL": 2, "WAIT": 1}),
        (["WAIT"], {"WAIT": 1}),
        ([], {}),
    ],
)
def test_e7_count_statuses(statuses: list[str], expected: dict[str, int]) -> None:
    before = statuses.copy()
    got = count_statuses(statuses)
    call = f"count_statuses({before!r})"
    assert isinstance(got, dict), _failure(call, "a dictionary of int counts", got)
    for status, count in got.items():
        assert type(count) is int, _failure(
            f"{call} count for {status!r}", "an int count (whole number)", count
        )
    assert got == expected, _failure(call, expected, got)
    assert statuses == before, _failure(f"input after {call}", before, statuses)


@pytest.mark.parametrize(
    "readings,limit,expected",
    [
        ({"TEMP_C": 6.0, "BUS_V": 5.0, "AUX_V": 7.0}, 5.0, ["TEMP_C", "AUX_V"]),
        ({"BUS_V": 5.0}, 5.0, []),
        ({"BUS_V": 4.0}, 5.0, []),
        ({"TEMP_C": -1.0, "BUS_V": -3.0}, -2.0, ["TEMP_C"]),
        ({}, 5.0, []),
    ],
)
def test_e8_channels_over_limit(
    readings: dict[str, float], limit: float, expected: list[str]
) -> None:
    before = readings.copy()
    got = channels_over_limit(readings, limit)
    call = f"channels_over_limit({before!r}, {limit!r})"
    assert got == expected, _failure(call, expected, got)
    assert readings == before, _failure(f"input after {call}", before, readings)


@pytest.mark.parametrize(
    "records,expected",
    [
        ([{"channel": "BUS_V", "status": "PASS"}, {"channel": "TEMP_C", "status": "FAIL"}], ["BUS_V", "TEMP_C"]),
        ([{"channel": "BUS_V"}, {"channel": "BUS_V"}], ["BUS_V", "BUS_V"]),
        ([{"status": "WAIT", "channel": "AUX_V"}], ["AUX_V"]),
        ([], []),
    ],
)
def test_e9_record_channels(records: list[dict[str, str]], expected: list[str]) -> None:
    before = [record.copy() for record in records]
    got = record_channels(records)
    call = f"record_channels({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert records == before, _failure(f"input after {call}", before, records)
    assert got is not records, _failure(call, "a separate new list", got)


@pytest.mark.parametrize(
    "values,expected",
    [([3.0, 1.0, 2.0], [1.0, 2.0, 3.0]), ([2.0, -1.0, 2.0], [-1.0, 2.0, 2.0]), ([4.5], [4.5])],
)
def test_e10_ascending_readings(values: list[float], expected: list[float]) -> None:
    before = values.copy()
    got = ascending_readings(values)
    call = f"ascending_readings({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert values == before, _failure(f"input after {call}", before, values)
    assert got is not values, _failure(call, "a separate new list", got)


@pytest.mark.parametrize(
    "channels,expected",
    [([3, 1, 3, 2], [1, 2, 3, 3]), ([1, 2], [1, 2]), ([4], [4]), ([], [])],
)
def test_e10_sorted_copy(channels: list[int], expected: list[int]) -> None:
    before = channels.copy()
    got = sorted_channels(channels)
    call = f"sorted_channels({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert channels == before, _failure(f"input after {call}", before, channels)
    assert got is not channels, _failure(call, "a separate new list, not an alias", got)


@pytest.mark.parametrize(
    "channels,expected",
    [([3, 1, 3, 2, 1], [1, 2, 3]), ([4, 4, 4], [4]), ([7, 2, 5], [2, 5, 7]), ([4], [4]), ([], [])],
)
def test_e11_unique_channels(channels: list[int], expected: list[int]) -> None:
    before = channels.copy()
    got = unique_channels(channels)
    call = f"unique_channels({before!r})"
    assert got == expected, _failure(call, expected, got)
    assert channels == before, _failure(f"input after {call}", before, channels)
    assert got is not channels, _failure(call, "a separate new list", got)


@pytest.mark.parametrize(
    "question,expected,reminder",
    [
        ("Q1", "B", "a key check before lookup; reread E6"),
        ("Q2", "C", "a last-item index for a nonempty list; reread E2"),
        ("Q3", "A", "a comparison using the count; reread E2"),
    ],
    ids=["Q1", "Q2", "Q3"],
)
def test_e12_collection_quiz(question: str, expected: str, reminder: str) -> None:
    answers = collection_answers()
    if not isinstance(answers, dict):
        pytest.fail(
            _failure("collection_answers()", "a dictionary with keys Q1, Q2, Q3", answers),
            pytrace=False,
        )
    if question not in answers:
        pytest.fail(
            f"collection_answers() {question}: answer missing; choose one option letter. "
            f"Think about {reminder}.",
            pytrace=False,
        )
    chosen = answers[question]
    if chosen != expected:
        pytest.fail(
            f"collection_answers() {question}: got {chosen!r}; expected an option letter "
            f"that fixes this problem. Think about {reminder}.",
            pytrace=False,
        )
    if set(answers) != {"Q1", "Q2", "Q3"}:
        pytest.fail(
            "collection_answers(): expected exactly the keys Q1, Q2, Q3; "
            "remove extra question keys.",
            pytrace=False,
        )
