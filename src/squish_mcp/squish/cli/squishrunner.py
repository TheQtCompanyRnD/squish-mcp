"""
Squish Runner CLI Management Module

Handles Squish test execution via squishrunner including:
- Running test suites and test cases
- Managing global script directories
- Configuring test execution parameters
- Generating test reports
"""

import logging
import os
import subprocess

from dataclasses import dataclass
from pathlib import Path

from squish_mcp.errors import ConfigurationException

from . import SQUISH_RUNNER
from . import validate_squish_installation


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class SquishRunnerExecutionResult:
    cmd: str
    stdout: str
    stderr: str
    return_code: int


@dataclass(frozen=True)
class GlobalScriptDirsResult:
    execution: SquishRunnerExecutionResult
    directories: list[str]


def _execute_squishrunner_command(cmd: list[str]) -> SquishRunnerExecutionResult:
    try:
        print(cmd)
        process = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return SquishRunnerExecutionResult(" ".join(cmd), process.stdout, process.stderr, process.returncode)
    except subprocess.CalledProcessError as e:
        log.warning(f"squishrunner command failed (rc={e.returncode}).\nStdout: {e.stdout}\nStderr: {e.stderr}")
        return SquishRunnerExecutionResult(" ".join(cmd), e.stdout, e.stderr, e.returncode)


def run_test(
    test_suite_path: Path,
    test_case_name: str | None = None,
    context: dict[str, str] | None = None,
) -> SquishRunnerExecutionResult:
    """
    Run a Squish test suite or test case.

    Args:
        test_suite_path: Absolute path to the test suite.
        context: Dictionary variables of options to pass to Squish.
        test_case_name: Optional test case name within the suite.

    Returns:
        SquishRunnerExecutionResult: command execution details.

    Raises:
        ConfigurationException: If Squish is not installed or paths are invalid.
    """
    validate_squish_installation()

    if not test_suite_path.exists():
        raise ConfigurationException(f"Test suite does not exist: {test_suite_path}")

    if test_case_name is not None:
        if not (test_suite_path / test_case_name).exists():
            raise ConfigurationException(f"Test case does not exist: {test_suite_path / test_case_name}")

    cmd = [SQUISH_RUNNER, "--testsuite", str(test_suite_path)]

    if context is None:
        context = {}

    for key, value in context.items():
        if value == "":
            cmd.append(f"--{key}")
        else:
            cmd.extend([f"--{key}", value])

    if test_case_name is not None:
        cmd.extend(["--testcase", test_case_name])

    cmd.extend(["--local"])

    return _execute_squishrunner_command(cmd)


def _parse_global_script_dirs_output(stdout: str) -> list[str]:
    """
    Parse squishrunner getGlobalScriptDirs output into directory list.

    Args:
        stdout: Raw stdout from squishrunner --config getGlobalScriptDirs

    Returns:
        List of global script directory paths.
    """
    if not stdout.strip():
        return []
    raw_dirs = stdout.strip().replace(";", "\n").split("\n")
    return [dir_path.strip() for dir_path in raw_dirs if dir_path.strip()]


def get_global_script_dirs() -> GlobalScriptDirsResult:
    """
    Get the global script directories configured in the active Squish test suite.

    Returns:
        GlobalScriptDirsResult with parsed directory list.

    Raises:
        ConfigurationException: If Squish is not installed.
    """
    validate_squish_installation()

    config_cmd = [SQUISH_RUNNER, "--config", "getGlobalScriptDirs"]
    result = _execute_squishrunner_command(config_cmd)

    directories = _parse_global_script_dirs_output(result.stdout) if result.return_code == 0 else []

    return GlobalScriptDirsResult(
        execution=result,
        directories=directories,
    )


def set_global_script_dirs(directories: list[str]) -> SquishRunnerExecutionResult:
    """
    Set the global script directories for Squish test execution.

    Args:
        directories: List of directory paths to set as global script directories.

    Raises:
        ConfigurationException: If Squish is not installed or directories are invalid.
    """
    validate_squish_installation()

    invalid_dirs = [d for d in directories if not d or not os.path.exists(d)]
    if invalid_dirs:
        raise ConfigurationException(f"Invalid directories: {', '.join(invalid_dirs)}")

    config_cmd = [SQUISH_RUNNER, "--config", "setGlobalScriptDirs", ",".join(directories)]
    return _execute_squishrunner_command(config_cmd)
