from pathlib import Path

import pytest

from squish_mcp.errors import ConfigurationException
from squish_mcp.errors import FileOperationException
from squish_mcp.squish.analysis.models import LocationType
from squish_mcp.squish.scripting import pom_generation
from squish_mcp.squish.scripting.parse_object_snapshot import SnapshotObject


def _make_strategy(
    fmt: pom_generation.POMFormat = pom_generation.POMFormat.SIMPLE_DICT,
    target_directory: Path = Path("/tmp"),
    class_name: str | None = None,
    location_type: LocationType = LocationType.GLOBAL_SIMPLE,
) -> pom_generation.OutputStrategy:
    return pom_generation.OutputStrategy(
        format=fmt,
        target_directory=target_directory,
        class_name=class_name,
        location_type=location_type,
    )


class TestVariableToMethodName:
    def test_empty_string(self) -> None:
        assert pom_generation.variable_to_method_name("") == "unknownObject"

    def test_simple_name_no_prefix(self) -> None:
        assert pom_generation.variable_to_method_name("submit_Button") == "submitButton"

    def test_strips_matching_prefix(self) -> None:
        result = pom_generation.variable_to_method_name("Calqlatr_display_Display", "Calqlatr")
        assert result == "displayDisplay"

    def test_strips_multi_word_prefix(self) -> None:
        result = pom_generation.variable_to_method_name("Address_Book_Add_OK_QPushButton", "Address_Book_Add")
        assert result == "okQpushbutton"

    def test_ignores_non_matching_prefix(self) -> None:
        result = pom_generation.variable_to_method_name("Other_App_button_Button", "Calqlatr")
        assert result == "otherAppButtonButton"

    def test_no_prefix_keeps_full_name(self) -> None:
        result = pom_generation.variable_to_method_name("Calqlatr_display_Display")
        assert result == "calqlatrDisplayDisplay"

    def test_numeric_start_gets_object_prefix(self) -> None:
        result = pom_generation.variable_to_method_name("Calqlatr_7_Text", "Calqlatr")
        assert result == "object_7Text"

    def test_single_segment_after_prefix(self) -> None:
        result = pom_generation.variable_to_method_name("Calqlatr_Text", "Calqlatr")
        assert result == "text"


class TestGeneratePomClassContent:
    def test_contains_class_definition(self, parsed_objects: list[SnapshotObject]) -> None:
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="TestPageObjects")
        content = pom_generation.pom_class_generator(parsed_objects, "TestPage", strategy)

        assert "class TestPageObjects():" in content

    def test_contains_staticmethods(self, parsed_objects: list[SnapshotObject]) -> None:
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="PageObjects")
        content = pom_generation.pom_class_generator(parsed_objects, "Page", strategy)

        assert content.count("@staticmethod") == len(parsed_objects)

    def test_methods_use_waitforobject(self, parsed_objects: list[SnapshotObject]) -> None:
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="PageObjects")
        content = pom_generation.pom_class_generator(parsed_objects, "Page", strategy)

        assert content.count("waitForObject") == len(parsed_objects)

    def test_method_names_strip_prefix(self, qt_quick_objects: list[SnapshotObject]) -> None:
        """Method names should not contain the container prefix."""
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="AddressBookObjects")
        content = pom_generation.pom_class_generator(qt_quick_objects, "AddressBook", strategy)

        # The container prefix "Address_Book_Add" should be stripped from method names.
        # Extract actual method names and verify none start with the prefix.
        method_names = [
            line.strip().split("(")[0].removeprefix("def ")
            for line in content.splitlines()
            if line.strip().startswith("def ")
        ]
        for name in method_names:
            assert not name.startswith("address"), f"Method '{name}' still contains the container prefix"

    def test_contains_imports(self, parsed_objects: list[SnapshotObject]) -> None:
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="PageObjects")
        content = pom_generation.pom_class_generator(parsed_objects, "Page", strategy)

        assert "from objectmaphelper import *" in content

    def test_generated_method_has_correct_body(self, qt_widgets_objects: list[SnapshotObject]) -> None:
        """A known object from the snapshot should produce a method with the correct waitForObject call."""
        strategy = _make_strategy(fmt=pom_generation.POMFormat.POM_CLASS, class_name="AddressBookObjects")
        content = pom_generation.pom_class_generator(qt_widgets_objects, "AddressBook", strategy)

        # The Qt Widgets snapshot contains an OK QPushButton — verify its generated method.
        ok_button = next(obj for obj in qt_widgets_objects if obj.type == "QPushButton" and obj.text == "&OK")
        expected_props = ok_button.as_prop_dict_str()
        assert f"return waitForObject({{{expected_props}}})" in content


