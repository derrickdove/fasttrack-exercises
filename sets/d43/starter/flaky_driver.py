"""Repair four station defects; legacy snippets below are evidence, not working code."""

from collections.abc import Callable


def voltage_in_volts(reply: str) -> float:
    """E1: Convert a unit-tagged reply into finite volts; reject invalid replies.

    Legacy bug:
        number, unit = reply.split()
        return float(number)  # assumes every reply uses volts
    """
    raise NotImplementedError("E1: compare the reply unit with the datasheet")


def query_voltage(
    exchange: Callable[[str, float | None], str], timeout_s: float = 0.25
) -> str:
    """E2: Validate a finite positive timeout, then make one bounded query.

    Legacy bug:
        return exchange("MEAS:VOLT?", None)  # None permits waiting forever
    """
    raise NotImplementedError("E2: pass a bounded timeout to the instrument exchange")


def missing_samples(counters: list[int], modulus: int = 256) -> int:
    """E3: Count missing forward samples, accounting for duplicate counters and wrap.

    Legacy bug:
        return sum(max(0, b - a - 1) for a, b in zip(counters, counters[1:]))
    """
    raise NotImplementedError("E3: account for the counter wrapping back to zero")


def powered_sample(write: Callable[[str], None], sample: Callable[[], float]) -> float:
    """E4: Enable output, sample once, and always attempt to disable the output.

    Legacy bug:
        write("OUTP ON")
        value = sample()
        write("OUTP OFF")
        return value
    """
    raise NotImplementedError("E4: guarantee output cleanup when the test step raises")
