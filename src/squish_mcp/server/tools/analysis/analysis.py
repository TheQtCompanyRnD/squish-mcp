import logging

from fastmcp.tools import tool

from squish_mcp.errors import AnalysisException
from squish_mcp.squish import analysis as squish_analysis
from squish_mcp.squish import scripting
from squish_mcp.squish.scripting.pom_generation import determine_output_strategy_from_patterns
from squish_mcp.squish.scripting.pom_generation import page_objects_from_snapshot

from . import code_suggestions
from . import squish_rules
from .models import BDDContextAnalysisResponse
from .models import BDDDocumentationAnalysisResponse
from .models import BDDTemplateResponse
from .models import CodeSuggestionsResponse
from .models import ExistingPatternsResponse
from .models import GlobalScriptsAnalysisResponse
from .models import ObjectMapStructureResponse
from .models import ObjectReferenceAnalysisResponse
from .models import ObjectReferencesResponse
from .models import PageObjectsGenerationResponse
from .models import SquishAPIDocumentationResponse
from .models import SquishRulesAnalysisResponse
from .models import TestTemplateResponse


log = logging.getLogger(__name__)


@tool
def analyze_object_references(test_suite_path: str) -> ObjectReferenceAnalysisResponse:
    """
    Analyze object-reference patterns that should be used for generating new test cases. This includes
    where and how object maps are stored and how the objects are then accessed.

    Args:
        test_suite_path: Path to a `suite_*` directory.
    """
    result = squish_analysis.analyze_object_references(test_suite_path)
    return ObjectReferenceAnalysisResponse.from_object_reference_analysis(result)


@tool
def analyze_global_scripts() -> GlobalScriptsAnalysisResponse:
    """
    Analyze global scripts usage patterns that should be used for generating new test cases.
    """
    result = squish_analysis.analyze_global_scripts()
    return GlobalScriptsAnalysisResponse.from_global_scripts_analysis(result)


@tool
def analyze_squish_api_documentation() -> SquishAPIDocumentationResponse:
    """
    Parse the local Squish documentation to find relevant information like the
    available functions and code snippets.
    """
    result = squish_analysis.fetch_squish_api_documentation()
    return SquishAPIDocumentationResponse.from_api_documentation(result)


@tool
def analyze_squish_rules() -> SquishRulesAnalysisResponse:
    """
    Analyze project-specific Squish rules (explicitly defined patterns).
    """
    result = squish_rules.read_squish_rules()
    return SquishRulesAnalysisResponse.from_squish_rules(result)


@tool
def analyze_bdd_documentation() -> BDDDocumentationAnalysisResponse:
    """
    Parse the local BDD-specific Squish documentation to find relevant information.
    """
    result = squish_analysis.fetch_squish_bdd_documentation()
    return BDDDocumentationAnalysisResponse.from_bdd_documentation(result)


@tool
def analyze_bdd_context(test_suite_path: str) -> BDDContextAnalysisResponse:
    """
    Analyze how BDD is used in a specific test suite.

    Args:
        test_suite_path: Path to a `suite_*` directory.
    """
    try:
        test_format_analysis = squish_analysis.analyze_test_script_formats(test_suite_path)
    except Exception as e:
        raise RuntimeError(f"BDD context unavailable: test format analysis not available: {e}") from e
    result = squish_analysis.extract_bdd_context(test_format_analysis=test_format_analysis)
    return BDDContextAnalysisResponse.from_bdd_context(result)


@tool
def analyze_existing_patterns(test_suite_path: str) -> ExistingPatternsResponse:
    """
    Analyze test suite to find common patterns that should be used for generating new test cases.

    Args:
        test_suite_path: Path to a `suite_*` directory.
    """
    result = squish_analysis.analyze_existing_patterns(
        squish_analysis.analyze_test_script_formats(test_suite_path=test_suite_path),
        squish_analysis.analyze_object_references(test_suite_path=test_suite_path),
        squish_analysis.analyze_global_scripts(),
    )
    return ExistingPatternsResponse.from_existing_patterns(result)


