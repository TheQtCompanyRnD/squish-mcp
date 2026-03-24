from collections.abc import Callable
from pathlib import Path

import pytest

from squish_mcp.errors import FileOperationException
from squish_mcp.squish.analysis import models
from squish_mcp.squish.analysis.models import LocationType
from squish_mcp.squish.scripting import code_generation
from squish_mcp.squish.scripting.suite_conf_management import SuiteConfiguration


TEST_CASE_MINIMAL_NAME = "test_example_minimal"
TEST_CASE_TEMPLATE_MINIMAL_NAME = "test_example_template_minimal"
TEST_CASE_EXAMPLE_NAME = "test_example"


def _create_default_test_case(suite_path: Path) -> code_generation.TestCaseCreationResult:
    return code_generation.create_test_case(
        str(suite_path),
        TEST_CASE_EXAMPLE_NAME,
    )


class TestTemplateGeneration:
    """Test test template generation functions."""

    def test_full_content_minimal(self, read_testcase: Callable[[str], str]) -> None:
        result = code_generation.generate_test_template(TEST_CASE_TEMPLATE_MINIMAL_NAME, "Minimal testcase template")

        assert result.template == read_testcase(TEST_CASE_TEMPLATE_MINIMAL_NAME)

    def test_template_with_no_analysis_uses_basic(self) -> None:
        """Template generation with no analysis falls back to basic template."""
        result = code_generation.generate_test_template(TEST_CASE_EXAMPLE_NAME, "Test user login", None)

        assert isinstance(result, code_generation.TestTemplateResult)
        assert "import names" in result.template
        assert "import squish" in result.template
        assert TEST_CASE_EXAMPLE_NAME in result.template
        assert "Test user login" in result.template
        assert result.object_pattern == LocationType.SUITE_NAMES

    def test_template_with_setup_and_closing_lines(self) -> None:
        """Template generation inserts setup and closing lines at correct positions."""
        analysis = models.ExistingPatterns(
            object_patterns=models.ObjectPatterns(references=[], primary_location=LocationType.SUITE_NAMES, files=[]),
            common_imports=[],
            api_usage={},
            global_script_usage=models.GlobalScriptUsage(available_functions=[], directories=[]),
        )

        result = code_generation.generate_test_template(
            TEST_CASE_EXAMPLE_NAME,
            "",
            analysis,
            setup_lines=["# Setup convention", "# setup_app()"],
            closing_lines=["# Verification convention", "# verify_screenshot()"],
        )

        template = result.template
        assert "# Setup convention" in template
        assert "# setup_app()" in template
        assert "# Verification convention" in template
        assert "# verify_screenshot()" in template

        # Setup should appear before closing
        assert template.index("# Setup convention") < template.index("# Verification convention")
        # Closing should appear before the final log
        assert template.index("# verify_screenshot()") < template.index(
            'test.log("Test case tst_test_example completed")'
        )

    def test_template_with_analysis_uses_patterns(self) -> None:
        """Template generation with analysis applies patterns."""
        analysis = models.ExistingPatterns(
            object_patterns=models.ObjectPatterns(
                references=[],
                primary_location=LocationType.GLOBAL_SIMPLE,
                files=["/path/to/global/login_pom.py", "/path/to/global/main_pom.py"],
            ),
            common_imports=["login_pom", "helpers"],
            api_usage={
                "startApplication": 10,
                "waitForObject": 25,
                "clickButton": 15,
            },
            global_script_usage=models.GlobalScriptUsage(
                available_functions=[],
                directories=[],
            ),
        )

        result = code_generation.generate_test_template(TEST_CASE_EXAMPLE_NAME, "Test login", analysis)

        assert isinstance(result, code_generation.TestTemplateResult)
        assert "import login_pom" in result.template
        assert "import helpers" in result.template
        assert "startApplication" in result.template
        assert result.object_pattern == LocationType.GLOBAL_SIMPLE


