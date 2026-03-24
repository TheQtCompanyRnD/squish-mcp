"""Object reference analysis.

Analyzes where object references are stored in Squish test environments
and detects patterns (POM classes, function-based, simple dicts).
"""

import glob
import logging
import os
import re

from squish_mcp.errors import AnalysisException
from squish_mcp.squish.analysis import models
from squish_mcp.squish.analysis.suite_directory import require_suite_directory
from squish_mcp.squish.cli import GLOBAL_SCRIPT_DIRS


log = logging.getLogger(__name__)

OBJECT_CONTENT_PREVIEW_MAX_LENGTH = 500
SUITE_SAMPLE_OBJECTS_LIMIT = 5


def analyze_object_reference_patterns(
    obj_ref_analysis: models.ObjectReferenceAnalysis | None,
) -> models.ObjectReferencePatterns:
    """Analyze object reference analysis to understand existing patterns.

    Args:
        obj_ref_analysis: Object reference analysis from analyze_object_references().

    Returns:
        models.ObjectReferencePatterns dataclass instance.
    """
    has_pom_classes = False
    has_function_based = False
    has_simple_dicts = True  # Default assumption
    global_script_locations: list[str] = []
    suite_names_locations: list[str] = []
    class_patterns: list[str] = []
    function_patterns: list[str] = []
    preferred_location_type = models.LocationType.SUITE_NAMES

    if obj_ref_analysis is not None:
        try:
            # Filter files by type
            global_files = [f for f in obj_ref_analysis.files if f.type in models.GLOBAL_LOCATION_TYPES]
            suite_files = [f for f in obj_ref_analysis.files if f.type == models.LocationType.SUITE_NAMES]

            # Analyze global object files
            for file_info in global_files:
                file_path = file_info.path
                global_script_locations.append(file_path)

                # Check for POM class patterns
                if "pom" in file_path.lower() or "object_references" in file_path or "object-references" in file_path:
                    has_pom_classes = True
                    class_patterns.append(file_path)

                # Check for function-based patterns in content preview
                if file_info.content_preview and "def " in file_info.content_preview:
                    has_function_based = True
                    function_patterns.append(file_path)

            # Analyze suite names files
            for file_info in suite_files:
                suite_names_locations.append(file_info.path)

            # Determine preferred location type
            if has_pom_classes and global_script_locations:
                preferred_location_type = models.LocationType.GLOBAL_POM
            elif has_function_based and global_script_locations:
                preferred_location_type = models.LocationType.GLOBAL_FUNCTIONS
            elif global_script_locations:
                preferred_location_type = models.LocationType.GLOBAL_SIMPLE
            else:
                preferred_location_type = models.LocationType.SUITE_NAMES

        except Exception as e:
            log.warning("Error analyzing object patterns: %s", e)

    return models.ObjectReferencePatterns(
        has_pom_classes=has_pom_classes,
        has_function_based=has_function_based,
        has_simple_dicts=has_simple_dicts,
        global_script_locations=global_script_locations,
        suite_names_locations=suite_names_locations,
        preferred_location_type=preferred_location_type,
        class_patterns=class_patterns,
        function_patterns=function_patterns,
    )


def _extract_base_directory(global_files: list[models.ObjectFileLocation]) -> str | None:
    """Extract common base directory from global object files."""
    if not global_files:
        return None

    paths = [f.path for f in global_files]
    if not paths:
        return None

    # Find common directory
    common_path = os.path.commonpath([os.path.dirname(p) for p in paths if p])
    return common_path if common_path else None


def analyze_current_object_map_structure(
    obj_ref_analysis: models.ObjectReferenceAnalysis | None,
) -> models.ObjectMapStructure:
    """Analyze the current object map structure from object reference analysis.

    Args:
        obj_ref_analysis: Object reference analysis from analyze_object_references().

    Returns:
        models.ObjectMapStructure dataclass instance.

    Raises:
        AnalysisException: If analysis fails.
    """
    object_files: list[models.ObjectFileInfo] = []
    existing_objects: dict[str, models.ObjectDefinition] = {}
    reference_patterns = models.ReferencePatterns(
        common_containers=[],
        naming_patterns=[],
        property_patterns=[],
    )
    page_organization = models.PageOrganization(strategy=models.OrganizationStrategy.UNKNOWN)

    if obj_ref_analysis is None:
        return models.ObjectMapStructure(
            object_files=object_files,
            reference_patterns=reference_patterns,
            page_organization=page_organization,
            existing_objects=existing_objects,
        )

    try:
        # Filter files by type
        global_files = [f for f in obj_ref_analysis.files if f.type in models.GLOBAL_LOCATION_TYPES]
        suite_files = [f for f in obj_ref_analysis.files if f.type == models.LocationType.SUITE_NAMES]

        # Process global object files
        for file_info in global_files:
            obj_file = models.ObjectFileInfo(
                type=file_info.type,
                path=file_info.path,
                objects=[],
                patterns=[],
                suite=None,
            )
            object_files.append(obj_file)

        # Process suite names.py files
        for file_info in suite_files:
            obj_file = models.ObjectFileInfo(
                type=models.LocationType.SUITE_NAMES,
                path=file_info.path,
                objects=[],
                patterns=[],
                suite=file_info.suite,
            )
            object_files.append(obj_file)

        # Determine file organization strategy
        if global_files:
            page_organization = models.PageOrganization(
                strategy=models.OrganizationStrategy.GLOBAL_FILES,
                base_directory=_extract_base_directory(global_files),
                suite=None,
            )
        elif suite_files:
            suite_name = next((f.suite for f in suite_files if f.suite), None)
            page_organization = models.PageOrganization(
                strategy=models.OrganizationStrategy.SUITE_NAMES,
                base_directory=None,
                suite=suite_name,
            )

    except Exception as e:
        raise AnalysisException(f"Error analyzing object map structure: {str(e)}") from e

    return models.ObjectMapStructure(
        object_files=object_files,
        reference_patterns=reference_patterns,
        page_organization=page_organization,
        existing_objects=existing_objects,
    )


