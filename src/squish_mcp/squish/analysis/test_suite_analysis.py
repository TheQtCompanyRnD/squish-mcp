"""Test suite format analysis.

Analyzes a Squish test suite to understand test script formats, BDD structure,
and object reference usage patterns.
"""

import glob
import logging
import os
import re

from squish_mcp.squish.analysis import models
from squish_mcp.squish.analysis.suite_directory import require_suite_directory


log = logging.getLogger(__name__)

_STANDARD_IMPORTS = ("squish", "__", "sys", "os", "time", "datetime")
_STEP_STANDARD_IMPORTS = (*_STANDARD_IMPORTS, "behave")

_TEST_PREVIEW_MAX_LENGTH = 1000
_STEP_PREVIEW_MAX_LENGTH = 500

_API_CALL_RE = re.compile(
    r"\b("
    r"waitForObject|waitForObjectExists|findObject|"
    r"clickButton|clickTab|clickLink|mouseClick|doubleClick|"
    r"startApplication|tapObject|longPress|snooze|"
    r"type|"
    r"test\.verify|test\.compare|test\.log|test\.vp|test\.xverify|test\.xcompare"
    r")\s*\("
)
_IMPORT_RE = re.compile(r"^(?:import|from)\s+([^\s]+)", re.MULTILINE)
_OBJ_REF_RE = re.compile(r"names\.[A-Za-z_][A-Za-z0-9_]*")
_BDD_STEP_RE = re.compile(r"^\s*(Given|When|Then|And|But)\s+(.+)", re.MULTILINE)
_STEP_DEF_RE = re.compile(r'@(given|when|then|step)\s*\(["\'](.+?)["\']\)', re.IGNORECASE)
_STEP_PLACEHOLDER_RE = re.compile(r"\\\|[^|]+\\\|")


def _truncate_preview(content: str, max_length: int) -> str:
    if len(content) > max_length:
        return content[:max_length] + "..."
    return content


def _has_non_standard_imports(imports: list[str], standard: tuple[str, ...] = _STANDARD_IMPORTS) -> bool:
    return any(imp for imp in imports if not imp.startswith(standard))


def _analyze_test_script_directory(tst_dir: str) -> models.TestCaseInfo | None:
    """Analyze a single tst_* directory and return its TestCaseInfo."""
    test_py_path = os.path.join(tst_dir, "test.py")
    if not os.path.exists(test_py_path):
        return None

    try:
        with open(test_py_path, "r", encoding="utf-8") as f:
            content = f.read()

        feature_file_path = os.path.join(tst_dir, "test.feature")
        has_feature_file = os.path.exists(feature_file_path)
        feature_content: str | None = None
        bdd_steps_used: list[tuple[str, str]] = []

        if has_feature_file:
            try:
                with open(feature_file_path, "r", encoding="utf-8") as f:
                    feature_content = f.read()
                bdd_steps_used = _BDD_STEP_RE.findall(feature_content)
            except Exception:
                feature_content = "Could not read feature file"

        api_calls = _API_CALL_RE.findall(content)
        imports = _IMPORT_RE.findall(content)
        obj_refs = _OBJ_REF_RE.findall(content)

        return models.TestCaseInfo(
            name=os.path.basename(tst_dir),
            path=test_py_path,
            squish_api_calls=api_calls,
            imports=imports,
            object_references=obj_refs,
            global_script_usage=_has_non_standard_imports(imports),
            content_preview=_truncate_preview(content, _TEST_PREVIEW_MAX_LENGTH),
            is_bdd=has_feature_file,
            feature_file=feature_file_path if has_feature_file else None,
            feature_content=feature_content,
            bdd_steps_used=bdd_steps_used,
            uses_behave="behave" in content.lower() or "feature" in content.lower(),
        )

    except Exception as e:
        return models.TestCaseInfo(
            name=os.path.basename(tst_dir),
            path=test_py_path,
            squish_api_calls=[],
            imports=[],
            object_references=[],
            global_script_usage=False,
            content_preview="",
            is_bdd=False,
            feature_file=None,
            feature_content=None,
            bdd_steps_used=[],
            uses_behave=False,
            error=f"Could not analyze: {e}",
        )


