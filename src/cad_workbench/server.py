from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Any

from mcp.server import MCPServer

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
    values_b = [0.0 if index == 0 else rotation_b * index / segments for index in range(segments + 1)]
    return f'''import cadquery as cq
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
'''


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
    values_b = [0.0 if index == 0 else rotation_b * index / segments for index in range(segments + 1)]
    return f'''import cadquery as cq
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
'''


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
            max(abs(left_angle), abs(right_angle), abs(carrier_angle), abs(spider_angle))
            / 90.0
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
    return f'''import cadquery as cq
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
'''


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
    payload = {"title": title, "code": code, "steps": steps or [],
               "formats": formats or ["step"], "animation": animation or [],
               "speed": max(0.1, min(float(animation_speed), 10.0)),
               "output_dir": str(output_dir)}
    payload_path = output_dir / "request.json"
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_state(status="queued", title=title, message="ClaudeのCADジョブを開始します")
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    completed = subprocess.run(
        [sys.executable, "-m", "cad_workbench.runner", str(payload_path)],
        cwd=output_dir, env=environment, capture_output=True, text=True,
        encoding="utf-8", timeout=120, check=False)
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
        code=_bevel_gear_code(
            teeth_a, teeth_b, module, face_width, bore, turns, duration
        ),
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
def viewer_help() -> dict[str, Any]:
    """CadQueryコードとOCP animationの必須形式を返す。"""
    return {
        "result": "最終オブジェクトを result に代入",
        "steps": "steps = ['ベース作成', '穴加工', '組立']",
        "animation": {"path": "/assembly/part-name", "action": "tx|ty|tz|t|rx|ry|rz|q",
                      "times": [0.0, 1.0, 2.0], "values": [0.0, 20.0, 0.0]},
        "note": "animation pathは直前にshowしたAssemblyの名前階層と一致させます",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
