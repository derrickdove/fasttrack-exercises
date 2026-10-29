"""Station records, TOML wiring checks, and deterministic setup ordering."""

from dataclasses import FrozenInstanceError, fields, is_dataclass

import pytest


@pytest.mark.parametrize("record,values", [
    ("Instrument", {"id": "psu1", "kind": "psu", "resource": "GPIB::1::INSTR"}),
    ("Uut", {"id": "uut1", "psu": "psu1", "psu_channel": 1, "dmm": "dmm1"}),
    ("StationConfig", {"name": "bench-1", "instruments": {}, "uuts": {}}),
])
def test_config_records_have_contract_fields_and_are_frozen(config, record, values):
    cls = getattr(config, record)
    instance = cls(**values)
    assert is_dataclass(instance), f"{record} must be a dataclass"
    assert [field.name for field in fields(instance)] == list(values)
    assert instance == cls(*values.values())
    for field, expected in values.items():
        assert getattr(instance, field) == expected
        with pytest.raises(FrozenInstanceError):
            setattr(instance, field, expected)


@pytest.mark.parametrize("string_path", [False, True], ids=["path-object", "path-string"])
def test_load_config_returns_named_instruments_and_uuts(config, station_file, station_text, string_path):
    path = station_file(station_text)
    loaded = config.load_station_config(str(path) if string_path else path)
    assert loaded == config.StationConfig(
        "Banc électrique",
        {"psu1": config.Instrument("psu1", "psu", "TCPIP::10.0.0.5::5025::SOCKET"),
         "dmm1": config.Instrument("dmm1", "dmm", "TCPIP::10.0.0.6::5025::SOCKET")},
        {"uut1": config.Uut("uut1", "psu1", 1, "dmm1")},
    )


@pytest.mark.parametrize("station", ["", "[station]\n", '[station]\nname = ""\n'],
                         ids=["no-station", "no-name", "empty-name"])
def test_config_rejects_missing_station_name(config, station_file, station_text, station):
    rest = station_text[station_text.index("[[instruments]]"):]
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(station + rest))


def test_config_rejects_duplicate_instrument_ids(config, station_file, station_text):
    bad = station_text + '\n[[instruments]]\nid = "psu1"\nkind = "psu"\nresource = "GPIB::9::INSTR"\n'
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


def test_config_rejects_duplicate_resources_across_kinds(config, station_file, station_text):
    bad = station_text.replace("TCPIP::10.0.0.6::5025::SOCKET", "TCPIP::10.0.0.5::5025::SOCKET")
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


def test_config_rejects_unknown_instrument_kind(config, station_file, station_text):
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(station_text.replace('kind = "psu"', 'kind = "scope"')))


def test_config_rejects_duplicate_uut_ids(config, station_file, station_text):
    bad = station_text + '\n[[uuts]]\nid = "uut1"\npsu = "psu1"\npsu_channel = 2\ndmm = "dmm1"\n'
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


@pytest.mark.parametrize("field,old", [("psu", "psu1"), ("dmm", "dmm1")])
def test_config_rejects_unknown_instrument_reference(config, station_file, station_text, field, old):
    bad = station_text.replace(f'{field} = "{old}"', f'{field} = "missing"')
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


@pytest.mark.parametrize("field,old,wrong", [("psu", "psu1", "dmm1"), ("dmm", "dmm1", "psu1")])
def test_config_rejects_reference_to_wrong_instrument_kind(config, station_file, station_text, field, old, wrong):
    bad = station_text.replace(f'{field} = "{old}"', f'{field} = "{wrong}"')
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


@pytest.mark.parametrize("channel", [0, 4])
def test_config_rejects_psu_channel_outside_one_to_three(config, station_file, station_text, channel):
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(station_text.replace("psu_channel = 1", f"psu_channel = {channel}")))


@pytest.mark.parametrize("channel", [1, 2, 3])
def test_config_accepts_each_psu_channel(config, station_file, station_text, channel):
    loaded = config.load_station_config(station_file(station_text.replace("psu_channel = 1", f"psu_channel = {channel}")))
    assert loaded.uuts["uut1"].psu_channel == channel


def test_config_rejects_two_uuts_on_same_psu_channel(config, station_file, station_text):
    bad = station_text + '\n[[uuts]]\nid = "uut2"\npsu = "psu1"\npsu_channel = 1\ndmm = "dmm1"\n'
    with pytest.raises(config.ConfigError):
        config.load_station_config(station_file(bad))


def test_config_allows_shared_dmm_distinct_channels_and_same_channel_on_other_psu(config, station_file, station_text):
    extra = '\n[[instruments]]\nid = "psu2"\nkind = "psu"\nresource = "GPIB::2::INSTR"\n'
    extra += '\n[[uuts]]\nid = "uut2"\npsu = "psu1"\npsu_channel = 2\ndmm = "dmm1"\n'
    extra += '\n[[uuts]]\nid = "uut3"\npsu = "psu2"\npsu_channel = 1\ndmm = "dmm1"\n'
    loaded = config.load_station_config(station_file(station_text + extra))
    assert loaded.uuts == {
        "uut1": config.Uut("uut1", "psu1", 1, "dmm1"),
        "uut2": config.Uut("uut2", "psu1", 2, "dmm1"),
        "uut3": config.Uut("uut3", "psu2", 1, "dmm1"),
    }


def test_config_allows_station_without_instruments_or_uuts(config, station_file):
    loaded = config.load_station_config(station_file('[station]\nname = "empty-bench"\n'))
    assert loaded == config.StationConfig("empty-bench", {}, {})


def test_setup_order_places_psus_before_dmms_and_sorts_ids_within_kind(config):
    instruments = {
        name: config.Instrument(name, kind, f"GPIB::{index}::INSTR")
        for index, (name, kind) in enumerate([
            ("a_dmm", "dmm"), ("z_psu", "psu"), ("z_dmm", "dmm"), ("b_psu", "psu"),
        ], 1)
    }
    station = config.StationConfig("bench-1", instruments, {})
    assert config.setup_order(station) == ["b_psu", "z_psu", "a_dmm", "z_dmm"]


def test_setup_order_for_empty_station_is_empty_list(config):
    assert config.setup_order(config.StationConfig("bench-1", {}, {})) == []
