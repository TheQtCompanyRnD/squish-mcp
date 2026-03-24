from dataclasses import dataclass
from enum import Enum


class LocationType(str, Enum):
    """How and where object references are stored."""

    SUITE_NAMES = "suite_names"
    GLOBAL_POM = "global_pom"
    GLOBAL_FUNCTIONS = "global_functions"
    GLOBAL_SIMPLE = "global_simple"
    OTHER = "other"


GLOBAL_LOCATION_TYPES: frozenset["LocationType"] = frozenset(
    {
        LocationType.GLOBAL_POM,
        LocationType.GLOBAL_FUNCTIONS,
        LocationType.GLOBAL_SIMPLE,
    }
)


class OrganizationStrategy(str, Enum):
    """Page organization strategy type."""

    GLOBAL_FILES = "global_files"
    SUITE_NAMES = "suite_names"
    UNKNOWN = "unknown"


# ==============================================================================
# Test Format Analysis
# ==============================================================================


@dataclass(frozen=True)
class TestCaseInfo:
    """Information about a single test case."""

    name: str
    path: str
    squish_api_calls: list[str]
    imports: list[str]
    object_references: list[str]
    global_script_usage: bool
    content_preview: str
    # BDD fields
    is_bdd: bool
    feature_file: str | None
    feature_content: str | None
    bdd_steps_used: list[tuple[str, str]]  # (step_type, step_text)
    uses_behave: bool
    # Error handling
    error: str | None = None


@dataclass(frozen=True)
class StepFileInfo:
    """Information about a BDD step definition file."""

    name: str
    path: str
    step_definitions: list[tuple[str, str]]  # (step_type, pattern)
    variable_steps: list[dict]  # Keep as dict - structure varies
    imports: list[str]
    global_script_usage: bool
    content_preview: str
    error: str | None = None


@dataclass(frozen=True)
class ResourceFileInfo:
    """Resource file metadata."""

    name: str
    path: str


@dataclass(frozen=True)
class TestSuiteInfo:
    """Information about a test suite."""

    path: str
    name: str
    test_cases: list[TestCaseInfo]
    resources: list[ResourceFileInfo]
    bdd_info: "BDDSuiteInfo | None" = None


@dataclass(frozen=True)
class BDDUsagePatterns:
    """BDD usage statistics."""

    total_bdd_tests: int
    common_steps: list[str]
    step_definitions: list[tuple[str, str]]


@dataclass(frozen=True)
class TestFormatPatterns:
    """Patterns extracted from test analysis."""

    squish_api_usage: list[str]
    global_script_imports: list[str]
    object_usage: list[str]
    bdd_usage: BDDUsagePatterns


@dataclass(frozen=True)
class TestFormatAnalysis:
    """Complete test format analysis result for a single suite."""

    suite: TestSuiteInfo
    patterns: TestFormatPatterns


# ==============================================================================
# Object Reference Analysis
# ==============================================================================


@dataclass(frozen=True)
class ObjectFileLocation:
    """Unified object file location information.

    Different location types have different optional fields:
    - SUITE_NAMES: suite, object_count, sample_objects, content_preview, error
    - GLOBAL_*: name, content_preview, error
    - OTHER: name only
    """

    type: LocationType
    path: str
    # Common optional fields
    name: str | None = None
    # Suite-specific fields
    suite: str | None = None
    object_count: int | None = None
    sample_objects: list[str] | None = None
    # Analysis fields
    content_preview: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class ObjectReferenceAnalysis:
    """Complete object reference analysis."""

    files: list[ObjectFileLocation]


@dataclass(frozen=True)
class ObjectReferencePatterns:
    """Patterns detected in object reference usage."""

    has_pom_classes: bool
    has_function_based: bool
    has_simple_dicts: bool
    global_script_locations: list[str]
    suite_names_locations: list[str]
    preferred_location_type: LocationType
    class_patterns: list[str]
    function_patterns: list[str]


# ==============================================================================
# Object Map Structure
# ==============================================================================


