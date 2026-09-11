"""Single-speed bicycle with a toothed-belt drivetrain (Gates Carbon Drive style).

Reuses the validated two-circle external-tangent construction from
examples/timing_belt.py (same `belt_path` math, proven correct via a
scipy.spatial.ConvexHull ground-truth check -- see CLAUDE.md's "external-
tangent sign convention" standard) to connect a 44T crank sprocket to a 16T
rear-hub sprocket. `belt_path_oriented` is a thin wrapper that lets the two
sprocket centers sit anywhere in the (X,Z) plane instead of only along a
local x-axis, which the bicycle needs (the bottom bracket sits lower than
the rear axle) but the single-plane timing_belt.py example did not.

World axes: X=forward, Y=lateral (drivetrain offset to +Y, the "drive
side"), Z=up. Wheels, sprockets and the crank all rotate about world Y.

Animated as one rigid group each: crank_group (front sprocket + both crank
arms + both pedals, about the bottom bracket), rear_wheel (rim + hub +
spokes + rear sprocket, about the rear axle -- rigidly one body, since a
real belt-drive hub has no freewheel slip modeled here), front_wheel (rim +
hub + spokes, about the front axle, spun at the same rate as the rear wheel
since both wheels share one radius and roll without slipping). The belt
body is a static ribbon (OCP Viewer animation has no mesh-deformation
action -- see project memory ocp-viewer-rigid-body-animation-limit); a ring
of small tooth markers riding just outside the belt's outer surface gets a
dense position (t) track per marker to approximate the belt "flowing".
"""

import math

import cadquery as cq

steps = [
    "フレーム(ダイヤモンド型)・フォーク・ハンドル・サドルを生成",
    "前後スプロケット(44T/16T)と外接線ベルト経路を厳密計算",
    "ベルト本体とベルト外周の歯マーカーを生成",
    "前後ホイール(リム・ハブ・スポーク)とクランク・ペダルを生成",
    "クランク/後輪/前輪をそれぞれ剛体グループとして組立",
    "ペダリング回転・後輪連動・前輪従動・ベルト歯マーカーのアニメーションを設定",
]

# --- world layout (mm), X=forward, Y=lateral, Z=up ----------------------
wheel_radius = 330.0
rim_inner = 295.0
wheel_width = 22.0
hub_radius = 20.0
hub_bore = 8.0
hub_width = 50.0
spoke_radius = 2.2
n_spokes = 12

wheelbase = 1020.0
rear_axle = (0.0, wheel_radius)          # (x, z)
front_axle = (wheelbase, wheel_radius)

bb = (430.0, 260.0)                      # bottom bracket
seat_tube_top = (388.0, 830.0)

# head_tube_bottom/top are derived from the steering axis (through front_axle)
# rather than placed by hand: a short fork_length previously put both the
# down_tube and head_tube close enough to front_axle that their straight
# centerlines cut through the front rim (which extends out to wheel_radius,
# not just rim_inner) partway along their length, even though neither
# endpoint touched it -- the same "checked the tip, not the whole strut"
# mistake as chain_stay/seat_stay/fork_blade below, just against a different
# wheel. fork_length=440 keeps both segments' closest approach to front_axle,
# minus their own tube radius, safely outside wheel_radius.
head_tube_angle_deg = 74.6
fork_length = 440.0  # must clear the rim's OUTER radius + down_tube's own radius, not just rim_inner
head_tube_len = 206.0
_u = (-math.cos(math.radians(head_tube_angle_deg)), math.sin(math.radians(head_tube_angle_deg)))
head_tube_bottom = (front_axle[0] + fork_length * _u[0], front_axle[1] + fork_length * _u[1])
head_tube_top = (head_tube_bottom[0] + head_tube_len * _u[0], head_tube_bottom[1] + head_tube_len * _u[1])
stem_top = (head_tube_top[0] - 45.0, head_tube_top[1] + 55.0)
saddle_base = (355.0, 892.0)

frame_tube_r = 13.0
fork_blade_r = 11.0
seatpost_r = 10.0
stem_r = 9.0
handlebar_r = 8.0
handlebar_half_width = 190.0

drive_y = 46.0                           # drivetrain lateral offset (drive side)
crank_arm_length = 170.0
crank_arm_r = 9.0
pedal_extra_y = 26.0
pedal_size = (50.0, 16.0, 34.0)

front_teeth = 44
rear_teeth = 16
sprocket_module = 3.0
front_radius = sprocket_module * front_teeth / 2.0  # pitch radius, 66 mm
rear_radius = sprocket_module * rear_teeth / 2.0    # pitch radius, 24 mm
sprocket_width = 6.0
sprocket_bore = 15.0
tooth_h = 1.6
tooth_w = 2.4

