"""
Parse object_snapshot.xml and generate Python object names for Squish testing.
Improved version that handles duplicates and organizes objects better.
"""

import json
import logging
import re
import xml.etree.ElementTree as ET

from collections import defaultdict
from collections import deque
from dataclasses import dataclass


log = logging.getLogger(__name__)

MAX_TEXT_IDENTIFIER_LEN = 20
SKIPPED_TYPES = {
    # Qt Quick internal types
    "ShaderEffect",
    "ShaderEffectSource",
    "Item",
    "QQuickItem",
    "DesignEffect",
    "DesignEffectPrivate",
    "DesignLayerBlurPrivate",
    "DesignBackgroundBlurPrivate",
    "DesignDropShadowPrivate",
    "DesignInnerShadowPrivate",
    "Repeater",
    # Qt Widgets layout types (not interactive elements)
    "QGridLayout",
    "QHBoxLayout",
    "QVBoxLayout",
    "QFormLayout",
    "QStackedLayout",
    "QBoxLayout",
    "QLayout",
    # Qt Widgets internal types
    "QWidgetLineControl",
    "QRegExpValidator",
    "QIntValidator",
    "QDoubleValidator",
}


@dataclass(frozen=True)
class SnapshotObject:
    id: str | None
    realname: dict | None
    type: str
    container: str | None
    container_prefix: str
    element_id: str
    var_name: str | None
    text: str | None
    object_name: str | None
    visible: bool
    original_type: str
    occurrence: int

    def as_squish_obj_dict(self) -> dict[str, str | int | bool]:
        obj_dict = {
            "type": self.type,
            "visible": self.visible,
            "unnamed": 1,
        }
        if self.id is not None:
            obj_dict["id"] = self.id
        if self.container is not None:
            obj_dict["container"] = self.container
        if self.text is not None:
            obj_dict["text"] = self.text
        if self.object_name is not None:
            obj_dict["object_name"] = self.object_name
        if self.occurrence > 1:
            obj_dict["occurrence"] = self.occurrence

        return obj_dict

    @property
    def squish_prop_hash(self) -> int:
        return hash(tuple(self.as_squish_obj_dict().values()))

    def with_occurrence(self, occurrence: int) -> "SnapshotObject":
        return SnapshotObject(
            id=self.id,
            realname=self.realname,
            type=self.type,
            container=self.container,
            container_prefix=self.container_prefix,
            element_id=self.element_id,
            var_name=self.var_name,
            text=self.text,
            object_name=self.object_name,
            visible=self.visible,
            original_type=self.original_type,
            occurrence=occurrence,
        )

    def with_var_name(self, var_name: str) -> "SnapshotObject":
        return SnapshotObject(
            id=self.id,
            realname=self.realname,
            type=self.type,
            container=self.container,
            container_prefix=self.container_prefix,
            element_id=self.element_id,
            var_name=var_name,
            text=self.text,
            object_name=self.object_name,
            visible=self.visible,
            original_type=self.original_type,
            occurrence=self.occurrence,
        )

    def as_prop_dict_str(self) -> str:
        obj_dict = self.as_squish_obj_dict()
        return _format_obj_dict_for_python(obj_dict)


def clean_type_name(type_name: str) -> str:
    """Clean and simplify type names for Python variable names."""
    cleaned = re.sub(r"\.ui_QMLTYPE_\d+", "", type_name)
    cleaned = re.sub(r"_QMLTYPE_\d+", "", cleaned)
    cleaned = re.sub(r"_QML_\d+", "", cleaned)
    cleaned = re.sub(r"\.ui$", "", cleaned)
    return cleaned


def text_to_identifier(text: str) -> str:
    text = re.sub(r"[^\w\s]", "_", str(text))
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    text = text.strip("_")
    text = text[:MAX_TEXT_IDENTIFIER_LEN]
    return text


def make_python_var_name(
    container_prefix: str,
    obj_id: str | None,
    obj_type: str,
    obj_text: str | None = None,
    occurrence: int | None = None,
) -> str:
    """Generate Python variable name following Squish naming conventions."""
    clean_type = clean_type_name(obj_type)
    var_components = []

    if obj_id and obj_id.strip():
        var_components.append(text_to_identifier(obj_id.strip()))
    if obj_text and obj_text.strip():
        var_components.append("text")
    if var_components:
        identifier = "_".join(var_components)
    elif clean_type:
        identifier = clean_type
    else:
        identifier = "object"

    var_name = f"{container_prefix}_{identifier}"

    if occurrence is not None and occurrence > 1:
        var_name += f"_{occurrence}"

    var_name = re.sub(r"[^\w]", "_", var_name)
    var_name = re.sub(r"_+", "_", var_name)
    var_name = var_name.strip("_")

    return var_name


