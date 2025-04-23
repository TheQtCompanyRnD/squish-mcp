from mcp.server.fastmcp import FastMCP
import subprocess
import os
from typing import Dict

mcp = FastMCP("SquishRunner-Server")

# CONFIGURE
SQUISH_RUNNER = os.getenv('SQUISH_RUNNER', "/Applications/Squish for Qt 9.0.0/bin/squishrunner")
HOST = "localhost"
PORT = "4322" # Default Squish server port
DEBUG_LOG = "paw"
SNOOZE_FACTOR = "1.0"

@mcp.tool()
def run_test(test_suite_path: str, context: Dict, test_path="") -> Dict:
    """
    Run a Squish test suite or test case. This is a wrapper around the squishrunner command line tool.
    
    IMPORTANT PATH HANDLING AND SQUISH TEST NAMING CONVENTIONS:
    - All paths are are absolute paths
    - Test suites are named like `suite_<test_suite_name>` - these are folders under the root path
    - Test cases are named like `tst_<test_name>` - these are folders under the test suite path
    - Test files are under the test case folders and are named like `test.py`

    Args:
        test_suite_path: Absolute path to the test suite
                        Example: "/Users/yourname/projects/addressbook/suite_py"
        context: Dictionary variables of options to pass to Squish
                Format: {"VAR_NAME": "value"}
        test_path: Absolute path to the test case from test_suite_path. If provided also the test suite path needs to be provided.
                  Example: "/Users/yourname/projects/addressbook/suite_py/tst_general"
    
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
            context={}
        )
    """

    squish_config = {
        "squishrunner": SQUISH_RUNNER,
        "host": HOST,
        "port": PORT,
        "debugLog": DEBUG_LOG
    } 

    # Check if squishrunner exists
    if not os.path.isfile(squish_config["squishrunner"]):
        return {
            "status": 1,
            "message": f"squishrunner not found at: {squish_config['squishrunner']}"
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

    if test_path:
        squish_config["testsuite"]=test_suite_path
        squish_config["testcase"]=test_path
    elif test_suite_path:
        squish_config["testsuite"]=test_suite_path
    
    cmd = [squish_config["squishrunner"]]

    # Convert config to command line arguments
    for key, value in squish_config.items():
        if key != "squishrunner":
            cmd.extend([f"--{key}", value])
    
    # Add any context variables as Squish options 
    for key, value in context.items():
        if value == "":
            cmd.extend([f"--{key}"])
        else:
            cmd.extend([f"--{key}", value])

    # Add snooze factor - squishrunner is picky about the order of the options
    cmd.extend([f"--snoozeFactor", SNOOZE_FACTOR])
        
    # CMD debug output
    debug_msg = f"Generated command: {' '.join(cmd)}\n"
    
    try:
        # Run Squish test
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
    
        if process.returncode != 0:
            return {
                "status": 1,
                "message": f"{debug_msg}Test failed with return code {process.returncode}.\nStdout: {process.stdout}\nStderr: {process.stderr}"
            }
        
        return {
            "status": 0,
            "message": f"{debug_msg}{process.stdout}"
        }
            
    except Exception as e:
        return {
            "status": 1,
            "message": f"{debug_msg}Error running test: {str(e)}"
        }

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