class TestGenerateFunctionBasedContent:
    def test_filename_derived_from_page_name(self, parsed_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_function_generator(parsed_objects, "My Page")
        assert isinstance(content, str)
        assert "# My Page Page Object Functions" in content

    def test_contains_function_definitions(self, parsed_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_function_generator(parsed_objects, "TestPage")
        assert content.count("\ndef ") == len(parsed_objects)

    def test_functions_use_waitforobject(self, parsed_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_function_generator(parsed_objects, "Page")
        assert content.count("waitForObject") == len(parsed_objects)

    def test_function_names_strip_prefix(self, qt_quick_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_function_generator(qt_quick_objects, "Calc")

        # Functions should not start with the container prefix "Calqlatr_"
        for line in content.splitlines():
            if line.startswith("def "):
                func_name = line.split("(")[0].removeprefix("def ")
                assert not func_name.startswith("calqlatr")

    def test_generated_function_has_correct_body(self, qt_quick_objects: list[SnapshotObject]) -> None:
        """A known object from the snapshot should produce a function with the correct waitForObject call."""
        content = pom_generation.pom_function_generator(qt_quick_objects, "Calc")

        # The Qt Quick snapshot contains a Display object — verify its generated function.
        display_obj = next(obj for obj in qt_quick_objects if obj.type == "Display")
        expected_props = display_obj.as_prop_dict_str()
        assert f"return waitForObject({{{expected_props}}})" in content


class TestGenerateSimpleDictContent:
    def test_filename_derived_from_page_name(
        self, parsed_objects: list[SnapshotObject], xml_snapshot_path: Path
    ) -> None:
        content = pom_generation.pom_dict_generator(parsed_objects, "My Page", str(xml_snapshot_path))
        assert "# My Page Page Object Definitions" in content

    def test_contains_objectmaphelper_import(
        self, parsed_objects: list[SnapshotObject], xml_snapshot_path: Path
    ) -> None:
        content = pom_generation.pom_dict_generator(parsed_objects, "Page", str(xml_snapshot_path))
        assert "from objectmaphelper import *" in content

    def test_root_container_derived_from_objects(self, qt_widgets_objects: list[SnapshotObject]) -> None:
        """Root container line should be derived from the parsed objects, not hardcoded."""
        content = pom_generation.pom_dict_generator(qt_widgets_objects, "Page", "test.xml")
        # Should contain the actual root container from the objects
        assert "Address_Book_Add_Dialog" in content
        # Root type should be Dialog (from the snapshot), not hardcoded QQuickWindowQmlImpl
        assert '"type": "Dialog"' in content

    def test_root_container_widgets(self, qt_quick_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_dict_generator(qt_quick_objects, "Calc", "test.xml")
        assert "Calqlatr_QQuickWindowQmlImpl" in content
        assert '"type": "QQuickWindowQmlImpl"' in content

    def test_contains_object_definitions(self, qt_quick_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_dict_generator(qt_quick_objects, "Page", "test.xml")
        # Each object should have a variable assignment
        for obj in qt_quick_objects:
            assert obj.var_name is not None and obj.var_name in content

    def test_nested_container_relationships(self, qt_quick_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_dict_generator(qt_quick_objects, "Calc", "test.xml")
        zero_text = next(obj for obj in qt_quick_objects if obj.type == "Text" and obj.text == "0")
        input_text = next(obj for obj in qt_quick_objects if obj.id == "inputText")
        number_pad = next(obj for obj in qt_quick_objects if obj.id == "numberPad")
        display = next(obj for obj in qt_quick_objects if obj.id == "display")

        assert zero_text.var_name is not None
        assert input_text.var_name is not None
        assert number_pad.var_name is not None
        assert display.var_name is not None

        assert f'{zero_text.var_name} = {{"container": {number_pad.var_name}, "text": "0", "type": "Text",' in content
        assert (
            f'{input_text.var_name} = {{"container": {display.var_name}, "id": "inputText", "text": "1293",' in content
        )

    def test_container_variables_defined_before_usage(self, qt_quick_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_dict_generator(qt_quick_objects, "Calc", "test.xml")
        zero_text = next(obj for obj in qt_quick_objects if obj.type == "Text" and obj.text == "0")
        input_text = next(obj for obj in qt_quick_objects if obj.id == "inputText")
        number_pad = next(obj for obj in qt_quick_objects if obj.id == "numberPad")
        display = next(obj for obj in qt_quick_objects if obj.id == "display")

        assert zero_text.var_name is not None
        assert input_text.var_name is not None
        assert number_pad.var_name is not None
        assert display.var_name is not None

        number_pad_def_index = content.index(f"{number_pad.var_name} = ")
        text_usage_index = content.index(f'{zero_text.var_name} = {{"container": {number_pad.var_name}')
        display_def_index = content.index(f"{display.var_name} = ")
        display_usage_index = content.index(f'{input_text.var_name} = {{"container": {display.var_name}')

        assert number_pad_def_index < text_usage_index
        assert display_def_index < display_usage_index

    def test_source_filename_in_header(self, parsed_objects: list[SnapshotObject]) -> None:
        content = pom_generation.pom_dict_generator(parsed_objects, "Page", "/some/path/snapshot.xml")

        assert "Generated from: snapshot.xml" in content


class TestGeneratePageObjectsFromSnapshot:
    @pytest.fixture
    def output_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "output"
        d.mkdir()
        return d

    def test_pom_class_format(
        self, xml_snapshot_path: Path, parsed_objects: list[SnapshotObject], output_dir: Path
    ) -> None:
        strategy = _make_strategy(
            fmt=pom_generation.POMFormat.POM_CLASS, class_name="TestObjects", target_directory=output_dir
        )

        parse_result = pom_generation.page_objects_from_snapshot(xml_snapshot_path, "TestPage", strategy, output_dir)

        assert parse_result.success
        assert parse_result.objects_found == len(parsed_objects)
        temp_output_path = parse_result.temp_file_path
        assert temp_output_path.exists()
        assert temp_output_path.parent == output_dir
        assert "class TestObjects" in temp_output_path.read_text(encoding="utf-8")

    def test_function_based_format(self, xml_snapshot_path: Path, output_dir: Path) -> None:
        strategy = _make_strategy(fmt=pom_generation.POMFormat.FUNCTION_BASED, target_directory=output_dir)

        parse_result = pom_generation.page_objects_from_snapshot(xml_snapshot_path, "TestPage", strategy, output_dir)

        assert parse_result.success
        assert parse_result.temp_file_path.exists()

    def test_simple_dict_format(self, xml_snapshot_path: Path, output_dir: Path) -> None:
        strategy = _make_strategy(target_directory=output_dir)

        parse_result = pom_generation.page_objects_from_snapshot(xml_snapshot_path, "TestPage", strategy, output_dir)

        assert parse_result.success
        assert "from objectmaphelper import *" in parse_result.temp_file_path.read_text(encoding="utf-8")

    def test_nonexistent_xml_file(self, output_dir: Path) -> None:
        strategy = _make_strategy()

        with pytest.raises(FileOperationException, match="XML file not found"):
            pom_generation.page_objects_from_snapshot(Path("/no/such/file.xml"), "Page", strategy, output_dir)

    def test_empty_page_name_raises(self, xml_snapshot_path: Path, output_dir: Path) -> None:
        strategy = _make_strategy()

        with pytest.raises(ConfigurationException, match="page_name cannot be empty"):
            pom_generation.page_objects_from_snapshot(xml_snapshot_path, "", strategy, output_dir)

    def test_whitespace_page_name_raises(self, xml_snapshot_path: Path, output_dir: Path) -> None:
        strategy = _make_strategy()

        with pytest.raises(ConfigurationException, match="page_name cannot be empty"):
            pom_generation.page_objects_from_snapshot(xml_snapshot_path, "   ", strategy, output_dir)

    def test_missing_output_directory_raises(self, xml_snapshot_path: Path, tmp_path: Path) -> None:
        strategy = _make_strategy()
        missing_output_dir = tmp_path / "missing"

        with pytest.raises(FileOperationException, match="Output directory not found"):
            pom_generation.page_objects_from_snapshot(xml_snapshot_path, "Page", strategy, missing_output_dir)
