"""
POM Generation Module - Page Object Model code generation.

This module generates Page Object Model (POM) code for Squish test automation
from XML object snapshots and analyzed patterns.

Key responsibilities:
- Parse XML object snapshots to extract UI hierarchy
- Generate object reference code (classes, functions, or dicts)
- Stage generated output in a local temporary file
- Create page-organized object map structure

This module consumes pattern analysis from squish/analysis/ and generates code.
"""

import tempfile

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from squish_mcp.errors import ConfigurationException
from squish_mcp.errors import FileOperationException
from squish_mcp.squish.analysis.models import LocationType
from squish_mcp.squish.analysis.models import ObjectReferencePatterns

from .parse_object_snapshot import SnapshotObject
from .parse_object_snapshot import generate_python_names
from .parse_object_snapshot import parse_object_snapshot
from .templates import get_template


PathLike = str | Path


class POMFormat(str, Enum):
    POM_CLASS = "pom_class"
    FUNCTION_BASED = "function_based"
    SIMPLE_DICT = "simple_dict"


@dataclass(frozen=True)
class OutputStrategy:
    format: POMFormat
    target_directory: Path
    location_type: LocationType = LocationType.OTHER
    class_name: str | None = None  # Only used for pom_class format


@dataclass(frozen=True)
class SnapshotParseResult:
    page_name: str
    xml_file: Path
    objects_found: int
    generated_format: str
    temp_file_path: Path
    success: bool
    error_message: str = ""


def _temporary_output_prefix(page_name: str) -> str:
    sanitized_page_name = "".join(ch if ch.isalnum() else "_" for ch in page_name.strip().lower())
    sanitized_page_name = sanitized_page_name.strip("_") or "page_objects"
    return f"squish_{sanitized_page_name[:32]}_"


def _as_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def _write_temporary_output_file(file_content: str, page_name: str, output_directory: PathLike) -> Path:
    output_dir_path = _as_path(output_directory)

    if not output_dir_path.exists():
        raise FileOperationException(f"Output directory not found: {output_dir_path}")
    if not output_dir_path.is_dir():
        raise FileOperationException(f"Output directory is not a directory: {output_dir_path}")

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".py",
            prefix=_temporary_output_prefix(page_name),
            delete=False,
            dir=output_dir_path,
        ) as temp_file:
            temp_file.write(file_content)
            temp_file_path = Path(temp_file.name)
    except OSError as exc:
        raise FileOperationException(f"Failed to write temporary output file: {exc}") from exc

    return temp_file_path


def page_objects_from_snapshot(
    xml_file_path: PathLike,
    page_name: str,
    output_strategy: OutputStrategy,
    output_directory: PathLike,
) -> SnapshotParseResult:
    """
    Parse XML snapshot and generate page object code.

    Args:
        xml_file_path: Path to XML snapshot file
        page_name: Name of the page/component
        output_strategy: Output configuration (format, target directory, etc.)
        output_directory: Existing directory where the temporary output file should be created

    Returns:
        SnapshotParseResult with generated code and metadata

    Raises:
        FileOperationException: If XML file doesn't exist
        ConfigurationException: If page_name is invalid
    """
    # Pre-execution validation
    xml_path = _as_path(xml_file_path)
    if not xml_path.exists():
        raise FileOperationException(f"XML file not found: {xml_path}")
    if not page_name or not page_name.strip():
        raise ConfigurationException("page_name cannot be empty")

    # Parse XML
    parsed_objects = parse_object_snapshot(str(xml_path))

    if output_strategy.format == POMFormat.POM_CLASS:
        file_content = pom_class_generator(parsed_objects, page_name, output_strategy)
    elif output_strategy.format == POMFormat.FUNCTION_BASED:
        file_content = pom_function_generator(parsed_objects, page_name)
    else:
        file_content = pom_dict_generator(parsed_objects, page_name, str(xml_path))
    temp_file_path = _write_temporary_output_file(file_content, page_name, output_directory)

    return SnapshotParseResult(
        page_name=page_name,
        xml_file=xml_path,
        objects_found=len(parsed_objects),
        generated_format=output_strategy.format.value,
        temp_file_path=temp_file_path,
        success=True,
        error_message="",
    )


