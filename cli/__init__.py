#!/usr/bin/env python3
"""
Squish CLI Module - Shared Configuration and Utilities

This module provides shared configuration for all Squish CLI tools including:
- Squish installation paths
- Default host/port settings
- Common utilities and constants

All CLI modules (squishrunner_cli, squishserver_cli) import from this module
to ensure consistent configuration across the codebase.

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import os
from typing import List, Optional

# =============================================================================
# SQUISH INSTALLATION CONFIGURATION
# =============================================================================

# Squish installation directory - can be overridden via environment variable
SQUISH_DIR = os.getenv('SQUISH_DIR', "/Applications/Froglogic/squish-9.0.0-for-qt68x/bin")

# Squish executable paths
SQUISH_RUNNER = os.getenv('SQUISH_RUNNER', f"{SQUISH_DIR}/squishrunner")
SQUISH_SERVER = os.getenv('SQUISH_SERVER', f"{SQUISH_DIR}/squishserver")

# =============================================================================
# DEFAULT NETWORK CONFIGURATION
# =============================================================================

# Default squishserver settings
DEFAULT_HOST = "localhost"
DEFAULT_PORT = "4322"

# =============================================================================
# GLOBAL SCRIPT DIRECTORIES
# =============================================================================

# Global script directories - can be configured per project
GLOBAL_SCRIPT_DIRS = [
    os.getenv('SQUISH_GLOBAL_SCRIPTS', "/Users/aaronlabomascus/dev/Qt/antares/antares/Cluster/test/antares-globals")
]

# =============================================================================
# PROJECT CONFIGURATION
# =============================================================================

# Project-specific rules file
SQUISH_RULES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "SQUISH-RULES.yaml")

# =============================================================================
# COMMON UTILITIES
# =============================================================================

def validate_squish_installation() -> tuple[bool, str]:
    """
    Validate that Squish is properly installed and accessible.
    
    Returns:
        Tuple of (is_valid, message) where is_valid is bool and message is str
    """
    if not os.path.exists(SQUISH_DIR):
        return False, f"Squish directory not found: {SQUISH_DIR}"
    
    if not os.path.isfile(SQUISH_RUNNER):
        return False, f"squishrunner not found: {SQUISH_RUNNER}"
    
    if not os.path.isfile(SQUISH_SERVER):
        return False, f"squishserver not found: {SQUISH_SERVER}"
    
    return True, f"Squish installation validated at: {SQUISH_DIR}"


def format_server_key(host: str, port: str) -> str:
    """
    Create a standardized server key for tracking servers.
    
    Args:
        host: Server host
        port: Server port
    
    Returns:
        Formatted server key string
    """
    return f"{host}:{port}"

# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================

# Validate configuration on import (optional - can be disabled for testing)
_VALIDATE_ON_IMPORT = os.getenv('SQUISH_VALIDATE_ON_IMPORT', '1') == '1'

if _VALIDATE_ON_IMPORT:
    _is_valid, _validation_message = validate_squish_installation()
    if not _is_valid:
        import warnings
        warnings.warn(f"Squish CLI Configuration Warning: {_validation_message}")