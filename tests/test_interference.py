from pathlib import Path

import cadquery as cq
import pytest

from cad_workbench import server


def export_solids(path: Path, solids: list[cq.Shape]) -> None:
    path.parent.mkdir(parents=True)
    cq.exporters.export(cq.Compound.makeCompound(solids), str(path))


def test_detects_overlapping_solids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = cq.Workplane("XY").box(10, 10, 10).val()
    second = cq.Workplane("XY").box(10, 10, 10).translate((8, 0, 0)).val()
    export_solids(tmp_path / "overlap" / "model.step", [first, second])
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)

    result = server.detect_cad_interference("job:overlap")

    assert result["solid_count"] == 2
    assert result["interference_count"] == 1
    assert result["clearance_violation_count"] == 0
    assert result["truncated"] is False
    assert result["findings"][0] == {
        "type": "interference",
        "solid_a": "solid_000",
        "solid_b": "solid_001",
        "overlap_volume_mm3": pytest.approx(200.0),
    }


def test_detects_clearance_violation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = cq.Workplane("XY").box(10, 10, 10).val()
    second = cq.Workplane("XY").box(10, 10, 10).translate((11, 0, 0)).val()
    export_solids(tmp_path / "clearance" / "model.step", [first, second])
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)

    result = server.detect_cad_interference(
        "job:clearance",
        clearance_mm=2.0,
    )

    assert result["interference_count"] == 0
    assert result["clearance_violation_count"] == 1
    assert result["findings"][0]["type"] == "clearance_violation"
    assert result["findings"][0]["distance_mm"] == pytest.approx(1.0)


def test_interference_result_limit_is_reported(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    solids = [
        cq.Workplane("XY").box(10, 10, 10).translate((offset, 0, 0)).val()
        for offset in (0, 1, 2)
    ]
    export_solids(tmp_path / "limited" / "model.step", solids)
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)

    result = server.detect_cad_interference("job:limited", max_results=1)

    assert result["finding_count"] == 1
    assert result["truncated"] is True
    assert any("max_results" in warning for warning in result["warnings"])


@pytest.mark.parametrize(
    "model_id",
    ["example:rc_4wd_drivetrain", "job:../secret", "../secret"],
)
def test_interference_rejects_unsafe_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model_id: str,
) -> None:
    monkeypatch.setattr(server, "JOBS_DIR", tmp_path)
    with pytest.raises(ValueError):
        server.detect_cad_interference(model_id)
