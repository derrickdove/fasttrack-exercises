"""E2: add the station's electronic load by following the supplied drivers."""

import math

from .base import Driver


class ElectronicLoad(Driver):
    """Draw a programmed current; read() reports measured current in amperes."""

    def set_current(self, current_a: float) -> None:
        """Program a finite current from 0 through 10 A, including both ends."""
        raise NotImplementedError("E2: validate current and send the formatted CURR command")

    def enable(self, enabled: bool) -> None:
        """Send INPUT ON or INPUT OFF using the inherited write helper."""
        raise NotImplementedError("E2: switch the electronic load input")

    def read(self) -> float:
        """Query MEAS:CURR? and return a finite float in amperes."""
        raise NotImplementedError("E2: query current through the inherited timeout helper")