def _analysis(
    location: LocationType,
    files: list[str] | None = None,
    common_imports: list[str] | None = None,
    api_usage: dict[str, int] | None = None,
) -> models.ExistingPatterns:
    """Build an ExistingPatterns with sensible defaults for test parametrization."""
    return models.ExistingPatterns(
        object_patterns=models.ObjectPatterns(
            references=[],
            primary_location=location,
            files=files or [],
        ),
        common_imports=common_imports or [],
        api_usage=api_usage or {},
        global_script_usage=models.GlobalScriptUsage(available_functions=[], directories=[]),
    )


_FULL_API: dict[str, int] = {
    "startApplication": 10,
    "waitForObject": 25,
    "clickButton": 15,
    "test.verify": 8,
}


class TestGenerateTestTemplateCharacterization:
    """Each parametrized case feeds a specific ExistingPatterns configuration into
    the generator and compares the resulting template string against a reference
    file stored in tests/squish/test_data/testcases/.
    """

    @pytest.mark.parametrize(
        ("test_name", "description", "analysis", "expected_pattern"),
        [
            pytest.param(
                "test_suite_names_full",
                "Full template with SUITE_NAMES pattern",
                _analysis(
                    LocationType.SUITE_NAMES,
                    files=["/path/to/suite/names.py"],
                    common_imports=["helpers", "utils"],
                    api_usage=_FULL_API,
                ),
                LocationType.SUITE_NAMES,
                id="suite_names_full_with_desc",
            ),
            pytest.param(
                "test_global_simple",
                "Template with GLOBAL_SIMPLE pattern",
                _analysis(
                    LocationType.GLOBAL_SIMPLE,
                    files=["/path/to/global/login_pom.py", "/path/to/global/main_pom.py"],
                    common_imports=["login_pom", "helpers"],
                    api_usage={"startApplication": 10, "waitForObject": 25, "clickButton": 15},
                ),
                LocationType.GLOBAL_SIMPLE,
                id="global_simple_with_files",
            ),
            pytest.param(
                "test_no_api_usage",
                "Template with no API usage patterns",
                _analysis(LocationType.OTHER, common_imports=["custom_lib"]),
                None,
                id="no_api_other_location",
            ),
            pytest.param(
                "test_suite_names_no_desc",
                "",
                _analysis(
                    LocationType.SUITE_NAMES,
                    files=["/path/to/suite/names.py"],
                    common_imports=["helpers", "utils"],
                    api_usage=_FULL_API,
                ),
                LocationType.SUITE_NAMES,
                id="suite_names_no_desc",
            ),
        ],
    )
    def test_generated_template_output(
        self,
        read_testcase: Callable[[str], str],
        test_name: str,
        description: str,
        analysis: models.ExistingPatterns,
        expected_pattern: LocationType | None,
    ) -> None:
        # Generate a Squish test template from the given analysis patterns
        result = code_generation.generate_test_template(test_name, description, analysis)

        # Compare the generated template against the saved reference file
        assert result.template == read_testcase(test_name)
        assert result.object_pattern == expected_pattern

    def test_with_setup_and_closing(self, read_testcase: Callable[[str], str]) -> None:
        """Separate case: setup_lines/closing_lines are injected into the template body."""
        result = code_generation.generate_test_template(
            "test_with_setup_closing",
            "",
            _analysis(LocationType.SUITE_NAMES, api_usage={"waitForObject": 5}),
            setup_lines=["# Setup convention", "setup_app()"],
            closing_lines=["# Teardown convention", "close_app()"],
        )

        assert result.template == read_testcase("test_with_setup_closing")
        assert result.object_pattern == LocationType.SUITE_NAMES


