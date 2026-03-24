"""LLM-oriented analysis helpers based on user-authored project context."""

import os

import yaml

from squish_mcp.errors import ConfigurationException
from squish_mcp.squish.analysis.context_models import CodingConventions
from squish_mcp.squish.analysis.context_models import SquishRules
from squish_mcp.squish.cli import SQUISH_RULES_FILE


def read_squish_rules() -> SquishRules:
    """Read and parse SQUISH-RULES.yaml for agent-facing conventions and memories."""
    if not os.path.exists(SQUISH_RULES_FILE):
        return SquishRules(memories={}, context={})

    try:
        with open(SQUISH_RULES_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        raise ConfigurationException(f"Error reading SQUISH-RULES.yaml: {e}") from e

    try:
        rules_data = yaml.safe_load(content) or {}
    except yaml.YAMLError as e:
        raise ConfigurationException(f"Error parsing SQUISH-RULES.yaml: {e}") from e

    return SquishRules(
        memories=rules_data.get("memories", {}),
        context=rules_data.get("context", {}),
    )


def get_coding_conventions() -> CodingConventions:
    """Extract project coding conventions from parsed rules for LLM guidance."""
    screenshot_verification: str | None = None
    setup_function: str | None = None

    rules = read_squish_rules()

    patterns = rules.memories.get("learned_patterns", [])
    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        pattern_text = pattern.get("pattern", "")
        context_text = pattern.get("context", "")

        if "screenshot verification" in pattern_text.lower():
            screenshot_verification = context_text
        elif "setup function" in pattern_text.lower():
            setup_function = context_text

    return CodingConventions(
        screenshot_verification=screenshot_verification,
        setup_function=setup_function,
    )
