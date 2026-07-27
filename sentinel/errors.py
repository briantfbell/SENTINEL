"""Shared exception vocabulary.

Root-level so every layer can raise domain-specific errors without a
circular dependency; the import contract in AGENTS.md section 6 governs
the layer tree and does not restrict modules outside it.
"""


class SentinelError(Exception):
    """Base class for every Sentinel domain exception."""
