"""
Squish Test Code Generation Module

Handles test code generation and file operations including:
- Test template generation (from analyzed patterns)
- BDD test template generation
- Test case file creation
- Suite configuration management
"""

import os
import re

from dataclasses import dataclass
from pathlib import Path

from squish_mcp.errors import FileOperationException
from squish_mcp.squish.analysis.models import GLOBAL_LOCATION_TYPES
from squish_mcp.squish.analysis.models import ExistingPatterns
from squish_mcp.squish.analysis.models import LocationType
from squish_mcp.squish.scripting.suite_conf_management import SuiteConfiguration
from squish_mcp.squish.scripting.templates import get_template


# Only these many most common APIs will be included in the template
COMMON_API_LIMIT = 5


@dataclass(frozen=True)
class TestTemplateResult:
    """Result of test template generation."""

    template: str
    object_pattern: LocationType | None


@dataclass(frozen=True)
class BDDTemplateResult:
    """Result of BDD template generation."""

    test_py_template: str
    feature_template: str
    step_definitions_template: str


@dataclass(frozen=True)
class TestSuiteCreationResult:
    """Result of creating a new test suite directory."""

    suite_path: str
    suite_conf_path: str
    names_path: str
    files_created: list[str]


@dataclass(frozen=True)
class TestCaseCreationResult:
    """Result of creating a new test case directory and files."""

    test_case_path: str
    test_py_path: str
    files_created: list[str]
    is_bdd: bool
    suite_conf_updated: bool
    feature_path: str | None = None
    suite_conf_path: str | None = None


def _build_imports(analysis: ExistingPatterns) -> tuple[list[str], LocationType | None]:
    """Build import lines and detect the primary object-reference location type."""
    imports = ["import squish"]
    object_pattern = analysis.object_patterns
    detected_pattern_type: LocationType | None = None

    if object_pattern.primary_location == LocationType.SUITE_NAMES:
        imports.append("import names")
        detected_pattern_type = LocationType.SUITE_NAMES
    elif object_pattern.primary_location in GLOBAL_LOCATION_TYPES:
        for file_path in object_pattern.files[:2]:
            basename = os.path.splitext(os.path.basename(file_path))[0]
            if basename not in ["__init__", "test"]:
                imports.append(f"import {basename}")
        detected_pattern_type = LocationType.GLOBAL_SIMPLE

    for imp in analysis.common_imports[:3]:
        if imp not in [i.split()[-1] for i in imports]:
            imports.append(f"import {imp}")

    return imports, detected_pattern_type


def _apis_contain(candidate: str, api_calls: list[str], exact: bool = False) -> bool:
    if exact:
        return candidate in api_calls
    return any(candidate in api_call for api_call in api_calls)


def _build_test_body(
    test_case_name: str,
    test_description: str,
    analysis: ExistingPatterns,
    setup_lines: list[str] | None,
    closing_lines: list[str] | None,
) -> str:
    """Build the function body for a generated test template."""
    object_pattern = analysis.object_patterns
    common_apis = list(analysis.api_usage.keys())[:COMMON_API_LIMIT]
    uses_suite_names = object_pattern.primary_location == LocationType.SUITE_NAMES

    body_lines: list[str] = [f'test.log("Starting test case: {test_case_name}")']

    if test_description:
        body_lines.append(f'test.log("Test description: {test_description}")')

    if setup_lines:
        body_lines.append("")
        body_lines.extend(setup_lines)

    if _apis_contain("startApplication", common_apis, exact=True):
        body_lines.append("")
        body_lines.append("# Start application")
        body_lines.append('# startApplication("YourApplication")')

    if _apis_contain("waitFor", common_apis):
        body_lines.append("")
        body_lines.append("# Wait for objects")
        obj_ref = "names.your_object" if uses_suite_names else "your_object_reference"
        body_lines.append(f"# waitForObject({obj_ref})")

    if _apis_contain("click", common_apis):
        body_lines.append("")
        body_lines.append("# Interact with UI")
        btn_ref = "names.your_button" if uses_suite_names else "your_button_reference"
        body_lines.append(f"# clickButton({btn_ref})")

    if _apis_contain("verify", common_apis):
        body_lines.append("")
        body_lines.append("# Verify results")
        body_lines.append('# test.verify(condition, "Verification message")')

    if closing_lines:
        body_lines.append("")
        body_lines.extend(closing_lines)

    body_lines.append("")
    body_lines.append(f'test.log("Test case {test_case_name} completed")')

    return "\n".join(f"    {s}" if s.strip() else "" for s in body_lines)


