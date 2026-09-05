"""Self-report instrument definitions.

An instrument is only accepted once it is defined here. Accepting a score for
an instrument the server cannot itself compute would leave exactly the hole
this package closes: a client-supplied number nobody can check.
"""

from app.instruments.phq8 import PHQ8

INSTRUMENTS = {PHQ8.code: PHQ8}

__all__ = ["INSTRUMENTS", "PHQ8"]
