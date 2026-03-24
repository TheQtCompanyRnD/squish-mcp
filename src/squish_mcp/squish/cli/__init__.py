"""
Squish CLI Module - Shared Configuration and Utilities

This module provides shared configuration for all Squish CLI tools including:
- Squish installation paths
- Default host/port settings
- Common utilities and constants
"""

import os

from pathlib import Path

from squish_mcp.errors import ConfigurationException


# =============================================================================
# SQUISH INSTALLATION CONFIGURATION
# =============================================================================

# Squish installation directory - can be overridden via environment variable - SET THIS VARIABLE
SQUISH_PREFIX = os.getenv("SQUISH_PREFIX", "")

# Squish executable paths
SQUISH_RUNNER = os.getenv("SQUISH_RUNNER", f"{SQUISH_PREFIX}/bin/squishrunner")
SQUISH_SERVER = os.getenv("SQUISH_SERVER", f"{SQUISH_PREFIX}/bin/squishserver")

# =============================================================================
# DEFAULT NETWORK CONFIGURATION
# =============================================================================

# Default squishserver settings
DEFAULT_HOST = "localhost"
DEFAULT_PORT = "4322"

# =============================================================================
# GLOBAL SCRIPT DIRECTORIES
# =============================================================================

# Global script directories - can be configured per project - SET THIS VARIABLE
GLOBAL_SCRIPT_DIRS = [os.getenv("SQUISH_GLOBAL_SCRIPTS", "")]

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

# Project-specific rules file (repository root)
SQUISH_RULES_FILE = str(Path(__file__).resolve().parent.parent.parent / "SQUISH-RULES.yaml")

# =============================================================================
# COMMON UTILITIES
# =============================================================================


def validate_squish_installation() -> None:
    """Validate that Squish is properly installed and accessible.

    Raises:
        ConfigurationException: If Squish directory or executables are not found.
    """
    if not os.path.exists(SQUISH_PREFIX):
        raise ConfigurationException(f"Squish directory not found: {SQUISH_PREFIX}")

    if not os.path.isfile(SQUISH_RUNNER):
        raise ConfigurationException(f"squishrunner not found: {SQUISH_RUNNER}")

    if not os.path.isfile(SQUISH_SERVER):
        raise ConfigurationException(f"squishserver not found: {SQUISH_SERVER}")
