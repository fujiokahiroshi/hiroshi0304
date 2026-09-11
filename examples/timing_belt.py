"""Timing belt drive: 20T driver pulley and 40T driven pulley (2:1 ratio).

The pulleys are rigid toothed cylinders and rotate correctly (OCP CAD Viewer
animation only supports rigid transforms -- see project memory
ocp-viewer-rigid-body-animation-limit, no scale/morph action exists). The
belt loop itself is built from the exact external-tangent construction for
two circles of different radii and is shown as a static swept ribbon.

To still convey the belt "flowing", a ring of small tooth-marker pins sits
on the belt centerline and each pin gets a dense position (t) track that
carries it along the same closed path at the belt's linear speed, wrapping
around the loop once every `loops` traversals. This approximates surface
motion with markers; it is not true bulk mesh deformation.
"""

import math

import cadquery as cq

steps = [
    "小プーリー(駆動,20T)と大プーリー(従動,40T)を生成",
    "2円の外接線からベルト経路(直線2本+円弧2本)を厳密計算",
    "ベルト経路の内外オフセットからベルト本体(帯状ソリッド)を生成",
    "ベルト経路上に歯マーカーを等間隔配置してAssemblyに組立",
    "プーリー回転(速度比2:1)と歯マーカーの経路移動アニメーションを設定",
]

# --- parameters ---------------------------------------------------------
teeth_small = 20
teeth_large = 40
module = 1.5
r1 = module * teeth_small / 2.0  # small (driver) pulley pitch radius
r2 = module * teeth_large / 2.0  # large (driven) pulley pitch radius
center_distance = 90.0
pulley_width = 8.0
bore = 6.0
tooth_h = 1.2
tooth_w = 1.6

belt_thickness = 2.0
belt_offset = tooth_h + belt_thickness / 2.0 + 0.1  # belt inner face clears tooth tips
belt_width = pulley_width

marker_pin_radius = 0.8
marker_spacing = 12.0

duration = 6.0
loops = 1.5
n_time_samples = 180

orange = cq.Color(0.85, 0.55, 0.15)
blue = cq.Color(0.2, 0.55, 0.85)
dark = cq.Color(0.18, 0.18, 0.2)
gold = cq.Color(0.85, 0.7, 0.15)