def generate_test_template(
    test_case_name: str,
    test_description: str = "",
    analysis: ExistingPatterns | None = None,
    setup_lines: list[str] | None = None,
    closing_lines: list[str] | None = None,
) -> TestTemplateResult:
    """
    Generate a test template based on existing patterns and project conventions.

    Args:
        test_case_name: Name of the test case
        test_description: Description of what the test should do
        analysis: Optional ExistingPatterns dataclass with patterns and conventions
        setup_lines: Optional code lines to insert after the opening log (e.g. setup conventions)
        closing_lines: Optional code lines to insert before the closing log (e.g. verification conventions)

    Returns:
        TestTemplateResult with generated template
    """
    if analysis is None:
        return _generate_basic_template(test_case_name, test_description)

    if not test_case_name.startswith("tst_"):
        test_case_name = f"tst_{test_case_name}"

    imports, detected_pattern_type = _build_imports(analysis)

    template = get_template("analysis_test_template.py.txt")
    template_content = template.substitute(
        name=test_case_name,
        description_comment=f"# Description: {test_description}\n" if test_description else "",
        imports="\n".join(imports),
        docstring_description=f"    {test_description}\n" if test_description else "",
        body=_build_test_body(test_case_name, test_description, analysis, setup_lines, closing_lines),
    ).rstrip("\n")

    return TestTemplateResult(template=template_content, object_pattern=detected_pattern_type)


def _generate_basic_template(test_case_name: str, test_description: str = "") -> TestTemplateResult:
    """Generate a basic fallback template when pattern analysis fails.

    Returns template with SUITE_NAMES pattern (using 'import names').
    """

    if not test_case_name.startswith("tst_"):
        test_case_name = f"tst_{test_case_name}"

    template = get_template("basic_test_template.py.txt")

    template_content = template.substitute(
        name=test_case_name,
        description=f"# Description: {test_description}" if test_description else "",
    )

    return TestTemplateResult(template=template_content, object_pattern=LocationType.SUITE_NAMES)


def _parse_bdd_step_pattern(step_pattern: str) -> tuple[str, list[str]]:
    """Parse a BDD step pattern with |any| placeholders and return the pattern and parameter names."""
    count = len(re.findall(r"\|any\|", step_pattern))
    if count == 1:
        parameter_names = ["value"]
    else:
        parameter_names = [f"value_{i + 1}" for i in range(count)]
    return step_pattern, parameter_names


def _gen_bdd_expression(function: str, params: list[str]) -> str:
    return f"{function}({', '.join(params)})"


def _generate_code_line(statement: str, indent: int = 0, commented_out: bool = False) -> str:
    return "    " * indent + ("# " if commented_out else "") + statement


