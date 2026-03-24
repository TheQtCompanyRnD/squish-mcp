"""LLM-oriented analysis helpers based on user-authored project context."""

import re

from squish_mcp.errors import AnalysisException
from squish_mcp.squish.analysis import models as analysis_models
from squish_mcp.squish.analysis.context_models import CodeSuggestion
from squish_mcp.squish.analysis.context_models import CodingConventions
from squish_mcp.squish.analysis.context_models import Severity
from squish_mcp.squish.analysis.context_models import SuggestionType
from squish_mcp.squish.analysis.test_suite_analysis import analyze_existing_patterns


TOP_COMMON_IMPORTS_LIMIT = 3
IGNORED_IMPORTS = frozenset({"sys", "os", "time"})


def _collect_import_suggestions(
    analysis: analysis_models.ExistingPatterns,
    test_content: str,
) -> list[CodeSuggestion]:
    current_imports = re.findall(r"^(?:import|from)\s+([^\s]+)", test_content, re.MULTILINE)
    missing_imports = [
        imp
        for imp in analysis.common_imports[:TOP_COMMON_IMPORTS_LIMIT]
        if imp not in current_imports and imp not in IGNORED_IMPORTS
    ]
    if not missing_imports:
        return []
    return [
        CodeSuggestion(
            type=SuggestionType.IMPORT,
            severity=Severity.INFO,
            message=f"Consider adding common project imports: {', '.join(missing_imports)}",
            suggestion=f"Add: {', '.join(f'import {imp}' for imp in missing_imports)}",
        )
    ]


def _collect_object_reference_suggestions(
    analysis: analysis_models.ExistingPatterns,
    test_content: str,
) -> list[CodeSuggestion]:
    if analysis.object_patterns.primary_location not in analysis_models.GLOBAL_LOCATION_TYPES:
        return []
    if "import names" not in test_content or "names." not in test_content:
        return []
    return [
        CodeSuggestion(
            type=SuggestionType.OBJECT_REFERENCE,
            severity=Severity.WARNING,
            message="Project uses global script objects, but test imports 'names'",
            suggestion="Consider using global script object references instead of names.py",
        )
    ]


def _collect_api_usage_suggestions(
    analysis: analysis_models.ExistingPatterns,
    test_content: str,
) -> list[CodeSuggestion]:
    if not analysis.api_usage:
        return []

    suggestions: list[CodeSuggestion] = []
    has_verification = bool(re.search(r"\btest\.verify\b", test_content))
    has_logging = bool(re.search(r"\btest\.log\b", test_content))
    uses_verify_elsewhere = any("verify" in api_name for api_name in analysis.api_usage)

    if uses_verify_elsewhere and not has_verification:
        suggestions.append(
            CodeSuggestion(
                type=SuggestionType.API_USAGE,
                severity=Severity.INFO,
                message="Most tests in this project use verification",
                suggestion="Consider adding test.verify() calls to validate results",
            )
        )

    if not has_logging:
        suggestions.append(
            CodeSuggestion(
                type=SuggestionType.API_USAGE,
                severity=Severity.INFO,
                message="Consider adding logging for better test traceability",
                suggestion="Add test.log() statements at key points",
            )
        )

    return suggestions


def _collect_convention_suggestions(
    conventions: CodingConventions | None,
    test_content: str,
) -> list[CodeSuggestion]:
    if conventions is None:
        return []

    suggestions: list[CodeSuggestion] = []

    if conventions.screenshot_verification is not None:
        mentions_screenshots = "screenshot" in test_content.lower() or "verify_image" in test_content.lower()
        if mentions_screenshots and "verify_image" not in test_content:
            suggestions.append(
                CodeSuggestion(
                    type=SuggestionType.CONVENTION,
                    severity=Severity.WARNING,
                    message="Project has specific screenshot verification patterns",
                    suggestion=conventions.screenshot_verification,
                )
            )

    if conventions.setup_function is not None:
        if "def main(" in test_content and "setup" not in test_content.lower():
            suggestions.append(
                CodeSuggestion(
                    type=SuggestionType.CONVENTION,
                    severity=Severity.INFO,
                    message="Project uses setup functions in tests",
                    suggestion=conventions.setup_function,
                )
            )

    return suggestions


def suggest_code_improvements(
    test_content: str,
    test_format_context: analysis_models.TestFormatAnalysis | None,
    object_ref_context: analysis_models.ObjectReferenceAnalysis | None,
    global_script_context: analysis_models.GlobalScriptsAnalysis | None,
    conventions_context: CodingConventions | None = None,
) -> list[CodeSuggestion]:
    """Suggest code improvements using project patterns and optional LLM-focused rules."""
    try:
        analysis = analyze_existing_patterns(test_format_context, object_ref_context, global_script_context)
    except AnalysisException as e:
        raise AnalysisException(f"Could not analyze patterns for suggestions: {e}") from e

    suggestions: list[CodeSuggestion] = []
    suggestions.extend(_collect_import_suggestions(analysis, test_content))
    suggestions.extend(_collect_object_reference_suggestions(analysis, test_content))
    suggestions.extend(_collect_api_usage_suggestions(analysis, test_content))

    suggestions.extend(_collect_convention_suggestions(conventions_context, test_content))

    return suggestions
