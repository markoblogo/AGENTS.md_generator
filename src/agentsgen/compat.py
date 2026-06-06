from __future__ import annotations

from .generated_artifacts import handle_generated_json_artifact
from .patch_engine import (
    FileResult as _FileResult,
    generated_sibling_path,
    handle_file,
    unified_diff,
    write_or_diff,
)

# Deprecated compatibility exports for older callers and tests.
FileResult = _FileResult
_handle_generated_json_file = handle_generated_json_artifact
_handle_file = handle_file
_write_or_diff = write_or_diff
_generated_sibling_path = generated_sibling_path
_unified_diff = unified_diff
