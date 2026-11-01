"""Driver for the station's voltage meter.

The meter replies with a bare decimal number in volts. Unit suffixes are
not part of this station's instrument protocol. Queries do not retry.
"""

import math

from .base import Driver


def _number(reply: str) -> float:
    """Accept surrounding whitespace but reject a nonfinite measurement."""
    value = float(reply.strip())
    if not math.isfinite(value):
        raise ValueError("nonfinite measurement")
    return value


class VoltageMeter(Driver):
    """Measure DC voltage on the meter's selected input.

    DC means direct current: the polarity is steady. This simplified meter
    has one input, so selecting channels is outside the driver contract.
    """

    def read(self) -> float:
        """Return one voltage measurement in volts."""
        return _number(self._query("MEAS:VOLT?"))

    def zero(self) -> None:
        """Ask the meter to clear its stored offset correction."""
        self._write("ZERO")
