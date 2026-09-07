"""Self-report instrument definitions.

An instrument is only accepted once it is defined here. Accepting a score for
an instrument the server cannot itself compute would leave exactly the hole
this package closes: a client-supplied number nobody can check.
"""

from app.instruments.gad7 import GAD7
from app.instruments.phq8 import PHQ8

INSTRUMENTS = {PHQ8.code: PHQ8, GAD7.code: GAD7}

__all__ = ["GAD7", "INSTRUMENTS", "PHQ8"]
