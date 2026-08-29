from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import cadquery as cq

from .runner import SAFE_BUILTINS, _densify_rotation_track, _safe_import
from .state import VIEWER_PORT, viewer_reachable
from .validation import validate_code


def load_job_model(job_dir: Path) -> dict[str, Any]:
    """Rebuild a generated model with the same restricted globals as the runner."""
    model_path = job_dir / "model.py"
    request_path = job_dir / "request.json"
    if not model_path.is_file() or not request_path.is_file():
        raise ValueError(f"CAD job is incomplete: {job_dir.name}")
    code = model_path.read_text(encoding="utf-8")
    validate_code(code)
    namespace: dict[str, Any] = {
        "cq": cq,
        "cad_step": lambda _label: None,
        "__builtins__": {**SAFE_BUILTINS, "__import__": _safe_import},
        "__name__": "__cad_inspection__",
    }
    exec(compile(code, str(model_path), "exec"), namespace, namespace)  # noqa: S102
    if "result" not in namespace:
        raise ValueError("CAD job does not define result")
    namespace["_request"] = json.loads(request_path.read_text(encoding="utf-8"))
    return namespace


def _as_shape(value: Any) -> cq.Shape:
    if isinstance(value, cq.Workplane):
        value = value.val()
    if not isinstance(value, cq.Shape):
        raise TypeError(f"Unsupported CAD component type: {type(value).__name__}")
    return value


def _world_location(assembly: cq.Assembly, key: str) -> cq.Location:
    location = cq.Location(cq.Vector(0, 0, 0))
    parts = key.split("/")
    for index in range(1, len(parts) + 1):
        ancestor = "/".join(parts[:index])
        node = assembly.objects.get(ancestor)
        if node is not None:
            location = location * node.loc
    return location


def component_shapes(result: Any) -> dict[str, cq.Shape]:
    """Return leaf component paths mapped to shapes in world coordinates."""
    if not isinstance(result, cq.Assembly):
        return {"result": _as_shape(result)}
    components: dict[str, cq.Shape] = {}
    for key, node in result.objects.items():
        if node.obj is None:
            continue
        shape = _as_shape(node.obj)
        components[key] = shape.moved(_world_location(result, key))
    return components


def _external_path(result: Any, key: str) -> str:
    if not isinstance(result, cq.Assembly):
        return "/result"
    root_name = result.name or "assembly"
    return f"/{root_name}/{key}"