def _analyze_steps_directory(steps_dir: str) -> list[models.StepFileInfo]:
    """Analyze all step definition files in a BDD steps directory."""
    step_file_infos: list[models.StepFileInfo] = []

    for step_file in glob.glob(os.path.join(steps_dir, "*.py")):
        if not os.path.isfile(step_file):
            continue
        try:
            with open(step_file, "r", encoding="utf-8") as f:
                step_content = f.read()

            step_definitions = _STEP_DEF_RE.findall(step_content)

            variable_steps = []
            for step_type, step_pattern in step_definitions:
                if "|any|" in step_pattern:
                    variable_steps.append(
                        {
                            "type": step_type,
                            "pattern": step_pattern,
                            "variable_count": step_pattern.count("|any|"),
                        }
                    )

            step_imports = _IMPORT_RE.findall(step_content)

            step_file_infos.append(
                models.StepFileInfo(
                    name=os.path.basename(step_file),
                    path=step_file,
                    step_definitions=step_definitions,
                    variable_steps=variable_steps,
                    imports=step_imports,
                    global_script_usage=_has_non_standard_imports(step_imports, _STEP_STANDARD_IMPORTS),
                    content_preview=_truncate_preview(step_content, _STEP_PREVIEW_MAX_LENGTH),
                )
            )

        except Exception as e:
            step_file_infos.append(
                models.StepFileInfo(
                    name=os.path.basename(step_file),
                    path=step_file,
                    step_definitions=[],
                    variable_steps=[],
                    imports=[],
                    global_script_usage=False,
                    content_preview="",
                    error=f"Could not analyze: {e}",
                )
            )

    return step_file_infos


def _collect_resources(suite_dir: str) -> list[models.ResourceFileInfo]:
    """Collect resource files (names.py, objects.map, etc.) from a suite directory."""
    resources: list[models.ResourceFileInfo] = []
    seen: set[str] = set()
    for pattern in ["names.py", "objects.map", "*.py"]:
        for path in glob.glob(os.path.join(suite_dir, pattern)):
            if os.path.isfile(path) and path not in seen:
                seen.add(path)
                resources.append(models.ResourceFileInfo(name=os.path.basename(path), path=path))
    return resources


def _build_bdd_info(suite_dir: str) -> models.BDDSuiteInfo | None:
    """Build BDD suite info if the suite has a shared/steps directory."""
    steps_dir = os.path.join(suite_dir, "shared", "steps")
    if not os.path.isdir(steps_dir):
        return None

    step_file_infos = _analyze_steps_directory(steps_dir)
    all_step_definitions = [sd for sf in step_file_infos for sd in sf.step_definitions]

    return models.BDDSuiteInfo(
        name=os.path.basename(suite_dir),
        path=suite_dir,
        steps_directory=steps_dir,
        step_files=step_file_infos,
        step_definitions=all_step_definitions,
    )


def _analyze_test_suite(suite_dir: str) -> models.TestSuiteInfo:
    """Analyze a complete suite_* directory."""
    test_cases: list[models.TestCaseInfo] = []
    for tst_dir in glob.glob(os.path.join(suite_dir, "tst_*")):
        if not os.path.isdir(tst_dir):
            continue
        test_case = _analyze_test_script_directory(tst_dir)
        if test_case is not None:
            test_cases.append(test_case)

    return models.TestSuiteInfo(
        path=suite_dir,
        name=os.path.basename(suite_dir),
        test_cases=test_cases,
        resources=_collect_resources(suite_dir),
        bdd_info=_build_bdd_info(suite_dir),
    )


def _compute_patterns(suite: models.TestSuiteInfo) -> models.TestFormatPatterns:
    """Derive patterns from the collected test suite."""
    squish_api_usage: list[str] = []
    global_script_imports: list[str] = []
    object_usage: list[str] = []
    total_bdd_tests = 0
    common_steps: list[str] = []
    bdd_step_definitions: list[tuple[str, str]] = []

    if suite.bdd_info:
        bdd_step_definitions.extend(suite.bdd_info.step_definitions)

    for tc in suite.test_cases:
        squish_api_usage.extend(tc.squish_api_calls)
        object_usage.extend(tc.object_references)
        global_script_imports.extend(imp for imp in tc.imports if not imp.startswith(_STANDARD_IMPORTS))
        if tc.is_bdd:
            total_bdd_tests += 1
            common_steps.extend(step_text for _, step_text in tc.bdd_steps_used)

    return models.TestFormatPatterns(
        squish_api_usage=squish_api_usage,
        global_script_imports=global_script_imports,
        object_usage=object_usage,
        bdd_usage=models.BDDUsagePatterns(
            total_bdd_tests=total_bdd_tests,
            common_steps=common_steps,
            step_definitions=bdd_step_definitions,
        ),
    )