def _discover_suite_names_files(test_suite_path: str) -> list[str]:
    names_files = glob.glob(os.path.join(test_suite_path, "**", "names.py"), recursive=True)
    return sorted({path for path in names_files if os.path.isfile(path)})


def analyze_object_references(test_suite_path: str) -> models.ObjectReferenceAnalysis:
    """Analyze where object references are stored in the test environment.

    Scans for names.py files in the suite, object files in global scripts,
    and other shared object-reference locations.

    Args:
        test_suite_path: Path to a `suite_*` directory.

    Returns:
        models.ObjectReferenceAnalysis dataclass instance.
    """
    suite_path = require_suite_directory(test_suite_path)
    all_files: list[models.ObjectFileLocation] = []

    # Look for names.py files in the suite
    for names_file in _discover_suite_names_files(suite_path):
        try:
            with open(names_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Count object definitions
            object_defs = re.findall(r"^[A-Za-z_][A-Za-z0-9_]*\s*=", content, re.MULTILINE)

            all_files.append(
                models.ObjectFileLocation(
                    type=models.LocationType.SUITE_NAMES,
                    path=names_file,
                    name="names.py",
                    suite=os.path.dirname(names_file),
                    object_count=len(object_defs),
                    sample_objects=object_defs[:SUITE_SAMPLE_OBJECTS_LIMIT],
                    content_preview=(
                        content[:OBJECT_CONTENT_PREVIEW_MAX_LENGTH] + "..."
                        if len(content) > OBJECT_CONTENT_PREVIEW_MAX_LENGTH
                        else content
                    ),
                    error=None,
                )
            )
        except Exception as e:
            all_files.append(
                models.ObjectFileLocation(
                    type=models.LocationType.SUITE_NAMES,
                    path=names_file,
                    name="names.py",
                    suite="",
                    object_count=0,
                    sample_objects=None,
                    content_preview=None,
                    error=f"Could not analyze: {str(e)}",
                )
            )

    # Look for object files in global script directories
    for global_dir in GLOBAL_SCRIPT_DIRS:
        if os.path.exists(global_dir):
            object_files = glob.glob(os.path.join(global_dir, "**", "*object*.py"), recursive=True)
            object_files.extend(glob.glob(os.path.join(global_dir, "**", "*name*.py"), recursive=True))
            object_files.extend(glob.glob(os.path.join(global_dir, "**", "*.map"), recursive=True))

            for obj_file in object_files:
                try:
                    with open(obj_file, "r", encoding="utf-8") as f:
                        content = f.read()

                    all_files.append(
                        models.ObjectFileLocation(
                            type=models.LocationType.GLOBAL_SIMPLE,
                            path=obj_file,
                            name=os.path.basename(obj_file),
                            content_preview=(
                                content[:OBJECT_CONTENT_PREVIEW_MAX_LENGTH] + "..."
                                if len(content) > OBJECT_CONTENT_PREVIEW_MAX_LENGTH
                                else content
                            ),
                            error=None,
                        )
                    )
                except Exception as e:
                    all_files.append(
                        models.ObjectFileLocation(
                            type=models.LocationType.GLOBAL_SIMPLE,
                            path=obj_file,
                            name=os.path.basename(obj_file),
                            content_preview=None,
                            error=f"Could not analyze: {str(e)}",
                        )
                    )

    # Look for other potential object reference files in the suite
    other_patterns = ["**/objects.py", "**/locators.py", "**/*_objects.py"]
    for pattern in other_patterns:
        files = glob.glob(os.path.join(suite_path, pattern), recursive=True)
        for file_path in files:
            # Check if not already in all_files
            if file_path not in [f.path for f in all_files]:
                all_files.append(
                    models.ObjectFileLocation(
                        type=models.LocationType.OTHER,
                        path=file_path,
                        name=os.path.basename(file_path),
                    )
                )

    return models.ObjectReferenceAnalysis(files=all_files)
