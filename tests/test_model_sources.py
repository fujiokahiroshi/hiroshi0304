import pytest

from cad_workbench.server import (
    _model_source_entries,
    _resolve_model_source,
    get_cad_model_source,
    list_cad_model_sources,
    search_cad_model_sources,
)


def test_lists_and_reads_example_sources() -> None:
    entries = _model_source_entries("examples")
    ids = {entry["model_id"] for entry in entries}
    assert "example:rc_4wd_drivetrain" in ids

    listing = list_cad_model_sources(source="examples", limit=10)
    assert listing["count"] >= 1
    assert all("_path" not in model for model in listing["models"])

    result = get_cad_model_source(
        model_id="example:rc_4wd_drivetrain",
        start_line=1,
        max_lines=30,
    )
    assert result["start_line"] == 1
    assert "cadquery" in result["content"]
    assert result["total_lines"] > 30


def test_searches_sources() -> None:
    result = search_cad_model_sources(
        query="rc_4wd_drivetrain",
        source="examples",
    )
    assert result["count"] >= 1
    assert result["matches"][0]["model_id"] == "example:rc_4wd_drivetrain"


@pytest.mark.parametrize("model_id", ["../secret", "job:../secret", "example:C:/secret"])
def test_rejects_unsafe_model_ids(model_id: str) -> None:
    with pytest.raises(ValueError):
        _resolve_model_source(model_id)
