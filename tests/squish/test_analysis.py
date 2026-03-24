"""Tests for squish/analysis/ — test suite analysis, object references, BDD context."""

import builtins
import typing as t

from pathlib import Path

import pytest

from squish_mcp.errors import AnalysisException
from squish_mcp.squish.analysis import models
from squish_mcp.squish.analysis import test_suite_analysis
from squish_mcp.squish.analysis.object_reference_analysis import analyze_current_object_map_structure
from squish_mcp.squish.analysis.object_reference_analysis import analyze_object_reference_patterns
from squish_mcp.squish.analysis.object_reference_analysis import analyze_object_references
from squish_mcp.squish.analysis.test_suite_analysis import _TEST_PREVIEW_MAX_LENGTH
from squish_mcp.squish.analysis.test_suite_analysis import analyze_test_script_formats
from squish_mcp.squish.analysis.test_suite_analysis import extract_bdd_context
from squish_mcp.squish.analysis.test_suite_analysis import extract_object_references


# standard_test.py: imports names, squish; calls startApplication, waitForObject,
# clickButton, test.verify, test.log; references names.main_window, names.ok_button
_STANDARD_API_CALLS = [
    "startApplication",
    "waitForObject",
    "clickButton",
    "test.verify",
    "test.log",
]
_STANDARD_IMPORTS = ["names", "squish"]
_STANDARD_OBJ_REFS = ["names.main_window", "names.ok_button"]

# bdd_steps.py: 3 step definitions, 1 variable step with 2 |any| placeholders
_BDD_STEP_DEFINITIONS = [
    ("given", "the application is running"),
    ("when", "I enter |any| in the |any| field"),
    ("then", "I should see the dashboard"),
]
_BDD_VARIABLE_STEPS = [
    {"type": "when", "pattern": "I enter |any| in the |any| field", "variable_count": 2},
]

# login.feature: 3 steps (Given/When/Then)
_FEATURE_STEPS_USED = [
    ("Given", "the application is running"),
    ("When", 'I enter "admin" in the username field'),
    ("Then", "I should see the dashboard"),
]


@pytest.fixture
def standard_analysis(suite_with_two_standard_tests: Path) -> models.TestFormatAnalysis:
    return analyze_test_script_formats(str(suite_with_two_standard_tests))


@pytest.fixture
def bdd_analysis(suite_with_bdd_tests: Path) -> models.TestFormatAnalysis:
    return analyze_test_script_formats(str(suite_with_bdd_tests))


@pytest.fixture
def bdd_context_result(bdd_analysis: models.TestFormatAnalysis) -> models.BDDContext:
    return extract_bdd_context(bdd_analysis)


