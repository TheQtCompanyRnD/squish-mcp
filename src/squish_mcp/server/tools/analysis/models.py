from dataclasses import asdict

from pydantic import BaseModel
from pydantic import Field

from squish_mcp.squish.analysis.context_models import CodeSuggestion
from squish_mcp.squish.analysis.context_models import SquishRules
from squish_mcp.squish.analysis.models import GLOBAL_LOCATION_TYPES
from squish_mcp.squish.analysis.models import APIDocumentation
from squish_mcp.squish.analysis.models import BDDContext
from squish_mcp.squish.analysis.models import BDDDocumentation
from squish_mcp.squish.analysis.models import ExistingPatterns
from squish_mcp.squish.analysis.models import GlobalScriptsAnalysis
from squish_mcp.squish.analysis.models import LocationType
from squish_mcp.squish.analysis.models import ObjectMapStructure
from squish_mcp.squish.analysis.models import ObjectReferenceAnalysis
from squish_mcp.squish.analysis.models import ObjectReferencePatterns
from squish_mcp.squish.analysis.models import ObjectReferences
from squish_mcp.squish.scripting.code_generation import BDDTemplateResult
from squish_mcp.squish.scripting.code_generation import TestTemplateResult
from squish_mcp.squish.scripting.pom_generation import OutputStrategy
from squish_mcp.squish.scripting.pom_generation import SnapshotParseResult


class ExistingPatternsResponse(BaseModel):
    """Analyzed test patterns from the existing codebase."""

    common_imports: list[str] = Field(description="Most frequently used imports across test scripts")
    api_usage: dict[str, int] = Field(description="Squish API call frequencies, e.g. {'waitForObject': 12}")
    global_scripts_available_functions: list[str] = Field(
        description="Functions available from global script directories"
    )
    global_scripts_directories: list[str] = Field(description="Paths to global script directories")
    object_references: list[str] = Field(description="Object references found across test scripts")
    object_ref_primary_location: str = Field(
        description="Primary storage location for object references (e.g. 'suite_names', 'global_pom')"
    )
    object_ref_files: list[str] = Field(description="Files containing object reference definitions")

    @classmethod
    def from_existing_patterns(cls, result: ExistingPatterns) -> "ExistingPatternsResponse":
        return cls(
            common_imports=result.common_imports,
            api_usage=result.api_usage,
            global_scripts_available_functions=result.global_script_usage.available_functions,
            global_scripts_directories=result.global_script_usage.directories,
            object_references=result.object_patterns.references,
            object_ref_primary_location=result.object_patterns.primary_location.value,
            object_ref_files=result.object_patterns.files,
        )


class ObjectReferenceAnalysisResponse(BaseModel):
    """Object-reference analysis."""

    message: str = Field(description="Summary of object reference files found")
    files: list[dict] = Field(description="Object file locations with type, path, object counts, and previews")

    @classmethod
    def from_object_reference_analysis(cls, result: ObjectReferenceAnalysis) -> "ObjectReferenceAnalysisResponse":
        global_files = [f for f in result.files if f.type in GLOBAL_LOCATION_TYPES]
        suite_files = [f for f in result.files if f.type == LocationType.SUITE_NAMES]
        return cls(
            message=(
                f"Found {len(result.files)} object reference files "
                f"({len(global_files)} global, {len(suite_files)} suite-local)"
            ),
            files=[asdict(f) for f in result.files],
        )


class GlobalScriptsAnalysisResponse(BaseModel):
    """Global-script analysis."""

    message: str = Field(description="Summary of global scripts found")
    directories: list[str] = Field(description="Paths to global script directories")
    files: list[dict] = Field(description="Script files with path, functions, classes, imports, and content preview")

    @classmethod
    def from_global_scripts_analysis(cls, result: GlobalScriptsAnalysis) -> "GlobalScriptsAnalysisResponse":
        total_functions = sum(len(f.functions) for f in result.files if f.error is None)
        return cls(
            message=(
                f"Found {len(result.files)} script files with {total_functions} functions "
                f"across {len(result.directories)} directories"
            ),
            directories=result.directories,
            files=[asdict(f) for f in result.files],
        )


