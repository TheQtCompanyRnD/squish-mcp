"""Project resource fetching.

Loads Squish API and BDD documentation.
"""

import os
import re
import urllib.request

from squish_mcp.errors import AnalysisException
from squish_mcp.squish.analysis import models
from squish_mcp.squish.cli import SQUISH_PREFIX


API_CONTENT_PREVIEW_MAX_LENGTH = 2000
BDD_CONTENT_PREVIEW_MAX_LENGTH = 3000


def fetch_squish_api_documentation() -> models.APIDocumentation:
    """Load and parse Squish API documentation from local Squish installation.

    Returns:
        models.APIDocumentation dataclass instance.

    Raises:
        AnalysisException: If documentation cannot be loaded.
    """
    # Construct path to local API documentation
    squish_api_html_path = os.path.join(SQUISH_PREFIX, "doc", "html", "squish-api.html")
    squish_api_html_path = os.path.abspath(squish_api_html_path)  # Normalize path

    if not os.path.exists(squish_api_html_path):
        raise AnalysisException(f"Local Squish API documentation not found at: {squish_api_html_path}")

    try:
        with open(squish_api_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
    except Exception as e:
        raise AnalysisException(f"Failed to load local Squish API documentation: {e}") from e

    # Basic parsing to extract API information
    api_functions = re.findall(
        r"<h[3-6][^>]*>([^<]*(?:test|wait|click|type|verify|compare|find|start)[^<]*)</h[3-6]>",
        html_content,
        re.IGNORECASE,
    )
    code_blocks = re.findall(r"<code[^>]*>([^<]+)</code>", html_content)
    sections = re.split(r"<h[2-3][^>]*>([^<]+)</h[2-3]>", html_content)

    return models.APIDocumentation(
        local_path=squish_api_html_path,
        functions=list(set(api_functions[:50])),
        code_examples=list(set(code_blocks[:30])),
        sections=[sections[i] for i in range(1, len(sections), 2)][:20],
        content_preview=(
            html_content[:API_CONTENT_PREVIEW_MAX_LENGTH] + "..."
            if len(html_content) > API_CONTENT_PREVIEW_MAX_LENGTH
            else html_content
        ),
    )


def fetch_squish_bdd_documentation() -> models.BDDDocumentation:
    """Fetch and parse Squish BDD documentation from Qt's official documentation.

    Returns:
        models.BDDDocumentation dataclass instance.

    Raises:
        AnalysisException: If documentation cannot be fetched or parsed.
    """
    url = "https://doc.qt.io/squish/behavior-driven-testing.html"

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            html_content = response.read().decode("utf-8")
    except Exception as e:
        raise AnalysisException(f"Failed to fetch Squish BDD documentation: {e}") from e

    # Extract step definition patterns
    step_patterns = re.findall(
        r'@(Given|When|Then|Step)\s*\(["\']([^"\']+)["\']\)',
        html_content,
        re.IGNORECASE,
    )

    # Extract placeholder syntax information
    placeholder_patterns = re.findall(r"\|([^|]+)\|", html_content)

    # Extract hook-related patterns
    hook_patterns = re.findall(r"(OnFeature|OnScenario|OnStep)(?:Start|End)", html_content)

    # Extract context object information
    context_features = re.findall(r"context\.([a-zA-Z_][a-zA-Z0-9_]*)", html_content)

    # Extract code examples
    code_blocks = re.findall(r"<code[^>]*>([^<]+)</code>", html_content)
    implementation_examples = list(
        {
            code
            for code in code_blocks
            if any(keyword in code for keyword in ["@Given", "@When", "@Then", "@Step", "context"])
        }
    )[:20]

    # Extract structured sections for best practices
    sections = re.split(r"<h[2-4][^>]*>([^<]+)</h[2-4]>", html_content)
    file_structure = [
        sections[i]
        for i in range(1, len(sections), 2)
        if any(keyword in sections[i].lower() for keyword in ["structure", "organization", "file"])
    ][:10]

    return models.BDDDocumentation(
        url=url,
        step_definition_patterns=list(set(step_patterns)),
        placeholder_syntax=list(set(placeholder_patterns)),
        hook_patterns=list(set(hook_patterns)),
        file_structure=file_structure,
        context_object_features=list(set(context_features)),
        implementation_examples=implementation_examples,
        content_preview=(
            html_content[:BDD_CONTENT_PREVIEW_MAX_LENGTH] + "..."
            if len(html_content) > BDD_CONTENT_PREVIEW_MAX_LENGTH
            else html_content
        ),
    )
