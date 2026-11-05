"""Published dependency constraints must match the APIs used by the server."""

from importlib.metadata import requires


def test_mcp_dependency_excludes_incompatible_major_version() -> None:
    dependencies = requires("duckbrain") or []
    mcp_requirement = next(item for item in dependencies if item.startswith("mcp["))
    assert "<2" in mcp_requirement
