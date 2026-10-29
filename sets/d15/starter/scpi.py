"""Small text/byte helpers for a test station's instrument commands."""


def encode_command(cmd: str, term: str = "\n") -> bytes:
    """E1: Return ASCII command bytes ending in exactly one nonempty term."""
    raise NotImplementedError("E1: Encode ASCII and keep exactly one trailing terminator")


def decode_reply(data: bytes, term: str = "\n") -> str:
    """E2: Decode ASCII, remove one trailing term, then strip whitespace."""
    raise NotImplementedError("E2: Decode a reply and translate decoding errors to ValueError")


def build(
    header: str,
    *args: str | int | float | bool,
    channels: list[int] | None = None,
) -> str:
    """E3: Join a header, comma-separated values, and an optional channel list."""
    raise NotImplementedError("E3: Format values and optional channels as SCPI text")


def is_query(cmd: str) -> bool:
    """E4: Check whether the first whitespace-separated token ends with ?."""
    raise NotImplementedError("E4: Inspect the command header for a query marker")


def short_form(header: str) -> str:
    """E4: Remove lowercase ASCII letters from a mixed-case SCPI header."""
    raise NotImplementedError("E4: Keep the uppercase short form, digits, and punctuation")
