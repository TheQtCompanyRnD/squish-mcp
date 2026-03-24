from pathlib import Path


TEST_DATA_DIR: Path = Path(__file__).parent
XML_SNAPSHOTS_DIR: Path = TEST_DATA_DIR / "xml_snapshots"
TESTCASES_DIR: Path = TEST_DATA_DIR / "testcases"
SUITE_FIXTURES_DIR: Path = TEST_DATA_DIR / "suite_fixtures"

TEST_CASE_MINIMAL_NAME = "test_example_minimal"
TEST_CASE_TEMPLATE_MINIMAL_NAME = "test_example_template_minimal"

QT_QUICK_SNAPSHOT = "qt_quick_0ba80d2c-9676-4539-9677-bfc348884b35.xml"
QT_WIDGETS_SNAPSHOT = "qt_widgets_0b8e2d53-269d-48c7-806a-a439fbf29923.xml"
