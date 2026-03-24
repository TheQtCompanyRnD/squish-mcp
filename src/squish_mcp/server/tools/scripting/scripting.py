import os

from pathlib import Path

from fastmcp.tools import tool

from squish_mcp.errors import FileOperationException
from squish_mcp.squish import scripting

from .models import SuiteConfigurationResponse
from .models import TestCaseCreationResponse
from .models import TestSuiteCreationResponse


def _require_existing_suite_path(suite_path: str) -> None:
    if not os.path.exists(suite_path):
        raise FileOperationException(f"Suite path does not exist: {suite_path}")


@tool
def create_test_suite(
    suite_path: str,
    wrapper: str = "",
) -> TestSuiteCreationResponse:
    """
    Create a new Squish test suite with the standard directory structure.

    Creates suite.conf and shared/names.py inside the given directory.
    The suite directory must not already exist.

    Args:
        suite_path: Absolute path to the test suite directory to create (must start with 'suite_')
        wrapper: Name of the wrapper to use (default 'Qt'). Written as WRAPPERS in suite.conf.
    """
    result = scripting.create_test_suite(suite_path, wrapper)
    return TestSuiteCreationResponse.from_creation_result(result)


@tool
def create_test_case(  # noqa: PLR0913
    suite_path: str,
    test_case_name: str,
    test_content: str = "",
    is_bdd: bool = False,
    test_description: str = "",
) -> TestCaseCreationResponse:
    """
    Create a new Squish test case within an existing test suite.

    Args:
        suite_path: Absolute path to the test suite directory (must start with 'suite_')
        test_case_name: Name of the test case (will be prefixed with 'tst_' if not already)
        test_content: Python code content for the test.py file (optional)
        is_bdd: Whether to create a BDD test with proper QtCare Squish BDD structure (default: False)
        test_description: Description for BDD feature file (optional, recommended for BDD tests)
    """
    result = scripting.create_test_case(suite_path, test_case_name, test_content, is_bdd, test_description)
    return TestCaseCreationResponse.from_creation_result(result)


@tool
def get_suite_configuration(suite_path: str) -> SuiteConfigurationResponse:
    """
    Read the suite configuration from a suite.conf file.

    Args:
        suite_path: Absolute path to the test suite directory
    """
    _require_existing_suite_path(suite_path)
    config = scripting.SuiteConfiguration.read(Path(suite_path))
    return SuiteConfigurationResponse.from_suite_configuration(config)