class SquishAPIDocumentationResponse(BaseModel):
    """Squish API documentation analysis."""

    message: str = Field(description="Summary of API documentation loaded")
    local_path: str = Field(description="Path to local API documentation file")
    functions: list[str] = Field(description="Available Squish API function names")
    code_examples: list[str] = Field(description="Code examples from the documentation")
    sections: list[str] = Field(description="Documentation section headings")
    content_preview: str = Field(description="Preview of the documentation content")

    @classmethod
    def from_api_documentation(cls, result: APIDocumentation) -> "SquishAPIDocumentationResponse":
        return cls(
            message=(
                f"Loaded API documentation with {len(result.functions)} functions "
                f"and {len(result.code_examples)} examples"
            ),
            local_path=result.local_path,
            functions=result.functions,
            code_examples=result.code_examples,
            sections=result.sections,
            content_preview=result.content_preview,
        )


class SquishRulesAnalysisResponse(BaseModel):
    """Parsed SQUISH-RULES.yaml data."""

    message: str = Field(description="Summary of project rules loaded")
    memories: dict = Field(description="Learned patterns and remembered project context")
    context: dict = Field(description="Project context entries from rules file")

    @classmethod
    def from_squish_rules(cls, result: SquishRules) -> "SquishRulesAnalysisResponse":
        pattern_count = len(result.memories.get("learned_patterns", []))
        return cls(
            message=f"Loaded project rules with {pattern_count} learned patterns",
            memories=result.memories,
            context=result.context,
        )


class BDDDocumentationAnalysisResponse(BaseModel):
    """Squish BDD documentation analysis."""

    message: str = Field(description="Summary of BDD documentation loaded")
    url: str = Field(description="Source documentation URL")
    step_definition_patterns: list[list[str]] = Field(description="Step patterns represented as [type, pattern] pairs")
    placeholder_syntax: list[str] = Field(description="Supported BDD placeholder syntax patterns")
    hook_patterns: list[str] = Field(description="Available BDD hook patterns")
    file_structure: list[str] = Field(description="Expected BDD file structure and organization")
    context_object_features: list[str] = Field(description="Features exposed on BDD context object")
    implementation_examples: list[str] = Field(description="Implementation examples from docs")
    content_preview: str = Field(description="Preview of the documentation content")

    @classmethod
    def from_bdd_documentation(cls, result: BDDDocumentation) -> "BDDDocumentationAnalysisResponse":
        return cls(
            message=(
                f"Loaded BDD documentation with {len(result.step_definition_patterns)} step patterns "
                f"and {len(result.implementation_examples)} examples"
            ),
            url=result.url,
            step_definition_patterns=[list(p) for p in result.step_definition_patterns],
            placeholder_syntax=result.placeholder_syntax,
            hook_patterns=result.hook_patterns,
            file_structure=result.file_structure,
            context_object_features=result.context_object_features,
            implementation_examples=result.implementation_examples,
            content_preview=result.content_preview,
        )


class BDDContextAnalysisResponse(BaseModel):
    """Analyzed BDD context in a test suite."""

    message: str = Field(description="Summary of BDD test structure found")
    has_bdd_tests: bool = Field(description="Whether any BDD tests were found in the suite")
    bdd_suite: dict | None = Field(default=None, description="BDD suite metadata with step directories and files")
    feature_files: list[dict] = Field(description="Feature files with content and used steps")
    step_definitions: list[list[str]] = Field(description="Flattened step definitions from the suite")
    step_files: list[dict] = Field(description="Flattened step files from the suite")
    relationships: list[dict] = Field(description="Mappings between feature steps and step definitions")

    @classmethod
    def from_bdd_context(cls, result: BDDContext) -> "BDDContextAnalysisResponse":
        result_dict = asdict(result)
        bdd_suite_dict = result_dict["bdd_suite"]
        if result.bdd_suite is not None:
            step_definitions = [list(step_def) for step_def in result.bdd_suite.step_definitions]
            step_files = bdd_suite_dict["step_files"]
            message = (
                f"Found {len(result.feature_files)} feature files in suite '{result.bdd_suite.name}' "
                f"with {len(step_definitions)} step definitions"
            )
        else:
            step_definitions = []
            step_files = []
            message = "No BDD test structure found in the suite"
        return cls(
            message=message,
            has_bdd_tests=result.has_bdd_tests,
            bdd_suite=bdd_suite_dict,
            feature_files=result_dict["feature_files"],
            step_definitions=step_definitions,
            step_files=step_files,
            relationships=result_dict["relationships"],
        )