def _generate_bdd_step_function(step_type: str, step_pattern: str, commented_out: bool = True) -> str:
    """
    Generate a BDD step function with proper parameter handling for |any| placeholders.

    Args:
        step_type: Type of step (given, when, then)
        step_pattern: Step pattern with |any| placeholders
        commented_out: Whether the body of the function should be commented out, defaults to False
    Returns:
        Generated step function code
    """
    pattern_for_decorator, parameter_names = _parse_bdd_step_pattern(step_pattern)

    # Create function signature
    params = ["context"] + parameter_names
    function_signature = f"def step({', '.join(params)}):"

    # Generate example implementation based on step pattern
    step_lower = step_pattern.lower()
    if "click" in step_lower or "press" in step_lower:
        target_obj = "waitForObject(names.button_name)"
        expr = _gen_bdd_expression("clickButton", [target_obj])
    elif "type" in step_lower or "enter" in step_lower:
        text = "sample text" if not parameter_names else parameter_names[0]
        target_obj = "waitForObject(names.input_field)"
        expr = _gen_bdd_expression("type", [target_obj, text])
    elif "verify" in step_lower or "see" in step_lower or "should" in step_lower:
        if parameter_names:
            target_obj = f"waitForObjectExists(names.expected_object_{parameter_names[0]})"
        else:
            target_obj = "waitForObjectExists(names.expected_object)"
        expr = _gen_bdd_expression("test.verify", [target_obj])
    else:
        expr = ""

    if expr:
        implementation = _generate_code_line(expr, indent=1, commented_out=commented_out)
    else:
        implementation = "    # TODO: Implement this step"

    if commented_out or not expr:
        implementation += "\n" + _generate_code_line("pass", indent=1)

    return f'''@{step_type}("{pattern_for_decorator}")
{function_signature}
{implementation}
'''


def generate_bdd_template(test_case_name: str, test_description: str = "") -> BDDTemplateResult:
    """
    Generate a BDD test template with proper QtCare Squish BDD structure.
    Supports |any| variable input syntax for parameterized steps.

    Args:
        test_case_name: Name of the test case
        test_description: Optional description of what the test should do

    Returns:
        BDDTemplateResult with test.py, feature, and step definition templates
    """
    # Generate test.py content
    test_py_content = get_template("bdd_script.py.txt").substitute()

    # Generate example step definitions with |any| support
    example_steps = [
        ("given", "The title of the application is |any|"),
        ("when", "I click the |any| button"),
        ("then", "I should see |any| in the result"),
    ]

    step_definitions_content = """# Example step definitions with variable input support
# Use |any| in step patterns to capture variable inputs

"""

    for step_type, pattern in example_steps:
        step_definitions_content += _generate_bdd_step_function(step_type, pattern) + "\n\n"

    # Generate test.feature content with examples using |any| syntax
    feature_template = get_template("bdd_feature_template.txt")

    feature_content = feature_template.substitute(
        name=test_case_name,
        test_description=test_description,
        feature_description=test_description if test_description else "Brief description of the feature under test",
        scenario_description=test_description if test_description else "Example scenario with variable inputs",
    )

    return BDDTemplateResult(
        test_py_template=test_py_content,
        feature_template=feature_content,
        step_definitions_template=step_definitions_content,
    )


def create_test_suite(suite_path: str, wrapper: str = "Qt") -> TestSuiteCreationResult:
    """Create a new Squish test suite directory with the standard structure.

    Structure created (based on suite_example_objects)::

        suite_path/
            suite.conf
            shared/scripts/
                    names.py

    Args:
        suite_path: Absolute path to the suite directory to create. (must start with 'suite_')
        wrapper: Wrapper name to include in suite.conf (default 'Qt').

    Returns:
        TestSuiteCreationResult with paths to all created artifacts.

    Raises:
        FileOperationException: If the directory name is invalid, the suite already
            exists, or file creation fails.
    """
    suite_name = os.path.basename(suite_path)
    if os.path.exists(suite_path):
        raise FileOperationException(f"Suite already exists: {suite_path}")

    if not suite_name.startswith("suite_"):
        raise FileOperationException(f"Suite directory name must start with 'suite_': {suite_name}")

    try:
        os.makedirs(suite_path, exist_ok=True)

        # Create suite.conf
        config = (
            SuiteConfiguration()
            .append_value_to_key("WRAPPERS", wrapper)
            .append_value_to_key("LANGUAGE", "Python")
            .append_value_to_key("OBJECTMAPSTYLE", "script")
            .append_value_to_key("VERSION", "3")
        )
        config.save_in_suite(Path(suite_path))

        # Create shared/scripts/names.py
        shared_scripts_dir = os.path.join(suite_path, "shared", "scripts")
        os.makedirs(shared_scripts_dir, exist_ok=True)
        names_path = os.path.join(shared_scripts_dir, "names.py")

        with open(names_path, "w", encoding="utf-8") as f:
            f.write("# encoding: UTF-8\n\nfrom objectmaphelper import *\n")

        return TestSuiteCreationResult(
            suite_path=suite_path,
            suite_conf_path=str(SuiteConfiguration.get_path(Path(suite_path))),
            names_path=names_path,
            files_created=["suite.conf", "shared/scripts/names.py"],
        )
    except FileOperationException:
        raise
    except Exception as e:
        raise FileOperationException(f"Error creating test suite: {str(e)}") from e


