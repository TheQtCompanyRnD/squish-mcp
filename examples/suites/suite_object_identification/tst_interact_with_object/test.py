# ruff: noqa: F821

# -*- coding: utf-8 -*-

import names


def main() -> None:
    startApplication("/path/to/application")

    mouseClick(waitForObject(names.example_object), 0, 0, Qt.LeftButton)
