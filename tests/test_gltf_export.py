import math
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np
import pygltflib as gltf
import pytest

from cad_workbench.gltf_export import (
    _quat_from_axis_angle_deg,
    _quat_multiply,
    export_assembly_to_glb,
)


def test_quat_multiply_identity_is_noop() -> None:
    identity = (0.0, 0.0, 0.0, 1.0)
    q = (0.1, 0.2, 0.3, math.sqrt(1 - 0.14))
    assert _quat_multiply(identity, q) == pytest.approx(q, abs=1e-9)


def test_quat_from_axis_angle_matches_known_rotation() -> None:
    x, y, z, w = _quat_from_axis_angle_deg("z", 90.0)
    assert x == 0.0
    assert y == 0.0
    assert z == pytest.approx(math.sin(math.pi / 4))
    assert w == pytest.approx(math.cos(math.pi / 4))


def _read_accessor(document: gltf.GLTF2, blob: bytes, index: int) -> np.ndarray:
    accessor = document.accessors[index]
    buffer_view = document.bufferViews[accessor.bufferView]
    type_size = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[accessor.type]
    raw = blob[buffer_view.byteOffset : buffer_view.byteOffset + 4 * type_size * accessor.count]
    array = np.frombuffer(raw, dtype=np.float32)
    return array.reshape(accessor.count, type_size) if type_size > 1 else array


def _spinning_box_assembly() -> tuple[cq.Assembly, list[dict]]:
    box = cq.Workplane("XY").box(1, 1, 1)
    spinner = cq.Assembly(name="spinner")
    spinner.add(box, name="body", color=cq.Color(0.5, 0.5, 0.5))
    root = cq.Assembly(name="root")
    root.add(spinner, name="spinner", loc=cq.Location(cq.Vector(5, 0, 0)))
    animation = [
        {
            "path": "/root/spinner",
            "action": "rz",
            "times": [0.0, 1.0, 2.0],
            "values": [0.0, 90.0, 180.0],
        }
    ]
    return root, animation


def test_export_assembly_to_glb_bakes_base_plus_delta_rotation() -> None:
    root, animation = _spinning_box_assembly()
    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "spinner.glb"
        stats = export_assembly_to_glb(root, animation, output_path, title="spinner_test")

        assert stats["animation_channel_count"] == 1
        assert stats["skipped_animation_paths"] == []
        assert output_path.is_file()

        document = gltf.GLTF2().load(str(output_path))
        blob = document.binary_blob()
        channel = document.animations[0].channels[0]
        sampler = document.animations[0].samplers[channel.sampler]
        node = document.nodes[channel.target.node]

        assert node.name == "spinner"
        assert channel.target.path == "rotation"

        values = _read_accessor(document, blob, sampler.output)
        magnitudes = np.linalg.norm(values, axis=1)
        assert np.allclose(magnitudes, 1.0, atol=1e-5)

        # t=0 -> 0 degree delta, so the baked quaternion must equal the node's
        # own rest rotation exactly (identity local transform here).
        assert np.allclose(values[0], node.rotation, atol=1e-5)

        # t=2 -> 180 degrees about Z composed onto the rest orientation.
        expected_180 = _quat_multiply(tuple(node.rotation), _quat_from_axis_angle_deg("z", 180.0))
        assert np.allclose(values[-1], expected_180, atol=1e-5)


def test_export_assembly_to_glb_reports_unmatched_animation_paths() -> None:
    root, animation = _spinning_box_assembly()
    animation.append(
        {"path": "/root/does_not_exist", "action": "rz", "times": [0.0], "values": [0.0]}
    )
    with tempfile.TemporaryDirectory() as tmp:
        stats = export_assembly_to_glb(root, animation, Path(tmp) / "spinner.glb")
        assert stats["skipped_animation_paths"] == ["/root/does_not_exist"]


def test_export_assembly_to_glb_wraps_scene_for_zup_to_yup() -> None:
    root, animation = _spinning_box_assembly()
    with tempfile.TemporaryDirectory() as tmp:
        output_path = Path(tmp) / "spinner.glb"
        export_assembly_to_glb(root, animation, output_path)
        document = gltf.GLTF2().load(str(output_path))
        root_node = document.nodes[document.scenes[document.scene].nodes[0]]
        assert root_node.name == "Zup_to_Yup"
        assert root_node.children == [0]
