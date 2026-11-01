"""Driver for the 0 through 30 volt bench supply.

The supply's readback is a bare decimal in volts. Writing a voltage does
not enable the output; operators control that separately with enable().
"""

import math

from .base import Driver


def _number(reply: str) -> float:
    """Accept surrounding whitespace but reject a nonfinite measurement."""
    value = float(reply.strip())
    if not math.isfinite(value):
        raise ValueError("nonfinite measurement")
    return value


class PowerSupply(Driver):
    """Set voltage and measure the supply's own output readback."""

    def set_voltage(self, voltage_v: float) -> None:
        """Set a finite voltage in the inclusive range 0 through 30 volts."""
        if not math.isfinite(voltage_v) or not 0 <= voltage_v <= 30:
            raise ValueError("voltage outside 0 through 30 V")
        self._write(f"VOLT {voltage_v:.3f}")

    def enable(self, enabled: bool) -> None:
        """Switch the output without changing its programmed voltage."""
        self._write("OUTP ON" if enabled else "OUTP OFF")

    def read(self) -> float:
        """Return one voltage readback in volts."""
        return _number(self._query("MEAS:VOLT?"))
