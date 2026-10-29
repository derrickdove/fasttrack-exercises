"""Operator commands use only main() and the documented module entry point."""

import json
import sys

import pytest


@pytest.mark.parametrize("value,expected,summary", [(24, 0, "PASS"), (31, 1, "FAIL"), ("nan", 2, "ERROR")],
                         ids=["pass", "fail", "error"])
def test_check_returns_exit_code_and_prints_summary(command, cli, report, themis, models, input_files, capsys,
                                                  value, expected, summary):
    limits, measurements = input_files
    measurements.write_text(f"name,value,unit\nbus_voltage,{value},V\n", encoding="utf-8")
    code = cli.main(command(input_files))
    captured = capsys.readouterr()
    results = themis.check_all([models.Measurement("bus_voltage", float(value), "V")],
                              {"bus_voltage": models.Limit("bus_voltage", 22.0, 30.0, "V")})
    assert code == expected
    assert captured.out.rstrip("\n") == report.summary_text(results).rstrip("\n")
    assert captured.out.startswith(f"OVERALL: {summary} ")
    assert captured.err == ""


@pytest.mark.parametrize("station", [None, "bench-\u03b1"], ids=["default-station", "named-station"])
def test_report_contains_results_and_exact_metadata(command, cli, input_files, tmp_path, capsys, station, monkeypatch):
    monkeypatch.chdir(tmp_path)
    input_files = tuple(path.relative_to(tmp_path) for path in input_files)
    destination = tmp_path / "operator report.json"
    args = command(input_files) + ["--report", str(destination)]
    if station is not None:
        args += ["--station", station]
    assert cli.main(args) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    content = destination.read_text(encoding="utf-8")
    data = json.loads(content)
    assert data["meta"] == {"station": station if station is not None else "unknown",
                            "limits": str(input_files[0]), "measurements": str(input_files[1])}
    assert data["summary"] == {"total": 1, "pass": 1, "fail": 0, "error": 0, "overall": "PASS"}
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert set(result) == {"name", "value", "low", "high", "unit", "status", "message"}
    assert {key: result[key] for key in result if key != "message"} == {
        "name": "bus_voltage", "value": 24.0, "low": 22.0, "high": 30.0, "unit": "V", "status": "PASS",
    }
    assert isinstance(result["message"], str)
    # The existing report contract allows either raw UTF-8 or escaped Unicode.
    assert content.rstrip("\n") in [json.dumps(data, sort_keys=True, indent=2, ensure_ascii=ascii_only)
                                       for ascii_only in [True, False]]


@pytest.mark.parametrize("row,expected,status", [("bus_voltage,31,V", 1, "FAIL"),
                                                ("bus_voltage,24,mV", 2, "ERROR")])
def test_report_is_written_for_fail_and_error(command, cli, input_files, tmp_path, capsys, row, expected, status):
    input_files[1].write_text("name,value,unit\n" + row + "\n", encoding="utf-8")
    destination = tmp_path / "failed.json"
    assert cli.main(command(input_files) + ["--report", str(destination)]) == expected
    assert json.loads(destination.read_text(encoding="utf-8"))["summary"]["overall"] == status
    assert capsys.readouterr().err == ""


def test_nan_measurement_writes_strict_json_error_report(command, cli, input_files, tmp_path, capsys):
    input_files[1].write_text("name,value,unit\nbus_voltage,nan,V\n", encoding="utf-8")
    destination = tmp_path / "nan.json"
    assert cli.main(command(input_files) + ["--report", str(destination)]) == 2
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.startswith("OVERALL: ERROR ")
    document = json.loads(destination.read_text(encoding="utf-8"),
                          parse_constant=lambda token: pytest.fail(f"invalid JSON constant: {token}"))
    assert document["summary"] == {"total": 1, "pass": 0, "fail": 0, "error": 1, "overall": "ERROR"}
    assert len(document["results"]) == 1
    result = document["results"][0]
    assert (result["name"], result["value"], result["low"], result["high"], result["status"]) == (
        "bus_voltage", None, 22.0, 30.0, "ERROR",
    )


def test_main_none_reads_process_arguments(command, cli, input_files, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chassis"] + command(input_files))
    assert cli.main() == 0
    assert capsys.readouterr().out.startswith("OVERALL: PASS ")


def test_python_module_entry_point_checks_files_and_writes_report(command, run_module, input_files, tmp_path):
    destination = tmp_path / "module report.json"
    completed = run_module(command(input_files) + ["--report", str(destination)])
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "OVERALL: PASS (1 pass, 0 fail, 0 error)"
    assert completed.stderr == ""
    assert json.loads(destination.read_text(encoding="utf-8"))["summary"]["overall"] == "PASS"


def test_python_module_entry_point_returns_usage_error(assert_input_error, run_module, ):
    completed = run_module(["check"])
    assert_input_error(completed.returncode, completed.stderr)


@pytest.mark.parametrize("args", [[], ["unknown"], ["check", "--limits", "limits.csv",
                                                        "--measurements", "measurements.csv", "--unknown"]],
                         ids=["no-command", "unknown-command", "unknown-option"])
def test_usage_errors_return_three_with_one_line(assert_input_error, cli, capsys, args):
    code = cli.main(args)
    assert_input_error(code, capsys.readouterr().err)


@pytest.mark.parametrize("index", [0, 1], ids=["missing-limits", "missing-measurements"])
def test_missing_input_file_returns_three_with_one_line(command, assert_input_error, cli, input_files, capsys, index):
    input_files[index].unlink()
    code = cli.main(command(input_files))
    assert_input_error(code, capsys.readouterr().err)


def test_invalid_limits_return_input_error(command, assert_input_error, cli, input_files, capsys):
    input_files[0].write_text("name,low,high,unit\nbus_voltage,30,22,V\n", encoding="utf-8")
    code = cli.main(command(input_files))
    assert_input_error(code, capsys.readouterr().err)


@pytest.mark.parametrize("content", ["name,unit,value\nbus_voltage,V,24\n",
                                      "name,value,unit\nbus_voltage,24\n",
                                      "name,value,unit\nbus_voltage,broken,V\n"],
                         ids=["bad-header", "wrong-column-count", "non-numeric-value"])
def test_invalid_measurement_file_returns_input_error(command, assert_input_error, cli, input_files, capsys, content):
    input_files[1].write_text(content, encoding="utf-8")
    code = cli.main(command(input_files))
    assert_input_error(code, capsys.readouterr().err)


def test_measurement_csv_accepts_quoted_names(command, cli, input_files, capsys):
    input_files[0].write_text('name,low,high,unit\n"bus, main",22,30,V\n', encoding="utf-8")
    input_files[1].write_text('name,value,unit\n"bus, main",24,V\n', encoding="utf-8")
    assert cli.main(command(input_files)) == 0
    assert capsys.readouterr().out.strip() == "OVERALL: PASS (1 pass, 0 fail, 0 error)"
