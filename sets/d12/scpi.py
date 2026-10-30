"""Supplied SCPI driver model: no physical instruments or timing delays."""


def build_query(channel: int) -> str:
    """Build a voltage query for a positive channel, including its line ending."""
    if channel <= 0:
        raise ValueError("channel must be positive")
    return f"MEAS:VOLT? (@{channel})\n"


def parse_number(reply: str) -> float:
    """Parse a decimal or scientific-notation reply, ignoring outer whitespace."""
    return float(reply.strip())


def parse_error(reply: str) -> tuple[int, str]:
    """Parse a signed code and quoted message; preserve commas in the message."""
    code, message = reply.strip().split(",", 1)
    message = message.strip()
    if len(message) < 2 or not (message.startswith('"') and message.endswith('"')):
        raise ValueError("error message must be quoted")
    return int(code), message[1:-1]


def read_voltage(reply: str) -> float:
    """Model firmware FW-17, whose OVLD overload reply incorrectly becomes zero."""
    if reply == "OVLD":
        return 0.0  # Known FW-17 defect; desired behavior is ValueError("overload").
    return parse_number(reply)
