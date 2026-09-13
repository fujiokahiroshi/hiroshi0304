"""Export a CadQuery Assembly (geometry + OCP Viewer animation tracks) to Unity-ready GLB.

CadQuery's own `Assembly.save(path, exportType="GLTF")` only writes static geometry
via OCCT's RWGltf writer -- it has no idea about the `animation` track list each
job's model.py produces for the OCP CAD Viewer (see `runner.py`). This module
rebuilds the glTF scene graph directly from the `cq.Assembly` tree so the same
animation tracks can be re-targeted as glTF animation channels, which Unity's
glTF importers (glTFast / UnityGLTF) play back natively.

Track semantics are reverse-engineered from the OCP CAD Viewer frontend
(ocp_vscode's `three-cad-viewer.esm.js`, `addRotationTrack`/`addTranslationTrack`/
`addPositionTrack`): each keyframe value is added to (translation) or composed
with (rotation, local-axis, post-multiplied) the object's REST transform, not
an absolute value. `_absolute_translation`/`_absolute_rotation` reproduce that.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import cadquery as cq
import numpy as np
import pygltflib as gltf

from .runner import _densify_rotation_track

_MESH_TOLERANCE = 0.3
_ANGULAR_TOLERANCE = 0.3

Vec3 = tuple[float, float, float]
Quat = tuple[float, float, float, float]

# glTF (like Unity) mandates a right-handed Y-up scene; CadQuery/OCCT is
# right-handed Z-up. Wrap the whole tree in one root node rotated -90 degrees
# about X instead of touching every transform individually.
_HALF = math.radians(-90.0) / 2.0
_ZUP_TO_YUP: Quat = (math.sin(_HALF), 0.0, 0.0, math.cos(_HALF))


def _decompose_location(loc: cq.Location) -> tuple[Vec3, Quat]:
    trsf = loc.wrapped.Transformation()
    t = trsf.TranslationPart()
    q = trsf.GetRotation()
    return (t.X(), t.Y(), t.Z()), (q.X(), q.Y(), q.Z(), q.W())


def _quat_multiply(a: Quat, b: Quat) -> Quat:
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def _quat_from_axis_angle_deg(axis: str, angle_deg: float) -> Quat:
    half = math.radians(angle_deg) / 2.0
    s, c = math.sin(half), math.cos(half)
    if axis == "x":
        return (s, 0.0, 0.0, c)
    if axis == "y":
        return (0.0, s, 0.0, c)
    if axis == "z":
        return (0.0, 0.0, s, c)
    raise ValueError(f"unknown rotation axis: {axis}")


def _leaf_shapes(node: cq.Assembly) -> list[cq.Shape]:
    obj = node.obj
    if obj is None:
        return []
    if isinstance(obj, cq.Shape):
        return [obj]
    return [v for v in obj.vals() if isinstance(v, cq.Shape)]


class _SceneBuilder:
    def __init__(self) -> None:
        self.blob = bytearray()
        self.buffer_views: list[gltf.BufferView] = []
        self.accessors: list[gltf.Accessor] = []
        self.meshes: list[gltf.Mesh] = []
        self.materials: list[gltf.Material] = []
        self._material_cache: dict[tuple[float, float, float, float], int] = {}

    def _add_accessor(
        self,
        data: bytes,
        component_type: int,
        count: int,
        type_: str,
        target: int | None = None,
        minimum: list[float] | None = None,
        maximum: list[float] | None = None,
    ) -> int:
        while len(self.blob) % 4 != 0:
            self.blob.append(0)
        offset = len(self.blob)
        self.blob.extend(data)
        view_index = len(self.buffer_views)
        self.buffer_views.append(
            gltf.BufferView(buffer=0, byteOffset=offset, byteLength=len(data), target=target)
        )
        accessor = gltf.Accessor(
            bufferView=view_index,
            componentType=component_type,
            count=count,
            type=type_,
            min=minimum,
            max=maximum,
        )
        index = len(self.accessors)
        self.accessors.append(accessor)
        return index

    def get_material(self, color: cq.Color | None) -> int | None:
        if color is None:
            return None
        rgba = tuple(round(component, 4) for component in color.toTuple())
        cached = self._material_cache.get(rgba)
        if cached is not None:
            return cached
        r, g, b, a = rgba
        material = gltf.Material(
            pbrMetallicRoughness=gltf.PbrMetallicRoughness(
                baseColorFactor=[r, g, b, a],
                metallicFactor=0.35,
                roughnessFactor=0.55,
            ),
            alphaMode="BLEND" if a < 0.999 else "OPAQUE",
            doubleSided=True,
        )
        index = len(self.materials)
        self.materials.append(material)
        self._material_cache[rgba] = index
        return index

    def add_shapes_mesh(self, shapes: list[cq.Shape], material_index: int | None) -> int | None:
        """Flat-shaded mesh: every triangle gets its own 3 vertices and a face normal."""
        position_chunks = []
        normal_chunks = []
        index_chunks = []
        vertex_offset = 0
        for shape in shapes:
            vertices, triangles = shape.tessellate(_MESH_TOLERANCE, _ANGULAR_TOLERANCE)
            if not triangles:
                continue
            points = np.array([(v.x, v.y, v.z) for v in vertices], dtype=np.float64)
            tri = np.asarray(triangles, dtype=np.int64)
            v0, v1, v2 = points[tri[:, 0]], points[tri[:, 1]], points[tri[:, 2]]
            face_normals = np.cross(v1 - v0, v2 - v0)
            lengths = np.linalg.norm(face_normals, axis=1)
            lengths[lengths == 0] = 1.0
            face_normals = face_normals / lengths[:, None]

            triangle_count = len(tri)
            positions = np.empty((triangle_count * 3, 3), dtype=np.float32)
            positions[0::3], positions[1::3], positions[2::3] = v0, v1, v2
            normals = np.empty((triangle_count * 3, 3), dtype=np.float32)
            normals[0::3] = normals[1::3] = normals[2::3] = face_normals

            position_chunks.append(positions)
            normal_chunks.append(normals)
            index_chunks.append(np.arange(triangle_count * 3, dtype=np.uint32) + vertex_offset)
            vertex_offset += triangle_count * 3

        if not position_chunks:
            return None

        positions = np.concatenate(position_chunks, axis=0)
        normals = np.concatenate(normal_chunks, axis=0)
        indices = np.concatenate(index_chunks, axis=0)

        position_accessor = self._add_accessor(
            positions.tobytes(),
            gltf.FLOAT,
            len(positions),
            "VEC3",
            target=gltf.ARRAY_BUFFER,
            minimum=positions.min(axis=0).tolist(),
            maximum=positions.max(axis=0).tolist(),
        )
        normal_accessor = self._add_accessor(
            normals.tobytes(), gltf.FLOAT, len(normals), "VEC3", target=gltf.ARRAY_BUFFER
        )
        index_accessor = self._add_accessor(
            indices.tobytes(),
            gltf.UNSIGNED_INT,
            len(indices),
            "SCALAR",
            target=gltf.ELEMENT_ARRAY_BUFFER,
        )
        primitive = gltf.Primitive(
            attributes=gltf.Attributes(POSITION=position_accessor, NORMAL=normal_accessor),
            indices=index_accessor,
            material=material_index,
        )
        mesh_index = len(self.meshes)
        self.meshes.append(gltf.Mesh(primitives=[primitive]))
        return mesh_index

    def add_animation_track(
        self,
        node_index: int,
        base_translation: Vec3,
        base_rotation: Quat,
        action: str,
        times: list[float],
        values: Any,
    ) -> tuple[int, str] | None:
        if action in ("rx", "ry", "rz"):
            axis = action[1]
            dense_times, dense_angles = _densify_rotation_track(times, [float(v) for v in values])
            output = [
                _quat_multiply(base_rotation, _quat_from_axis_angle_deg(axis, angle))
                for angle in dense_angles
            ]
            times = dense_times
            component_size, type_, target_path = 4, "VEC4", "rotation"
        elif action == "q":
            output = [_quat_multiply(base_rotation, tuple(v)) for v in values]
            component_size, type_, target_path = 4, "VEC4", "rotation"
        elif action == "t":
            output = [
                (base_translation[0] + v[0], base_translation[1] + v[1], base_translation[2] + v[2])
                for v in values
            ]
            component_size, type_, target_path = 3, "VEC3", "translation"
        elif action in ("tx", "ty", "tz"):
            axis_index = {"tx": 0, "ty": 1, "tz": 2}[action]
            output = []
            for v in values:
                translated = list(base_translation)
                translated[axis_index] += float(v)
                output.append(tuple(translated))
            component_size, type_, target_path = 3, "VEC3", "translation"
        else:
            return None

        times_array = np.asarray(times, dtype=np.float32)
        values_array = np.asarray(output, dtype=np.float32).reshape(-1, component_size)
        input_accessor = self._add_accessor(
            times_array.tobytes(),
            gltf.FLOAT,
            len(times_array),
            "SCALAR",
            minimum=[float(times_array.min())],
            maximum=[float(times_array.max())],
        )
        output_accessor = self._add_accessor(
            values_array.tobytes(), gltf.FLOAT, len(values_array), type_
        )
        return input_accessor, output_accessor, target_path  # type: ignore[return-value]


def export_assembly_to_glb(
    result: cq.Assembly,
    animation: list[dict[str, Any]],
    output_path: Path,
    title: str = "CAD model",
) -> dict[str, Any]:
    """Write `result` and its `animation` tracks to a single Unity-importable .glb file."""
    builder = _SceneBuilder()
    nodes: list[gltf.Node] = []
    path_to_node: dict[str, int] = {}
    base_transforms: dict[int, tuple[Vec3, Quat]] = {}

    def build(assembly: cq.Assembly, path: str) -> int:
        translation, rotation = _decompose_location(assembly.loc)
        node = gltf.Node(name=assembly.name, translation=list(translation), rotation=list(rotation))
        index = len(nodes)
        nodes.append(node)
        path_to_node[path] = index
        base_transforms[index] = (translation, rotation)

        shapes = _leaf_shapes(assembly)
        if shapes:
            material_index = builder.get_material(assembly.color)
            mesh_index = builder.add_shapes_mesh(shapes, material_index)
            if mesh_index is not None:
                node.mesh = mesh_index

        child_indices = [build(child, f"{path}/{child.name}") for child in assembly.children]
        if child_indices:
            node.children = child_indices
        return index

    build(result, f"/{result.name}")

    channels: list[gltf.AnimationChannel] = []
    samplers: list[gltf.AnimationSampler] = []
    skipped: list[str] = []
    for track in animation:
        path = str(track["path"])
        node_index = path_to_node.get(path)
        if node_index is None:
            skipped.append(path)
            continue
        base_translation, base_rotation = base_transforms[node_index]
        built = builder.add_animation_track(
            node_index,
            base_translation,
            base_rotation,
            str(track["action"]),
            [float(v) for v in track["times"]],
            track["values"],
        )
        if built is None:
            skipped.append(f"{path} ({track['action']})")
            continue
        input_accessor, output_accessor, target_path = built
        sampler_index = len(samplers)
        samplers.append(
            gltf.AnimationSampler(
                input=input_accessor, output=output_accessor, interpolation="LINEAR"
            )
        )
        channels.append(
            gltf.AnimationChannel(
                sampler=sampler_index,
                target=gltf.AnimationChannelTarget(node=node_index, path=target_path),
            )
        )

    animations = (
        [gltf.Animation(name=title, channels=channels, samplers=samplers)] if channels else []
    )

    wrapper_index = len(nodes)
    nodes.append(gltf.Node(name="Zup_to_Yup", rotation=list(_ZUP_TO_YUP), children=[0]))

    document = gltf.GLTF2(
        asset=gltf.Asset(generator="cad_workbench.gltf_export", version="2.0"),
        scene=0,
        scenes=[gltf.Scene(nodes=[wrapper_index])],
        nodes=nodes,
        meshes=builder.meshes,
        materials=builder.materials,
        accessors=builder.accessors,
        bufferViews=builder.buffer_views,
        buffers=[gltf.Buffer(byteLength=len(builder.blob))],
        animations=animations,
    )
    document.set_binary_blob(bytes(builder.blob))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))

    return {
        "output": str(output_path),
        "node_count": len(nodes),
        "mesh_count": len(builder.meshes),
        "material_count": len(builder.materials),
        "animation_channel_count": len(channels),
        "skipped_animation_paths": skipped,
    }
