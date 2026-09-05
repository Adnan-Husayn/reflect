"""RAVDESS evaluation harness for Reflect (PCS26/146).

Produces the four numbers that are currently provisional in
`backend/app/config.py`: `fusion_weight_text`, `fusion_weight_voice`,
`fusion_weight_face` and `conflict_threshold`.
"""

from .filenames import CANONICAL_EMOTIONS, Clip, RavdessFilenameError, parse_filename
from .manifest import ManifestRow, assert_actor_disjoint, build_manifest, read_manifest, write_manifest

__all__ = [
    "CANONICAL_EMOTIONS",
    "Clip",
    "ManifestRow",
    "RavdessFilenameError",
    "assert_actor_disjoint",
    "build_manifest",
    "parse_filename",
    "read_manifest",
    "write_manifest",
]