class TestAnalyzeTestScriptFormats:
    # --- Basic discovery ---

    def test_empty_directory_returns_empty(self, tmp_path: Path) -> None:
        suite = tmp_path / "suite_empty"
        suite.mkdir()
        result = analyze_test_script_formats(str(suite))

        assert result.suite.test_cases == []
        assert result.patterns.squish_api_usage == []

    def test_discovers_standard_suite(self, standard_suite_generator: t.Callable[[list[str]], Path]) -> None:
        test_names = ["1", "2"]
        suite_path = standard_suite_generator(test_names)
        result = analyze_test_script_formats(str(suite_path))

        suite = result.suite
        assert suite.name == "suite_py"
        assert len(suite.test_cases) == len(test_names)

    def test_extracts_test_case_names(self, standard_analysis: models.TestFormatAnalysis) -> None:
        names = {tc.name for tc in standard_analysis.suite.test_cases}
        assert names == {"tst_1", "tst_2"}

    # --- Standard test case fields ---

    def test_extracts_api_calls(self, standard_analysis: models.TestFormatAnalysis) -> None:
        tc = standard_analysis.suite.test_cases[0]
        assert tc.squish_api_calls == _STANDARD_API_CALLS

    def test_extracts_imports(self, standard_analysis: models.TestFormatAnalysis) -> None:
        tc = standard_analysis.suite.test_cases[0]
        assert tc.imports == _STANDARD_IMPORTS

    def test_extracts_object_references(self, standard_analysis: models.TestFormatAnalysis) -> None:
        tc = standard_analysis.suite.test_cases[0]
        assert tc.object_references == _STANDARD_OBJ_REFS

    def test_global_script_usage_true_for_non_standard_imports(
        self, standard_analysis: models.TestFormatAnalysis
    ) -> None:
        tc = standard_analysis.suite.test_cases[0]
        assert tc.global_script_usage is True

    def test_standard_test_not_bdd(self, standard_analysis: models.TestFormatAnalysis) -> None:
        for tc in standard_analysis.suite.test_cases:
            assert tc.is_bdd is False
            assert tc.feature_file is None

    def test_uses_behave_false_for_standard_test(self, standard_analysis: models.TestFormatAnalysis) -> None:
        for tc in standard_analysis.suite.test_cases:
            assert tc.uses_behave is False

    def test_no_bdd_info_on_standard_suite(self, standard_analysis: models.TestFormatAnalysis) -> None:
        assert standard_analysis.suite.bdd_info is None

    # --- Resources ---

    def test_discovers_resources(self, standard_analysis: models.TestFormatAnalysis) -> None:
        resources = standard_analysis.suite.resources
        assert len(resources) == 1
        assert resources[0].name == "names.py"

    def test_resource_deduplication(self, standard_analysis: models.TestFormatAnalysis) -> None:
        """names.py matches both 'names.py' and '*.py' patterns but appears only once."""
        resource_names = [r.name for r in standard_analysis.suite.resources]
        assert resource_names.count("names.py") == 1

    # --- BDD test case ---

    def test_discovers_bdd_suite(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        suite = bdd_analysis.suite
        assert suite.name == "suite_bdd"
        assert suite.bdd_info is not None
        assert suite.bdd_info.steps_directory.endswith("steps")

    def test_bdd_test_case_has_feature(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        tc = bdd_analysis.suite.test_cases[0]
        assert tc.is_bdd is True
        assert tc.feature_file is not None
        assert tc.feature_content is not None
        assert "Feature: Login" in tc.feature_content

    def test_bdd_test_case_uses_behave(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        tc = bdd_analysis.suite.test_cases[0]
        assert tc.uses_behave is True

    def test_bdd_steps_extracted_from_feature(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        tc = bdd_analysis.suite.test_cases[0]
        assert tc.bdd_steps_used == _FEATURE_STEPS_USED

    def test_bdd_step_definitions_parsed(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        bdd = bdd_analysis.suite.bdd_info
        assert bdd is not None
        assert bdd.step_definitions == _BDD_STEP_DEFINITIONS

    def test_bdd_step_files_found(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        bdd = bdd_analysis.suite.bdd_info
        assert bdd is not None
        assert len(bdd.step_files) == 1
        assert bdd.step_files[0].name == "steps.py"

    def test_bdd_step_file_global_script_usage(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        bdd = bdd_analysis.suite.bdd_info
        assert bdd is not None
        assert bdd.step_files[0].global_script_usage is True

    def test_bdd_variable_steps_detected(self, bdd_analysis: models.TestFormatAnalysis) -> None:
        bdd = bdd_analysis.suite.bdd_info
        assert bdd is not None
        assert bdd.step_files[0].variable_steps == _BDD_VARIABLE_STEPS

    # --- Edge cases ---

    def test_unreadable_test_file_records_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        suite = tmp_path / "suite_err"
        suite.mkdir()
        tst = suite / "tst_broken"
        tst.mkdir()
        test_py = tst / "test.py"
        test_py.write_text("valid python")

        def fail_test_py_reads(path: str, *_args: object, **_kwargs: object) -> t.IO[str]:
            if path == str(test_py):
                raise PermissionError("permission denied")
            return builtins.open(path, "r", encoding="utf-8")

        monkeypatch.setattr(test_suite_analysis, "open", fail_test_py_reads, raising=False)

        result = analyze_test_script_formats(str(suite))
        tc = result.suite.test_cases[0]
        assert tc.error is not None
        assert tc.error.startswith("Could not analyze:")
        assert tc.squish_api_calls == []
        assert tc.imports == []
        assert tc.object_references == []
        assert tc.global_script_usage is False
        assert tc.content_preview == ""
        assert tc.is_bdd is False
        assert tc.uses_behave is False

    def test_content_preview_truncated(self, tmp_path: Path) -> None:
        suite = tmp_path / "suite_big"
        suite.mkdir()
        tst = suite / "tst_big"
        tst.mkdir()
        (tst / "test.py").write_text("x = 1\n" * 500)

        result = analyze_test_script_formats(str(suite))
        tc = result.suite.test_cases[0]
        assert tc.content_preview.endswith("...")
        assert len(tc.content_preview) == _TEST_PREVIEW_MAX_LENGTH + len("...")

    def test_empty_suite_directory(self, tmp_path: Path) -> None:
        suite = tmp_path / "suite_empty"
        suite.mkdir()

        result = analyze_test_script_formats(str(suite))
        assert result.suite.test_cases == []

    def test_missing_test_py_skipped(self, tmp_path: Path) -> None:
        suite = tmp_path / "suite_py"
        suite.mkdir()
        (suite / "tst_no_script").mkdir()

        result = analyze_test_script_formats(str(suite))
        assert result.suite.test_cases == []

    def test_nonexistent_suite_path_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "suite_missing"
        with pytest.raises(AnalysisException, match="path does not exist"):
            analyze_test_script_formats(str(missing))

    def test_non_suite_directory_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "not_a_suite"
        bad.mkdir()
        with pytest.raises(AnalysisException, match="must start with 'suite_'"):
            analyze_test_script_formats(str(bad))

    def test_file_path_raises(self, tmp_path: Path) -> None:
        suite_file = tmp_path / "suite_py_file.txt"
        suite_file.write_text("x")
        with pytest.raises(AnalysisException, match="expected a directory"):
            analyze_test_script_formats(str(suite_file))

    # --- Patterns ---

    def test_patterns_derived_from_test_cases(self, standard_analysis: models.TestFormatAnalysis) -> None:
        all_api_calls = [call for tc in standard_analysis.suite.test_cases for call in tc.squish_api_calls]
        assert standard_analysis.patterns.squish_api_usage == all_api_calls

        all_obj_refs = [ref for tc in standard_analysis.suite.test_cases for ref in tc.object_references]
        assert standard_analysis.patterns.object_usage == all_obj_refs


class TestExtractBddContext:
    def test_no_bdd_suite(self, standard_analysis: models.TestFormatAnalysis) -> None:
        bdd = extract_bdd_context(standard_analysis)

        assert bdd.has_bdd_tests is False
        assert bdd.feature_files == []
        assert bdd.bdd_suite is None
        assert bdd.relationships == []

    def test_bdd_suite_detected(self, bdd_context_result: models.BDDContext) -> None:
        assert bdd_context_result.has_bdd_tests is True
        assert bdd_context_result.bdd_suite is not None
        assert len(bdd_context_result.feature_files) == 1

    def test_feature_file_content_captured(self, bdd_context_result: models.BDDContext) -> None:
        ff = bdd_context_result.feature_files[0]
        assert ff.suite == "suite_bdd"
        assert ff.test_case == "tst_login_bdd"
        assert "Feature: Login" in ff.feature_content

    def test_feature_file_steps_used(self, bdd_context_result: models.BDDContext) -> None:
        ff = bdd_context_result.feature_files[0]
        assert ff.steps_used == _FEATURE_STEPS_USED

    def test_step_definitions_aggregated(self, bdd_context_result: models.BDDContext) -> None:
        assert bdd_context_result.bdd_suite is not None
        all_step_defs = list(bdd_context_result.bdd_suite.step_definitions)
        assert all_step_defs == _BDD_STEP_DEFINITIONS

    def test_relationships_count_matches_resolved_steps(self, bdd_context_result: models.BDDContext) -> None:
        assert len(bdd_context_result.relationships) == len(_FEATURE_STEPS_USED)

    def test_relationships_structure(self, bdd_context_result: models.BDDContext) -> None:
        for rel in bdd_context_result.relationships:
            assert rel.suite == "suite_bdd"
            assert rel.feature_file is not None
            assert rel.step_used is not None
            assert rel.step_definition is not None

    def test_relationships_map_to_matching_step_definition(self, bdd_context_result: models.BDDContext) -> None:
        by_step_used = {rel.step_used: rel.step_definition for rel in bdd_context_result.relationships}
        assert by_step_used["Given the application is running"] == "@given('the application is running')"
        assert by_step_used['When I enter "admin" in the username field'] == "@when('I enter |any| in the |any| field')"
        assert by_step_used["Then I should see the dashboard"] == "@then('I should see the dashboard')"


class TestExtractObjectReferences:
    def test_empty_content(self) -> None:
        result = extract_object_references("")

        assert result.names_objects == []
        assert result.direct_objects == []
        assert result.global_script_objects == []
        assert result.unknown_objects == []

    def test_names_references(self) -> None:
        code = "waitForObject(names.main_window)\nclickButton(names.ok_btn)\n"
        result = extract_object_references(code)

        assert "main_window" in result.names_objects
        assert "ok_btn" in result.names_objects

    def test_names_deduplicated(self) -> None:
        code = "waitForObject(names.btn)\nclickButton(names.btn)\nfindObject(names.btn)\n"
        result = extract_object_references(code)

        assert result.names_objects.count("btn") == 1

    def test_unknown_identifier_objects(self) -> None:
        code = "waitForObject(some_var)\n"
        result = extract_object_references(code)

        assert "some_var" in result.unknown_objects

    def test_global_script_objects(self) -> None:
        code = "waitForObject(pom.login_button)\n"
        result = extract_object_references(code)

        assert "pom.login_button" in result.global_script_objects

    def test_mixed_references(self) -> None:
        code = "waitForObject(names.main_win)\nclickButton(local_btn)\nfindObject(page.search_box)\n"
        result = extract_object_references(code)

        assert "main_win" in result.names_objects
        assert "local_btn" in result.unknown_objects
        assert "page.search_box" in result.global_script_objects

    def test_string_literal_classified_as_unknown(self) -> None:
        """Quoted strings are stripped and classified as unknown if they look like identifiers."""
        code = 'waitForObject("literal_string")\n'
        result = extract_object_references(code)

        assert "literal_string" in result.unknown_objects


class TestAnalyzeObjectReferences:
    def test_empty_directory(self, tmp_path: Path) -> None:
        suite = tmp_path / "suite_empty"
        suite.mkdir()
        result = analyze_object_references(str(suite))

        assert result.files == []

    def test_finds_suite_names_py(self, suite_with_two_standard_tests: Path) -> None:
        result = analyze_object_references(str(suite_with_two_standard_tests))

        suite_files = [f for f in result.files if f.type == models.LocationType.SUITE_NAMES]
        assert len(suite_files) == 1
        assert suite_files[0].name == "names.py"

    def test_counts_object_definitions(self, suite_with_two_standard_tests: Path) -> None:
        result = analyze_object_references(str(suite_with_two_standard_tests))

        suite_file = next(f for f in result.files if f.type == models.LocationType.SUITE_NAMES)
        # main_window, ok_button, input_field, dashboard
        assert suite_file.object_count == 4  # noqa: PLR2004

    def test_sample_objects_populated(self, suite_with_two_standard_tests: Path) -> None:
        result = analyze_object_references(str(suite_with_two_standard_tests))

        suite_file = next(f for f in result.files if f.type == models.LocationType.SUITE_NAMES)
        assert suite_file.sample_objects is not None
        assert len(suite_file.sample_objects) > 0

    def test_content_preview_populated(self, suite_with_two_standard_tests: Path) -> None:
        result = analyze_object_references(str(suite_with_two_standard_tests))

        suite_file = next(f for f in result.files if f.type == models.LocationType.SUITE_NAMES)
        assert suite_file.content_preview is not None
        assert "main_window" in suite_file.content_preview

    def test_non_suite_directory_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "not_a_suite"
        bad.mkdir()
        with pytest.raises(AnalysisException, match="must start with 'suite_'"):
            analyze_object_references(str(bad))

    def test_nonexistent_suite_path_raises(self, tmp_path: Path) -> None:
        missing = tmp_path / "suite_missing"
        with pytest.raises(AnalysisException, match="path does not exist"):
            analyze_object_references(str(missing))

    def test_file_path_raises(self, tmp_path: Path) -> None:
        suite_file = tmp_path / "suite_py.txt"
        suite_file.write_text("x")
        with pytest.raises(AnalysisException, match="expected a directory"):
            analyze_object_references(str(suite_file))


class TestAnalyzeObjectReferencePatterns:
    def test_none_input_defaults_to_suite_names(self) -> None:
        result = analyze_object_reference_patterns(None)

        assert result.preferred_location_type == models.LocationType.SUITE_NAMES
        assert result.has_simple_dicts is True
        assert result.has_pom_classes is False
        assert result.has_function_based is False

    def test_suite_files_only(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.SUITE_NAMES,
                    path="/project/suite_py/names.py",
                    name="names.py",
                    suite="/project/suite_py",
                ),
            ]
        )
        result = analyze_object_reference_patterns(analysis)

        assert result.preferred_location_type == models.LocationType.SUITE_NAMES
        assert result.suite_names_locations == ["/project/suite_py/names.py"]

    def test_global_pom_detected(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.GLOBAL_SIMPLE,
                    path="/scripts/login-pom/object_references.py",
                    name="object_references.py",
                    content_preview="class LoginObjects:\n    pass",
                ),
            ]
        )
        result = analyze_object_reference_patterns(analysis)

        assert result.preferred_location_type == models.LocationType.GLOBAL_POM
        assert result.has_pom_classes is True

    def test_global_function_based_detected(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.GLOBAL_SIMPLE,
                    path="/scripts/helpers/objects.py",
                    name="objects.py",
                    content_preview="def get_login_button():\n    return waitForObject(...)",
                ),
            ]
        )
        result = analyze_object_reference_patterns(analysis)

        assert result.preferred_location_type == models.LocationType.GLOBAL_FUNCTIONS
        assert result.has_function_based is True

    def test_global_simple_detected(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.GLOBAL_SIMPLE,
                    path="/scripts/objects.py",
                    name="objects.py",
                    content_preview='login_btn = {"type": "QPushButton"}',
                ),
            ]
        )
        result = analyze_object_reference_patterns(analysis)

        assert result.preferred_location_type == models.LocationType.GLOBAL_SIMPLE
        assert result.global_script_locations == ["/scripts/objects.py"]

    def test_pom_takes_precedence_over_functions(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.GLOBAL_SIMPLE,
                    path="/scripts/login-pom/object_references.py",
                    name="object_references.py",
                    content_preview="def get_button():\n    pass",
                ),
            ]
        )
        result = analyze_object_reference_patterns(analysis)

        # "object_references" in path triggers POM, "def " triggers functions.
        # POM takes precedence.
        assert result.preferred_location_type == models.LocationType.GLOBAL_POM


