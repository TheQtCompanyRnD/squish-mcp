from dataclasses import dataclass
from pathlib import Path

import pytest

from squish_mcp.squish.scripting import parse_object_snapshot
from squish_mcp.squish.scripting.parse_object_snapshot import SKIPPED_TYPES
from tests.squish.test_data import QT_QUICK_SNAPSHOT
from tests.squish.test_data import QT_WIDGETS_SNAPSHOT
from tests.squish.test_data import XML_SNAPSHOTS_DIR


@dataclass
class SnapshotExpectation:
    """Expected results for a snapshot file."""

    objects_count: int
    expected_types: set[str]
    container_prefix: str
    root_type: str
    text_objects: set[str]


SNAPSHOT_EXPECTATIONS: dict[str, SnapshotExpectation] = {
    QT_WIDGETS_SNAPSHOT: SnapshotExpectation(
        objects_count=11,
        expected_types={"Dialog", "QLabel", "LineEdit", "QPushButton"},
        container_prefix="Address_Book_Add",
        root_type="Dialog",
        text_objects={"&Forename:", "John", "&Surname:", "&Email:", "&Phone:", "&OK", "&Cancel"},
    ),
    QT_QUICK_SNAPSHOT: SnapshotExpectation(
        objects_count=35,
        expected_types={"QQuickWindowQmlImpl", "NumberPad", "Display", "Text", "Rectangle"},
        container_prefix="Calqlatr",
        root_type="QQuickWindowQmlImpl",
        text_objects={"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "/", "*", "-", "=", "+", "1293", "42269*"},
    ),
}

DUPLICATE_BUTTONS_EXPECTED_COUNT = 2
DUPLICATE_BUTTONS_EXPECTED_OCCURRENCES = [1, 2]


@pytest.fixture(params=SNAPSHOT_EXPECTATIONS.keys(), ids=lambda x: x.split("_")[1])
def snapshot_fixture(request: pytest.FixtureRequest) -> tuple[Path, SnapshotExpectation]:
    """Parametrized fixture providing XML path and expected results for each snapshot."""
    xml_filename = request.param
    xml_path = XML_SNAPSHOTS_DIR / xml_filename
    expectations = SNAPSHOT_EXPECTATIONS[xml_filename]
    return xml_path, expectations


def test_parse_filters_skipped_types(snapshot_fixture: tuple[Path, SnapshotExpectation]) -> None:
    """Test that generic / skipped types are filtered out."""
    xml_path, expectations = snapshot_fixture
    objects = parse_object_snapshot(str(xml_path))
    assert not any(obj.type in SKIPPED_TYPES for obj in objects)


def test_parse_generates_variable_names(snapshot_fixture: tuple[Path, SnapshotExpectation]) -> None:
    """Test that Python variable names are generated correctly."""
    xml_path, expectations = snapshot_fixture
    objects = parse_object_snapshot(str(xml_path))

    for obj in objects:
        assert obj.var_name
        # prefix_identifier_type
        assert "_" in obj.var_name
        assert not obj.var_name.startswith("_")
        assert not obj.var_name.endswith("_")


def test_parse_handles_duplicates(tmp_path: Path) -> None:
    """Test that duplicate objects are handled correctly."""
    xml_path = tmp_path / "duplicates.xml"
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<ui>
    <execution>
        <state>
            <element id="window_1">
                <children>
                    <element id="button_1" class="Button">
                        <properties>
                            <property name="id">
                                <string>testButton</string>
                            </property>
                        </properties>
                    </element>
                    <element id="button_2" class="Button">
                        <properties>
                            <property name="id">
                                <string>testButton</string>
                            </property>
                        </properties>
                    </element>
                </children>
                <properties>
                    <property name="id">
                        <string>rootElement</string>
                    </property>
                </properties>
            </element>
        </state>
    </execution>
</ui>
"""
    xml_path.write_text(xml_content)
    objects = parse_object_snapshot(str(xml_path))
    test_buttons = [obj for obj in objects if obj.id == "testButton"]

    # Both buttons share the same id, but the parser assigns different occurrence
    # numbers, making them distinct objects that survive deduplication.
    assert len(test_buttons) == DUPLICATE_BUTTONS_EXPECTED_COUNT
    occurrences = sorted(obj.occurrence for obj in test_buttons)
    assert occurrences == DUPLICATE_BUTTONS_EXPECTED_OCCURRENCES, (
        f"Expected occurrences [1, 2] for duplicate buttons, got {occurrences}"
    )
    var_names = {obj.var_name for obj in test_buttons}
    assert len(var_names) == DUPLICATE_BUTTONS_EXPECTED_COUNT, "Duplicate buttons should have distinct var_names"


def test_parse_snapshot_file_characteristics(snapshot_fixture: tuple[Path, SnapshotExpectation]) -> None:
    """Test that each snapshot file is parsed with expected characteristics."""
    xml_path, expectations = snapshot_fixture
    objects = parse_object_snapshot(str(xml_path))

    assert len(objects) == expectations.objects_count, (
        f"Expected {expectations.objects_count} objects, found {len(objects)}"
    )

    found_types = {obj.type for obj in objects}
    expected_types = expectations.expected_types
    difference = found_types ^ expected_types
    assert not difference, f"Expected types {expected_types}, found {found_types}"

    for obj in objects:
        if obj.container is None:
            continue
        assert obj.container.startswith(expectations.container_prefix), (
            f"Expected container prefix '{expectations.container_prefix}' in '{obj.container}'"
        )

    parsed_texts = {obj.text for obj in objects}
    for text in expectations.text_objects:
        assert text in parsed_texts, f"{text} not found in snapshot"


def test_parse_snapshot_containers(snapshot_fixture: tuple[Path, SnapshotExpectation]) -> None:
    """Test that container relationships are properly established."""
    xml_path, expectations = snapshot_fixture
    objects = parse_object_snapshot(str(xml_path))

    root_containers = {obj.container for obj in objects if obj.container is not None}
    root_type = expectations.root_type

    assert any(container.endswith(f"_{root_type}") or container == root_type for container in root_containers), (
        f"Expected a container ending with '_{root_type}' in {root_containers}"
    )


def test_parse_nonexistent_file() -> None:
    """Test parsing a non-existent file."""
    objects = parse_object_snapshot("/nonexistent/file.xml")
    assert objects == []