@dataclass(frozen=True)
class ObjectFileInfo:
    """Information about an object file in the map."""

    type: LocationType
    path: str
    objects: list[dict]  # Keep as dict - structure varies by Squish version
    patterns: list[str]
    suite: str | None = None  # Only for suite_names type


@dataclass(frozen=True)
class ReferencePatterns:
    """Object reference patterns in the codebase."""

    common_containers: list[str]
    naming_patterns: list[str]
    property_patterns: list[str]


@dataclass(frozen=True)
class PageOrganization:
    """Page organization strategy."""

    strategy: OrganizationStrategy
    base_directory: str | None = None  # For global_files strategy
    suite: str | None = None  # For suite_names strategy


@dataclass(frozen=True)
class ObjectDefinition:
    """Definition of a single object."""

    definition: dict
    file: str
    type: LocationType


@dataclass(frozen=True)
class ObjectMapStructure:
    """Current object map structure analysis."""

    object_files: list[ObjectFileInfo]
    reference_patterns: ReferencePatterns
    page_organization: PageOrganization
    existing_objects: dict[str, ObjectDefinition]  # object_name -> definition


# ==============================================================================
# BDD Analysis
# ==============================================================================


@dataclass(frozen=True)
class BDDSuiteInfo:
    """BDD suite information."""

    name: str
    path: str
    steps_directory: str
    step_files: list[StepFileInfo]
    step_definitions: list[tuple[str, str]]


@dataclass(frozen=True)
class FeatureFileInfo:
    """Feature file information."""

    test_case: str
    suite: str
    feature_file: str
    feature_content: str
    steps_used: list[tuple[str, str]]


@dataclass(frozen=True)
class StepRelationship:
    """Relationship between feature file step and step definition."""

    feature_file: str
    step_used: str
    step_definition: str
    suite: str


@dataclass(frozen=True)
class BDDContext:
    """Comprehensive BDD context."""

    has_bdd_tests: bool
    bdd_suite: BDDSuiteInfo | None
    feature_files: list[FeatureFileInfo]
    relationships: list[StepRelationship]


# ==============================================================================
# Documentation
# ==============================================================================


@dataclass(frozen=True)
class APIDocumentation:
    """Squish API documentation."""

    local_path: str
    functions: list[str]
    code_examples: list[str]
    sections: list[str]
    content_preview: str


@dataclass(frozen=True)
class BDDDocumentation:
    """Squish BDD documentation."""

    url: str
    step_definition_patterns: list[tuple[str, str]]
    placeholder_syntax: list[str]
    hook_patterns: list[str]
    file_structure: list[str]
    context_object_features: list[str]
    implementation_examples: list[str]
    content_preview: str


# ==============================================================================
# Global Scripts Analysis
# ==============================================================================


@dataclass(frozen=True)
class GlobalScriptFileInfo:
    """Information about a global script file."""

    path: str
    relative_path: str
    size: int
    lines: int
    functions: list[str]
    classes: list[str]
    imports: list[str]
    content: str
    error: str | None = None


@dataclass(frozen=True)
class GlobalScriptsAnalysis:
    """Global scripts analysis result."""

    directories: list[str]
    files: list[GlobalScriptFileInfo]


# ==============================================================================
# Existing Patterns
# ==============================================================================


@dataclass(frozen=True)
class ObjectPatterns:
    """Object reference patterns."""

    references: list[str]
    primary_location: LocationType
    files: list[str]


@dataclass(frozen=True)
class GlobalScriptUsage:
    """Global script usage information."""

    available_functions: list[str]
    directories: list[str]


@dataclass(frozen=True)
class ExistingPatterns:
    """Synthesized pattern analysis from all contexts."""

    common_imports: list[str]
    object_patterns: ObjectPatterns
    api_usage: dict[str, int]  # API call -> frequency
    global_script_usage: GlobalScriptUsage


@dataclass(frozen=True)
class ObjectReferences:
    """Object references extracted from test content."""

    names_objects: list[str]
    direct_objects: list[str]
    global_script_objects: list[str]
    unknown_objects: list[str]