class TestBDDTemplateGeneration:
    """Test BDD template generation."""

    def test_bdd_template_returns_dataclass(self) -> None:
        """BDD template returns BDDTemplateResult."""
        result = code_generation.generate_bdd_template("test_bdd_example", "Test BDD scenario")

        assert isinstance(result, code_generation.BDDTemplateResult)
        assert isinstance(result.test_py_template, str)
        assert isinstance(result.feature_template, str)
        assert isinstance(result.step_definitions_template, str)

    def test_bdd_template_has_test_py_structure(self) -> None:
        """BDD test.py has correct structure."""
        result = code_generation.generate_bdd_template("test_example", "")

        assert "findFile('scripts', 'python/bdd.py')" in result.test_py_template
        assert "setupHooks" in result.test_py_template
        assert "collectStepDefinitions" in result.test_py_template
        assert "runFeatureFile('test.feature')" in result.test_py_template

    def test_bdd_template_has_feature_structure(self) -> None:
        """BDD feature file has Gherkin structure."""
        result = code_generation.generate_bdd_template("test_example", "User login")

        assert "Feature:" in result.feature_template
        assert "Background:" in result.feature_template
        assert "Scenario:" in result.feature_template
        assert "@test" in result.feature_template
        assert "User login" in result.feature_template

    def test_bdd_template_has_step_definitions(self) -> None:
        """BDD step definitions have correct decorators."""
        result = code_generation.generate_bdd_template("test_example", "")

        step_defs_lower = result.step_definitions_template.lower()
        assert "@given" in step_defs_lower
        assert "@when" in step_defs_lower
        assert "@then" in step_defs_lower
        assert "|any|" in result.step_definitions_template