def toothed_pulley(pitch_radius, teeth, width, bore_dia, th, tw):
    body = cq.Workplane("XY").circle(pitch_radius).extrude(width)
    for i in range(teeth):
        ang = 360.0 * i / teeth
        tooth = (
            cq.Workplane("XY")
            .center(pitch_radius + th / 2.0, 0)
            .rect(th, tw)
            .extrude(width)
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        body = body.union(tooth)
    body = body.cut(cq.Workplane("XY").circle(bore_dia / 2.0).extrude(width))
    return body.translate((0, 0, -width / 2.0))


def belt_path(ra, ca, rb, cb, d):
    """Closed path around two circles via their external (open-belt) tangents.

    Returns (point_at, total_len) where point_at(s) samples the path by
    arc length s, and the path is c1-far-arc -> tangent -> c2-far-arc -> tangent.
    """
    gamma = math.degrees(math.acos((ra - rb) / d))

    def m(sign):
        a = math.radians(sign * gamma)
        return (math.cos(a), math.sin(a))

    m_up = m(1.0)
    m_lo = m(-1.0)
    t1_up = (ca[0] + ra * m_up[0], ca[1] + ra * m_up[1])
    t2_up = (cb[0] + rb * m_up[0], cb[1] + rb * m_up[1])
    t1_lo = (ca[0] + ra * m_lo[0], ca[1] + ra * m_lo[1])
    t2_lo = (cb[0] + rb * m_lo[0], cb[1] + rb * m_lo[1])

    ls = math.hypot(t2_up[0] - t1_up[0], t2_up[1] - t1_up[1])
    arc_b_deg = 2.0 * gamma           # large pulley, far side (short arc)
    arc_a_deg = 360.0 - 2.0 * gamma   # small pulley, far side (long arc)
    arc_b_len = math.radians(arc_b_deg) * rb
    arc_a_len = math.radians(arc_a_deg) * ra
    total_len = 2.0 * ls + arc_a_len + arc_b_len

    seg_a_end = ls
    seg_b_end = seg_a_end + arc_b_len
    seg_c_end = seg_b_end + ls

    def point_at(s):
        s = s % total_len
        if s <= seg_a_end:
            f = s / ls
            return (t1_up[0] + (t2_up[0] - t1_up[0]) * f, t1_up[1] + (t2_up[1] - t1_up[1]) * f)
        if s <= seg_b_end:
            f = (s - seg_a_end) / arc_b_len
            ang = math.radians(gamma) - f * math.radians(arc_b_deg)
            return (cb[0] + rb * math.cos(ang), cb[1] + rb * math.sin(ang))
        if s <= seg_c_end:
            f = (s - seg_b_end) / ls
            return (t2_lo[0] + (t1_lo[0] - t2_lo[0]) * f, t2_lo[1] + (t1_lo[1] - t2_lo[1]) * f)
        f = (s - seg_c_end) / arc_a_len
        ang = math.radians(-gamma) - f * math.radians(arc_a_deg)
        return (ca[0] + ra * math.cos(ang), ca[1] + ra * math.sin(ang))

    return point_at, total_len


cad_step(steps[0])  # noqa: F821 - injected by cad_workbench.runner
c1 = (0.0, 0.0)
c2 = (center_distance, 0.0)
pulley_small = toothed_pulley(r1, teeth_small, pulley_width, bore, tooth_h, tooth_w)
pulley_large = toothed_pulley(r2, teeth_large, pulley_width, bore, tooth_h, tooth_w)

cad_step(steps[1])  # noqa: F821 - injected by cad_workbench.runner
point_center, belt_len = belt_path(r1 + belt_offset, c1, r2 + belt_offset, c2, center_distance)

cad_step(steps[2])  # noqa: F821 - injected by cad_workbench.runner
half_t = belt_thickness / 2.0
point_outer, len_outer = belt_path(
    r1 + belt_offset + half_t, c1, r2 + belt_offset + half_t, c2, center_distance
)
point_inner, len_inner = belt_path(
    r1 + belt_offset - half_t, c1, r2 + belt_offset - half_t, c2, center_distance
)
n_belt_samples = 160
outer_pts = [point_outer(len_outer * i / n_belt_samples) for i in range(n_belt_samples)]
inner_pts = [point_inner(len_inner * i / n_belt_samples) for i in range(n_belt_samples)]
outer_solid = cq.Workplane("XY").polyline(outer_pts).close().extrude(belt_width)
inner_solid = cq.Workplane("XY").polyline(inner_pts).close().extrude(belt_width)
belt_body = outer_solid.cut(inner_solid).translate((0, 0, -belt_width / 2.0))

cad_step(steps[3])  # noqa: F821 - injected by cad_workbench.runner
marker_gap = 0.2  # clears the belt's outer surface so markers read as raised teeth, not buried
marker_radial_offset = belt_offset + half_t + marker_pin_radius + marker_gap
point_marker, marker_path_len = belt_path(
    r1 + marker_radial_offset, c1, r2 + marker_radial_offset, c2, center_distance
)
n_markers = max(8, round(belt_len / marker_spacing))
marker_s0 = [belt_len * i / n_markers for i in range(n_markers)]
marker_shape = (
    cq.Workplane("XY")
    .circle(marker_pin_radius)
    .extrude(belt_width * 0.9)
    .translate((0, 0, -belt_width * 0.45))
)

belt_teeth = cq.Assembly(name="belt_teeth")
for idx, s0 in enumerate(marker_s0):
    x0, y0 = point_marker(s0 / belt_len * marker_path_len)
    belt_teeth.add(
        marker_shape,
        name=f"tooth_{idx:02d}",
        loc=cq.Location(cq.Vector(x0, y0, 0)),
        color=gold,
    )

result = cq.Assembly(name="timing_belt")
result.add(pulley_small, name="pulley_small", color=orange)
result.add(pulley_large, name="pulley_large", loc=cq.Location(cq.Vector(*c2, 0)), color=blue)
result.add(belt_body, name="belt_body", color=dark)
result.add(belt_teeth, name="belt_teeth")

cad_step(steps[4])  # noqa: F821 - injected by cad_workbench.runner
v_belt = loops * belt_len / duration  # mm/s, constant along the inextensible belt
omega_small = v_belt / r1  # rad/s
omega_large = v_belt / r2  # rad/s

times = [duration * i / n_time_samples for i in range(n_time_samples + 1)]
values_small = [-math.degrees(omega_small * t) for t in times]
values_large = [-math.degrees(omega_large * t) for t in times]

animation = [
    {"path": "/timing_belt/pulley_small", "action": "rz", "times": times, "values": values_small},
    {"path": "/timing_belt/pulley_large", "action": "rz", "times": times, "values": values_large},
]
for idx, s0 in enumerate(marker_s0):
    x0, y0 = point_marker(s0 / belt_len * marker_path_len)
    marker_values = []
    for t in times:
        frac = (s0 + v_belt * t) / belt_len
        x, y = point_marker(frac * marker_path_len)
        marker_values.append([x - x0, y - y0, 0.0])
    animation.append(
        {
            "path": f"/timing_belt/belt_teeth/tooth_{idx:02d}",
            "action": "t",
            "times": times,
            "values": marker_values,
        }
    )
