from pydantic import BaseModel
from pydantic import Field

from squish_mcp.squish.scripting.code_generation import TestCaseCreationResult
from squish_mcp.squish.scripting.code_generation import TestSuiteCreationResult
from squish_mcp.squish.scripting.suite_conf_management import SuiteConfiguration


class TestSuiteCreationResponse(BaseModel):
    """Result of creating a new Squish test suite."""

    message: str = Field(description="Summary of what was created")
    suite_path: str = Field(description="Absolute path to the created test suite directory")
    suite_conf_path: str = Field(description="Absolute path to the created suite.conf file")
    names_path: str = Field(description="Absolute path to the created names.py file")
    files_created: list[str] = Field(description="Relative paths of all created files")

    @classmethod
    def from_creation_result(cls, result: TestSuiteCreationResult) -> "TestSuiteCreationResponse":
        return cls(
            message="Created a test suite with an empty names.py file and suite.conf that holds default configuration.",
            suite_path=result.suite_path,
            suite_conf_path=result.suite_conf_path,
            names_path=result.names_path,
            files_created=result.files_created,
        )


class TestCaseCreationResponse(BaseModel):
    """Result of creating a new Squish test case."""

    message: str = Field(description="Summary of what was created")
    test_case_path: str = Field(description="Absolute path to the created test case directory")
    test_py_path: str = Field(description="Absolute path to the created test.py file")
    files_created: list[str] = Field(description="All file paths that were created")
    is_bdd: bool = Field(description="Whether this is a BDD test case with .feature file")
    feature_path: str | None = Field(default=None, description="Path to the .feature file (BDD tests only)")
    suite_conf_path: str | None = Field(default=None, description="Path to suite.conf that was updated")

    @classmethod
    def from_creation_result(cls, result: TestCaseCreationResult) -> "TestCaseCreationResponse":
        test_type = "BDD " if result.is_bdd else ""
        return cls(
            message=f"Created {test_type}test case with {len(result.files_created)} files",
            test_case_path=result.test_case_path,
            test_py_path=result.test_py_path,
            files_created=result.files_created,
            is_bdd=result.is_bdd,
            feature_path=result.feature_path,
            suite_conf_path=result.suite_conf_path,
        )


class SuiteConfigurationResponse(BaseModel):
    """Configuration parsed from a suite.conf file."""

    message: str = Field(description="Summary of the suite configuration")
    content: str = Field(description="Raw content of the suite.conf file")

    @classmethod
    def from_suite_configuration(cls, result: SuiteConfiguration) -> "SuiteConfigurationResponse":
        return cls(
            message=f"Suite configuration with {len(result.config)} entries",
            content=str(result),
        )
