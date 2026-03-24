# ruff: noqa: F821

# -*- coding: utf-8 -*-


def main() -> None:
    startApplication("/path/to/application")
    snapshot_path = "/path/to/suite"

    # creating snapshot per top level element, i.e. different windows
    for index, top_level_element in enumerate(object.topLevelObjects()):
        saveObjectSnapshot(top_level_element, snapshot_path + f"snapshot_{index}.xml")