belt_thickness = 2.2
belt_offset = tooth_h + belt_thickness / 2.0 + 0.1
belt_width = sprocket_width

marker_pin_radius = 1.1
marker_spacing = 26.0
marker_gap = 0.25

pedal_turns = 2.0
duration = 5.0
n_time_samples = 150

red = cq.Color(0.75, 0.12, 0.14)
silver = cq.Color(0.72, 0.74, 0.77)
dark = cq.Color(0.16, 0.16, 0.18)
orange = cq.Color(0.85, 0.55, 0.15)
blue = cq.Color(0.2, 0.55, 0.85)
gold = cq.Color(0.85, 0.7, 0.15)
black = cq.Color(0.08, 0.08, 0.09)


def tube(p0, p1, radius):
    v0 = cq.Vector(*p0)
    v1 = cq.Vector(*p1)
    d = v1 - v0
    length = d.Length
    direction = cq.Vector(d.x / length, d.y / length, d.z / length)
    return cq.Workplane(obj=cq.Solid.makeCylinder(radius, length, v0, direction))


def belt_path(ra, ca, rb, cb, d):
    """Closed path around two circles via their external (open-belt) tangents.

    Identical to examples/timing_belt.py -- see CLAUDE.md's "external-tangent
    sign convention" standard. Assumes ca, cb lie along the local x-axis;
    belt_path_oriented() below lifts that restriction.
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
    arc_b_deg = 2.0 * gamma
    arc_a_deg = 360.0 - 2.0 * gamma
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


def belt_path_oriented(ra, ca, rb, cb):
    """belt_path() for two circle centers at an arbitrary angle, not just along x."""
    d = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
    theta = math.atan2(cb[1] - ca[1], cb[0] - ca[0])
    point_local, total_len = belt_path(ra, (0.0, 0.0), rb, (d, 0.0), d)
    ct, st = math.cos(theta), math.sin(theta)

    def point_world(s):
        lx, ly = point_local(s)
        return (ca[0] + lx * ct - ly * st, ca[1] + lx * st + ly * ct)

    return point_world, total_len


def toothed_disc_xz(pitch_radius, teeth, width, bore_dia, th, tw, lateral_y):
    """A toothed disc in the (X,Z) plane, axis along world Y, pitch center at (0,Z=0)."""
    body = cq.Workplane("XZ").circle(pitch_radius).extrude(width)
    for i in range(teeth):
        ang = 360.0 * i / teeth
        tooth = (
            cq.Workplane("XZ")
            .center(pitch_radius + th / 2.0, 0)
            .rect(th, tw)
            .extrude(width)
            .rotate((0, 0, 0), (0, 1, 0), ang)
        )
        body = body.union(tooth)
    if bore_dia > 0:
        body = body.cut(cq.Workplane("XZ").circle(bore_dia / 2.0).extrude(width))
    return body.translate((0, lateral_y + width / 2.0, 0))


def ring_xz(ro, ri, width, lateral_y):
    outer = cq.Workplane("XZ").circle(ro).extrude(width)
    inner = cq.Workplane("XZ").circle(ri).extrude(width)
    return outer.cut(inner).translate((0, lateral_y + width / 2.0, 0))


cad_step(steps[0])  # noqa: F821 - injected by cad_workbench.runner


def pull_back(p_from, p_to, distance):
    """Shorten a strut so its tip stops at a hub's outer surface, not its center."""
    dx, dz = p_to[0] - p_from[0], p_to[1] - p_from[1]
    length = math.hypot(dx, dz)
    f = max(0.0, (length - distance) / length)
    return (p_from[0] + dx * f, p_from[1] + dz * f)


hub_clear = hub_radius + frame_tube_r + 3.0  # centerline clearance must also cover the strut's own radius
frame_members = [
    ("top_tube", seat_tube_top, head_tube_top, frame_tube_r),
    ("down_tube", bb, head_tube_bottom, frame_tube_r),
    ("seat_tube", bb, seat_tube_top, frame_tube_r),
    ("head_tube", head_tube_bottom, head_tube_top, frame_tube_r),
    ("stem", head_tube_top, stem_top, stem_r),
    ("seatpost", seat_tube_top, saddle_base, seatpost_r),
]
frame_group = cq.Assembly(name="frame")
for name, p0, p1, radius in frame_members:
    shape = tube((p0[0], 0.0, p0[1]), (p1[0], 0.0, p1[1]), radius)
    frame_group.add(shape, name=name, color=red)