def analyze_test_script_formats(test_suite_path: str) -> models.TestFormatAnalysis:
    """Analyze an existing Squish test suite to understand test script formats.

    Scans the suite directory to discover test cases, BDD structure,
    API usage patterns, and global script imports.

    Args:
        test_suite_path: Path to a `suite_*` directory.

    Returns:
        models.TestFormatAnalysis dataclass instance.
    """
    suite_dir = require_suite_directory(test_suite_path)
    suite = _analyze_test_suite(suite_dir)

    return models.TestFormatAnalysis(
        suite=suite,
        patterns=_compute_patterns(suite),
    )


def analyze_existing_patterns(
    test_format_context: models.TestFormatAnalysis | None,
    object_ref_context: models.ObjectReferenceAnalysis | None,
    global_script_context: models.GlobalScriptsAnalysis | None,
) -> models.ExistingPatterns:
    """Synthesize aggregated project patterns from existing analysis results."""
    common_imports: list[str] = []
    api_usage: dict[str, int] = {}
    object_refs: list[str] = []
    primary_location = models.LocationType.OTHER
    object_files: list[str] = []

    if test_format_context is not None:
        patterns = test_format_context.patterns
        common_imports = list(set(patterns.global_script_imports))

        api_frequency: dict[str, int] = {}
        for call in patterns.squish_api_usage:
            api_frequency[call] = api_frequency.get(call, 0) + 1
        api_usage = dict(sorted(api_frequency.items(), key=lambda item: item[1], reverse=True))
        object_refs = list(set(patterns.object_usage))

    if object_ref_context is not None:
        global_files = [f for f in object_ref_context.files if f.type in models.GLOBAL_LOCATION_TYPES]
        suite_files = [f for f in object_ref_context.files if f.type == models.LocationType.SUITE_NAMES]
        other_files = [f for f in object_ref_context.files if f.type == models.LocationType.OTHER]

        if global_files:
            primary_location = global_files[0].type
            object_files = [f.path for f in global_files]
        elif suite_files:
            primary_location = models.LocationType.SUITE_NAMES
            object_files = [f.path for f in suite_files]
        else:
            primary_location = models.LocationType.OTHER
            object_files = [f.path for f in other_files]

    available_functions: list[str] = []
    directories: list[str] = []
    if global_script_context is not None:
        files = global_script_context.files
        common_functions: list[str] = []
        for file_info in files:
            common_functions.extend(file_info.functions)
        available_functions = common_functions[:20]
        directories = global_script_context.directories

    return models.ExistingPatterns(
        common_imports=common_imports,
        object_patterns=models.ObjectPatterns(
            references=object_refs,
            primary_location=primary_location,
            files=object_files,
        ),
        api_usage=api_usage,
        global_script_usage=models.GlobalScriptUsage(
            available_functions=available_functions,
            directories=directories,
        ),
    )


def _extract_bdd_relationships(
    step_definitions: list[tuple[str, str]],
    suite_name: str,
    feature_file: str,
    bdd_steps_used: list[tuple[str, str]],
) -> list[models.StepRelationship]:
    relationships: list[models.StepRelationship] = []
    for step_keyword, step_text in bdd_steps_used:
        # Previously we linked each used step to every definition, producing many false
        # relationships. We now filter by compatible step type and actual text/pattern match.
        allowed_types = _allowed_step_definition_types(step_keyword)
        for step_type, step_pattern in step_definitions:
            normalized_step_type = step_type.lower()
            if normalized_step_type not in allowed_types:
                continue
            if not _step_matches_pattern(step_text, step_pattern):
                continue
            relationships.append(
                models.StepRelationship(
                    feature_file=feature_file,
                    step_used=f"{step_keyword} {step_text}",
                    step_definition=f"@{normalized_step_type}('{step_pattern}')",
                    suite=suite_name,
                )
            )
    return relationships


def _allowed_step_definition_types(step_keyword: str) -> set[str]:
    normalized_keyword = step_keyword.lower()
    # "And"/"But" inherit context from previous steps in Gherkin, so allow all
    # explicit step-definition types here instead of forcing one.
    if normalized_keyword in {"and", "but"}:
        return {"given", "when", "then", "step"}
    if normalized_keyword in {"given", "when", "then"}:
        return {normalized_keyword, "step"}
    return {"step"}


