import re
from pathlib import PurePosixPath


def sanitize_filename(filename: str) -> str:
    """
    Sanitize an uploaded filename to prevent path traversal and shell injection.

    Steps:
    1. Strip any leading path components (handles both / and \\ separators).
    2. Keep only alphanumeric chars, dots, hyphens, and underscores.
    3. Reject filenames that resolve to empty or just dots.

    Returns a safe basename string. Raises ValueError if no safe name can be derived.
    """
    # Normalize separators and take only the final component
    safe = PurePosixPath(filename.replace("\\", "/")).name

    # Strip directory traversal artifacts
    safe = safe.lstrip("./")

    # Allow only safe characters
    safe = re.sub(r"[^\w.\-]", "_", safe)

    if not safe or safe.replace(".", "").replace("_", "") == "":
        raise ValueError(f"Filename '{filename}' is not safe and cannot be sanitized.")

    return safe
