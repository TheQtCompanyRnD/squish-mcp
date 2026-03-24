"""
Context-layer model types for LLM context synthesis.

These types are used by server-side LLM helpers
(`server.tools.analysis.llm_context_analysis`) and are specific to the
LLM/agent layer.

For Squish-domain types, import from squish_mcp.squish.analysis.models.
"""

from dataclasses import dataclass
from enum import Enum


class SuggestionType(str, Enum):
    """Type of code suggestion."""

    IMPORT = "import"
    OBJECT_REFERENCE = "object_reference"
    API_USAGE = "api_usage"
    CONVENTION = "convention"


class Severity(str, Enum):
    """Suggestion severity level."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class CodingConventions:
    """Project coding conventions."""

    screenshot_verification: str | None = None
    setup_function: str | None = None


@dataclass(frozen=True)
class CodeSuggestion:
    """A code improvement suggestion."""

    type: SuggestionType
    severity: Severity
    message: str
    suggestion: str


@dataclass(frozen=True)
class SquishRules:
    """
    Squish project rules from YAML.

    Uses dict for flexible YAML structure. The memories and context sections
    can have arbitrary keys defined by the user in SQUISH-RULES.yaml.
    """

    memories: dict  # Keep as dict - YAML structure is flexible
    context: dict  # Keep as dict - YAML structure is flexible