# chain_stay, seat_stay and fork_blade run at Y=0 in a naive single-centerline
# build, which is the *same* lateral plane as the wheel rim (also Y=0-centered)
# -- a single tube from the frame to the axle then cuts straight through the
# rim disc partway along its length even though both of its endpoints clear
# it. Route these as a left/right pair at a constant lateral offset instead
# (matching how a real frame straddles the wheel) so the whole strut -- not
# just its tip -- stays outside the rim's Y-span; see CLAUDE.md's "bores
# must sit inside a full ring" standard for the same "tip-position, not
# radius-mismatch" family of bug this generalizes.
straddle_y = wheel_width / 2.0 + frame_tube_r + 5.0  # also clears each strut's own radius, not just its centerline
chain_stay_tip = pull_back(bb, rear_axle, hub_clear)
seat_stay_tip = pull_back(seat_tube_top, rear_axle, hub_clear)
fork_blade_tip = pull_back(head_tube_bottom, front_axle, hub_clear)
for side, label in ((-1.0, "l"), (1.0, "r")):
    y = side * straddle_y
    frame_group.add(
        tube((bb[0], y, bb[1]), (chain_stay_tip[0], y, chain_stay_tip[1]), frame_tube_r * 0.85),
        name=f"chain_stay_{label}",
        color=red,
    )
    frame_group.add(
        tube((seat_tube_top[0], y, seat_tube_top[1]), (seat_stay_tip[0], y, seat_stay_tip[1]), frame_tube_r * 0.7),
        name=f"seat_stay_{label}",
        color=red,
    )
    frame_group.add(
        tube((head_tube_bottom[0], y, head_tube_bottom[1]), (fork_blade_tip[0], y, fork_blade_tip[1]), fork_blade_r),
        name=f"fork_blade_{label}",
        color=red,
    )

handlebar = tube(
    (stem_top[0], -handlebar_half_width, stem_top[1]),
    (stem_top[0], handlebar_half_width, stem_top[1]),
    handlebar_r,
)
frame_group.add(handlebar, name="handlebar", color=silver)
saddle = cq.Workplane("XY").box(90, 45, 20).translate((saddle_base[0] + 8, 0, saddle_base[1] + 10))
frame_group.add(saddle, name="saddle", color=black)

cad_step(steps[1])  # noqa: F821 - injected by cad_workbench.runner
point_belt_center, belt_len = belt_path_oriented(
    front_radius + belt_offset, bb, rear_radius + belt_offset, rear_axle
)

cad_step(steps[2])  # noqa: F821 - injected by cad_workbench.runner
half_t = belt_thickness / 2.0
point_outer, len_outer = belt_path_oriented(
    front_radius + belt_offset + half_t, bb, rear_radius + belt_offset + half_t, rear_axle
)
point_inner, len_inner = belt_path_oriented(
    front_radius + belt_offset - half_t, bb, rear_radius + belt_offset - half_t, rear_axle
)
n_belt_samples = 200
outer_pts = [point_outer(len_outer * i / n_belt_samples) for i in range(n_belt_samples)]
inner_pts = [point_inner(len_inner * i / n_belt_samples) for i in range(n_belt_samples)]
belt_outer_solid = cq.Workplane("XZ").polyline(outer_pts).close().extrude(belt_width)
belt_inner_solid = cq.Workplane("XZ").polyline(inner_pts).close().extrude(belt_width)
belt_body = belt_outer_solid.cut(belt_inner_solid).translate((0, drive_y + belt_width / 2.0, 0))

marker_radial_offset = belt_offset + half_t + marker_pin_radius + marker_gap
point_marker, marker_path_len = belt_path_oriented(
    front_radius + marker_radial_offset, bb, rear_radius + marker_radial_offset, rear_axle
)
n_markers = max(8, round(belt_len / marker_spacing))
marker_s0 = [belt_len * i / n_markers for i in range(n_markers)]
marker_shape = (
    cq.Workplane("XZ").circle(marker_pin_radius).extrude(belt_width * 0.9).translate((0, -belt_width * 0.45, 0))
)
belt_teeth = cq.Assembly(name="belt_teeth")
for idx, s0 in enumerate(marker_s0):
    x0, z0 = point_marker(s0 / belt_len * marker_path_len)
    belt_teeth.add(
        marker_shape,
        name=f"tooth_{idx:02d}",
        loc=cq.Location(cq.Vector(x0, drive_y, z0)),
        color=gold,
    )

cad_step(steps[3])  # noqa: F821 - injected by cad_workbench.runner
rim_local = ring_xz(wheel_radius, rim_inner, wheel_width, 0.0)
hub_local = ring_xz(hub_radius, hub_bore, hub_width, 0.0)
spokes_local = []
for i in range(n_spokes):
    a = 2.0 * math.pi * i / n_spokes
    p_hub = (hub_radius * math.cos(a), 0.0, hub_radius * math.sin(a))
    p_rim = (rim_inner * math.cos(a), 0.0, rim_inner * math.sin(a))
    spokes_local.append(tube(p_hub, p_rim, spoke_radius))

