import shutil
import typing as t

from pathlib import Path

import pytest

from squish_mcp.squish.scripting.parse_object_snapshot import SnapshotObject
from squish_mcp.squish.scripting.parse_object_snapshot import parse_object_snapshot
from tests.squish.test_data import QT_QUICK_SNAPSHOT
from tests.squish.test_data import QT_WIDGETS_SNAPSHOT
from tests.squish.test_data import SUITE_FIXTURES_DIR
from tests.squish.test_data import TESTCASES_DIR
from tests.squish.test_data import XML_SNAPSHOTS_DIR


def _copy_fixture(name: str, dest: Path) -> None:
    shutil.copy(SUITE_FIXTURES_DIR / name, dest)


@pytest.fixture(params=[QT_QUICK_SNAPSHOT, QT_WIDGETS_SNAPSHOT], ids=["quick", "widgets"])
def xml_snapshot_path(request: pytest.FixtureRequest) -> Path:
    """Parametrized fixture providing XML snapshot paths."""
    return XML_SNAPSHOTS_DIR / request.param


@pytest.fixture
def parsed_objects(xml_snapshot_path: Path) -> list[SnapshotObject]:
    """Parsed SnapshotObject list from the parametrized XML snapshot."""
    return parse_object_snapshot(str(xml_snapshot_path))


@pytest.fixture
def qt_quick_objects() -> list[SnapshotObject]:
    """Parsed objects from the Qt Quick snapshot (non-parametrized)."""
    return parse_object_snapshot(str(XML_SNAPSHOTS_DIR / QT_QUICK_SNAPSHOT))


@pytest.fixture
def qt_widgets_objects() -> list[SnapshotObject]:
    """Parsed objects from the Qt Widgets snapshot (non-parametrized)."""
    return parse_object_snapshot(str(XML_SNAPSHOTS_DIR / QT_WIDGETS_SNAPSHOT))


@pytest.fixture
def read_testcase() -> t.Callable[[str], str]:
    """Return a reader that loads a testcase file by name (without extension)."""

    def _read(name: str) -> str:
        return (TESTCASES_DIR / name).with_suffix(".py").read_text()

    return _read


@pytest.fixture
def temp_suite_with_cases(tmp_path: Path) -> Path:
    """Temporary suite directory with suite.conf containing test cases."""
    suite_path = tmp_path / "suite_example"
    suite_path.mkdir()
    (suite_path / "suite.conf").write_text(
        "AUT=myapp\nLANGUAGE=Python\nTEST_CASES=tst_case1 tst_case2 tst_case3\nVERSION=3\n"
    )
    return suite_path


@pytest.fixture
def temp_suite_empty(tmp_path: Path) -> Path:
    """Temporary suite directory with suite.conf containing no test cases."""
    suite_path = tmp_path / "suite_example"
    suite_path.mkdir()
    (suite_path / "suite.conf").write_text("AUT=myapp\nLANGUAGE=Python\nTEST_CASES=\n")
    return suite_path


@pytest.fixture
def standard_suite_generator(tmp_path: Path) -> t.Callable[[list[str]], Path]:
    """Suite directory generator for suite_py with standard test cases and names.py."""

    def generate(test_names: list[str]) -> Path:
        suite = tmp_path / "suite_py"
        suite.mkdir()

        for test_name in test_names:
            tst = suite / f"tst_{test_name}"
            tst.mkdir()
            _copy_fixture("standard_test.py", tst / "test.py")

        _copy_fixture("names.py", suite / "names.py")

        return suite

    return generate


@pytest.fixture
def suite_with_two_standard_tests(standard_suite_generator: t.Callable[[list[str]], Path]) -> Path:
    return standard_suite_generator(["1", "2"])


@pytest.fixture
def suite_minimal(standard_suite_generator: t.Callable[[list[str]], Path]) -> Path:
    return standard_suite_generator(["1"])


@pytest.fixture
def suite_with_bdd_tests(tmp_path: Path) -> Path:
    """Suite directory with a BDD test case."""
    suite = tmp_path / "suite_bdd"
    suite.mkdir()

    tst = suite / "tst_login_bdd"
    tst.mkdir()
    _copy_fixture("bdd_test.py", tst / "test.py")
    _copy_fixture("login.feature", tst / "test.feature")

    steps_dir = suite / "shared" / "steps"
    steps_dir.mkdir(parents=True)
    _copy_fixture("bdd_steps.py", steps_dir / "steps.py")

    return suite
