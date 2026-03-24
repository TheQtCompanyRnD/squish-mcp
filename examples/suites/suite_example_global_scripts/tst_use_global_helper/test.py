# ruff: noqa: F821

# Shared/global script lookup should use Squish APIs in test scripts.
source(findFile("scripts", "example_helpers.py"))


def main() -> None:
    test.log("suite_example_global_scripts:tst_use_global_helper started")
    test.compare(add(2, 3), 5, "helper add() from global scripts")
    test.verify(flip(True) is False, "helper flip() from global scripts")
    test.log("suite_example_global_scripts:tst_use_global_helper finished")
