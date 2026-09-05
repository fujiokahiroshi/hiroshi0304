from __future__ import annotations

import base64
import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import MCPServer
from mcp.types import ImageContent, TextContent

from .state import JOBS_DIR, VIEWER_PORT, read_state, viewer_reachable, write_state
from .validation import validate_code

mcp = MCPServer(
    "Claude CAD Workbench",
    instructions=(
        "CadQueryでパラメトリックCADを作成します。create_cad_modelのcodeでは完成物をresultへ、"
        "工程をstepsへ、OCP CAD Viewerのアニメーショントラックをanimationへ代入します。"
        "実行中の工程を画面へ逐次反映するため、各工程の直前にcad_step(steps[index])を呼びます。"
    ),
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RC_4WD_TEMPLATE = PROJECT_ROOT / "examples" / "rc_4wd_drivetrain.py"
SCREW_GEAR_TEMPLATE = PROJECT_ROOT / "examples" / "screw_gear_pair.py"
COMPOUND_PLANETARY_TEMPLATE = PROJECT_ROOT / "examples" / "compound_planetary_three_shaft.py"
CARDAN_JOINT_TEMPLATE = PROJECT_ROOT / "examples" / "cardan_joint.py"
DOUBLE_CARDAN_JOINT_TEMPLATE = PROJECT_ROOT / "examples" / "double_cardan_joint.py"
PREVIEW_DIR = PROJECT_ROOT / "runtime" / "previews"


def _rc_4wd_drivetrain_code() -> str:
    return RC_4WD_TEMPLATE.read_text(encoding="utf-8")


def _screw_gear_code() -> str:
    return SCREW_GEAR_TEMPLATE.read_text(encoding="utf-8")


def _cardan_joint_code() -> str:
    return CARDAN_JOINT_TEMPLATE.read_text(encoding="utf-8")


def _double_cardan_joint_code() -> str:
    return DOUBLE_CARDAN_JOINT_TEMPLATE.read_text(encoding="utf-8")


def _compound_planetary_code() -> str:
    return COMPOUND_PLANETARY_TEMPLATE.read_text(encoding="utf-8")


MODEL_ID_PATTERN = re.compile(r"^(example|job):([A-Za-z0-9_-]+)$")


def _model_source_entries(source: str = "all") -> list[dict[str, Any]]:
    if source not in {"all", "examples", "jobs"}:
        raise ValueError("source must be all, examples, or jobs")

    entries: list[dict[str, Any]] = []
    if source in {"all", "examples"}:
        examples_dir = PROJECT_ROOT / "examples"
        for path in examples_dir.glob("*.py"):
            resolved = path.resolve()
            stat = resolved.stat()
            entries.append(
                {
                    "model_id": f"example:{resolved.stem}",
                    "source": "examples",
                    "name": resolved.stem,
                    "relative_path": resolved.relative_to(PROJECT_ROOT).as_posix(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
                    "size_bytes": stat.st_size,
                    "exports": [],
                    "_path": resolved,
                }
            )

    if source in {"all", "jobs"}:
        for path in JOBS_DIR.glob("*/model.py"):
            resolved = path.resolve()
            stat = resolved.stat()
            exports = [
                candidate.name
                for candidate in (resolved.with_name("model.step"), resolved.with_name("model.stl"))
                if candidate.is_file()
            ]
            entries.append(
                {
                    "model_id": f"job:{resolved.parent.name}",
                    "source": "jobs",
                    "name": resolved.parent.name,
                    "relative_path": resolved.relative_to(PROJECT_ROOT).as_posix(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(),
                    "size_bytes": stat.st_size,
                    "exports": exports,
                    "_path": resolved,
                }
            )

    return sorted(entries, key=lambda item: item["modified"], reverse=True)


def _resolve_model_source(model_id: str) -> Path:
    match = MODEL_ID_PATTERN.fullmatch(model_id)
    if match is None:
        raise ValueError("model_id must use example:<name> or job:<name>")
    source, name = match.groups()
    if source == "example":
        candidate = (PROJECT_ROOT / "examples" / f"{name}.py").resolve()
        allowed_parent = (PROJECT_ROOT / "examples").resolve()
    else:
        candidate = (JOBS_DIR / name / "model.py").resolve()
        allowed_parent = (JOBS_DIR / name).resolve()
    if candidate.parent != allowed_parent or not candidate.is_file():
        raise ValueError(f"CAD model source not found: {model_id}")
    return candidate


def _resolve_step_source(model_id: str | None = None) -> tuple[str, Path]:
    if model_id is None:
        candidates = [path.resolve() for path in JOBS_DIR.glob("*/model.step")]
        if not candidates:
            raise ValueError("No generated STEP models are available")
        step_path = max(candidates, key=lambda path: path.stat().st_mtime)
        return f"job:{step_path.parent.name}", step_path

    match = MODEL_ID_PATTERN.fullmatch(model_id)
    if match is None or match.group(1) != "job":
        raise ValueError("geometry inspection requires a job:<name> model_id")
    name = match.group(2)
    step_path = (JOBS_DIR / name / "model.step").resolve()
    allowed_parent = (JOBS_DIR / name).resolve()
    if step_path.parent != allowed_parent or not step_path.is_file():
        raise ValueError(f"STEP model not found: {model_id}")
    return model_id, step_path


def _resolve_job_dir(model_id: str | None = None) -> tuple[str, Path]:
    if model_id is None:
        candidates = [path.parent.resolve() for path in JOBS_DIR.glob("*/model.py")]
        if not candidates:
            raise ValueError("No generated CAD jobs are available")
        job_dir = max(candidates, key=lambda path: (path / "model.py").stat().st_mtime)
        model_id = f"job:{job_dir.name}"
    else:
        match = MODEL_ID_PATTERN.fullmatch(model_id)
        if match is None or match.group(1) != "job":
            raise ValueError("operation requires a job:<name> model_id")
        job_dir = (JOBS_DIR / match.group(2)).resolve()
    allowed_parent = JOBS_DIR.resolve()
    if job_dir.parent != allowed_parent:
        raise ValueError(f"CAD job not found: {model_id}")
    if not (job_dir / "model.py").is_file() or not (job_dir / "request.json").is_file():
        raise ValueError(f"CAD job is incomplete: {model_id}")
    return model_id, job_dir


def _run_job_tool(action: str, job_dir: Path, *arguments: str) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "cad_workbench.job_tools",
            action,
            str(job_dir),
            *arguments,
        ],
        cwd=job_dir,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(completed.stderr[-2000:] or "CAD job tool returned no data")
    try:
        response = json.loads(lines[-1])
    except json.JSONDecodeError as exc:
        raise RuntimeError(completed.stdout[-2000:]) from exc
    if not response.get("ok"):
        raise RuntimeError(str(response.get("error", completed.stderr[-2000:])))
    if completed.returncode != 0:
        response["process_warning"] = (
            f"Inspection completed before process exit code {completed.returncode}"
        )
    response.pop("ok", None)
    return response


def _gear_code(
    teeth_a: int,
    teeth_b: int,
    module: float,
    thickness: float,
    bore: float,
    turns: float,
    duration: float,
) -> str:
    center_distance = module * (teeth_a + teeth_b) / 2
    rotation_a = 360.0 * turns
    rotation_b = -rotation_a * teeth_a / teeth_b
    phase_b = 180.0 / teeth_b
    segments = max(1, math.ceil(max(abs(rotation_a), abs(rotation_b)) / 90.0))
    timeline = [duration * index / segments for index in range(segments + 1)]
    values_a = [rotation_a * index / segments for index in range(segments + 1)]
    values_b = [
        0.0 if index == 0 else rotation_b * index / segments for index in range(segments + 1)
    ]
    return f"""import cadquery as cq
import math

steps = [
    "歯車Aの歯形を作成",
    "歯車Bの歯形を作成",
    "軸穴を加工",
    "歯数比から回転アニメーションを設定",
]

def make_spur_gear(teeth, module, thickness, bore):
    pitch_radius = module * teeth / 2.0
    root_radius = max(module, pitch_radius - 1.25 * module)
    outer_radius = pitch_radius + module
    root_width = math.pi * module * 0.58
    tip_width = math.pi * module * 0.28
    gear = cq.Workplane("XY").circle(root_radius).extrude(thickness)
    tooth = (
        cq.Workplane("XY")
        .polyline([
            (root_radius - 0.05 * module, -root_width / 2.0),
            (outer_radius, -tip_width / 2.0),
            (outer_radius, tip_width / 2.0),
            (root_radius - 0.05 * module, root_width / 2.0),
        ])
        .close()
        .extrude(thickness)
    )
    for index in range(teeth):
        gear = gear.union(tooth.rotate((0, 0, 0), (0, 0, 1), index * 360.0 / teeth))
    if bore > 0:
        gear = gear.faces(">Z").workplane().hole(bore)
    return gear

cad_step(steps[0])
gear_a = make_spur_gear({teeth_a}, {module!r}, {thickness!r}, {bore!r})
cad_step(steps[1])
gear_b = make_spur_gear({teeth_b}, {module!r}, {thickness!r}, {bore!r})
cad_step(steps[2])
gear_b = gear_b.rotate((0, 0, 0), (0, 0, 1), {phase_b!r})

marker_radius = max(0.8, {module!r} * 0.45)
marker_a = (
    cq.Workplane("XY", origin=({module * teeth_a * 0.32!r}, 0, {thickness!r}))
    .circle(marker_radius)
    .extrude(max(0.8, {thickness!r} * 0.08))
)
marker_b = (
    cq.Workplane("XY", origin=({module * teeth_b * 0.32!r}, 0, {thickness!r}))
    .circle(marker_radius)
    .extrude(max(0.8, {thickness!r} * 0.08))
)
gear_a_group = cq.Assembly(name="gear_a")
gear_a_group.add(gear_a, name="body", color=cq.Color("gold"))
gear_a_group.add(marker_a, name="rotation_marker", color=cq.Color("red"))
gear_b_group = cq.Assembly(name="gear_b")
gear_b_group.add(gear_b, name="body", color=cq.Color("steelblue"))
gear_b_group.add(marker_b, name="rotation_marker", color=cq.Color("white"))

result = cq.Assembly(name="gear_train")
result.add(gear_a_group, name="gear_a")
result.add(
    gear_b_group,
    name="gear_b",
    loc=cq.Location(cq.Vector({center_distance!r}, 0, 0)),
)

cad_step(steps[3])
animation = [
    {{
        "path": "/gear_train/gear_a",
        "action": "rz",
        "times": {timeline!r},
        "values": {values_a!r},
    }},
    {{
        "path": "/gear_train/gear_b",
        "action": "rz",
        "times": {timeline!r},
        "values": {values_b!r},
    }},
]
"""


def _bevel_gear_code(
    teeth_a: int,
    teeth_b: int,
    module: float,
    face_width: float,
    bore: float,
    turns: float,
    duration: float,
) -> str:
    rotation_a = 360.0 * turns
    rotation_b = -rotation_a * teeth_a / teeth_b
    segments = max(1, math.ceil(max(abs(rotation_a), abs(rotation_b)) / 90.0))
    timeline = [duration * index / segments for index in range(segments + 1)]
    values_a = [rotation_a * index / segments for index in range(segments + 1)]
    values_b = [
        0.0 if index == 0 else rotation_b * index / segments for index in range(segments + 1)
    ]
    return f"""import cadquery as cq
import math

steps = [
    "ピッチ円錐角を計算",
    "傘歯車Aを作成",
    "傘歯車Bを直交軸へ配置",
    "歯数比で連動アニメーションを設定",
]

def make_bevel_gear(teeth, module, face_width, bore, mate_teeth):
    pitch_radius = module * teeth / 2.0
    mate_radius = module * mate_teeth / 2.0
    cone_distance = math.hypot(pitch_radius, mate_radius)
    pitch_angle = math.atan2(pitch_radius, mate_radius)
    usable_width = min(face_width, cone_distance * 0.32)
    scale = (cone_distance - usable_width) / cone_distance
    z_large = mate_radius
    z_small = z_large - usable_width * math.cos(pitch_angle)
    axial_depth = z_large - z_small

    root_large = max(module, pitch_radius - 1.25 * module)
    outer_large = pitch_radius + module
    root_small = root_large * scale
    outer_small = outer_large * scale
    root_width_large = math.pi * module * 0.56
    tip_width_large = math.pi * module * 0.26
    root_width_small = root_width_large * scale
    tip_width_small = tip_width_large * scale

    gear = (
        cq.Workplane("XY", origin=(0, 0, z_small))
        .circle(root_small)
        .workplane(offset=axial_depth)
        .circle(root_large)
        .loft(combine=True)
    )
    small_profile = [
        (root_small - 0.03 * module, -root_width_small / 2.0),
        (outer_small, -tip_width_small / 2.0),
        (outer_small, tip_width_small / 2.0),
        (root_small - 0.03 * module, root_width_small / 2.0),
    ]
    large_profile = [
        (root_large - 0.03 * module, -root_width_large / 2.0),
        (outer_large, -tip_width_large / 2.0),
        (outer_large, tip_width_large / 2.0),
        (root_large - 0.03 * module, root_width_large / 2.0),
    ]
    tooth = (
        cq.Workplane("XY", origin=(0, 0, z_small))
        .polyline(small_profile)
        .close()
        .workplane(offset=axial_depth)
        .polyline(large_profile)
        .close()
        .loft(combine=True)
    )
    for index in range(teeth):
        gear = gear.union(tooth.rotate((0, 0, 0), (0, 0, 1), index * 360.0 / teeth))
    if bore > 0:
        cutter = cq.Workplane("XY", origin=(0, 0, 0)).circle(bore / 2.0).extrude(z_large + module)
        gear = gear.cut(cutter)
    return gear, pitch_radius, z_large, pitch_angle

cad_step(steps[0])
cad_step(steps[1])
gear_a, radius_a, apex_a, angle_a = make_bevel_gear(
    {teeth_a}, {module!r}, {face_width!r}, {bore!r}, {teeth_b}
)
cad_step(steps[2])
gear_b_raw, radius_b, apex_b, angle_b = make_bevel_gear(
    {teeth_b}, {module!r}, {face_width!r}, {bore!r}, {teeth_a}
)
phase_b = 180.0 / {teeth_b}
gear_b = (
    gear_b_raw
    .rotate((0, 0, 0), (0, 1, 0), 90.0)
    .rotate((0, 0, 0), (1, 0, 0), phase_b)
)

marker_size = max(0.8, {module!r} * 0.45)
marker_a = (
    cq.Workplane("XY", origin=(radius_a * 0.58, 0, apex_a))
    .circle(marker_size)
    .extrude(max(0.8, {face_width!r} * 0.08))
)
marker_b = (
    cq.Workplane("XY", origin=(radius_b * 0.58, 0, apex_b))
    .circle(marker_size)
    .extrude(max(0.8, {face_width!r} * 0.08))
    .rotate((0, 0, 0), (0, 1, 0), 90.0)
    .rotate((0, 0, 0), (1, 0, 0), phase_b)
)

group_a = cq.Assembly(name="bevel_a")
group_a.add(gear_a, name="body", color=cq.Color("gold"))
group_a.add(marker_a, name="rotation_marker", color=cq.Color("red"))
group_b = cq.Assembly(name="bevel_b")
group_b.add(gear_b, name="body", color=cq.Color("steelblue"))
group_b.add(marker_b, name="rotation_marker", color=cq.Color("white"))

result = cq.Assembly(name="bevel_pair")
result.add(group_a, name="bevel_a")
result.add(group_b, name="bevel_b")

cad_step(steps[3])
animation = [
    {{
        "path": "/bevel_pair/bevel_a",
        "action": "rz",
        "times": {timeline!r},
        "values": {values_a!r},
    }},
    {{
        "path": "/bevel_pair/bevel_b",
        "action": "rx",
        "times": {timeline!r},
        "values": {values_b!r},
    }},
]
"""


def _differential_code(
    side_teeth: int,
    pinion_teeth: int,
    module: float,
    face_width: float,
    bore: float,
    carrier_turns: float,
    turn_bias: float,
    duration: float,
) -> str:
    carrier_angle = 360.0 * carrier_turns
    left_angle = carrier_angle * (1.0 + turn_bias)
    right_angle = carrier_angle * (1.0 - turn_bias)
    spider_angle = -(left_angle - carrier_angle) * side_teeth / pinion_teeth
    segments = max(
        1,
        math.ceil(
            max(abs(left_angle), abs(right_angle), abs(carrier_angle), abs(spider_angle)) / 90.0
        ),
    )
    timeline = [duration * index / segments for index in range(segments + 1)]

    def keyed(angle: float) -> list[float]:
        return [0.0 if index == 0 else angle * index / segments for index in range(segments + 1)]

    left_values = keyed(left_angle)
    right_values = keyed(right_angle)
    carrier_values = keyed(carrier_angle)
    spider_values = keyed(spider_angle)
    spider_opposite_values = keyed(-spider_angle)
    return f"""import cadquery as cq
import math

steps = [
    "左右のサイド傘歯車を作成",
    "スパイダー傘歯車を作成",
    "キャリアとクロスシャフトを組立",
    "差動回転式をタイムラインへ設定",
]

def make_bevel_gear(teeth, module, face_width, bore, mate_teeth):
    pitch_radius = module * teeth / 2.0
    mate_radius = module * mate_teeth / 2.0
    cone_distance = math.hypot(pitch_radius, mate_radius)
    pitch_angle = math.atan2(pitch_radius, mate_radius)
    usable_width = min(face_width, cone_distance * 0.30)
    scale = (cone_distance - usable_width) / cone_distance
    z_large = mate_radius
    z_small = z_large - usable_width * math.cos(pitch_angle)
    depth = z_large - z_small
    root_large = max(module, pitch_radius - 1.25 * module)
    outer_large = pitch_radius + module
    root_small = root_large * scale
    outer_small = outer_large * scale
    root_w = math.pi * module * 0.56
    tip_w = math.pi * module * 0.26
    gear = (
        cq.Workplane("XY", origin=(0, 0, z_small))
        .circle(root_small)
        .workplane(offset=depth)
        .circle(root_large)
        .loft(combine=True)
    )
    tooth = (
        cq.Workplane("XY", origin=(0, 0, z_small))
        .polyline([
            (root_small, -root_w * scale / 2),
            (outer_small, -tip_w * scale / 2),
            (outer_small, tip_w * scale / 2),
            (root_small, root_w * scale / 2),
        ])
        .close()
        .workplane(offset=depth)
        .polyline([
            (root_large, -root_w / 2),
            (outer_large, -tip_w / 2),
            (outer_large, tip_w / 2),
            (root_large, root_w / 2),
        ])
        .close()
        .loft(combine=True)
    )
    for index in range(teeth):
        gear = gear.union(tooth.rotate((0, 0, 0), (0, 0, 1), index * 360.0 / teeth))
    if bore > 0:
        gear = gear.cut(
            cq.Workplane("XY").circle(bore / 2.0).extrude(z_large + module)
        )
    return gear, pitch_radius, z_large

def marker(radius, z_large, module, face_width):
    return (
        cq.Workplane("XY", origin=(radius * 0.56, 0, z_large))
        .circle(max(0.7, module * 0.42))
        .extrude(max(0.7, face_width * 0.08))
    )

cad_step(steps[0])
side_raw, side_radius, side_apex = make_bevel_gear(
    {side_teeth}, {module!r}, {face_width!r}, {bore!r}, {pinion_teeth}
)
side_marker_raw = marker(side_radius, side_apex, {module!r}, {face_width!r})
left_body = side_raw.rotate((0, 0, 0), (0, 1, 0), 90)
left_marker = side_marker_raw.rotate((0, 0, 0), (0, 1, 0), 90)
right_body = side_raw.rotate((0, 0, 0), (0, 1, 0), -90)
right_marker = side_marker_raw.rotate((0, 0, 0), (0, 1, 0), -90)

left_group = cq.Assembly(name="left_side")
left_group.add(left_body, name="body", color=cq.Color("gold"))
left_group.add(left_marker, name="marker", color=cq.Color("red"))
right_group = cq.Assembly(name="right_side")
right_group.add(right_body, name="body", color=cq.Color("orange"))
right_group.add(right_marker, name="marker", color=cq.Color("white"))

cad_step(steps[1])
pinion_raw, pinion_radius, pinion_apex = make_bevel_gear(
    {pinion_teeth}, {module!r}, {face_width!r}, {bore!r}, {side_teeth}
)
pinion_marker_raw = marker(pinion_radius, pinion_apex, {module!r}, {face_width!r})
phase = 180.0 / {pinion_teeth}
top_body = pinion_raw.rotate((0, 0, 0), (0, 0, 1), phase)
top_marker = pinion_marker_raw.rotate((0, 0, 0), (0, 0, 1), phase)
bottom_body = (
    pinion_raw.rotate((0, 0, 0), (0, 1, 0), 180)
    .rotate((0, 0, 0), (0, 0, 1), phase)
)
bottom_marker = (
    pinion_marker_raw.rotate((0, 0, 0), (0, 1, 0), 180)
    .rotate((0, 0, 0), (0, 0, 1), phase)
)
top_group = cq.Assembly(name="pinion_top")
top_group.add(top_body, name="body", color=cq.Color("steelblue"))
top_group.add(top_marker, name="marker", color=cq.Color(0.1, 1.0, 0.1))
bottom_group = cq.Assembly(name="pinion_bottom")
bottom_group.add(bottom_body, name="body", color=cq.Color("royalblue"))
bottom_group.add(bottom_marker, name="marker", color=cq.Color(0.1, 0.9, 1.0))

cad_step(steps[2])
carrier_radius = side_radius + {module!r} * 3.0
carrier_ring = (
    cq.Workplane("YZ")
    .circle(carrier_radius + {module!r})
    .circle(carrier_radius)
    .extrude({module!r} * 1.6, both=True)
)
cross_shaft = (
    cq.Workplane("XY", origin=(0, 0, -side_radius * 1.15))
    .circle(max(0.8, {module!r} * 0.65))
    .extrude(side_radius * 2.3)
)
carrier = cq.Assembly(name="carrier")
carrier.add(carrier_ring, name="ring", color=cq.Color("gray"))
carrier.add(cross_shaft, name="cross_shaft", color=cq.Color(0.75, 0.75, 0.78))
carrier.add(top_group, name="pinion_top")
carrier.add(bottom_group, name="pinion_bottom")

result = cq.Assembly(name="differential")
result.add(left_group, name="left_side")
result.add(right_group, name="right_side")
result.add(carrier, name="carrier")

cad_step(steps[3])
animation = [
    {{"path": "/differential/left_side", "action": "rx",
      "times": {timeline!r}, "values": {left_values!r}}},
    {{"path": "/differential/right_side", "action": "rx",
      "times": {timeline!r}, "values": {right_values!r}}},
    {{"path": "/differential/carrier", "action": "rx",
      "times": {timeline!r}, "values": {carrier_values!r}}},
    {{"path": "/differential/carrier/pinion_top", "action": "rz",
      "times": {timeline!r}, "values": {spider_values!r}}},
    {{"path": "/differential/carrier/pinion_bottom", "action": "rz",
      "times": {timeline!r}, "values": {spider_opposite_values!r}}},
]
"""


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return (cleaned or "cad-model")[:48]


@mcp.tool()
def create_cad_model(
    title: str,
    code: str,
    steps: list[str] | None = None,
    formats: list[str] | None = None,
    animation: list[dict[str, Any]] | None = None,
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """CadQueryコードを検査・実行し、OCP Viewerに表示してSTEP/STLを保存する。

    code must assign the final Workplane, Shape, or Assembly to result. Define literal steps
    and call cad_step(label) before each operation for live UI updates. Animation tracks
    use path, action (tx/ty/tz/t/rx/ry/rz/q), times, values. Prefer a named Assembly.
    """
    validate_code(code)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    output_dir = (JOBS_DIR / f"{timestamp}-{_slug(title)}").resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    payload = {
        "title": title,
        "code": code,
        "steps": steps or [],
        "formats": formats or ["step"],
        "animation": animation or [],
        "speed": max(0.1, min(float(animation_speed), 10.0)),
        "output_dir": str(output_dir),
    }
    payload_path = output_dir / "request.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_state(status="queued", title=title, message="ClaudeのCADジョブを開始します")
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "cad_workbench.runner", str(payload_path)],
        cwd=output_dir,
        env=environment,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=120,
        check=False,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if lines:
        try:
            response = json.loads(lines[-1])
        except json.JSONDecodeError:
            response = {"ok": False, "error": completed.stdout[-2000:]}
    else:
        response = {"ok": False, "error": completed.stderr[-2000:] or "runner returned no data"}
    if completed.returncode != 0:
        response["stderr"] = completed.stderr[-2000:]
    return response


@mcp.tool()
def get_cad_status() -> dict[str, Any]:
    """現在のCADジョブ、工程表示、出力先を取得する。"""
    state = read_state()
    state["viewer_connected"] = viewer_reachable()
    state["viewer_port"] = VIEWER_PORT
    if not state["viewer_connected"] and state.get("status") == "complete":
        state["viewer_note"] = "モデル生成は完了。Viewerは現在停止しています。"
    return state


@mcp.tool()
def create_gear_animation(
    teeth_a: int = 20,
    teeth_b: int = 40,
    module: float = 2.0,
    thickness: float = 8.0,
    bore: float = 6.0,
    turns: float = 2.0,
    duration: float = 4.0,
) -> dict[str, Any]:
    """噛み合う2枚の平歯車を作り、正しい歯数比で逆回転アニメーションを再生する。

    Dimensions are millimetres. Gear B angular speed is automatically calculated as
    `-speed_a * teeth_a / teeth_b`. The OCP Viewer must be running on port 3939.
    """
    if not 8 <= teeth_a <= 120 or not 8 <= teeth_b <= 120:
        raise ValueError("歯数は8～120の範囲で指定してください")
    if not 0.5 <= module <= 10:
        raise ValueError("モジュールは0.5～10 mmの範囲で指定してください")
    if not 1 <= thickness <= 100:
        raise ValueError("厚みは1～100 mmの範囲で指定してください")
    if not 0 <= bore < module * min(teeth_a, teeth_b) - 2.5 * module:
        raise ValueError("軸穴径が歯車の歯底径に対して大きすぎます")
    if not 0.1 <= turns <= 100 or not 0.2 <= duration <= 120:
        raise ValueError("回転数または再生時間が範囲外です")
    return create_cad_model(
        title=f"gear-{teeth_a}T-{teeth_b}T",
        code=_gear_code(teeth_a, teeth_b, module, thickness, bore, turns, duration),
        formats=["step", "stl"],
        animation_speed=1.0,
    )


@mcp.tool()
def create_bevel_gear_animation(
    teeth_a: int = 16,
    teeth_b: int = 32,
    module: float = 2.0,
    face_width: float = 8.0,
    bore: float = 6.0,
    turns: float = 2.0,
    duration: float = 5.0,
) -> dict[str, Any]:
    """90度で噛み合う傘歯車対を作り、歯数比で連動回転させる。

    Pitch-cone angles and cone distance are calculated from tooth counts. Dimensions
    are millimetres. Gear B rotates about the X axis at `-teeth_a / teeth_b` speed.
    """
    if not 8 <= teeth_a <= 80 or not 8 <= teeth_b <= 80:
        raise ValueError("歯数は8～80の範囲で指定してください")
    if not 0.5 <= module <= 8:
        raise ValueError("モジュールは0.5～8 mmの範囲で指定してください")
    pitch_a = module * teeth_a / 2.0
    pitch_b = module * teeth_b / 2.0
    cone_distance = math.hypot(pitch_a, pitch_b)
    if not 1 <= face_width <= cone_distance * 0.32:
        raise ValueError(f"歯幅は1～{cone_distance * 0.32:.2f} mmで指定してください")
    root_diameter = 2 * (min(pitch_a, pitch_b) - 1.25 * module)
    if not 0 <= bore < root_diameter:
        raise ValueError("軸穴径が小さい側の歯底径に対して大きすぎます")
    if not 0.1 <= turns <= 100 or not 0.2 <= duration <= 120:
        raise ValueError("回転数または再生時間が範囲外です")
    return create_cad_model(
        title=f"bevel-gear-{teeth_a}T-{teeth_b}T",
        code=_bevel_gear_code(teeth_a, teeth_b, module, face_width, bore, turns, duration),
        formats=["step", "stl"],
        animation_speed=1.0,
    )


@mcp.tool()
def create_differential_animation(
    side_teeth: int = 24,
    pinion_teeth: int = 12,
    module: float = 1.5,
    face_width: float = 5.0,
    bore: float = 5.0,
    carrier_turns: float = 1.0,
    turn_bias: float = 0.5,
    duration: float = 6.0,
) -> dict[str, Any]:
    """オープンデファレンシャルを作り、旋回時の差動回転をアニメーションする。

    turn_bias=0 gives equal wheel speed. Positive bias makes the left side faster and
    the right side slower while preserving left + right = 2 * carrier. Use 0..0.9.
    """
    if not 12 <= side_teeth <= 60 or not 8 <= pinion_teeth <= 30:
        raise ValueError("サイド歯数は12～60、ピニオン歯数は8～30で指定してください")
    if not 0.5 <= module <= 5:
        raise ValueError("モジュールは0.5～5 mmの範囲で指定してください")
    cone_distance = math.hypot(module * side_teeth / 2, module * pinion_teeth / 2)
    if not 1 <= face_width <= cone_distance * 0.30:
        raise ValueError(f"歯幅は1～{cone_distance * 0.30:.2f} mmで指定してください")
    if not 0 <= bore < module * pinion_teeth - 2.5 * module:
        raise ValueError("軸穴径がピニオン歯底径に対して大きすぎます")
    if not 0 <= turn_bias <= 0.9:
        raise ValueError("turn_biasは0～0.9で指定してください")
    if not 0.1 <= carrier_turns <= 50 or not 0.5 <= duration <= 120:
        raise ValueError("回転数または再生時間が範囲外です")
    return create_cad_model(
        title=f"differential-{side_teeth}T-{pinion_teeth}T",
        code=_differential_code(
            side_teeth,
            pinion_teeth,
            module,
            face_width,
            bore,
            carrier_turns,
            turn_bias,
            duration,
        ),
        formats=["step", "stl"],
        animation_speed=1.0,
    )


@mcp.tool()
def create_rc_4wd_drivetrain_animation(
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """Generate an animated 1/10 RC 4WD drivetrain with transparent open differentials.

    Includes 22T/70T primary reduction, 15T/39T final drives, treaded tires,
    24T side gears, and 12T spider gears. Twelve animation tracks demonstrate
    the inside/outside wheel-speed difference while cornering.
    """
    if not 0.1 <= animation_speed <= 10.0:
        raise ValueError("animation_speed must be between 0.1 and 10.0")
    return create_cad_model(
        title="rc-4wd-transparent-real-differentials",
        code=_rc_4wd_drivetrain_code(),
        formats=["step", "stl"],
        animation_speed=animation_speed,
    )


@mcp.tool()
def create_screw_gear_animation(
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """Generate and animate a meshed crossed-axis screw-gear pair.

    Uses two 14T involute helical gears with module 2.5, 45-degree helix angles,
    perpendicular Z/X axes, and synchronized two-track rotation.
    """
    if not 0.1 <= animation_speed <= 10.0:
        raise ValueError("animation_speed must be between 0.1 and 10.0")
    return create_cad_model(
        title="screw-gear-pair-14T-14T",
        code=_screw_gear_code(),
        formats=["step", "stl"],
        animation_speed=animation_speed,
    )


@mcp.tool()
def create_compound_planetary_animation(
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """Generate the validated three-shaft compound planetary animation.

    The blue ring carries rigidly connected inner and outer gear zones. A purple
    external pinion drives it while the green carrier and yellow sun rotate under
    the planetary constraint 24*sun + 56*ring = 80*carrier. Two planets use a
    carrier-parent hierarchy for simultaneous revolution and relative self-spin.
    """
    if not 0.1 <= animation_speed <= 10.0:
        raise ValueError("animation_speed must be between 0.1 and 10.0")
    return create_cad_model(
        title="compound-planetary-three-shaft",
        code=_compound_planetary_code(),
        formats=["step"],
        animation_speed=animation_speed,
    )


@mcp.tool()
def create_cardan_joint_animation(
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """Generate a universal (Cardan/Hooke's) joint with correct non-constant-velocity motion.

    Two shafts cross at a fixed 25-degree angle. The blue handle_yoke is the
    steering handle and spins at a uniform rate; the cross (spider) and the
    yellow wheel_yoke (drives the wheels) follow the classical relation
    tan(phi) = tan(theta) / cos(beta), derived from the pin directions rather than
    assumed, so the wheel-side speed visibly fluctuates within each handle revolution.
    """
    if not 0.1 <= animation_speed <= 10.0:
        raise ValueError("animation_speed must be between 0.1 and 10.0")
    return create_cad_model(
        title="cardan-joint-25deg",
        code=_cardan_joint_code(),
        formats=["step"],
        animation_speed=animation_speed,
    )


@mcp.tool()
def create_double_cardan_joint_animation(
    animation_speed: float = 1.0,
) -> dict[str, Any]:
    """Generate a double (Z-configuration) Cardan joint that restores constant velocity.

    Input and output shafts are parallel, connected through an intermediate shaft
    tilted 25 degrees from each. A single universal joint would make the far side
    fluctuate in speed (see create_cardan_joint_animation); wiring two joints
    through a correctly phased intermediate shaft -- its two fork hinges built
    parallel, not twisted -- makes the second joint's non-uniformity exactly
    cancel the first, so the output tracks the input 1:1 at every instant
    (verified numerically to within floating-point noise).
    """
    if not 0.1 <= animation_speed <= 10.0:
        raise ValueError("animation_speed must be between 0.1 and 10.0")
    return create_cad_model(
        title="double-cardan-joint",
        code=_double_cardan_joint_code(),
        formats=["step"],
        animation_speed=animation_speed,
    )


@mcp.tool()
def list_cad_model_sources(
    source: str = "all",
    limit: int = 50,
) -> dict[str, Any]:
    """List readable CAD Python sources from examples and generated jobs."""
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")
    entries = _model_source_entries(source)
    models = [
        {key: value for key, value in entry.items() if key != "_path"} for entry in entries[:limit]
    ]
    return {"total": len(entries), "count": len(models), "models": models}


@mcp.tool()
def get_cad_model_source(
    model_id: str,
    start_line: int = 1,
    max_lines: int = 500,
) -> dict[str, Any]:
    """Read a safe line range from a CAD Python source selected by model ID."""
    if start_line < 1:
        raise ValueError("start_line must be at least 1")
    if not 1 <= max_lines <= 500:
        raise ValueError("max_lines must be between 1 and 500")
    path = _resolve_model_source(model_id)
    lines = path.read_text(encoding="utf-8").splitlines()
    start_index = min(start_line - 1, len(lines))
    end_index = min(start_index + max_lines, len(lines))
    content = "\n".join(lines[start_index:end_index])
    return {
        "model_id": model_id,
        "start_line": start_index + 1 if lines else 0,
        "end_line": end_index,
        "total_lines": len(lines),
        "has_more": end_index < len(lines),
        "content": content,
    }


@mcp.tool()
def search_cad_model_sources(
    query: str,
    source: str = "all",
    limit: int = 20,
) -> dict[str, Any]:
    """Search CAD Python sources and return the first matching line per model."""
    query = query.strip()
    if not query or len(query) > 100:
        raise ValueError("query must contain between 1 and 100 characters")
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    needle = query.casefold()
    matches: list[dict[str, Any]] = []
    for entry in _model_source_entries(source):
        lines = entry["_path"].read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if needle in line.casefold():
                matches.append(
                    {
                        "model_id": entry["model_id"],
                        "line": line_number,
                        "snippet": line.strip()[:240],
                    }
                )
                break
        if len(matches) >= limit:
            break
    return {"query": query, "count": len(matches), "matches": matches}


@mcp.tool(structured_output=False)
def get_cad_preview() -> list[TextContent | ImageContent]:
    """Capture the current OCP CAD Viewer image and return it to the model."""
    if not viewer_reachable():
        raise ConnectionError(f"OCP CAD Viewer is not reachable at http://127.0.0.1:{VIEWER_PORT}")

    from ocp_vscode import save_screenshot

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    target = (PREVIEW_DIR / f"cad-preview-{timestamp}.png").resolve()
    save_screenshot(str(target), port=VIEWER_PORT, polling=True)
    if not target.is_file() or target.stat().st_size == 0:
        raise RuntimeError(
            "OCP CAD Viewer did not return a screenshot. Open the browser view first."
        )
    data = base64.b64encode(target.read_bytes()).decode("ascii")
    relative_path = target.relative_to(PROJECT_ROOT).as_posix()
    return [
        TextContent(
            text=json.dumps(
                {
                    "preview": relative_path,
                    "size_bytes": target.stat().st_size,
                    "viewer_port": VIEWER_PORT,
                },
                ensure_ascii=False,
            )
        ),
        ImageContent(data=data, mimeType="image/png"),
    ]


@mcp.tool()
def inspect_cad_geometry(model_id: str | None = None) -> dict[str, Any]:
    """Inspect exact STEP geometry for a generated job, defaulting to the latest job."""
    import cadquery as cq

    resolved_id, step_path = _resolve_step_source(model_id)
    shape = cq.importers.importStep(str(step_path)).val()
    bounding_box = shape.BoundingBox()
    center = shape.Center()
    valid = bool(shape.isValid())
    volume = float(shape.Volume())
    size = {
        "x": round(float(bounding_box.xlen), 6),
        "y": round(float(bounding_box.ylen), 6),
        "z": round(float(bounding_box.zlen), 6),
    }
    warnings: list[str] = []
    if not valid:
        warnings.append("OpenCascade reports an invalid shape")
    if volume <= 0:
        warnings.append("The imported shape has no positive volume")
    collapsed_axes = [axis for axis, length in size.items() if length <= 1e-6]
    if collapsed_axes:
        warnings.append(f"Near-zero bounding-box axes: {', '.join(collapsed_axes)}")

    return {
        "model_id": resolved_id,
        "step_file": f"jobs/{step_path.parent.name}/model.step",
        "units": "mm",
        "valid": valid,
        "shape_type": shape.ShapeType(),
        "bounding_box_mm": {
            "min": {
                "x": round(float(bounding_box.xmin), 6),
                "y": round(float(bounding_box.ymin), 6),
                "z": round(float(bounding_box.zmin), 6),
            },
            "max": {
                "x": round(float(bounding_box.xmax), 6),
                "y": round(float(bounding_box.ymax), 6),
                "z": round(float(bounding_box.zmax), 6),
            },
            "size": size,
        },
        "volume_mm3": round(volume, 6),
        "surface_area_mm2": round(float(shape.Area()), 6),
        "center_of_mass_mm": {
            "x": round(float(center.x), 6),
            "y": round(float(center.y), 6),
            "z": round(float(center.z), 6),
        },
        "topology": {
            "solids": len(shape.Solids()),
            "faces": len(shape.Faces()),
            "edges": len(shape.Edges()),
            "vertices": len(shape.Vertices()),
        },
        "step_size_bytes": step_path.stat().st_size,
        "warnings": warnings,
    }


@mcp.tool()
def detect_cad_interference(
    model_id: str | None = None,
    clearance_mm: float = 0.0,
    max_results: int = 100,
    max_candidate_pairs: int = 5000,
    volume_tolerance_mm3: float = 1e-6,
) -> dict[str, Any]:
    """Detect solid overlaps and optional clearance violations in a STEP job."""
    import cadquery as cq

    if not 0.0 <= clearance_mm <= 1000.0:
        raise ValueError("clearance_mm must be between 0 and 1000")
    if not 1 <= max_results <= 1000:
        raise ValueError("max_results must be between 1 and 1000")
    if not 1 <= max_candidate_pairs <= 100000:
        raise ValueError("max_candidate_pairs must be between 1 and 100000")
    if not 0.0 <= volume_tolerance_mm3 <= 1.0:
        raise ValueError("volume_tolerance_mm3 must be between 0 and 1")

    resolved_id, step_path = _resolve_step_source(model_id)
    shape = cq.importers.importStep(str(step_path)).val()
    solids = list(shape.Solids())
    boxes = [solid.BoundingBox() for solid in solids]

    def boxes_are_candidates(first: Any, second: Any) -> bool:
        margin = clearance_mm
        return not (
            first.xmax + margin < second.xmin
            or second.xmax + margin < first.xmin
            or first.ymax + margin < second.ymin
            or second.ymax + margin < first.ymin
            or first.zmax + margin < second.zmin
            or second.zmax + margin < first.zmin
        )

    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    broad_phase_candidates = 0
    exact_pairs_checked = 0
    interference_count = 0
    clearance_violation_count = 0
    candidate_limit_reached = False
    result_limit_reached = False

    for first_index, first in enumerate(solids):
        if candidate_limit_reached or result_limit_reached:
            break
        for second_index in range(first_index + 1, len(solids)):
            if not boxes_are_candidates(boxes[first_index], boxes[second_index]):
                continue
            if broad_phase_candidates >= max_candidate_pairs:
                candidate_limit_reached = True
                break
            broad_phase_candidates += 1
            second = solids[second_index]
            try:
                common = first.intersect(second)
                overlap_volume = float(common.Volume())
                exact_pairs_checked += 1
                if overlap_volume > volume_tolerance_mm3:
                    interference_count += 1
                    findings.append(
                        {
                            "type": "interference",
                            "solid_a": f"solid_{first_index:03d}",
                            "solid_b": f"solid_{second_index:03d}",
                            "overlap_volume_mm3": round(overlap_volume, 6),
                        }
                    )
                elif clearance_mm > 0.0:
                    distance = float(first.distance(second))
                    if distance < clearance_mm:
                        clearance_violation_count += 1
                        findings.append(
                            {
                                "type": "clearance_violation",
                                "solid_a": f"solid_{first_index:03d}",
                                "solid_b": f"solid_{second_index:03d}",
                                "distance_mm": round(distance, 6),
                                "required_clearance_mm": clearance_mm,
                            }
                        )
            except Exception as exc:  # noqa: BLE001 - isolate OpenCascade pair failures
                warnings.append(
                    f"solid_{first_index:03d}/solid_{second_index:03d}: {type(exc).__name__}: {exc}"
                )
            if len(findings) >= max_results:
                result_limit_reached = True
                break

    truncated = candidate_limit_reached or result_limit_reached
    if candidate_limit_reached:
        warnings.append(f"Stopped after max_candidate_pairs={max_candidate_pairs} candidate pairs")
    if result_limit_reached:
        warnings.append(f"Stopped after max_results={max_results} findings")

    return {
        "model_id": resolved_id,
        "step_file": f"jobs/{step_path.parent.name}/model.step",
        "units": "mm",
        "solid_count": len(solids),
        "clearance_mm": clearance_mm,
        "broad_phase_candidates": broad_phase_candidates,
        "exact_pairs_checked": exact_pairs_checked,
        "interference_count": interference_count,
        "clearance_violation_count": clearance_violation_count,
        "finding_count": len(findings),
        "truncated": truncated,
        "findings": findings,
        "warnings": warnings,
        "limitations": [
            "Checks imported STEP solids, not named assembly components.",
            (
                "STEP import may lose component names and hierarchy, so intentional "
                "same-part overlaps can be reported."
            ),
            "Touching faces are not interference unless positive overlap volume exists.",
        ],
    }


@mcp.tool()
def list_cad_components(model_id: str | None = None) -> dict[str, Any]:
    """List named assembly components and world-space bounds for a generated CAD job.

    Call this before inspect_component_clearance to obtain exact component paths.
    Defaults to the latest generated job.
    """
    resolved_id, job_dir = _resolve_job_dir(model_id)
    response = _run_job_tool("list", job_dir)
    return {
        "model_id": resolved_id,
        "units": "mm",
        **response,
    }


@mcp.tool()
def inspect_component_clearance(
    model_id: str,
    component_a: str,
    component_b: str,
    required_clearance_mm: float = 0.5,
) -> dict[str, Any]:
    """Measure overlap volume and minimum clearance between two named components.

    Use paths returned by list_cad_components. A result is interference when overlap
    volume is positive, insufficient_clearance when the measured gap is below the
    requested value, and pass otherwise.
    """
    if not 0.0 <= required_clearance_mm <= 1000.0:
        raise ValueError("required_clearance_mm must be between 0 and 1000")
    resolved_id, job_dir = _resolve_job_dir(model_id)
    response = _run_job_tool(
        "clearance",
        job_dir,
        component_a,
        component_b,
        str(required_clearance_mm),
    )
    return {
        "model_id": resolved_id,
        "units": "mm",
        **response,
    }


@mcp.tool()
def show_cad_job(
    model_id: str | None = None,
    with_animation: bool = True,
    reset_camera: bool = True,
) -> dict[str, Any]:
    """Redisplay a generated job in the existing OCP Viewer tab without opening a tab.

    Set with_animation=true to restore its timeline. The tool never launches a browser;
    open http://127.0.0.1:3939 once and reuse that tab.
    """
    resolved_id, job_dir = _resolve_job_dir(model_id)
    response = _run_job_tool(
        "show",
        job_dir,
        "1" if with_animation else "0",
        "1" if reset_camera else "0",
    )
    return {
        "model_id": resolved_id,
        "reused_existing_tab": True,
        **response,
    }


@mcp.tool(structured_output=False)
def get_cad_views(
    views: list[str] | None = None,
) -> list[TextContent | ImageContent]:
    """Capture multiple standard OCP CAD Viewer camera views as MCP images."""
    import time

    if not viewer_reachable():
        raise ConnectionError(f"OCP CAD Viewer is not reachable at http://127.0.0.1:{VIEWER_PORT}")

    from ocp_vscode import Camera, save_screenshot, set_viewer_config, status

    camera_by_name = {
        "iso": Camera.ISO,
        "front": Camera.FRONT,
        "back": Camera.BACK,
        "left": Camera.LEFT,
        "right": Camera.RIGHT,
        "top": Camera.TOP,
        "bottom": Camera.BOTTOM,
    }
    requested = views if views is not None else ["iso", "front", "right", "top"]
    if not requested:
        raise ValueError("views must contain at least one camera name")
    normalized = [view.strip().lower() for view in requested]
    invalid = [view for view in normalized if view not in camera_by_name]
    if invalid:
        raise ValueError(
            "unsupported views: "
            + ", ".join(invalid)
            + "; choose from "
            + ", ".join(camera_by_name)
        )
    normalized = list(dict.fromkeys(normalized))

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    original = status(port=VIEWER_PORT)
    captures: list[dict[str, Any]] = []
    images: list[ImageContent] = []
    try:
        for view in normalized:
            set_viewer_config(
                reset_camera=camera_by_name[view],
                port=VIEWER_PORT,
            )
            time.sleep(0.35)
            target = (PREVIEW_DIR / f"cad-{view}-{timestamp}.png").resolve()
            save_screenshot(str(target), port=VIEWER_PORT, polling=True)
            if not target.is_file() or target.stat().st_size == 0:
                raise RuntimeError(f"OCP CAD Viewer did not return the {view} screenshot")
            relative_path = target.relative_to(PROJECT_ROOT).as_posix()
            captures.append(
                {
                    "view": view,
                    "preview": relative_path,
                    "size_bytes": target.stat().st_size,
                }
            )
            images.append(
                ImageContent(
                    data=base64.b64encode(target.read_bytes()).decode("ascii"),
                    mimeType="image/png",
                )
            )
    finally:
        if isinstance(original, dict):
            restore = {
                key: original[key]
                for key in ("position", "quaternion", "target", "zoom")
                if key in original
            }
            set_viewer_config(
                **restore,
                reset_camera=Camera.KEEP,
                port=VIEWER_PORT,
            )

    metadata = TextContent(
        text=json.dumps(
            {
                "viewer_port": VIEWER_PORT,
                "view_count": len(captures),
                "captures": captures,
                "camera_restored": isinstance(original, dict),
            },
            ensure_ascii=False,
        )
    )
    return [metadata, *images]


@mcp.tool()
def get_viewer_selection() -> dict[str, Any]:
    """Report the part last clicked in the OCP CAD Viewer.

    Ask the user to click the part or spot they mean in the viewer, then call
    this tool to read back its Assembly path, name, and world-space bounding
    box/sphere (mm). Use this instead of asking the user to describe a 3D
    location in words. The click persists until the next one, so if the
    reported path does not appear under the currently shown model's Assembly
    tree, it is stale -- ask the user to click again in the current model.
    """
    if not viewer_reachable():
        raise ConnectionError(f"OCP CAD Viewer is not reachable at http://127.0.0.1:{VIEWER_PORT}")

    from ocp_vscode import status as viewer_status

    state = viewer_status(port=VIEWER_PORT)
    last_pick = state.get("lastPick")
    if not last_pick:
        return {
            "picked": False,
            "message": "ビューアでまだ何もクリックされていません。パーツをクリックしてから再度呼び出してください。",
        }

    bbox = last_pick.get("boundingBox") or {}
    bmin = bbox.get("min") or {}
    bmax = bbox.get("max") or {}
    sphere = last_pick.get("boundingSphere") or {}
    center = sphere.get("center") or {}
    return {
        "picked": True,
        "path": last_pick.get("path"),
        "name": last_pick.get("name"),
        "units": "mm",
        "bounding_box": {
            "min": {"x": bmin.get("x"), "y": bmin.get("y"), "z": bmin.get("z")},
            "max": {"x": bmax.get("x"), "y": bmax.get("y"), "z": bmax.get("z")},
        },
        "center": {"x": center.get("x"), "y": center.get("y"), "z": center.get("z")},
        "radius_mm": sphere.get("radius"),
        "note": (
            "pathが現在表示中のモデルのAssembly階層に見当たらない場合は、"
            "古いクリックが残っている可能性があります。"
        ),
    }


@mcp.tool()
def get_viewer_state() -> dict[str, Any]:
    """Report what the user is currently looking at in the OCP CAD Viewer.

    Returns the live camera (position/target/quaternion/zoom), the animation
    timeline's current scrub position (0..1, and the job's declared duration
    if known), and which named Assembly paths are currently hidden. Use this
    instead of asking the user to describe their current view, playback
    position, or visibility toggles in words -- combine with
    get_viewer_selection when they also click a specific part.
    """
    if not viewer_reachable():
        raise ConnectionError(f"OCP CAD Viewer is not reachable at http://127.0.0.1:{VIEWER_PORT}")

    from ocp_vscode import status as viewer_status

    state = viewer_status(port=VIEWER_PORT)
    position = state.get("position") or [None, None, None]
    target = state.get("target") or [None, None, None]
    quaternion = state.get("quaternion") or [None, None, None, None]
    hidden_paths = [
        path
        for path, flags in (state.get("states") or {}).items()
        if isinstance(flags, list) and flags and flags[0] == 0
    ]
    return {
        "units": "mm",
        "camera": {
            "position": {"x": position[0], "y": position[1], "z": position[2]},
            "target": {"x": target[0], "y": target[1], "z": target[2]},
            "quaternion": {
                "x": quaternion[0],
                "y": quaternion[1],
                "z": quaternion[2],
                "w": quaternion[3],
            },
            "zoom": state.get("zoom"),
            "ortho": state.get("ortho"),
        },
        "animation_relative_time": state.get("relative_time"),
        "hidden_paths": hidden_paths,
        "active_tab": state.get("tab"),
    }


@mcp.tool()
def viewer_help() -> dict[str, Any]:
    """CadQueryコードとOCP animationの必須形式を返す。"""
    return {
        "result": "最終オブジェクトを result に代入",
        "steps": "steps = ['ベース作成', '穴加工', '組立']",
        "animation": {
            "path": "/assembly/part-name",
            "action": "tx|ty|tz|t|rx|ry|rz|q",
            "times": [0.0, 1.0, 2.0],
            "values": [0.0, 20.0, 0.0],
        },
        "note": "animation pathは直前にshowしたAssemblyの名前階層と一致させます",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