rear_sprocket_local = toothed_disc_xz(
    rear_radius, rear_teeth, sprocket_width, sprocket_bore, tooth_h, tooth_w, drive_y
)
front_sprocket_local = toothed_disc_xz(
    front_radius, front_teeth, sprocket_width, sprocket_bore, tooth_h, tooth_w, drive_y
)

crank_arm_1 = tube((0.0, drive_y, 0.0), (0.0, drive_y, crank_arm_length), crank_arm_r)
crank_arm_2 = tube((0.0, drive_y, 0.0), (0.0, drive_y, -crank_arm_length), crank_arm_r)
pedal_1 = cq.Workplane("XY").box(*pedal_size).translate((0.0, drive_y + pedal_extra_y, crank_arm_length))
pedal_2 = cq.Workplane("XY").box(*pedal_size).translate((0.0, drive_y + pedal_extra_y, -crank_arm_length))

cad_step(steps[4])  # noqa: F821 - injected by cad_workbench.runner
crank_group = cq.Assembly(name="crank_group")
crank_group.add(front_sprocket_local, name="front_sprocket", color=orange)
crank_group.add(crank_arm_1, name="crank_arm_1", color=silver)
crank_group.add(crank_arm_2, name="crank_arm_2", color=silver)
crank_group.add(pedal_1, name="pedal_1", color=black)
crank_group.add(pedal_2, name="pedal_2", color=black)

rear_wheel_group = cq.Assembly(name="rear_wheel")
rear_wheel_group.add(rim_local, name="rim", color=dark)
rear_wheel_group.add(hub_local, name="hub", color=silver)
for i, spoke in enumerate(spokes_local):
    rear_wheel_group.add(spoke, name=f"spoke_{i:02d}", color=silver)
rear_wheel_group.add(rear_sprocket_local, name="rear_sprocket", color=blue)

front_wheel_group = cq.Assembly(name="front_wheel")
front_wheel_group.add(rim_local, name="rim", color=dark)
front_wheel_group.add(hub_local, name="hub", color=silver)
for i, spoke in enumerate(spokes_local):
    front_wheel_group.add(spoke, name=f"spoke_{i:02d}", color=silver)

result = cq.Assembly(name="bicycle")
result.add(frame_group, name="frame")
result.add(crank_group, name="crank_group", loc=cq.Location(cq.Vector(bb[0], 0.0, bb[1])))
result.add(rear_wheel_group, name="rear_wheel", loc=cq.Location(cq.Vector(rear_axle[0], 0.0, rear_axle[1])))
result.add(front_wheel_group, name="front_wheel", loc=cq.Location(cq.Vector(front_axle[0], 0.0, front_axle[1])))
result.add(belt_body, name="belt_body", color=dark)
result.add(belt_teeth, name="belt_teeth")

cad_step(steps[5])  # noqa: F821 - injected by cad_workbench.runner
omega_front = 2.0 * math.pi * pedal_turns / duration        # crank angular speed, rad/s
v_belt = omega_front * front_radius                         # mm/s, at the front sprocket pitch circle
omega_rear = v_belt / rear_radius                            # rad/s, rear sprocket == rear wheel (rigid)
omega_wheel = omega_rear                                     # front wheel matches rear (equal radii, no slip)

times = [duration * i / n_time_samples for i in range(n_time_samples + 1)]
crank_values = [-math.degrees(omega_front * t) for t in times]
rear_wheel_values = [-math.degrees(omega_rear * t) for t in times]
front_wheel_values = [-math.degrees(omega_wheel * t) for t in times]

animation = [
    {"path": "/bicycle/crank_group", "action": "ry", "times": times, "values": crank_values},
    {"path": "/bicycle/rear_wheel", "action": "ry", "times": times, "values": rear_wheel_values},
    {"path": "/bicycle/front_wheel", "action": "ry", "times": times, "values": front_wheel_values},
]
for idx, s0 in enumerate(marker_s0):
    x0, z0 = point_marker(s0 / belt_len * marker_path_len)
    marker_values = []
    for t in times:
        frac = (s0 + v_belt * t) / belt_len
        x, z = point_marker(frac * marker_path_len)
        marker_values.append([x - x0, 0.0, z - z0])
    animation.append(
        {
            "path": f"/bicycle/belt_teeth/tooth_{idx:02d}",
            "action": "t",
            "times": times,
            "values": marker_values,
        }
    )
