import typing as t

from collections.abc import Callable
from pathlib import Path

import pytest

from squish_mcp.errors import AnalysisException
from squish_mcp.errors import ConfigurationException
from squish_mcp.errors import FileOperationException
from squish_mcp.errors import TestExecutionException as SquishTestExecutionException
from squish_mcp.server.tools.analysis import analysis as analysis_tools
from squish_mcp.server.tools.scripting import scripting as scripting_tools
from squish_mcp.server.tools.squishrunner import squishrunner as squishrunner_tools
from squish_mcp.squish.analysis import models as analysis_models
from squish_mcp.squish.cli import squishrunner as squishrunner_cli
from squish_mcp.squish.scripting import pom_generation


LOGIN_PAGE = "Login"
LOGIN_XML_PATH = "/tmp/login.xml"
TEST_SUITE_PATH = "/tmp/suite_py"
OUTPUT_DIRECTORY = "/tmp"


_TReturn = t.TypeVar("_TReturn")


def _minimal_patterns() -> analysis_models.ObjectReferencePatterns:
    return analysis_models.ObjectReferencePatterns(
        has_pom_classes=False,
        has_function_based=False,
        has_simple_dicts=True,
        global_script_locations=[],
        suite_names_locations=[],
        preferred_location_type=analysis_models.LocationType.SUITE_NAMES,
        class_patterns=[],
        function_patterns=[],
    )


def _runner_result(
    return_code: int,
    stdout: str = "",
    stderr: str = "",
    cmd: str = "cmd",
) -> squishrunner_cli.SquishRunnerExecutionResult:
    return squishrunner_cli.SquishRunnerExecutionResult(cmd=cmd, stdout=stdout, stderr=stderr, return_code=return_code)


def _snapshot_result(
    *,
    success: bool,
    error_message: str,
    objects_found: int = 0,
    temp_file_path: Path | None = None,
) -> pom_generation.SnapshotParseResult:
    return pom_generation.SnapshotParseResult(
        page_name=LOGIN_PAGE,
        xml_file=Path(LOGIN_XML_PATH),
        objects_found=objects_found,
        generated_format="simple_dict",
        temp_file_path=temp_file_path or Path(),
        success=success,
        error_message=error_message,
    )


def _global_dirs_result(
    return_code: int = 0,
    directories: list[str] | None = None,
    stderr: str = "",
) -> squishrunner_cli.GlobalScriptDirsResult:
    return squishrunner_cli.GlobalScriptDirsResult(
        execution=_runner_result(return_code=return_code, stderr=stderr, cmd="get"),
        directories=directories or [],
    )


def _patch_pom_workflow_prereqs(monkeypatch: pytest.MonkeyPatch) -> None:
    def _empty_object_reference_context(
        test_suite_path: str,
    ) -> analysis_models.ObjectReferenceAnalysis:
        _ = test_suite_path
        return analysis_models.ObjectReferenceAnalysis(files=[])

    monkeypatch.setattr(
        analysis_tools.squish_analysis,
        "analyze_object_references",
        _empty_object_reference_context,
    )
    monkeypatch.setattr(
        analysis_tools.squish_analysis,
        "analyze_object_reference_patterns",
        lambda _ctx: _minimal_patterns(),
    )
    monkeypatch.setattr(
        analysis_tools,
        "determine_output_strategy_from_patterns",
        lambda _suite_path, _patterns, _page: pom_generation.OutputStrategy(
            format=pom_generation.POMFormat.SIMPLE_DICT,
            target_directory=Path("/tmp"),
            location_type=analysis_models.LocationType.SUITE_NAMES,
        ),
    )


