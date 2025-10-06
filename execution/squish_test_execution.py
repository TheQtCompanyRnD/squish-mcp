#!/usr/bin/env python3
"""
Squish Test Execution Module

This module provides the main test execution functions for Squish test automation.
It serves as the execution layer that orchestrates calls to the CLI interface.

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

from typing import Dict

# Import functions from CLI module
from cli.squishrunner_cli import (
    run_test as cli_run_test
)

def run_test(test_suite_path: str, context: Dict, test_path: str = "", 
             suite_or_test_case: str = 'suite') -> Dict:
    """
    Run a Squish test suite or test case through the execution layer.
    
    This function serves as the main execution entry point and delegates
    to the CLI interface for the actual test execution.
    
    Args:
        test_suite_path: Absolute path to the test suite
        context: Dictionary of context variables for the test
        test_path: Optional path to specific test case
        suite_or_test_case: Either 'suite' or 'case'
    
    Returns:
        Dict with execution results from CLI layer
    """
    return cli_run_test(test_suite_path, context, test_path, suite_or_test_case)

