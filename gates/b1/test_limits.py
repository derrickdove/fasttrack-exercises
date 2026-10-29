"""Block 1's CSV loader, including operator-facing file errors."""

from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest


HEADER = "name,low,high,unit\n"


def test_limits_loads_csv_as_dictionary_of_limit_records(
    limits: ModuleType, models: ModuleType
) -> None:
    path = Path(__file__).parent / "data" / "limits.csv"
    loaded = limits.load_limits(path)
    assert isinstance(loaded, dict)
    assert loaded == {
        "bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V"),
        "supply_current": models.Limit("supply_current", None, 3.0, "A"),
        "chassis_temperature": models.Limit("chassis_temperature", -20.5, None, "degC"),
    }


def test_limits_accepts_string_path(
    limits: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    path = csv_file(HEADER + "bus_voltage,22,30,V\n")
    assert limits.load_limits(str(path))["bus_voltage"].high == 30.0


@pytest.mark.parametrize(
    "row,expected", [("offset,0,,V\n", (0.0, None)), ("offset,,0,V\n", (None, 0.0))],
    ids=["empty-high", "empty-low"],
)
def test_limits_empty_bound_becomes_none(
    limits: ModuleType, csv_file: Callable[[str], Path],
    row: str, expected: tuple[float | None, float | None],
) -> None:
    limit = limits.load_limits(csv_file(HEADER + row))["offset"]
    assert (limit.low, limit.high) == expected


def test_limits_strips_header_and_all_cells(
    limits: ModuleType, models: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    loaded = limits.load_limits(csv_file(
        " name , low , high , unit \n  bus_voltage  , 22.0 , 30.0 , V \n"
        " supply_current ,  , 3.0 , A \n"
    ))
    assert loaded == {
        "bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V"),
        "supply_current": models.Limit("supply_current", None, 3.0, "A"),
    }


def test_limits_ignores_blank_lines_and_comments_before_and_after_header(
    limits: ModuleType, models: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    loaded = limits.load_limits(csv_file(
        "\n   \n# Station limits\n  # header follows, not a CSV row\n" + HEADER
        + "\n# Bus rail\nbus_voltage,22,30,V\n  \n  # end of limits\n"
    ))
    assert loaded == {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")}


def test_limits_header_only_returns_empty_dictionary(
    limits: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    assert limits.load_limits(csv_file(HEADER)) == {}


def test_limits_handles_quoted_csv_cells(
    limits: ModuleType, models: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    loaded = limits.load_limits(csv_file(HEADER + '"#supply, main",22,30,"volts, DC"\n'))
    assert loaded == {"#supply, main": models.Limit("#supply, main", 22.0, 30.0, "volts, DC")}


@pytest.mark.parametrize("header", [
    "name,low,high", "name,high,low,unit", "label,low,high,unit", "name,low,high,unit,extra"
], ids=["missing-column", "wrong-order", "wrong-name", "extra-column"])
def test_limits_rejects_bad_header(
    bad_limits: Callable[[str, int], None], header: str
) -> None:
    bad_limits(header + "\nbus_voltage,22,30,V\n", 1)


@pytest.mark.parametrize("row", ["bus_voltage,22,30", "bus_voltage,22,30,V,extra"],
                         ids=["too-few", "too-many"])
def test_limits_rejects_wrong_column_count(
    bad_limits: Callable[[str, int], None], row: str
) -> None:
    bad_limits(HEADER + row + "\n", 2)


@pytest.mark.parametrize("row", ["bus_voltage,broken,30,V", "bus_voltage,22,broken,V"],
                         ids=["bad-low", "bad-high"])
def test_limits_rejects_non_numeric_bound(
    bad_limits: Callable[[str, int], None], row: str
) -> None:
    bad_limits(HEADER + row + "\n", 2)


@pytest.mark.parametrize("name", ["", "   "], ids=["empty", "whitespace"])
def test_limits_rejects_empty_name(
    bad_limits: Callable[[str, int], None], name: str
) -> None:
    bad_limits(HEADER + f"{name},22,30,V\n", 2)


def test_limits_rejects_duplicate_names(bad_limits: Callable[[str, int], None]) -> None:
    bad_limits(HEADER + "bus_voltage,22,30,V\nbus_voltage,23,29,V\n", 3)


def test_limits_rejects_duplicate_names_after_stripping(
    bad_limits: Callable[[str, int], None]
) -> None:
    bad_limits(HEADER + " bus_voltage ,22,30,V\nbus_voltage,23,29,V\n", 3)


@pytest.mark.parametrize("row", ["bus_voltage,30,22,V", "bus_voltage,,,V"],
                         ids=["reversed-bounds", "both-bounds-empty"])
def test_limits_wraps_invalid_limit_in_file_error(
    bad_limits: Callable[[str, int], None], row: str
) -> None:
    bad_limits(HEADER + row + "\n", 2)


@pytest.mark.parametrize("row", [
    "rail,nan,,V", "rail,,nan,V", "rail,NaN,30,V", "rail,22,NaN,V", "rail,nan,nan,V",
], ids=["nan-low-only", "nan-high-only", "nan-low", "nan-high", "both-nan"])
def test_limits_rejects_nan_bounds_with_physical_line_number(
    bad_limits: Callable[[str, int], None], row: str,
) -> None:
    bad_limits("# station\n" + HEADER + "bus_voltage,22,30,V\n\n" + row + "\n", 5)


def test_limits_error_counts_physical_lines_including_comments_and_blanks(
    bad_limits: Callable[[str, int], None]
) -> None:
    content = "# station\n\n" + HEADER + "bus_voltage,22,30,V\n\n"
    content += "# current\n\n# range\n\n# next reading\n\nsupply_current,,broken,A\n"
    bad_limits(content, 12)


def test_limit_file_error_is_exception(limits: ModuleType) -> None:
    assert issubclass(limits.LimitFileError, Exception)


def test_limits_rejects_file_without_header(
    limits: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    with pytest.raises(limits.LimitFileError):
        limits.load_limits(csv_file(""))


def test_limits_ignores_comment_with_csv_punctuation(
    limits: ModuleType, models: ModuleType, csv_file: Callable[[str], Path]
) -> None:
    loaded = limits.load_limits(csv_file(
        '# operator note,"unfinished quote\n' + HEADER + 'bus_voltage,22,30,V\n'
    ))
    assert loaded == {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")}
