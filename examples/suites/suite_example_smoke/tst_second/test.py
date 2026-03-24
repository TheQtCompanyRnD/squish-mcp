# ruff: noqa: F821

# -*- coding: utf-8 -*-


def main() -> None:
    test.log("suite_example_smoke:tst_second started")
    test.compare(1 + 1, 2, "sanity check")
    test.log("suite_example_smoke:tst_second finished")