def test_pom_generation_parse_failure_raises_analysis(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_pom_workflow_prereqs(monkeypatch)
    monkeypatch.setattr(
        analysis_tools,
        "page_objects_from_snapshot",
        lambda _xml, _page, _strategy, _output_dir: _snapshot_result(
            success=False, error_message="snapshot parse failed"
        ),
    )

    with pytest.raises(AnalysisException, match="snapshot parse failed"):
        analysis_tools.generate_page_objects_from_snapshot(
            TEST_SUITE_PATH, LOGIN_XML_PATH, LOGIN_PAGE, OUTPUT_DIRECTORY
        )


@pytest.mark.parametrize(
    ("tool_fn", "extra_args"),
    [
        pytest.param(scripting_tools.get_suite_configuration, [], id="get_suite_configuration"),
        pytest.param(scripting_tools.create_test_case, ["tst_case_name"], id="create_test_case"),
    ],
)
def test_scripting_missing_suite_path_raises_file_error(
    tmp_path: Path,
    tool_fn: Callable[..., t.Any],
    extra_args: tuple[object, ...],
) -> None:
    missing_path = str(tmp_path / "suite_missing")
    with pytest.raises(FileOperationException, match="Suite path does not exist"):
        tool_fn(missing_path, *extra_args)


def test_create_test_suite_already_exists_raises_file_error(tmp_path: Path) -> None:
    existing = tmp_path / "suite_existing"
    existing.mkdir()
    with pytest.raises(FileOperationException, match="Suite already exists"):
        scripting_tools.create_test_suite(str(existing))


def test_create_test_suite_non_suite_prefix_raises_file_error(tmp_path: Path) -> None:
    bad_name = tmp_path / "not_a_suite"
    with pytest.raises(FileOperationException, match="must start with 'suite_'"):
        scripting_tools.create_test_suite(str(bad_name))


def test_create_test_suite_success_returns_response(tmp_path: Path) -> None:
    suite_path = tmp_path / "suite_new"
    result = scripting_tools.create_test_suite(str(suite_path))
    assert result.suite_path == str(suite_path)
    assert "suite.conf" in result.files_created
    assert "shared/scripts/names.py" in result.files_created


def test_run_test_raises_on_global_script_setup_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "get_global_script_dirs",
        lambda: _global_dirs_result(directories=["/tmp"]),
    )
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "set_global_script_dirs",
        lambda _dirs: _runner_result(return_code=2, stdout="x", stderr="bad config", cmd="cfg"),
    )
    with pytest.raises(ConfigurationException, match=r"setGlobalScriptDirs failed \(rc=2\)"):
        squishrunner_tools.run_test("/tmp/suite_py", {})


def test_run_test_raises_on_runner_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "get_global_script_dirs",
        lambda: _global_dirs_result(directories=["/tmp"]),
    )
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "set_global_script_dirs",
        lambda _dirs: _runner_result(return_code=0, cmd="cfg"),
    )
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "run_test",
        lambda _suite, _tc, _ctx, _report=None: _runner_result(
            return_code=5,
            stdout="test output",
            stderr="test error",
            cmd="run",
        ),
    )

    with pytest.raises(SquishTestExecutionException, match=r"Test run failed \(rc=5\)"):
        squishrunner_tools.run_test("/tmp/suite_py", {})


def test_run_test_uses_runtime_configured_dirs(monkeypatch: pytest.MonkeyPatch) -> None:
    configured_dirs = ["/tmp/runtime"]
    applied_dirs: list[str] = []

    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "get_global_script_dirs",
        lambda: _global_dirs_result(directories=configured_dirs),
    )

    def set_dirs(dirs: list[str]) -> squishrunner_cli.SquishRunnerExecutionResult:
        applied_dirs.extend(dirs)
        return _runner_result(return_code=0, cmd="cfg")

    monkeypatch.setattr(squishrunner_tools.squishrunner, "set_global_script_dirs", set_dirs)
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "run_test",
        lambda _suite, _tc, _ctx, _report=None: _runner_result(return_code=0, stdout="ok", cmd="run"),
    )

    squishrunner_tools.run_test("/tmp/suite_py", {})

    assert applied_dirs == configured_dirs


def test_set_global_script_dirs_returns_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    dirs = ["/tmp/one", "/tmp/two"]
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "set_global_script_dirs",
        lambda _dirs: _runner_result(return_code=0, cmd="set"),
    )

    result = squishrunner_tools.set_global_script_dirs(dirs)

    assert result is None


def test_get_global_script_dirs_raises_on_nonzero_rc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        squishrunner_tools.squishrunner,
        "get_global_script_dirs",
        lambda: squishrunner_cli.GlobalScriptDirsResult(
            execution=_runner_result(return_code=3, stderr="cannot query", cmd="get"),
            directories=[],
        ),
    )
    with pytest.raises(ConfigurationException, match=r"getGlobalScriptDirs failed \(rc=3\)"):
        squishrunner_tools.get_global_script_dirs()
