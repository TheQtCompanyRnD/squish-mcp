# ruff: noqa: F821

# -*- coding: utf-8 -*-


def main() -> None:
    test.log("suite_example_smoke:tst_smoke started")
    test.verify(True, "basic smoke condition")
    test.log("suite_example_smoke:tst_smoke finished")
