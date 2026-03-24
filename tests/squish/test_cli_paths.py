from pathlib import Path

from squish_mcp import squish
from squish_mcp.squish.cli import SQUISH_RULES_FILE


def test_squish_rules_path_points_to_repo_root() -> None:
    repo_root = Path(squish.__file__).resolve().parent.parent
    expected = repo_root / "SQUISH-RULES.yaml"
    assert Path(SQUISH_RULES_FILE).resolve() == expected
