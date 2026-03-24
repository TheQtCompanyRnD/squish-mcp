import logging

from pathlib import Path

from fastmcp.tools import tool

from squish_mcp.errors import ConfigurationException
from squish_mcp.errors import TestExecutionException
from squish_mcp.squish.cli import GLOBAL_SCRIPT_DIRS
from squish_mcp.squish.cli import squishrunner
from squish_mcp.squish.cli.squishrunner import GlobalScriptDirsResult
from squish_mcp.squish.cli.squishrunner import SquishRunnerExecutionResult

from .models import TestRunResponse


log = logging.getLogger(__name__)


def _raise_on_configuration_error(operation: str, return_code: int, stdout: str = "", stderr: str = "") -> None:
    if return_code == 0:
        return
    details = [f"{operation} failed (rc={return_code})."]
    if stdout:
        details.append(f"Stdout: {stdout}")
    if stderr:
        details.append(f"Stderr: {stderr}")
    raise ConfigurationException("\n".join(details))


def _raise_on_test_execution_error(return_code: int, stdout: str, stderr: str) -> None:
    if return_code == 0:
        return
    raise TestExecutionException(f"Test run failed (rc={return_code}).\nStdout: {stdout}\nStderr: {stderr}")


@tool
def run_test(test_suite_path: str, context: dict, test_case_name: str | None = None) -> TestRunResponse:
    """
    Run a Squish test suite or test case.

    You need to figure out the test suite and test case absolute paths on your own.
    You may be asked to either run a full test suite or a single test case within a test suite.

    This is a wrapper around the squishrunner command line tool.

    IMPORTANT PATH HANDLING AND SQUISH TEST NAMING CONVENTIONS:
    - All paths are absolute paths, but you should infer missing ones from context.
    - Test suites are named like `suite_<test_suite_name>` - these are folders under the root path
    - Test cases are named like `tst_<test_name>` - these are folders under the test suite path
    - Test files are under the test case folders and are named like `test.py`

    Args:
        test_suite_path: Absolute path to the test suite which you should figure out on your own
                        Example: "/Users/yourname/projects/addressbook/suite_py"
        context: Dictionary variables of options to pass to Squish
                Format: {"VAR_NAME": "value"}
        test_case_name: Name of the test case to run.
                  Example: "tst_general"

    Returns:
        Test run results with squishrunner output.
    """
    configured_dirs_result: GlobalScriptDirsResult = squishrunner.get_global_script_dirs()
    _raise_on_configuration_error(
        operation="getGlobalScriptDirs",
        return_code=configured_dirs_result.execution.return_code,
        stdout=configured_dirs_result.execution.stdout,
        stderr=configured_dirs_result.execution.stderr,
    )
    runtime_configured_dirs = configured_dirs_result.directories
    default_dirs = [d for d in GLOBAL_SCRIPT_DIRS if d]
    dirs_to_apply = runtime_configured_dirs or default_dirs

    config_run_result = squishrunner.set_global_script_dirs(dirs_to_apply)
    _raise_on_configuration_error(
        operation="setGlobalScriptDirs",
        return_code=config_run_result.return_code,
        stdout=config_run_result.stdout,
        stderr=config_run_result.stderr,
    )

    test_run_result: SquishRunnerExecutionResult = squishrunner.run_test(Path(test_suite_path), test_case_name, context)

    _raise_on_test_execution_error(
        return_code=test_run_result.return_code,
        stdout=test_run_result.stdout,
        stderr=test_run_result.stderr,
    )

    return TestRunResponse(
        stdout=test_run_result.stdout,
        stderr=test_run_result.stderr,
    )


@tool
def get_global_script_dirs() -> list[str]:
    """
    Get the global script directories configured in the active Squish test suite.
    This uses the squishrunner --config getGlobalScriptDirs command.

    Returns:
        List of global script directory paths.
    """
    result = squishrunner.get_global_script_dirs()
    _raise_on_configuration_error(
        operation="getGlobalScriptDirs",
        return_code=result.execution.return_code,
        stderr=result.execution.stderr,
    )
    return result.directories


@tool
def set_global_script_dirs(directories: list[str]) -> None:
    """
    Set the global script directories for Squish test execution.

    Args:
        directories: List of directory paths to set as global script directories
    """
    result = squishrunner.set_global_script_dirs(directories)
    _raise_on_configuration_error(
        operation="setGlobalScriptDirs",
        return_code=result.return_code,
        stdout=result.stdout,
        stderr=result.stderr,
    )