def make_unique_var_name(candidate_var_name: str, used_var_names: set[str]) -> str:
    if candidate_var_name not in used_var_names:
        return candidate_var_name

    suffix = 2
    while True:
        deduped_candidate_var_name = f"{candidate_var_name}_{suffix}"
        if deduped_candidate_var_name not in used_var_names:
            return deduped_candidate_var_name
        suffix += 1


def extract_property_value(element: ET.Element, prop_name: str) -> str | None:
    """Extract property value from XML element."""
    for prop in element.findall(f'./properties/property[@name="{prop_name}"]/string'):
        if prop is not None:
            return prop.text
    return None


def _realname_str_to_dict(realname_str: str) -> dict:
    """Convert realname string to a dictionary."""
    realname_str = realname_str.strip("{}")
    parts = [part.strip() for part in realname_str.split() if "=" in part]
    realname_dict = {}
    for part in parts:
        key, value = part.split("=", 1)
        value = value.strip("'\"")
        if key == "container":
            value = _realname_str_to_dict(value)  # Recursively parse nested container
        realname_dict[key] = value
    return realname_dict


def extract_realname(element: ET.Element) -> str | None:
    """Extract the realname content if it exists."""
    realname_elem = element.find("realname")
    if realname_elem is not None and realname_elem.text:
        return realname_elem.text.strip()
    return None


def should_include_object(
    obj_id: str | None,
    obj_text: str | None,
    obj_name: str | None,
    obj_type: str,
    clean_type: str,
) -> bool:
    # Include objects with meaningful identifiers
    has_identifier = any(
        [
            obj_id is not None and len(obj_id.strip()) > 0,
            obj_name is not None and len(obj_name.strip()) > 0,
        ]
    )

    # Include objects with visible text content
    has_text = obj_text is not None and len(obj_text.strip()) > 0

    # Include common UI element types (both Qt Quick and Qt Widgets)
    is_ui_element = clean_type in {
        # Qt Quick types
        "Rectangle",
        "Image",
        "Button",
        "Slider",
        "Text",
        # Qt Widgets types
        "QPushButton",
        "QLabel",
        "Dialog",
        "LineEdit",
        "QCheckBox",
        "QRadioButton",
        "QComboBox",
        "QSpinBox",
        "QTextEdit",
        "QListWidget",
        "QTableWidget",
        "QTreeWidget",
        "QGroupBox",
        "QTabWidget",
    }

    # Include custom UI components
    has_ui_marker = any(e in obj_type.lower() for e in ("ui", "comp", "gauge"))

    # Include types ending with _ui
    is_custom_ui = clean_type.endswith("_ui")

    return any(
        [
            has_identifier,
            has_text and (is_ui_element or has_ui_marker or is_custom_ui),
            is_ui_element,
            has_ui_marker,
            is_custom_ui,
        ]
    )


def _objects_from_element_tree(
    root: ET.Element,
    container_prefix: str,
) -> list[SnapshotObject]:
    """Process all elements iteratively using a deque."""
    objects: list[SnapshotObject] = []
    occurrences: dict[int, int] = defaultdict(int)
    used_var_names: set[str] = set()

    # Queue items: (element, parent_var_name)
    top_level_elements = root.findall(".//state/element")
    queue: deque[tuple[ET.Element, str | None]] = deque((e, None) for e in top_level_elements)

    while queue:
        element, parent_var_name = queue.popleft()

        element_id = element.get("id", "")
        class_name = element.get("class", "")
        simplified_type = element.get("simplifiedType", "")

        realname_str = extract_realname(element)
        realname = _realname_str_to_dict(realname_str) if realname_str else None

        obj_id = extract_property_value(element, "id")
        obj_text = extract_property_value(element, "text")
        obj_name = extract_property_value(element, "objectName")
        visible = extract_property_value(element, "visible")

        obj_type = class_name
        if realname is not None and "type" in realname:
            obj_type = realname["type"]
        elif simplified_type:
            obj_type = simplified_type

        clean_type = clean_type_name(obj_type)
        should_include = should_include_object(obj_id, obj_text, obj_name, obj_type, clean_type)

        var_name = None
        if should_include and clean_type not in SKIPPED_TYPES:
            candidate = SnapshotObject(
                realname=realname,
                var_name=var_name,
                container=parent_var_name,
                container_prefix=container_prefix,
                id=obj_id,
                type=clean_type,
                text=obj_text,
                object_name=obj_name,
                visible=(visible == "true") if visible else True,
                element_id=element_id,
                original_type=obj_type,
                occurrence=1,
            )

            occurrences[candidate.squish_prop_hash] += 1
            candidate_occurrence = occurrences[candidate.squish_prop_hash]
            candidate_var_name = make_python_var_name(
                container_prefix,
                obj_id,
                obj_type,
                obj_text,
                candidate_occurrence,
            )
            deduped_candidate_var_name = make_unique_var_name(candidate_var_name, used_var_names)
            new_candidate = candidate.with_var_name(deduped_candidate_var_name).with_occurrence(candidate_occurrence)
            used_var_names.add(deduped_candidate_var_name)
            objects.append(new_candidate)
            var_name = deduped_candidate_var_name

        for child in element.findall("children/element"):
            queue.append((child, var_name or parent_var_name))

    return objects