def determine_output_strategy_from_patterns(
    test_suite_path: str, pattern_analysis: ObjectReferencePatterns, page_name: str
) -> OutputStrategy:
    """Determine POM output strategy from analyzed object-reference patterns."""
    location_type = pattern_analysis.preferred_location_type
    target_directory: Path | None = None
    pom_format = POMFormat.SIMPLE_DICT
    class_name: str | None = None

    if location_type == LocationType.GLOBAL_POM:
        pom_format = POMFormat.POM_CLASS
        class_name = f"{page_name.replace('-', '_').replace(' ', '_').title()}_Objects"
        if pattern_analysis.global_script_locations:
            base_dir = Path(pattern_analysis.global_script_locations[0]).parent
            target_directory = base_dir / f"{page_name.lower().replace(' ', '-')}-pom"
    elif location_type == LocationType.GLOBAL_FUNCTIONS:
        pom_format = POMFormat.FUNCTION_BASED
        if pattern_analysis.global_script_locations:
            target_directory = Path(pattern_analysis.global_script_locations[0]).parent
    elif location_type == LocationType.GLOBAL_SIMPLE:
        pom_format = POMFormat.SIMPLE_DICT
        if pattern_analysis.global_script_locations:
            target_directory = Path(pattern_analysis.global_script_locations[0]).parent
    else:
        pom_format = POMFormat.SIMPLE_DICT
        if pattern_analysis.suite_names_locations:
            target_directory = Path(pattern_analysis.suite_names_locations[0]).parent

    if not target_directory:
        target_directory = Path(test_suite_path) / "shared" / "scripts"

    return OutputStrategy(
        format=pom_format,
        target_directory=target_directory,
        location_type=location_type,
        class_name=class_name,
    )


def pom_class_generator(parsed_objects: list[SnapshotObject], page_name: str, strategy: OutputStrategy) -> str:
    """
    Generate POM class-based content.

    Args:
        parsed_objects: Filtered objects from parse_object_snapshot
        page_name: Name of the page
        strategy: Output strategy configuration

    Returns:
        Dict with file contents for POM structure
    """
    class_name = strategy.class_name or "PageObjects"

    header = get_template("pom_class_header.py.txt").substitute(
        page_name=page_name,
        class_name=class_name,
    )

    method_template = get_template("pom_class_method.py.txt")
    methods = []
    for obj in sorted(parsed_objects, key=lambda x: x.var_name):
        methods.append(
            method_template.substitute(
                method_name=variable_to_method_name(obj.var_name or "var", obj.container_prefix),
                obj_type=obj.type,
                props_str=obj.as_prop_dict_str(),
            )
        )

    return header + "\n".join(methods)


def pom_function_generator(parsed_objects: list[SnapshotObject], page_name: str) -> str:
    """
    Generate function-based content.

    Args:
        parsed_objects: Filtered objects from parse_object_snapshot
        page_name: Name of the page

    Returns:
        Dict with file content
    """
    header = get_template("pom_function_header.py.txt").substitute(page_name=page_name)

    entry_template = get_template("pom_function_entry.py.txt")
    entries = []
    for obj in sorted(parsed_objects, key=lambda x: x.var_name):
        entries.append(
            entry_template.substitute(
                func_name=variable_to_method_name(obj.var_name or "var", obj.container_prefix),
                obj_type=obj.type,
                props_str=obj.as_prop_dict_str(),
            )
        )

    return header + "\n".join(entries)


def pom_dict_generator(parsed_objects: list[SnapshotObject], page_name: str, xml_file_path: str) -> str:
    """
    Generate simple dictionary definitions content.

    Derives the root container definition from the parsed objects rather
    than hardcoding an application-specific container.

    Args:
        parsed_objects: Parsed SnapshotObject list from the XML snapshot
        page_name: Name of the page
        xml_file_path: Path to source XML file

    Returns:
        Dict mapping filename to content string
    """

    body_str = "# No objects parsed from snapshot"
    if parsed_objects:
        container_var_names = {obj.var_name for obj in parsed_objects if obj.var_name is not None}
        body_lines = generate_python_names(parsed_objects, container_var_names=container_var_names)
        body_str = "\n".join(body_lines)

    pom_dict_contents = get_template("pom_dict.py.txt").substitute(
        page_name=page_name,
        xml_basename=Path(xml_file_path).name,
        pom_dict_body=body_str,
    )

    return pom_dict_contents


def variable_to_method_name(var_name: str, container_prefix: str = "") -> str:
    """
    Convert variable name to camelCase method name.

    Strips the container prefix (derived from the application window title
    during snapshot parsing) from the variable name before converting.

    Args:
        var_name: Variable name to convert
        container_prefix: Prefix to strip

    Returns:
        camelCase method name
    """
    if not var_name:
        return "unknownObject"

    # Strip the container prefix if provided
    clean_name = var_name
    if container_prefix:
        prefix_with_sep = f"{container_prefix}_"
        if clean_name.startswith(prefix_with_sep):
            clean_name = clean_name[len(prefix_with_sep) :]

    # Split on underscores and convert to camelCase
    parts = clean_name.split("_")
    if not parts:
        return "unknownObject"

    # First part lowercase, rest capitalized
    method_name = parts[0].lower()
    for part in parts[1:]:
        if part:
            method_name += part.capitalize()

    # Ensure it's a valid Python identifier
    if not method_name or not method_name[0].isalpha():
        method_name = f"object_{method_name}"

    return method_name