class TestTemplateResponse(BaseModel):
    """Generated test template based on existing project patterns."""

    message: str = Field(description="Summary of what was generated")
    template: str = Field(description="Generated Python test script content, ready to write to test.py")
    object_pattern: str | None = Field(
        description=(
            "Object reference pattern used in the template (e.g. 'suite_names', 'global_simple'), or null if unknown"
        )
    )

    @classmethod
    def from_template_result(cls, result: TestTemplateResult, test_case_name: str) -> "TestTemplateResponse":
        pattern_value = result.object_pattern.value if result.object_pattern else None
        pattern_label = pattern_value or "unknown"
        return cls(
            message=f"Generated template for '{test_case_name}' using '{pattern_label}' object pattern",
            template=result.template,
            object_pattern=pattern_value,
        )


class BDDTemplateResponse(BaseModel):
    """Generated BDD test template with all required files."""

    message: str = Field(description="Summary of what was generated")
    test_py_template: str = Field(description="Content for test.py with BDD boilerplate (source, setupHooks, etc.)")
    feature_template: str = Field(description="Content for test.feature with Gherkin Background and Scenario sections")
    step_definitions_template: str = Field(description="Content for step definitions Python file")

    @classmethod
    def from_bdd_result(cls, result: BDDTemplateResult, test_case_name: str) -> "BDDTemplateResponse":
        return cls(
            message=f"Generated BDD template for '{test_case_name}' with test.py, feature file, and step definitions",
            test_py_template=result.test_py_template,
            feature_template=result.feature_template,
            step_definitions_template=result.step_definitions_template,
        )


class CodeSuggestionItem(BaseModel):
    """A single code improvement suggestion."""

    type: str = Field(description="Category: 'import', 'object_references', 'api_usage', or 'convention'")
    severity: str = Field(description="Severity: 'info', 'warning', or 'error'")
    message: str = Field(description="Description of the issue")
    suggestion: str = Field(description="Recommended fix or improvement")


class CodeSuggestionsResponse(BaseModel):
    """Code improvement suggestions based on project patterns."""

    total: int = Field(description="Total number of suggestions found")
    suggestions: list[CodeSuggestionItem] = Field(description="Ordered list of improvement suggestions")

    @classmethod
    def from_suggestions(cls, suggestions: list[CodeSuggestion]) -> "CodeSuggestionsResponse":
        items = [
            CodeSuggestionItem(
                type=s.type.value,
                severity=s.severity.value,
                message=s.message,
                suggestion=s.suggestion,
            )
            for s in suggestions
        ]
        return cls(total=len(items), suggestions=[item.model_dump() for item in items])


class ObjectReferencesResponse(BaseModel):
    """Object references extracted from test code, classified by type."""

    names_objects: list[str] = Field(description="Objects referenced via names.py (e.g. names.someButton)")
    direct_objects: list[str] = Field(description="Objects referenced with inline property dicts")
    global_script_objects: list[str] = Field(description="Objects referenced via global script modules")
    unknown_objects: list[str] = Field(description="Object references that could not be classified")
    total_references: int = Field(description="Total count of all object references found")
    primary_pattern: str = Field(
        description="Dominant reference style: 'names', 'global_scripts', 'direct', or 'unknown'"
    )

    @classmethod
    def from_object_references(cls, result: ObjectReferences) -> "ObjectReferencesResponse":
        total = (
            len(result.names_objects)
            + len(result.direct_objects)
            + len(result.global_script_objects)
            + len(result.unknown_objects)
        )

        if result.names_objects:
            primary = "names"
        elif result.global_script_objects:
            primary = "global_scripts"
        elif result.direct_objects:
            primary = "direct"
        else:
            primary = "unknown"

        return cls(
            names_objects=result.names_objects,
            direct_objects=result.direct_objects,
            global_script_objects=result.global_script_objects,
            unknown_objects=result.unknown_objects,
            total_references=total,
            primary_pattern=primary,
        )