def parse_object_snapshot(xml_file: str) -> list[SnapshotObject]:
    """Parse the object snapshot XML and extract meaningful objects."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        log.error("Error parsing XML: %s", e)
        return []

    first_element = root.find(".//state/element")
    if first_element is not None:
        title = extract_property_value(first_element, "title") or extract_property_value(first_element, "windowTitle")

        if title:
            container_prefix = re.sub(r"[^\w\s]", "_", title)
            container_prefix = re.sub(r"\s+", "_", container_prefix)
            container_prefix = re.sub(r"_+", "_", container_prefix)
            container_prefix = container_prefix.strip("_")
        else:
            root_class = clean_type_name(first_element.get("class", "Window"))
            container_prefix = root_class
    else:
        container_prefix = "window"

    return _objects_from_element_tree(root, container_prefix)


def _topological_sort(dependencies: dict[str, set[str]], dependents: dict[str, set[str]]) -> list[str]:
    """Topological sorting of objects based on container dependencies. (Kahn's algorithm)"""
    ready_queue: deque[str] = deque(sorted(name for name, deps in dependencies.items() if not deps))
    queued: set[str] = set(ready_queue)

    processed: set[str] = set()
    ordered_names: list[str] = []

    """
    - pop left -> name
    - emit name (add to ordered_names)
    - remove it from dependent node's dependency sets
    - if any dependent node has no more dependencies, add to ready queue (sorted)
    """
    while ready_queue:
        name = ready_queue.popleft()
        queued.discard(name)
        ordered_names.append(name)
        processed.add(name)
        newly_ready: list[str] = []
        for dependent in dependents.get(name, set()):
            dependencies[dependent].discard(name)
            if not dependencies[dependent] and dependent not in processed and dependent not in queued:
                queued.add(dependent)
                newly_ready.append(dependent)

        for dependent in sorted(newly_ready):
            ready_queue.append(dependent)

    return ordered_names


def _sort_objects_for_variable_containers(objects: list[SnapshotObject]) -> list[SnapshotObject]:
    """
    Sort objects so container variables are defined before objects that reference them.
    Falls back to name sorting if a dependency cycle is detected.
    """
    objects_by_name = {obj.var_name: obj for obj in objects}
    dependencies: dict[str, set[str]] = defaultdict(set)
    dependents: dict[str, set[str]] = defaultdict(set)

    # construct dependency graph
    for obj in objects:
        assert obj.var_name is not None
        if obj.container is not None and obj.container in objects_by_name:
            dependencies[obj.var_name].add(obj.container)
            dependents[obj.container].add(obj.var_name)
        else:
            # Add the root explicitly
            dependencies[obj.var_name].update(set())

    # perform topological sort (Kahn)
    ordered_names = _topological_sort(dependencies, dependents)

    if len(ordered_names) != len(objects):
        log.warning("Dependency cycle detected while sorting object definitions; falling back to name sort")
        return sorted(objects, key=lambda x: x.var_name)

    return [objects_by_name[name] for name in ordered_names]


def _format_obj_dict_for_python(obj_dict: dict[str, str | int | bool], unquoted_keys: set[str] | None = None) -> str:
    """Render object dictionary with optional unquoted values (for containers)."""
    unquoted_keys = unquoted_keys or set()

    rendered_entries = []
    for key in sorted(obj_dict.keys()):
        value = obj_dict[key]
        if key in unquoted_keys:
            rendered_value = str(value)
        elif isinstance(value, bool):
            rendered_value = "True" if value else "False"
        else:
            rendered_value = json.dumps(value)
        rendered_entries.append(f'"{key}": {rendered_value}')

    return "{" + ", ".join(rendered_entries) + "}"


def generate_python_names(objects: list[SnapshotObject], container_var_names: set[str] | None = None) -> list[str]:
    """Generate Python code for names.py file."""
    lines = []
    container_var_names = container_var_names or set()

    for obj in _sort_objects_for_variable_containers(objects):
        obj_dict = obj.as_squish_obj_dict()
        unquoted_keys = {"container"} if obj.container in container_var_names else set()
        props_str = _format_obj_dict_for_python(obj_dict, unquoted_keys=unquoted_keys)
        lines.append(f"{obj.var_name} = {props_str}")

    return lines
