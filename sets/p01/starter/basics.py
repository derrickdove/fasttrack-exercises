"""Small value and text helpers for a test station."""


def station_label() -> str:
    """Return the fixed station label."""
    raise NotImplementedError("E1: Return the fixed station label")


def millivolts_to_volts(millivolts: float) -> float:
    """Return a millivolt reading converted to volts."""
    raise NotImplementedError("E2: Divide millivolts by one thousand")


def channel_label(channel: int, volts: float) -> str:
    """Return a channel label for a reading already in volts."""
    raise NotImplementedError("E3: Build a channel label with an f-string")


def clean_operator(entry: str) -> str:
    """Return the operator entry stripped and uppercase."""
    raise NotImplementedError("E4: Strip the entry then make it uppercase")


def serial_length(serial: str) -> int:
    """Return the number of characters in a serial number."""
    raise NotImplementedError("E5: Return the serial number length")


def first_character(serial: str) -> str:
    """Return the first character of a nonempty serial number."""
    raise NotImplementedError("E6: Return the first character")


def last_character(serial: str) -> str:
    """Return the last character of a nonempty serial number."""
    raise NotImplementedError("E6: Return the last character")


def model_prefix(model: str) -> str:
    """Return the first three characters of a model name."""
    raise NotImplementedError("E7: Slice out the first three model characters")


def reading_field(reply: str) -> str:
    """Return the middle text field of a three-field comma reply."""
    raise NotImplementedError("E8: Split the reply and pick the reading text")


def parse_channel(text: str) -> int:
    """Return a whole channel number converted from text."""
    raise NotImplementedError("E9: Convert channel text to an integer")


def parse_voltage(text: str) -> float:
    """Return a voltage converted from numeric text."""
    raise NotImplementedError("E9: Convert voltage text to a float")


def reading_value(reply: str) -> float:
    """Return the numeric reading from a channel=value reply with a newline."""
    raise NotImplementedError("E10: Clean and split the reply then convert its reading")


def status_message(channel: int, millivolts: float) -> str:
    """Return a channel status line with the millivolt reading shown in volts."""
    raise NotImplementedError("E11: Convert millivolts then label the channel reading")


def error_answers() -> dict[str, str]:
    """Return Q1 through Q3 paired with the chosen uppercase quiz letters."""
    raise NotImplementedError("E12: Choose the cause of each error in the README")
