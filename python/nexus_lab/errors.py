class NexusError(Exception):
    """Expected operational failure suitable for a CLI response."""


class BoundaryError(NexusError):
    """A path or operation escaped its authorized security zone."""


class IntegrityError(NexusError):
    """An integrity or ledger verification failed."""


class AuthorizationError(NexusError):
    """No applicable authorization exists for the requested action."""

