import cadquery as cq
import pytest

from cad_workbench.job_tools import (
    component_shapes,
    inspect_clearance,
    list_components,
    resolve_component,
)


def make_test_assembly() -> cq.Assembly:
    box = cq.Workplane("XY").box(10, 10, 10).val()
    nested = cq.Assembly(name="nested")
    nested.add(box, name="box_b")
    result = cq.Assembly(name="test_assembly")
    result.add(box, name="box_a")
    result.add(
        nested,
        name="nested",
        loc=cq.Location(cq.Vector(8, 0, 0)),
    )
    return result


def test_lists_components_with_world_locations() -> None:
    result = make_test_assembly()

    entries = list_components(result)

    assert [entry["component_id"] for entry in entries] == ["box_a", "nested/box_b"]
    assert entries[0]["path"] == "/test_assembly/box_a"
    assert entries[0]["center_mm"] == [0.0, 0.0, 0.0]
    assert entries[1]["center_mm"] == [8.0, 0.0, 0.0]
    assert component_shapes(result)["nested/box_b"].Center().x == pytest.approx(8.0)


def test_inspects_named_component_overlap() -> None:
    result = make_test_assembly()

    inspection = inspect_clearance(result, "box_a", "nested/box_b", 0.5)

    assert inspection["status"] == "interference"
    assert inspection["interference"] is True
    assert inspection["overlap_volume_mm3"] == pytest.approx(200.0)
    assert inspection["minimum_clearance_mm"] == 0.0


def test_resolves_full_viewer_path() -> None:
    result = make_test_assembly()

    key, shape = resolve_component(result, "/test_assembly/nested/box_b")

    assert key == "nested/box_b"
    assert shape.Center().x == pytest.approx(8.0)


def test_rejects_same_component() -> None:
    result = make_test_assembly()

    with pytest.raises(ValueError, match="must be different"):
        inspect_clearance(result, "box_a", "box_a", 0.5)