def _step_matches_pattern(step_text: str, step_pattern: str) -> bool:
    normalized_text = step_text.strip()
    normalized_pattern = step_pattern.strip().replace('\\"', '"').replace("\\'", "'")
    if not normalized_text or not normalized_pattern:
        return False

    # Treat placeholders (for example |any|) as wildcards and match the full step text.
    escaped_pattern = re.escape(normalized_pattern)
    escaped_pattern = _STEP_PLACEHOLDER_RE.sub(".+?", escaped_pattern)
    escaped_pattern = escaped_pattern.replace(r"\ ", r"\s+")

    if re.fullmatch(escaped_pattern, normalized_text, flags=re.IGNORECASE):
        return True

    # Fallback: accept raw regex patterns if the step definition uses them.
    try:
        return re.fullmatch(normalized_pattern, normalized_text, flags=re.IGNORECASE) is not None
    except re.error:
        return False


def _extract_suite_bdd_context(
    suite: models.TestSuiteInfo,
) -> tuple[list[models.StepRelationship], list[models.FeatureFileInfo]]:
    relationships: list[models.StepRelationship] = []
    feature_infos: list[models.FeatureFileInfo] = []

    if not suite.bdd_info:
        return relationships, feature_infos

    log.debug("Processing test suite: %s", suite.name)
    for test_case in suite.test_cases:
        if not (test_case.is_bdd and test_case.feature_file and test_case.feature_content):
            continue

        log.debug("Processing test case: %s with feature file: %s", test_case.name, test_case.feature_file)

        feature_infos.append(
            models.FeatureFileInfo(
                test_case=test_case.name,
                suite=suite.name,
                feature_file=test_case.feature_file,
                feature_content=test_case.feature_content,
                steps_used=test_case.bdd_steps_used,
            )
        )

        relationships.extend(
            _extract_bdd_relationships(
                suite.bdd_info.step_definitions,
                suite.name,
                test_case.feature_file,
                test_case.bdd_steps_used,
            )
        )

    return relationships, feature_infos


def extract_bdd_context(test_format_analysis: models.TestFormatAnalysis) -> models.BDDContext:
    """Extract comprehensive BDD context from test format analysis.

    Processes test format analysis to extract feature files, step definitions,
    and relationships between tests, features, and step implementations for
    a single suite.

    Args:
        test_format_analysis: The test format analysis from analyze_test_script_formats().

    Returns:
        models.BDDContext dataclass instance.
    """
    has_bdd_tests = False
    bdd_suite: models.BDDSuiteInfo | None = None
    feature_files: list[models.FeatureFileInfo] = []
    relationships: list[models.StepRelationship] = []

    suite = test_format_analysis.suite
    if suite.bdd_info is not None:
        has_bdd_tests = True
        bdd_suite = suite.bdd_info
        suite_relationships, suite_feature_files = _extract_suite_bdd_context(suite)
        feature_files.extend(suite_feature_files)
        relationships.extend(suite_relationships)

    log.debug("Has BDD tests: %s, feature files: %d", has_bdd_tests, len(feature_files))

    return models.BDDContext(
        has_bdd_tests=has_bdd_tests,
        bdd_suite=bdd_suite,
        feature_files=feature_files,
        relationships=relationships,
    )


def extract_object_references(test_content: str) -> models.ObjectReferences:
    """Extract object references from test content.

    Parses test code to identify object references by category:
    names.* references, direct objects, global script objects, and unknown objects.

    Args:
        test_content: The test code to analyze.

    Returns:
        models.ObjectReferences with extracted references.
    """
    names_objects: list[str] = []
    direct_objects: list[str] = []
    global_script_objects: list[str] = []
    unknown_objects: list[str] = []

    names_refs = re.findall(r"names\.([A-Za-z_][A-Za-z0-9_]*)", test_content)
    names_objects = list(set(names_refs))

    function_patterns = [
        r"waitForObject\s*\(\s*([^)]+)\s*\)",
        r"clickButton\s*\(\s*([^)]+)\s*\)",
        r"findObject\s*\(\s*([^)]+)\s*\)",
        r"mouseClick\s*\(\s*([^)]+)\s*\)",
        r"type\s*\(\s*([^)]+)\s*,",
    ]

    for pattern in function_patterns:
        matches = re.findall(pattern, test_content)
        for match in matches:
            obj_ref = match.strip().strip("\"'")
            if not obj_ref.startswith("names.") and obj_ref not in direct_objects:
                if "." in obj_ref and not obj_ref.startswith(("names.", "self.")):
                    global_script_objects.append(obj_ref)
                elif obj_ref.isidentifier():
                    unknown_objects.append(obj_ref)

    return models.ObjectReferences(
        names_objects=names_objects,
        direct_objects=direct_objects,
        global_script_objects=global_script_objects,
        unknown_objects=unknown_objects,
    )