class PageObjectsGenerationResponse(BaseModel):
    """Result of generating page object references from an XML snapshot."""

    message: str = Field(description="Summary of what was generated")
    temp_file_path: str = Field(
        description="Absolute path to a local temporary file containing the generated object definitions"
    )
    page_name: str = Field(description="Name of the page/component these objects belong to")
    xml_file: str = Field(description="Source XML snapshot file path")
    objects_found: int = Field(description="Number of object definitions generated")
    summary: str = Field(description="Human-readable summary including format and temporary output path")
    output_strategy: dict = Field(description="Strategy used for output format and target location")
    pattern_analysis: dict = Field(description="Analysis of existing object reference patterns in the project")
    object_context: dict | None = Field(default=None, description="Current object reference context, if available")

    @classmethod
    def from_results(  # noqa: PLR0913
        cls,
        parse_result: SnapshotParseResult,
        output_strategy: OutputStrategy,
        pattern_analysis: ObjectReferencePatterns,
        obj_ref_context: ObjectReferenceAnalysis | None,
        page_name: str,
    ) -> "PageObjectsGenerationResponse":
        return cls(
            message=f"Generated {parse_result.objects_found} objects in {parse_result.generated_format} format",
            temp_file_path=str(parse_result.temp_file_path),
            page_name=parse_result.page_name,
            xml_file=str(parse_result.xml_file),
            objects_found=parse_result.objects_found,
            summary=(
                f"Generated {parse_result.objects_found} object definitions for {page_name} "
                f"in {parse_result.generated_format} format at {parse_result.temp_file_path}"
            ),
            output_strategy={
                **asdict(output_strategy),
                "target_directory": str(output_strategy.target_directory),
            },
            pattern_analysis=asdict(pattern_analysis),
            object_context=asdict(obj_ref_context) if obj_ref_context else None,
        )


class ObjectMapSummary(BaseModel):
    """High-level statistics of the object map."""

    total_object_files: int = Field(description="Total number of object definition files")
    global_files: int = Field(description="Files stored in global script directories")
    suite_names_files: int = Field(description="Suite-local names.py files")
    total_objects: int = Field(description="Total object definitions across all files")
    organization_strategy: str = Field(
        description="How objects are organized: 'global_files', 'suite_names', or 'unknown'"
    )


class ObjectMapStructureResponse(BaseModel):
    """Analysis of the current object map structure and organization patterns."""

    object_files: list[dict] = Field(description="Object definition files with their contents and patterns")
    reference_patterns: dict = Field(description="Common containers, naming, and property patterns")
    page_organization: dict = Field(description="Page organization strategy and associated directory or suite")
    existing_objects: dict = Field(description="All existing object definitions keyed by object name")
    summary: ObjectMapSummary = Field(description="High-level summary with counts and strategy")

    @classmethod
    def from_structure(cls, structure: ObjectMapStructure) -> "ObjectMapStructureResponse":
        structure_dict = asdict(structure)
        return cls(
            object_files=structure_dict["object_files"],
            reference_patterns=structure_dict["reference_patterns"],
            page_organization=structure_dict["page_organization"],
            existing_objects=structure_dict["existing_objects"],
            summary=ObjectMapSummary(
                total_object_files=len(structure.object_files),
                global_files=len([f for f in structure.object_files if f.type in GLOBAL_LOCATION_TYPES]),
                suite_names_files=len([f for f in structure.object_files if f.type == LocationType.SUITE_NAMES]),
                total_objects=len(structure.existing_objects),
                organization_strategy=structure.page_organization.strategy.value,
            ).model_dump(),
        )