class TestAnalyzeObjectMapStructure:
    def test_none_input(self) -> None:
        result = analyze_current_object_map_structure(None)

        assert result.object_files == []
        assert result.existing_objects == {}
        assert result.page_organization.strategy == models.OrganizationStrategy.UNKNOWN

    def test_suite_files_strategy(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.SUITE_NAMES,
                    path="/project/suite_py/names.py",
                    name="names.py",
                    suite="/project/suite_py",
                ),
            ]
        )
        result = analyze_current_object_map_structure(analysis)

        assert result.page_organization.strategy == models.OrganizationStrategy.SUITE_NAMES
        assert result.page_organization.suite == "/project/suite_py"
        assert len(result.object_files) == 1
        assert result.object_files[0].type == models.LocationType.SUITE_NAMES

    def test_global_files_strategy(self) -> None:
        analysis = models.ObjectReferenceAnalysis(
            files=[
                models.ObjectFileLocation(
                    type=models.LocationType.GLOBAL_POM,
                    path="/scripts/pom/objects.py",
                    name="objects.py",
                ),
            ]
        )
        result = analyze_current_object_map_structure(analysis)

        assert result.page_organization.strategy == models.OrganizationStrategy.GLOBAL_FILES
        assert result.page_organization.base_directory is not None
        assert len(result.object_files) == 1

    def test_global_takes_precedence_over_suite(self) -> None:
        files = [
            models.ObjectFileLocation(
                type=models.LocationType.GLOBAL_SIMPLE,
                path="/scripts/objects.py",
                name="objects.py",
            ),
            models.ObjectFileLocation(
                type=models.LocationType.SUITE_NAMES,
                path="/project/suite_py/names.py",
                name="names.py",
                suite="/project/suite_py",
            ),
        ]
        analysis = models.ObjectReferenceAnalysis(files=files)
        result = analyze_current_object_map_structure(analysis)

        assert result.page_organization.strategy == models.OrganizationStrategy.GLOBAL_FILES
        assert len(result.object_files) == len(files)
