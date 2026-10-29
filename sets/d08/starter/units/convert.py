def to_base(value: float, unit: str) -> tuple[float, str]:
    """Convert one of the six supported prefixed units; reject other units."""
    raise NotImplementedError("E1: scale the reading and return its base unit")
