"""UUID generation utilities."""

import uuid


def generate_request_id() -> str:
    """
    Generate a unique request ID.

    Returns:
        str: Request ID in format 'req_<uuid>'
    """
    return f"req_{uuid.uuid4().hex[:12]}"


def generate_error_request_id() -> str:
    """
    Generate a unique error request ID.

    Returns:
        str: Error request ID in format 'req_error_<uuid>'
    """
    return f"req_error_{uuid.uuid4().hex[:8]}"