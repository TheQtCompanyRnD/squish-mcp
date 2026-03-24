"""Validation helpers for analysis entrypoints."""

import os

from squish_mcp.errors import AnalysisException


def require_suite_directory(test_suite_path: str) -> str:
    """Return a validated absolute suite directory path.

    Args:
        test_suite_path: Candidate path for a Squish suite directory.

    Returns:
        Absolute suite directory path.

    Raises:
        AnalysisException: If the path is missing, does not exist, is not a
            directory, or does not use the `suite_` naming convention.
    """
    if not test_suite_path:
        raise AnalysisException("test_suite_path is required.")

    suite_path = os.path.abspath(test_suite_path)

    if not os.path.exists(suite_path):
        raise AnalysisException(f"Invalid test_suite_path: path does not exist: {suite_path}")
    if not os.path.isdir(suite_path):
        raise AnalysisException(f"Invalid test_suite_path: expected a directory, got: {suite_path}")
    if not os.path.basename(suite_path).startswith("suite_"):
        raise AnalysisException(
            f"Invalid test_suite_path: directory name must start with 'suite_': {os.path.basename(suite_path)}"
        )

    return suite_path