def create_test_case(  # noqa: PLR0913
    suite_path: str,
    test_case_name: str,
    test_content: str = "",
    is_bdd: bool = False,
    test_description: str = "",
) -> TestCaseCreationResult:
    """
    Create a new Squish test case within an existing test suite.

    Args:
        suite_path: Absolute path to the test suite directory (must start with 'suite_')
        test_case_name: Name of the test case (will be prefixed with 'tst_' if not already)
        test_content: Python code content for the test.py file (optional)
        is_bdd: Whether to create a BDD test with proper structure (default: False)
        test_description: Description for BDD feature (optional)

    Returns:
        TestCaseCreationResult with paths and creation status

    Raises:
        FileOperationException: If suite path invalid or file creation fails
    """

    # Validate suite path
    if not os.path.exists(suite_path):
        raise FileOperationException(f"Suite path does not exist: {suite_path}")

    if not os.path.basename(suite_path).startswith("suite_"):
        raise FileOperationException(f"Suite directory name must start with 'suite_': {os.path.basename(suite_path)}")

    # Ensure test case name starts with 'tst_'
    if not test_case_name.startswith("tst_"):
        test_case_name = f"tst_{test_case_name}"

    # Create test case directory
    test_case_path = os.path.join(suite_path, test_case_name)

    try:
        # Create the test case directory
        os.makedirs(test_case_path, exist_ok=True)

        # Create test.py file
        test_py_path = os.path.join(test_case_path, "test.py")

        files_created = ["test.py"]

        # Determine what content to use
        if is_bdd:
            # Create BDD test structure
            bdd_template = generate_bdd_template(test_case_name, test_description)
            test_content = bdd_template.test_py_template

            # Also create the test.feature file
            feature_path = os.path.join(test_case_path, "test.feature")
            with open(feature_path, "w", encoding="utf-8") as f:
                f.write(bdd_template.feature_template)
            files_created.append("test.feature")

        elif not test_content.strip():
            # Create a basic test template
            template = get_template("testcase.py.txt")
            test_content = template.substitute(name=test_case_name)

        # Write the test.py file
        with open(test_py_path, "w", encoding="utf-8") as f:
            f.write(test_content)

        # Prepare optional fields
        feature_path_result = None
        if is_bdd:
            feature_path_result = os.path.join(test_case_path, "test.feature")

        suite_conf_updated_result = False
        suite_conf_path_result = None
        try:
            old_config = SuiteConfiguration.read(Path(suite_path))
            updated_config = old_config.append_value_to_key("TEST_CASES", test_case_name)
            updated_config.save_in_suite(Path(suite_path))

        except FileOperationException:
            # Ignore suite.conf update errors - test case was created successfully
            pass

        return TestCaseCreationResult(
            test_case_path=test_case_path,
            test_py_path=test_py_path,
            files_created=files_created,
            is_bdd=is_bdd,
            suite_conf_updated=suite_conf_updated_result,
            feature_path=feature_path_result,
            suite_conf_path=suite_conf_path_result,
        )

    except Exception as e:
        raise FileOperationException(f"Error creating test case: {str(e)}") from e