class TestSuiteConfiguration:
    """Test suite.conf reading and updating."""

    def test_read_suite_conf(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_example"
        suite_path.mkdir()
        (suite_path / "suite.conf").write_text("AUT=myapp\nLANGUAGE=Python\nVERSION=3\n")

        config = SuiteConfiguration.read(suite_path)

        assert config.get_key_value("AUT") == "myapp"
        assert config.get_key_value("LANGUAGE") == "Python"
        assert config.get_key_value("VERSION") == "3"

    def test_update_suite_conf(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_example"
        suite_path.mkdir()
        (suite_path / "suite.conf").write_text("AUT=notmyapp\nLANGUAGE=Java\nVERSION=5\n")

        updated_config = SuiteConfiguration(
            config={"AUT": "myapp", "WRAPPERS": "Qt"},
        )
        updated_config.save_in_suite(suite_path)

        # Read back and verify
        config = SuiteConfiguration.read(suite_path)
        assert updated_config == config


class TestTestCaseCreation:
    """Test test case creation."""

    def test_full_content_minimal(
        self,
        temp_suite_empty: Path,
        read_testcase: Callable[[str], str],
    ) -> None:
        result = code_generation.create_test_case(str(temp_suite_empty), TEST_CASE_MINIMAL_NAME)

        with open(result.test_py_path) as f:
            actual = f.read()

        assert actual == read_testcase(TEST_CASE_MINIMAL_NAME)

    def test_create_test_case_returns_dataclass(self, temp_suite_empty: Path) -> None:
        result = _create_default_test_case(temp_suite_empty)

        assert isinstance(result, code_generation.TestCaseCreationResult)

    def test_create_test_case_creates_directory(self, temp_suite_empty: Path) -> None:
        result = _create_default_test_case(temp_suite_empty)

        assert Path(result.test_case_path).exists()
        assert Path(result.test_case_path).is_dir()

    def test_create_test_case_creates_test_py(self, temp_suite_empty: Path) -> None:
        result = _create_default_test_case(temp_suite_empty)

        assert Path(result.test_py_path).exists()
        assert result.test_py_path.endswith("test.py")
        assert "test.py" in result.files_created

    def test_create_bdd_test_creates_feature(self, temp_suite_empty: Path) -> None:
        result = code_generation.create_test_case(
            str(temp_suite_empty), "test_bdd", is_bdd=True, test_description="Test BDD"
        )

        assert result.is_bdd is True
        assert result.feature_path is not None
        assert Path(result.feature_path).exists()
        assert "test.feature" in result.files_created

    def test_create_test_case_nonexistent_suite_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "suite_missing"
        with pytest.raises(FileOperationException, match="Suite path does not exist"):
            code_generation.create_test_case(str(missing), TEST_CASE_EXAMPLE_NAME)

    def test_create_test_case_non_suite_prefix_raises(self, tmp_path: Path) -> None:
        non_suite = tmp_path / "not_a_suite"
        non_suite.mkdir()

        with pytest.raises(FileOperationException, match="must start with 'suite_'"):
            code_generation.create_test_case(str(non_suite), TEST_CASE_EXAMPLE_NAME)


class TestTestSuiteCreation:
    """Test test suite creation."""

    def test_create_test_suite_returns_dataclass(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_new"
        result = code_generation.create_test_suite(str(suite_path))

        assert isinstance(result, code_generation.TestSuiteCreationResult)

    def test_create_test_suite_creates_directory(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_new"
        code_generation.create_test_suite(str(suite_path))
        assert suite_path.exists()
        assert suite_path.is_dir()

    def test_create_test_suite_creates_suite_conf(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_new"
        result = code_generation.create_test_suite(str(suite_path))

        conf_path = Path(result.suite_conf_path)
        assert conf_path.exists()
        assert conf_path.name == "suite.conf"
        assert "suite.conf" in result.files_created

    def test_create_test_suite_custom_wrapper(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_web"
        code_generation.create_test_suite(str(suite_path), wrapper="Web")

        config = SuiteConfiguration.read(suite_path)
        assert config.get_key_value("WRAPPERS") == "Web"

    def test_create_test_suite_creates_shared_dir(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_new"
        code_generation.create_test_suite(str(suite_path))

        shared_dir = suite_path / "shared"
        assert shared_dir.exists()
        assert shared_dir.is_dir()

    def test_create_test_suite_already_exists_raises(self, tmp_path: Path) -> None:
        suite_path = tmp_path / "suite_existing"
        suite_path.mkdir()

        with pytest.raises(FileOperationException, match="Suite already exists"):
            code_generation.create_test_suite(str(suite_path))

    def test_create_test_suite_non_suite_prefix_raises(self, tmp_path: Path) -> None:
        non_suite = tmp_path / "not_a_suite"

        with pytest.raises(FileOperationException, match="must start with 'suite_'"):
            code_generation.create_test_suite(str(non_suite))


class TestParseBddStepPattern:
    """Characterization tests for _parse_bdd_step_pattern."""

    @staticmethod
    def _parse(pattern: str) -> list[str]:
        _, names = code_generation._parse_bdd_step_pattern(pattern)
        return names

    def test_no_placeholders_returns_empty(self) -> None:
        assert self._parse("I click the button") == []

    def test_single_placeholder_with_status_keyword(self) -> None:
        assert self._parse("The status is |any|") == ["value"]

    def test_three_placeholders_no_keyword(self) -> None:
        assert self._parse("Set |any| to |any| and |any|") == ["value_1", "value_2", "value_3"]


class TestGenerateBddStepFunction:
    """Characterization tests for _generate_bdd_step_function."""

    def test_no_placeholder_generates_todo(self) -> None:
        result = code_generation._generate_bdd_step_function("given", "The application launches successfully")
        assert result == (
            '@given("The application launches successfully")\n'
            "def step(context):\n"
            "    # TODO: Implement this step\n"
            "    pass\n"
        )

    def test_single_placeholder_without_keyword(self) -> None:
        result = code_generation._generate_bdd_step_function("given", "The title of the application is |any|")
        assert result == (
            '@given("The title of the application is |any|")\n'
            "def step(context, value):\n"
            "    # TODO: Implement this step\n"
            "    pass\n"
        )

    def test_single_placeholder_with_keyword(self) -> None:
        """Note: The verify branch concatenates the param name into an object name literal,
        the parameter is never used in the body."""
        result = code_generation._generate_bdd_step_function("then", "I should see |any| in the result")
        assert result == (
            '@then("I should see |any| in the result")\n'
            "def step(context, value):\n"
            "    # test.verify(waitForObjectExists(names.expected_object_value))\n"
            "    pass\n"
        )

    def test_enter_pattern_uses_only_first_param(self) -> None:
        """Note: Two placeholders but only first_value used in body."""
        result = code_generation._generate_bdd_step_function("when", "I enter |any| in the |any| field")
        assert result == (
            '@when("I enter |any| in the |any| field")\n'
            "def step(context, value_1, value_2):\n"
            "    # type(waitForObject(names.input_field), value_1)\n"
            "    pass\n"
        )

    def test_click_pattern_ignores_parameter(self) -> None:
        """Note: The click branch never uses the parameter in the body."""
        result = code_generation._generate_bdd_step_function("when", "I click the |any| button")
        assert result == (
            '@when("I click the |any| button")\n'
            "def step(context, value):\n"
            "    # clickButton(waitForObject(names.button_name))\n"
            "    pass\n"
        )
