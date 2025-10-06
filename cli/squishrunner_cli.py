#!/usr/bin/env python3
"""
Squish Runner CLI Management Module

Handles Squish test execution via squishrunner including:
- Running test suites and test cases
- Managing global script directories
- Configuring test execution parameters
- Generating test reports

IMPORTANT: This file requires Python 3.10+ due to f-string usage and type hints.
Do not use with Python 2.x - it will cause syntax errors.
"""

import subprocess
import os
from typing import Dict, List, Optional

# Import shared configuration
from . import (
    SQUISH_RUNNER, 
    DEFAULT_HOST, 
    DEFAULT_PORT, 
    GLOBAL_SCRIPT_DIRS,
    validate_squish_installation
)

# Import squishserver management functions
from .squishserver_cli import (
    start_squish_server,
    stop_squish_server
)

# Default execution settings
DEBUG_LOG = "paw"
SNOOZE_FACTOR = "1.0"

def run_test(test_suite_path: str, context: Dict, test_path: str = "", 
             suite_or_test_case: str = 'suite') -> Dict:
    """
    Run a Squish test suite or test case.
    You need to figure out the test suite and test case absolute paths on your own, the user should have to provide it.
    Pay careful attention to if a test suite is being asked for (directory prefixed with 'suite_')
        or if a test case is being asked for (directory prefixed with 'tst_')
    This is a wrapper around the squishrunner command line tool.
    
    IMPORTANT PATH HANDLING AND SQUISH TEST NAMING CONVENTIONS:
    - All paths are are absolute paths, but you should figure out what the paths are if not explicitly provided by the user!!!
    - Test suites are named like `suite_<test_suite_name>` - these are folders under the root path
    - Test cases are named like `tst_<test_name>` - these are folders under the test suite path
    - Test files are under the test case folders and are named like `test.py`

    Usage Reference: IMPORTANT
    For test suite invocations, expecting squishrunner calls to look like
        /path/to/squishrunner --testsuite /path/to/testsuite --local --reportgen html,report-dir
    Expecting test case squishrunner commands to look like
        /path/to/squishrunner --host localhost --port 4322 --testcase /path/to/testcase --wrapper Qt --reportgen html,report-dir

    Args:
        test_suite_path: Absolute path to the test suite which you should figure out on your own
                        Example: "/Users/yourname/projects/addressbook/suite_py"
        context: Dictionary variables of options to pass to Squish
                Format: {"VAR_NAME": "value"}
        test_path: Absolute path to the test case from test_suite_path. If provided also the test suite path needs to be provided.
                  Example: "/Users/yourname/projects/addressbook/suite_py/tst_general"
        suite_or_test_case: 'suite' or 'case' are the only valid options
                If the user requests for a test case or only a single test beginning in "tst_" then use 'case'
                If the user requests for a test suite or a reference directory beginning with "suite_" than use 'suite'
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str   # Contains stdout for success, error message for failure
        }

    Example Usage:
        result = run_test(
            test_path="/Users/yourname/projects/addressbook/suite_py/tst_general",
            test_suite_path="/Users/yourname/projects/addressbook/suite_py",
            context={},
            'suite'
        )
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg
        }

    squish_config = {
        "squishrunner": SQUISH_RUNNER,
        "host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "debugLog": DEBUG_LOG
    } 
    
    # Validate paths
    if test_path and not os.path.exists(test_path):
        return {
            "status": 1,
            "message": f"Test path does not exist: {test_path}"
        }
    if not os.path.exists(test_suite_path):
        return {
            "status": 1,
            "message": f"Test suite path does not exist: {test_suite_path}"
        }
    
    # Configure global scripts if defined
    cmd = [squish_config["squishrunner"]]
    cmd.extend(["--config", "setGlobalScriptDirs"])
    for script_dir in GLOBAL_SCRIPT_DIRS:
        cmd.extend([script_dir])

    if test_path:
        squish_config["testcase"] = test_path
    if test_suite_path:
        squish_config["testsuite"] = test_suite_path

    # Create report directory path
    current_dir = os.getcwd()
    report_dir = os.path.join(current_dir, "squish_mcp_results")
    
    # Ensure the report directory exists
    os.makedirs(report_dir, exist_ok=True)

    if suite_or_test_case == 'suite':
        # For test suite invocations, expecting squishrunner calls to look like
        # /path/to/squishrunner --testsuite /path/to/testsuite --local --reportgen html,report-dir
        # Additional options can be provided via the context items.
        
        cmd = [squish_config["squishrunner"]]
        
        # Convert config to command line arguments
        cmd.extend(["--testsuite", test_suite_path])
        
        # Add any context variables as Squish options 
        for key, value in context.items():
            if value == "":
                cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", value])
        
        # Add HTML report generation
        cmd.extend(["--reportgen", f"html,{report_dir}"])
        cmd.extend(["--local"])

    elif suite_or_test_case == 'case':
        # Start squishserver for test case execution
        server_start_result = start_squish_server(DEFAULT_HOST, DEFAULT_PORT, daemon=True, verbose=False)
        if server_start_result["status"] != 0:
            # Notify, but continue onward assuming its already running
            print(f"Failed to start Squish server: {server_start_result['message']}")

        # Expecting test case squishrunner commands to look like
        # /path/to/squishrunner --host localhost --port 4322 --testcase /path/to/testcase --wrapper Qt --reportgen html,report-dir

        cmd = [squish_config["squishrunner"]]
        cmd.extend(["--host", DEFAULT_HOST])
        cmd.extend(["--port", DEFAULT_PORT])
        cmd.extend(["--testcase", test_path])
        cmd.extend(["--wrapper", "Qt"])
        
        # Add HTML report generation
        cmd.extend(["--reportgen", f"html,{report_dir}"])
        
    # CMD debug output
    debug_msg = f"Generated command: {' '.join(cmd)}\n"
    print(f"{debug_msg}")
    
    # Track whether we started a server (only for test cases)
    server_started = suite_or_test_case == 'case'
    
    try:
        # Run Squish test
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
    
        # Stop squishserver if we started it
        if server_started:
            stop_result = stop_squish_server(DEFAULT_HOST, DEFAULT_PORT, force=False)
            if stop_result["status"] != 0:
                # Log warning but don't fail the test
                debug_msg += f"Warning: Failed to stop Squish server: {stop_result['message']}\n"
    
        if process.returncode != 0:
            return {
                "status": 1,
                "message": f"{debug_msg}Test failed with return code {process.returncode}.\nHTML report location: {report_dir}\nStdout: {process.stdout}\nStderr: {process.stderr}"
            }
        
        return {
            "status": 0,
            "message": f"{debug_msg}{process.stdout}\n\nHTML report generated at: {report_dir}"
        }
            
    except Exception as e:
        # Stop squishserver if we started it, even on exception
        if server_started:
            try:
                stop_result = stop_squish_server(DEFAULT_HOST, DEFAULT_PORT, force=True)
                if stop_result["status"] != 0:
                    debug_msg += f"Warning: Failed to stop Squish server after error: {stop_result['message']}\n"
            except:
                debug_msg += "Warning: Could not stop Squish server after error\n"
                
        return {
            "status": 1,
            "message": f"{debug_msg}Error running test: {str(e)}\nHTML report location: {report_dir}"
        }

def get_global_script_dirs() -> Dict:
    """
    Get the global script directories configured in the active Squish test suite.
    This uses the squishrunner --config getGlobalScriptDirs command.
    
    Returns:
        Dict with the following structure:
        {
            "status": int,  # 0 for success, 1 for error
            "message": str,   # Contains stdout for success, error message for failure
            "directories": List[str]  # List of global script directory paths
        }
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg,
            "directories": []
        }
    
    cmd = [SQUISH_RUNNER, "--config", "getGlobalScriptDirs"]
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            return {
                "status": 1,
                "message": f"Command failed with return code {process.returncode}.\nStdout: {process.stdout}\nStderr: {process.stderr}",
                "directories": []
            }
        
        # Parse the output - squishrunner returns directories separated by newlines or semicolons
        directories = []
        if process.stdout.strip():
            # Handle both newline and semicolon separated paths
            raw_dirs = process.stdout.strip().replace(';', '\n').split('\n')
            directories = [dir_path.strip() for dir_path in raw_dirs if dir_path.strip()]
        
        return {
            "status": 0,
            "message": f"Found {len(directories)} global script directories",
            "directories": directories
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error getting global script directories: {str(e)}",
            "directories": []
        }

def set_global_script_dirs(directories: List[str]) -> Dict:
    """
    Set the global script directories for Squish test execution.
    
    Args:
        directories: List of directory paths to set as global script directories
    
    Returns:
        Dict with operation status
    """
    # Validate Squish installation
    is_valid, validation_msg = validate_squish_installation()
    if not is_valid:
        return {
            "status": 1,
            "message": validation_msg
        }
    
    # Validate that directories exist
    invalid_dirs = []
    for directory in directories:
        if not os.path.exists(directory):
            invalid_dirs.append(directory)
    
    if invalid_dirs:
        return {
            "status": 1,
            "message": f"Invalid directories: {', '.join(invalid_dirs)}"
        }
    
    cmd = [SQUISH_RUNNER, "--config", "setGlobalScriptDirs"] + directories
    
    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        if process.returncode != 0:
            return {
                "status": 1,
                "message": f"Command failed with return code {process.returncode}.\nStdout: {process.stdout}\nStderr: {process.stderr}"
            }
        
        return {
            "status": 0,
            "message": f"Successfully set {len(directories)} global script directories"
        }
        
    except Exception as e:
        return {
            "status": 1,
            "message": f"Error setting global script directories: {str(e)}"
        }