def list_components(result: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, shape in component_shapes(result).items():
        box = shape.BoundingBox()
        center = shape.Center()
        entries.append(
            {
                "component_id": key,
                "path": _external_path(result, key),
                "name": key.rsplit("/", 1)[-1],
                "shape_type": shape.ShapeType(),
                "solid_count": len(shape.Solids()),
                "bounding_box_mm": {
                    "min": [round(box.xmin, 6), round(box.ymin, 6), round(box.zmin, 6)],
                    "max": [round(box.xmax, 6), round(box.ymax, 6), round(box.zmax, 6)],
                    "size": [round(box.xlen, 6), round(box.ylen, 6), round(box.zlen, 6)],
                },
                "center_mm": [round(center.x, 6), round(center.y, 6), round(center.z, 6)],
            }
        )
    return sorted(entries, key=lambda item: item["path"])


def resolve_component(result: Any, query: str) -> tuple[str, cq.Shape]:
    components = component_shapes(result)
    normalized = query.strip().strip("/")
    if isinstance(result, cq.Assembly):
        root_name = result.name or "assembly"
        if normalized == root_name:
            normalized = ""
        elif normalized.startswith(f"{root_name}/"):
            normalized = normalized[len(root_name) + 1 :]
    if normalized in components:
        return normalized, components[normalized]
    leaf_matches = [
        (key, shape)
        for key, shape in components.items()
        if key.rsplit("/", 1)[-1] == normalized
    ]
    if len(leaf_matches) == 1:
        return leaf_matches[0]
    if len(leaf_matches) > 1:
        candidates = ", ".join(key for key, _shape in leaf_matches[:20])
        raise ValueError(f"Ambiguous component '{query}'; choose one of: {candidates}")
    raise ValueError(f"CAD component not found: {query}")


def inspect_clearance(
    result: Any,
    component_a: str,
    component_b: str,
    required_clearance_mm: float,
) -> dict[str, Any]:
    key_a, shape_a = resolve_component(result, component_a)
    key_b, shape_b = resolve_component(result, component_b)
    if key_a == key_b:
        raise ValueError("component_a and component_b must be different")
    common = shape_a.intersect(shape_b)
    overlap = float(common.Volume())
    distance = float(shape_a.distance(shape_b))
    if overlap > 1e-6:
        status = "interference"
    elif distance < required_clearance_mm:
        status = "insufficient_clearance"
    else:
        status = "pass"
    return {
        "component_a": {"component_id": key_a, "path": _external_path(result, key_a)},
        "component_b": {"component_id": key_b, "path": _external_path(result, key_b)},
        "overlap_volume_mm3": round(overlap, 6),
        "minimum_clearance_mm": round(distance, 6),
        "required_clearance_mm": required_clearance_mm,
        "interference": overlap > 1e-6,
        "status": status,
    }


def show_job(namespace: dict[str, Any], with_animation: bool, reset_camera: bool) -> dict[str, Any]:
    if not viewer_reachable():
        raise ConnectionError(f"OCP CAD Viewer is not reachable on port {VIEWER_PORT}")
    from ocp_vscode import Animation, Camera, set_port, show

    set_port(VIEWER_PORT)
    camera = Camera.RESET if reset_camera else Camera.KEEP
    show(namespace["result"], reset_camera=camera, port=VIEWER_PORT)
    tracks = namespace.get("animation", namespace["_request"].get("animation", []))
    if not with_animation or not tracks:
        return {"displayed": True, "animation_tracks": 0, "viewer_port": VIEWER_PORT}
    time.sleep(1.0)
    animation = Animation()
    for track in tracks:
        action = str(track["action"])
        times = [float(item) for item in track["times"]]
        values = track["values"]
        if action in {"rx", "ry", "rz"}:
            times, values = _densify_rotation_track(
                times, [float(item) for item in values]
            )
        animation.add_track(str(track["path"]), action, times, values)
    animation.animate(float(namespace["_request"].get("speed", 1.0)))
    time.sleep(0.25)
    animation.set_relative_time(0.0, port=VIEWER_PORT)
    return {
        "displayed": True,
        "animation_tracks": len(tracks),
        "viewer_port": VIEWER_PORT,
    }


def run_command(argv: list[str]) -> dict[str, Any]:
    if len(argv) < 2:
        raise ValueError("Expected action and job directory")
    action = argv[0]
    job_dir = Path(argv[1]).resolve()
    namespace = load_job_model(job_dir)
    result = namespace["result"]
    if action == "list":
        components = list_components(result)
        return {"component_count": len(components), "components": components}
    if action == "clearance":
        if len(argv) != 5:
            raise ValueError("clearance expects component_a, component_b, required clearance")
        return inspect_clearance(result, argv[2], argv[3], float(argv[4]))
    if action == "show":
        if len(argv) != 4:
            raise ValueError("show expects with_animation and reset_camera flags")
        return show_job(namespace, argv[2] == "1", argv[3] == "1")
    raise ValueError(f"Unknown job tool action: {action}")


def main() -> int:
    try:
        print(json.dumps({"ok": True, **run_command(sys.argv[1:])}, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 - subprocess boundary returns diagnostics
        print(
            json.dumps(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()},
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.stdout.flush()
    sys.stderr.flush()
    # Some Windows OpenCascade builds crash while destroying large Assembly graphs.
    # This process is intentionally isolated, so exit after the complete JSON response.
    os._exit(exit_code)
