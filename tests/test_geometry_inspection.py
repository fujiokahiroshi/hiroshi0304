from pathlib import Path

import cadquery as cq
import pytest

from cad_workbench import server


def test_inspects_step_geometry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job_dir = tmp_path / "cube"
    job_dir.mkdir()
    step_path = job_dir / "model.step"
    cq.exporters.export(cq.Workplane("XY").box(10, 20, 30), str(step_path))
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)

    result = server.inspect_cad_geometry("job:cube")

    assert result["valid"] is True
    assert result["units"] == "mm"
    assert result["shape_type"] in {"Solid", "Compound"}
    assert result["bounding_box_mm"]["size"] == {
        "x": 10.0,
        "y": 20.0,
        "z": 30.0,
    }
    assert result["volume_mm3"] == pytest.approx(6000.0)
    assert result["center_of_mass_mm"] == {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0,
    }
    assert result["topology"]["solids"] == 1
    assert result["warnings"] == []


@pytest.mark.parametrize(
    "model_id",
    ["example:rc_4wd_drivetrain", "job:../secret", "../secret"],
)
def test_geometry_inspection_rejects_unsafe_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model_id: str,
) -> None:
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    with pytest.raises(ValueError):
        server.inspect_cad_geometry(model_id)
