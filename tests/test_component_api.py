from pathlib import Path

import pytest

from cad_workbench import server


def make_job(tmp_path: Path, name: str = "demo") -> Path:
    job_dir = tmp_path / name
    job_dir.mkdir()
    (job_dir / "model.py").write_text("result = cq.Workplane('XY').box(1, 1, 1)")
    (job_dir / "request.json").write_text('{"animation": [], "speed": 1.0}')
    return job_dir


def test_list_cad_components_uses_job_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    make_job(tmp_path)
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "_run_job_tool",
        lambda action, job_dir, *args: {
            "component_count": 1,
            "components": [{"component_id": "body"}],
        },
    )

    result = server.list_cad_components("job:demo")

    assert result["model_id"] == "job:demo"
    assert result["component_count"] == 1


def test_inspect_component_clearance_returns_named_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    make_job(tmp_path)
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "_run_job_tool",
        lambda action, job_dir, *args: {
            "status": "pass",
            "overlap_volume_mm3": 0.0,
            "minimum_clearance_mm": 1.0,
        },
    )

    result = server.inspect_component_clearance("job:demo", "motor", "gear", 0.5)

    assert result["status"] == "pass"
    assert result["minimum_clearance_mm"] == 1.0


def test_show_cad_job_reuses_viewer_tab(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    make_job(tmp_path)
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    monkeypatch.setattr(
        server,
        "_run_job_tool",
        lambda action, job_dir, *args: {
            "displayed": True,
            "animation_tracks": 2,
            "viewer_port": 3939,
        },
    )

    result = server.show_cad_job("job:demo", with_animation=True)

    assert result["displayed"] is True
    assert result["reused_existing_tab"] is True
    assert result["animation_tracks"] == 2


@pytest.mark.parametrize("model_id", ["example:demo", "job:../secret", "../secret"])
def test_component_api_rejects_unsafe_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model_id: str,
) -> None:
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    with pytest.raises(ValueError):
        server.list_cad_components(model_id)
