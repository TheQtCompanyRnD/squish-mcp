"""Global scripts analysis.

Analyzes global script directories to discover available utility functions,
classes, and imports provided by the Squish test environment.
"""

import glob
import os
import subprocess

from squish_mcp.errors import AnalysisException
from squish_mcp.squish.analysis import models
from squish_mcp.squish.cli import SQUISH_RUNNER
from squish_mcp.squish.cli import validate_squish_installation


CONTENT_PREVIEW_MAX_LENGTH = 2000


def analyze_global_scripts() -> models.GlobalScriptsAnalysis:
    """Analyze global script directories to discover available utilities.

    Returns:
        models.GlobalScriptsAnalysis dataclass instance.

    Raises:
        ConfigurationException: If Squish is not installed.
        AnalysisException: If the analysis subprocess fails.
    """
    validate_squish_installation()

    cmd = [SQUISH_RUNNER, "--config", "getGlobalScriptDirs"]

    process = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if process.returncode != 0:
        raise AnalysisException(f"getGlobalScriptDirs failed (rc={process.returncode})")

    directories = []
    if process.stdout.strip():
        raw_dirs = process.stdout.strip().replace(";", "\n").split("\n")
        directories = [dir_path.strip() for dir_path in raw_dirs if dir_path.strip()]

    if not directories:
        return models.GlobalScriptsAnalysis(directories=[], files=[])

    files = []

    for directory in directories:
        if not os.path.exists(directory):
            continue

        python_files = glob.glob(os.path.join(directory, "**", "*.py"), recursive=True)

        for file_path in python_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                lines = content.split("\n")
                functions = [line.strip() for line in lines if line.strip().startswith("def ")]
                classes = [line.strip() for line in lines if line.strip().startswith("class ")]
                imports = [
                    line.strip()
                    for line in lines
                    if line.strip().startswith("import ") or line.strip().startswith("from ")
                ]

                file_info = models.GlobalScriptFileInfo(
                    path=file_path,
                    relative_path=os.path.relpath(file_path, directory),
                    size=len(content),
                    lines=len(lines),
                    functions=functions,
                    classes=classes,
                    imports=imports,
                    content=(
                        content[:CONTENT_PREVIEW_MAX_LENGTH] + "..."
                        if len(content) > CONTENT_PREVIEW_MAX_LENGTH
                        else content
                    ),
                    error=None,
                )

                files.append(file_info)

            except Exception as e:
                files.append(
                    models.GlobalScriptFileInfo(
                        path=file_path,
                        relative_path="",
                        size=0,
                        lines=0,
                        functions=[],
                        classes=[],
                        imports=[],
                        content="",
                        error=f"Could not read file: {str(e)}",
                    )
                )

    return models.GlobalScriptsAnalysis(directories=directories, files=files)
