"""Connect a chassis test station to simulated instruments."""

from contextlib import closing

import pyvisa
from pyvisa.resources import MessageBasedResource


def open_resource(resource_name: str, sim_file: str) -> MessageBasedResource:
    """Open the named simulated instrument with newline endings and a 2000 ms timeout."""
    raise NotImplementedError("E1: Open a resource using the supplied simulation file")


def identify(resource: MessageBasedResource) -> dict[str, str]:
    """Query *IDN?; return four stripped, nonempty identification fields."""
    raise NotImplementedError("E2: Query and parse the instrument identification")


def read_voltage(resource: MessageBasedResource) -> float:
    """Query MEAS:VOLT:DC? and convert the reply to volts as a float."""
    raise NotImplementedError("E3: Query the DC voltage and convert the reply")


def list_instruments(sim_file: str) -> list[str]:
    """Return sorted resource names from the simulation, then close the manager."""
    raise NotImplementedError("E4: List the simulation's available resource names")