@tool
def generate_test_template(
    test_suite_path: str,
    test_case_name: str,
    test_description: str = "",
) -> TestTemplateResponse:
    """
    Generate a test template based on existing patterns and project conventions.

    Args:
        test_suite_path: Path to a `suite_*` directory.
        test_case_name: Name of the test case
        test_description: Optional description of what the test should do
    """
    existing_pattern_analysis = squish_analysis.analyze_existing_patterns(
        squish_analysis.analyze_test_script_formats(test_suite_path),
        squish_analysis.analyze_object_references(test_suite_path),
        squish_analysis.analyze_global_scripts(),
    )

    setup_lines: list[str] | None = None
    closing_lines: list[str] | None = None

    conventions = squish_rules.get_coding_conventions()
    if conventions.setup_function is not None:
        setup_lines = ["# Setup based on project conventions", "# " + conventions.setup_function]
    if conventions.screenshot_verification is not None:
        closing_lines = [
            "# Screenshot verification (project pattern)",
            "# " + conventions.screenshot_verification,
        ]

    result = scripting.generate_test_template(
        test_case_name, test_description, existing_pattern_analysis, setup_lines, closing_lines
    )
    return TestTemplateResponse.from_template_result(result, test_case_name)


@tool
def generate_bdd_template(
    test_case_name: str,
    test_description: str = "",
) -> BDDTemplateResponse:
    """
    Generate a BDD test template that can be used as a starting point for creating new BDD-style test cases.

    Args:
        test_case_name: Name of the test case
        test_description: Description for the BDD feature (recommended)
    """
    result = scripting.generate_bdd_template(test_case_name, test_description)
    return BDDTemplateResponse.from_bdd_result(result, test_case_name)


@tool
def suggest_code_improvements(
    test_content: str,
    test_suite_path: str,
) -> CodeSuggestionsResponse:
    """
    Analyze test content and suggest improvements based on project patterns.

    Args:
        test_content: The test code to analyze
        test_suite_path: Path to a `suite_*` directory.
    """
    suggestions = code_suggestions.suggest_code_improvements(
        test_content,
        squish_analysis.analyze_test_script_formats(test_suite_path),
        squish_analysis.analyze_object_references(test_suite_path),
        squish_analysis.analyze_global_scripts(),
        squish_rules.get_coding_conventions(),
    )
    return CodeSuggestionsResponse.from_suggestions(suggestions)


@tool
def extract_object_references(test_content: str) -> ObjectReferencesResponse:
    """
    Extract object references from test content to understand what objects are being used.

    Args:
        test_content: The test code to analyze
    """
    result = squish_analysis.extract_object_references(test_content)
    return ObjectReferencesResponse.from_object_references(result)


@tool
def generate_page_objects_from_snapshot(
    test_suite_path: str,
    xml_file_path: str,
    page_name: str,
    output_directory: str,
) -> PageObjectsGenerationResponse:
    """
    Generate page object references from an XML object snapshot file.

    This tool:
    1. Calls parse_object_snapshot.py to filter XML elements and generate basic definitions
    2. Analyzes object reference patterns to understand existing style and locations
    3. Determines output format (simple dicts vs classes/functions) based on existing patterns
    4. Writes the generated Python code to a local temporary file and returns its path

    Args:
        xml_file_path: Absolute path to the XML object snapshot file
        page_name: Name of the page/component these objects belong to
        test_suite_path: Path to a `suite_*` directory.
        output_directory: Existing directory where the temporary output file should be created

    Note:
        To generate the XML snapshot file, a testcase script has to call
            `saveObjectSnapshot(some_object, "snapshot_name.xml")`,
        where `some_object` is the root object of the component to capture.
        In case of an empty testcase, a variation of the following can be used:
            ```
            import object
            all_top_level_objects = object.topLevelObjects()
            top_level_object = all_top_level_objects[0] # change to a suitable index in case of multi-window apps.
            saveObjectSnapshot(top_level_object, "snapshot_name.xml")
            ```
        The snapshot will be placed next to the test script that is being executed,
        so the `xml_file_path` should be constructed accordingly.
    """
    obj_ref_context = squish_analysis.analyze_object_references(test_suite_path)
    pattern_analysis = squish_analysis.analyze_object_reference_patterns(obj_ref_context)
    output_strategy = determine_output_strategy_from_patterns(test_suite_path, pattern_analysis, page_name)

    parse_result = page_objects_from_snapshot(xml_file_path, page_name, output_strategy, output_directory)

    if not parse_result.success:
        raise AnalysisException(parse_result.error_message)

    return PageObjectsGenerationResponse.from_results(
        parse_result, output_strategy, pattern_analysis, obj_ref_context, page_name
    )


@tool
def analyze_object_map_structure(test_suite_path: str) -> ObjectMapStructureResponse:
    """
    Analyze the current object map structure to understand existing patterns.

    Args:
        test_suite_path: Path to a `suite_*` directory.
    """
    obj_ref_analysis = squish_analysis.analyze_object_references(test_suite_path)
    structure = squish_analysis.analyze_current_object_map_structure(obj_ref_analysis)
    return ObjectMapStructureResponse.from_structure(structure)
