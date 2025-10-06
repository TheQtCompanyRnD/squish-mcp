#!/usr/bin/env python3
"""
Squish Context Module

This module handles comprehensive Squish environment analysis and context initialization including:
- Global script analysis and caching
- Test format analysis
- Object reference pattern analysis
- Squish API documentation fetching
- Project-specific rules loading

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

# Auto-import all public functions from the module
from .squish_context_init import *