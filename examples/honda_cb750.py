"""Honda CB750-style air-cooled inline-4 naked motorcycle, with a real slider-crank engine.

Realism targets (mm, roughly production CB750 K0 numbers): wheelbase 1455, seat
height ~800, head angle 62.5 deg (~27.5 deg rake), fork offset 65, 19"-ish front /
18"-ish wheels, chain final drive. World axes: X=forward, Y=lateral (crank/wheel
axis, +Y = chain/drive side), Z=up, ground at Z=0.

Engine kinematics are the exact slider-crank relation used in examples/rc35_glow_engine.py
(same tan/asin formulas), NOT a marker approximation, extended to 4 inline cylinders on
one rigid crankshaft:
  * All 4 bores share one (X,Z) centerline (crank_c) -- a normal inline engine has no
    piston offset -- and differ only in Y. Cylinders 1&4 share crank phase, 2&3 share the
    opposite (180 deg) phase: the standard flat/180 inline-4 crank layout.
  * The crankshaft is ONE rigid shape (four crank-pin throws on one main journal) that
    spins as a single "ry" track. Each piston is a separate Z-only "tz" track; each rod is
    a separate translate-with-the-pin "t" track plus its own tilt "ry" track -- the same
    three-group decomposition as rc35_glow_engine.py's crank_rotation / piston_translation
    / rod_pivot_translation, just repeated per cylinder.
  * 6 crank turns (3 complete 4-stroke cycles) drive, through an unmodelled primary+gearbox
    reduction and then a real countershaft/rear-wheel chain sprocket pair (belt_path
    construction from examples/timing_belt.py -- CLAUDE.md's external-tangent standard),
    the rear wheel; the front wheel matches the resulting ground speed at its own radius
    (front_r != rear_r here, so this is omega_rear*rear_r/front_r, not a straight copy).

The final-drive chain itself is the timing_belt.py tooth-marker approximation (a static
ribbon + markers riding its surface), not individually modelled links like
examples/road_bike.py's chain -- this session's stated priority was the engine, not the
final drive -- see project memory on the rigid-body animation ceiling for why a flowing
chain/belt can't be a true continuous deformation either way.
"""

import math

import cadquery as cq

steps = [
    "フレーム(ヘッドパイプ・ダブルクレードル・スイングアームピボット・シートレール)を一体化",
    "フロントフォーク・ハンドル・ヘッドライト・前後フェンダーを生成",
    "燃料タンク・シート・ミラー・ステップを生成",
    "前後ホイール(トーラスタイヤ・スポーク・フロントディスク・リアドラム)を生成",
    "クランクケース・4気筒シリンダー/ヘッド・排気管・キャブレターを生成",
    "外接線からファイナルチェーン経路を計算し、スプロケット・歯マーカーを配置",
    "クランク軸(4本のピン,180度位相)・ピストン・コンロッドの正確なスライダークランク運動を設定",
    "クランク→(内部変速比)→カウンターシャフト→チェーン→後輪、前輪従動のアニメーションを設定",
]

# ---------------------------------------------------------------- geometry
wheel_front_r, wheel_rear_r = 335.0, 325.0
front_rim_out, front_rim_in, front_rim_w = 300.0, 278.0, 26.0
rear_rim_out, rear_rim_in, rear_rim_w = 292.0, 270.0, 34.0
tire_minor_f = wheel_front_r - front_rim_out
tire_minor_r = wheel_rear_r - rear_rim_out

wheelbase = 1455.0
rear_axle = (0.0, wheel_rear_r)
front_axle = (wheelbase, wheel_front_r)

head_angle = math.radians(62.5)
u = (-math.cos(head_angle), math.sin(head_angle))
fw = (math.sin(head_angle), math.cos(head_angle))
fork_offset, fork_length, head_tube_len = 65.0, 560.0, 120.0


def along(p, d, t):
    return (p[0] + d[0] * t, p[1] + d[1] * t)


def pull_back(p_from, p_to, distance):
    """Shorten a strut so its tip stops at a hub's outer surface, not its centre --
    the straddled-Y fix alone (see swingarm/fork below) only clears the wheel's rim/tyre;
    the tip can still plunge past the hub's own radius if it still aims at the exact axle."""
    dx, dz = p_to[0] - p_from[0], p_to[1] - p_from[1]
    length = math.hypot(dx, dz)
    f = max(0.0, (length - distance) / length)
    return (p_from[0] + dx * f, p_from[1] + dz * f)


def clip_to_box(p_outside, p_inside, x_lo, x_hi, z_lo, z_hi, margin=6.0):
    """Shorten a strut whose nominal endpoint (p_inside) sits inside a box -- e.g. a frame
    tube aimed at the crank centreline, which is naturally deep inside the engine case -- so
    it stops just outside the box's surface instead of tunnelling through the block. Finds the
    last point along the segment still outside the box by bisection, then backs off by margin."""
    def inside(t):
        x = p_outside[0] + (p_inside[0] - p_outside[0]) * t
        z = p_outside[1] + (p_inside[1] - p_outside[1]) * t
        return x_lo <= x <= x_hi and z_lo <= z <= z_hi
    if not inside(1.0):
        return p_inside
    lo, hi = 0.0, 1.0  # lo: outside the box, hi: inside the box
    for _ in range(40):
        mid = (lo + hi) / 2.0
        lo, hi = (lo, mid) if inside(mid) else (mid, hi)
    length = math.hypot(p_inside[0] - p_outside[0], p_inside[1] - p_outside[1])
    t_clip = max(lo - margin / length, 0.0)
    return (p_outside[0] + (p_inside[0] - p_outside[0]) * t_clip, p_outside[1] + (p_inside[1] - p_outside[1]) * t_clip)


axis_pt = along(front_axle, fw, -fork_offset)
crown = along(axis_pt, u, fork_length)
head_tube_bottom = along(crown, u, 15.0)
head_tube_top = along(head_tube_bottom, u, head_tube_len)
stem_top = along(head_tube_top, u, 40.0)
bar_dir = (0.30, 0.95)
bar_c = (stem_top[0] + bar_dir[0] * 90.0, stem_top[1] + bar_dir[1] * 90.0)

crank_c = (620.0, 300.0)                 # engine crank centreline (X,Z); all 4 bores share it
swingarm_pivot = (430.0, 260.0)
seat_top = (310.0, 800.0)
countershaft_c = (560.0, 260.0)

frame_r, swing_r, fork_tube_r = 17.0, 16.0, 17.0

drive_y = 95.0                            # final-drive chain lateral offset
cyl_pitch = 78.0
cyl_ys = [-1.5 * cyl_pitch, -0.5 * cyl_pitch, 0.5 * cyl_pitch, 1.5 * cyl_pitch]  # 1,2,3,4
cyl_phase = [0.0, 180.0, 180.0, 0.0]       # standard flat/180 inline-4 crank

# Case box bounds, computed once up front (before the case solid itself exists) so both the
# frame and the exhaust routing can clip against the same numbers instead of aiming at the
# crank centreline / drifting through the block by coincidence of waypoint placement.
case_half_y = cyl_ys[-1] + 42.0
case_x_min, case_x_max = crank_c[0] - 120.0, crank_c[0] + 100.0
case_z_min, case_z_max = crank_c[1] - 125.0, crank_c[1] + 45.0
bore_r, cyl_outer_r = 32.0, 45.0
THROW, ROD = 31.0, 115.0                   # stroke 62 mm, rod ratio 3.7
THETA0 = 70.0                              # initial crank angle, deg (matches rc35 convention)

chain_pitch = 15.875                       # 5/8" motorcycle chain
front_sprocket_teeth, rear_sprocket_teeth = 17, 43
sprocket_w, tooth_h, tooth_w = 8.0, 2.2, 3.2
belt_thickness = 3.0

engine_turns = 6.0                         # 3 complete 4-stroke cycles
gearbox_ratio = 2.57                       # unmodelled primary+top-gear reduction
duration = 6.0
n_time = 180

# ---------------------------------------------------------------- colours
paint = cq.Color(0.05, 0.08, 0.28)
black = cq.Color(0.07, 0.07, 0.08)
rubber = cq.Color(0.12, 0.12, 0.13)
alloy = cq.Color(0.74, 0.76, 0.79)
steel = cq.Color(0.5, 0.52, 0.55)
chrome = cq.Color(0.82, 0.84, 0.86)
chain_col = cq.Color(0.35, 0.35, 0.37)
gold = cq.Color(0.85, 0.7, 0.15)
lens = cq.Color(0.85, 0.85, 0.6)

# ---------------------------------------------------------------- helpers


def vec(p):
    return cq.Vector(*p)


def p3(p, y=0.0):
    return (p[0], y, p[1])


def tube(p0, p1, r):
    v0, v1 = vec(p0), vec(p1)
    d = v1 - v0
    length = d.Length
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, length, v0, cq.Vector(d.x / length, d.y / length, d.z / length)))


def cyl_y(r, y0, y1, x, z):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r, y1 - y0, cq.Vector(x, y0, z), cq.Vector(0, 1, 0)))


def ring_y(ro, ri, y0, y1, x, z):
    return cyl_y(ro, y0, y1, x, z).cut(cyl_y(ri, y0 - 1.0, y1 + 1.0, x, z))


def axial_ring(centre, d, half_len, ro, ri):
    outer = tube(p3(along(centre, d, -half_len)), p3(along(centre, d, half_len)), ro)
    inner = tube(p3(along(centre, d, -half_len - 1.0)), p3(along(centre, d, half_len + 1.0)), ri)
    return outer.cut(inner)


def box(sx, sy, sz, c):
    return cq.Workplane("XY").box(sx, sy, sz).translate(c)


def sweep_tube(points, r, tangents=None):
    pts = [vec(p) for p in points]
    if tangents is None:
        path = cq.Workplane("XY").spline(pts, includeCurrent=False)
    else:
        path = cq.Workplane("XY").spline(pts, tangents=[vec(t) for t in tangents], includeCurrent=False)
    t0 = (pts[1] - pts[0]).normalized()
    ref = cq.Vector(0, 0, 1) if abs(t0.z) < 0.9 else cq.Vector(1, 0, 0)
    xd = t0.cross(ref).normalized()
    return cq.Workplane(cq.Plane(origin=pts[0], xDir=xd, normal=t0)).circle(r).sweep(path, transition="round")


def poly_tube(points, r):
    """Straight tube segments joined by ball fillets at each waypoint -- unlike sweep_tube's
    spline, this cannot overshoot past its control points: a spline pinned only at its two end
    tangents is free to balloon far outside the waypoints' own bounding box wherever the path
    reverses direction (the exhaust routing's spline here ended up spanning Z from -170 to +795,
    a ~1000 mm bulge nothing in the waypoints asked for, silently sweeping through the tank/
    seat/chain-drive area). A polyline of exact cylinders has no such freedom.
    """
    shape = None
    for p0, p1 in zip(points[:-1], points[1:]):
        seg = tube(p0, p1, r)
        shape = seg if shape is None else shape.union(seg)
    for p in points[1:-1]:
        ball = cq.Workplane(obj=cq.Solid.makeSphere(r, vec(p)))
        shape = shape.union(ball)
    return shape


def ry_of_heading(phi):
    return -math.degrees(phi)


def fender(cx, cz, r_out, r_in, width, a0_deg, a1_deg, n=20):
    pts = [(cx + r_out * math.cos(math.radians(a0_deg + (a1_deg - a0_deg) * i / n)),
            cz + r_out * math.sin(math.radians(a0_deg + (a1_deg - a0_deg) * i / n))) for i in range(n + 1)]
    pts += [(cx + r_in * math.cos(math.radians(a1_deg - (a1_deg - a0_deg) * i / n)),
             cz + r_in * math.sin(math.radians(a1_deg - (a1_deg - a0_deg) * i / n))) for i in range(n + 1)]
    # Workplane("XZ") extrudes along its normal, -Y, giving [-width, 0] before centering --
    # translating by -width/2 (as if extrude ran +Y) actually pushes the whole fender to one
    # side ([-1.5*width, -0.5*width]) instead of straddling the wheel's centreline; +width/2
    # is the correct recentring for a -Y extrude.
    return cq.Workplane("XZ").polyline(pts).close().extrude(width).translate((0, width / 2.0, 0))


# -------------------------------------------------- validated belt/chain math
def belt_path(ra, ca, rb, cb, d):
    """Identical to examples/timing_belt.py -- CLAUDE.md's external-tangent standard."""
    gamma = math.degrees(math.acos((ra - rb) / d))

    def m(sign):
        a = math.radians(sign * gamma)
        return (math.cos(a), math.sin(a))

    m_up, m_lo = m(1.0), m(-1.0)
    t1_up = (ca[0] + ra * m_up[0], ca[1] + ra * m_up[1])
    t2_up = (cb[0] + rb * m_up[0], cb[1] + rb * m_up[1])
    t1_lo = (ca[0] + ra * m_lo[0], ca[1] + ra * m_lo[1])
    t2_lo = (cb[0] + rb * m_lo[0], cb[1] + rb * m_lo[1])
    ls = math.hypot(t2_up[0] - t1_up[0], t2_up[1] - t1_up[1])
    arc_b_deg, arc_a_deg = 2.0 * gamma, 360.0 - 2.0 * gamma
    arc_b_len, arc_a_len = math.radians(arc_b_deg) * rb, math.radians(arc_a_deg) * ra
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
    d = math.hypot(cb[0] - ca[0], cb[1] - ca[1])
    theta = math.atan2(cb[1] - ca[1], cb[0] - ca[0])
    point_local, total_len = belt_path(ra, (0.0, 0.0), rb, (d, 0.0), d)
    ct, st = math.cos(theta), math.sin(theta)

    def point_world(s):
        lx, ly = point_local(s)
        return (ca[0] + lx * ct - ly * st, ca[1] + lx * st + ly * ct)

    return point_world, total_len


def pitch_radius(teeth):
    return chain_pitch / (2.0 * math.sin(math.pi / teeth))


def sprocket(teeth, width, inner_r, phase_deg=0.0):
    rp = pitch_radius(teeth)
    r_root, r_tip = rp - 5.0, rp + 4.5
    da = 2.0 * math.pi / teeth
    pts = []
    for i in range(teeth):
        a0 = da * i
        for f, r in ((0.25, r_root), (0.42, r_tip), (0.58, r_tip), (0.75, r_root)):
            a = a0 + f * da
            pts.append((r * math.cos(a), r * math.sin(a)))
    body = cq.Workplane("XZ").polyline(pts).close().extrude(width).translate((0, width / 2.0, 0))
    body = body.cut(cyl_y(inner_r, -width, width, 0, 0))
    if phase_deg:
        body = body.rotate((0, 0, 0), (0, 1, 0), phase_deg)
    return body


# =================================================================== frame
cad_step(steps[0])  # noqa: F821 - injected by cad_workbench.runner
frame = ring_y(24.0, 16.0, -36.0, 36.0, crank_c[0], crank_c[1])                # crankcase cradle collar
# The down tube and lower rail nominally aim at the crank centreline (crank_c), which sits
# deep inside the engine case -- clip each to stop just outside the case box instead of
# running a full-radius tube through the block (see clip_to_box).
down_tube_tip = clip_to_box(head_tube_bottom, crank_c, case_x_min, case_x_max, case_z_min, case_z_max)
lower_rail_tip = clip_to_box(swingarm_pivot, crank_c, case_x_min, case_x_max, case_z_min, case_z_max)
frame = frame.union(tube(p3(head_tube_bottom), p3(down_tube_tip), frame_r))    # down tube
frame = frame.union(tube(p3(swingarm_pivot), p3(lower_rail_tip), frame_r))     # lower rail (cradle underside)
frame = frame.union(tube(p3(head_tube_top), p3(seat_top), frame_r))            # top rail / backbone
frame = frame.union(tube(p3(seat_top), p3(swingarm_pivot), frame_r * 0.75))    # seat stay, closes the triangle
frame = frame.union(tube(p3(head_tube_bottom), p3(head_tube_top), frame_r * 1.05))  # steering head
for t0 in (0.0, head_tube_len):
    p_lo = along(head_tube_bottom, u, t0)
    frame = frame.union(tube(p3(p_lo), p3(along(p_lo, u, 8.0)), 24.0))         # headset cups
frame = frame.cut(tube(p3(along(head_tube_bottom, u, -5.0)), p3(along(head_tube_top, u, 5.0)), 18.5))  # steerer bore

# swingarm, one side + a cross-tube, matching the "whole strut clears the wheel, not just its
# tip" standard: build the wheel-side end at a lateral offset (like a real single/box-section
# arm) rather than a single centreline tube through the rim.
# Clearance must be measured against the TYRE's cross-section (its torus minor radius,
# tire_minor_r) not the narrower rim width -- and the tube's own radius then further eats into
# that clearance from its centreline, so it must be subtracted too, not just added as if the
# tube had zero thickness.
swing_y = tire_minor_r + swing_r + 8.0
rear_hub_clear = 24.0 + swing_r + 5.0
swing_tip = pull_back(swingarm_pivot, rear_axle, rear_hub_clear)
swingarm = tube((swingarm_pivot[0], -swing_y, swingarm_pivot[1]), (swing_tip[0], -swing_y, swing_tip[1]), swing_r)
swingarm = swingarm.union(tube((swingarm_pivot[0], swing_y, swingarm_pivot[1]), (swing_tip[0], swing_y, swing_tip[1]), swing_r))
swingarm = swingarm.union(tube((swingarm_pivot[0], -swing_y, swingarm_pivot[1]), (swingarm_pivot[0], swing_y, swingarm_pivot[1]), swing_r * 0.7))
frame = frame.union(swingarm)

# ================================================= fork, bars, light, fenders
cad_step(steps[1])  # noqa: F821 - injected by cad_workbench.runner
fork_y = tire_minor_f + fork_tube_r + 8.0   # see swing_y: clear the tyre's cross-section, minus the tube's own radius
front_hub_clear = 9.0 + fork_tube_r + 20.0
fork_tip = pull_back(crown, front_axle, front_hub_clear)
fork = None
for side in (-1.0, 1.0):
    blade = tube((crown[0], side * fork_y, crown[1]), (fork_tip[0], side * fork_y, fork_tip[1]), fork_tube_r)
    slider = tube((crown[0], side * fork_y, crown[1] - 40.0), (crown[0], side * fork_y, crown[1] + 90.0), fork_tube_r + 4.0)
    fork = blade.union(slider) if fork is None else fork.union(blade).union(slider)
    # bore must clear the front_hub axle stub (radius 9.0, see front_hub below), not just fit a
    # nominal 5.5 mm bolt -- a narrower bore lets the stub itself poke through the dropout.
    fork = fork.union(ring_y(20.0, 10.0, side * fork_y - 3.0, side * fork_y + 3.0, front_axle[0], front_axle[1]))
# A real triple clamp is two plates straddling the *whole* head tube -- the lower one down at
# the crown (axle end of the steerer, below the head tube) and the upper one above the head
# tube near the stem, not both crammed into the ~15 mm gap between crown and head_tube_bottom
# where the frame's down tube and steering-head tube already meet. Put triple_bottom at crown
# (below the head tube) and triple_top up past head_tube_top, in the stem's own clear stretch.
triple_bottom = box(150.0, 30.0, 16.0, p3(along(crown, u, -80.0)))
triple_top_c = along(stem_top, u, -15.0)
triple_top = box(160.0, 34.0, 20.0, p3(triple_top_c))
fork = fork.union(triple_top).union(triple_bottom)
# The steerer proper only needs to fill the frame's own bore (head_tube_bottom-5 to
# head_tube_top+5, matching the cut below); past that it's just the stem shaft, which is
# narrower in real forks and must not compete for space with the top_rail welded at
# head_tube_top itself.
fork = fork.union(tube(p3(along(head_tube_bottom, u, -5.0)), p3(along(head_tube_top, u, 5.0)), 17.0))
fork = fork.union(tube(p3(along(head_tube_top, u, 20.0)), p3(stem_top), 11.0))

bar_half = [(0, 0, 0), (0, 60, 6), (0, 150, 22), (30, 210, 30), (60, 230, 26)]
handlebar = sweep_tube([(bar_c[0] + x, y, bar_c[1] + z) for x, y, z in bar_half], 13.0, tangents=[(0, 1, 0), (1, 0.3, 0)])
handlebar = handlebar.union(sweep_tube([(bar_c[0] + x, -y, bar_c[1] + z) for x, y, z in bar_half], 13.0, tangents=[(0, -1, 0), (1, -0.3, 0)]))
handlebar = handlebar.union(tube((bar_c[0], -230.0, bar_c[1] + 26.0), (bar_c[0], 230.0, bar_c[1] + 26.0), 13.0))
mirrors = None
for side in (-1.0, 1.0):
    stalk = tube((bar_c[0] - 20.0, side * 210.0, bar_c[1] + 40.0), (bar_c[0] - 90.0, side * 250.0, bar_c[1] + 130.0), 5.0)
    y_lo, y_hi = min(side * 244.0, side * 256.0), max(side * 244.0, side * 256.0)
    head = cyl_y(28.0, y_lo, y_hi, bar_c[0] - 92.0, bar_c[1] + 132.0)
    mirrors = stalk.union(head) if mirrors is None else mirrors.union(stalk).union(head)

# A real headlight sits well forward of the steering head, held out on its own bracket -- the
# original "-40" nudge here pulled it *back* toward the head tube instead, landing it almost
# on top of the tank behind the head tube. Push it forward past the fork crown instead.
headlight_c = along(head_tube_top, u, -30.0)
headlight_c = (headlight_c[0] + 160.0, headlight_c[1])
headlight = cyl_y(95.0, -55.0, 55.0, headlight_c[0], headlight_c[1])
headlight = headlight.cut(cyl_y(80.0, -70.0, -40.0, headlight_c[0] - 25.0, headlight_c[1]))
headlight_lens = cyl_y(80.0, -42.0, -40.0, headlight_c[0] - 25.0, headlight_c[1])
bracket = tube((head_tube_top[0], -50.0, head_tube_top[1] - 20.0), (headlight_c[0], -50.0, headlight_c[1]), 9.0)
bracket = bracket.union(tube((head_tube_top[0], 50.0, head_tube_top[1] - 20.0), (headlight_c[0], 50.0, headlight_c[1]), 9.0))
instrument = cyl_y(45.0, -20.0, 20.0, stem_top[0] - 15.0, stem_top[1] + 30.0)

front_fender = fender(front_axle[0], front_axle[1], wheel_front_r + 16.0, wheel_front_r + 6.0, front_rim_w + 20.0, 25.0, 165.0)
rear_fender = fender(rear_axle[0], rear_axle[1], wheel_rear_r + 15.0, wheel_rear_r + 6.0, rear_rim_w + 16.0, 55.0, 165.0)
# The stay's nominal lower end (near the axle) was aimed well inside the tire's own radius --
# pull it back to stop just outside the tire's silhouette instead, the same fix as the fork/
# swingarm-vs-hub struts above.
stay_from = (seat_top[0] - 20.0, seat_top[1] - 10.0)
stay_to = pull_back(stay_from, rear_axle, wheel_rear_r + 20.0)
rear_fender = rear_fender.union(tube((stay_from[0], 0.0, stay_from[1]), (stay_to[0], 0.0, stay_to[1]), 8.0))

# ============================================== tank, seat, footpegs
cad_step(steps[2])  # noqa: F821 - injected by cad_workbench.runner
# Position the tank along the top rail (backbone), not "up the fork axis" from head_tube_top --
# u points mostly vertical (toward the headlight/handlebar zone), so offsetting along it put the
# tank's nose up near the instrument cluster instead of back along the backbone where a real
# tank sits. Rail_dir runs from head_tube_top to seat_top; front_dist/height place the tank
# along and above that rail, clear of the handlebar/instrument/fork cluster near the head tube.
rail_len = math.hypot(seat_top[0] - head_tube_top[0], seat_top[1] - head_tube_top[1])
rail_dir = ((seat_top[0] - head_tube_top[0]) / rail_len, (seat_top[1] - head_tube_top[1]) / rail_len)
tank_front_c = along(head_tube_top, rail_dir, 180.0)
tank_rear_c = seat_top
tank = cq.Workplane("XY").workplane(offset=tank_front_c[1] - 15.0).center(tank_front_c[0] - 40.0, 0.0)
tank = tank.rect(160.0, 340.0).workplane(offset=70.0).center(0.0, 0.0).rect(220.0, 300.0)
tank = tank.workplane(offset=70.0).center(-80.0, 0.0).rect(120.0, 210.0).loft(combine=True)
# Real tanks tunnel over the backbone tube rather than burying it in solid tank material.
tank = tank.cut(tube(p3(head_tube_top), p3(seat_top), frame_r + 4.0))

saddle_pts = [(190, 0), (150, 60), (60, 95), (-40, 100), (-150, 90), (-220, 55), (-235, 0),
              (-220, -55), (-150, -90), (-40, -100), (60, -95), (150, -60)]
seat = cq.Workplane("XY").spline(saddle_pts, periodic=True).close().extrude(60.0)
seat = seat.translate((seat_top[0] - 40.0, 0.0, seat_top[1] + 20.0))
seat = seat.edges(">Z").fillet(14.0)

peg_y = 200.0
footpegs = None
for side in (-1.0, 1.0):
    p0 = (crank_c[0] - 30.0, side * (peg_y - 60.0), crank_c[1] - 40.0)
    p1 = (crank_c[0] - 30.0, side * peg_y, crank_c[1] - 60.0)
    peg = tube(p0, p1, 8.0).union(tube(p1, (p1[0], p1[1] + side * 55.0, p1[2]), 9.0))
    footpegs = peg if footpegs is None else footpegs.union(peg)

# ======================================================== wheels & brakes
cad_step(steps[3])  # noqa: F821 - injected by cad_workbench.runner


def tire_wheel(axle, wheel_r, rim_out, rim_in, rim_w, tire_minor):
    tire = cq.Workplane(obj=cq.Solid.makeTorus(wheel_r - tire_minor, tire_minor, cq.Vector(*p3(axle)), cq.Vector(0, 1, 0)))
    rim = ring_y(rim_out, rim_in, -rim_w / 2.0, rim_w / 2.0, axle[0], axle[1])
    return tire, rim


front_tire, front_rim = tire_wheel((0.0, 0.0), wheel_front_r, front_rim_out, front_rim_in, front_rim_w, tire_minor_f)
rear_tire, rear_rim = tire_wheel((0.0, 0.0), wheel_rear_r, rear_rim_out, rear_rim_in, rear_rim_w, tire_minor_r)


def spokes(axle, flange_ys, flange_r, rim_in, n=20):
    out = []
    per_side = n // 2
    for k in range(per_side):
        for side_i, fy in enumerate(flange_ys):
            sign = 1.0 if fy > 0 else -1.0
            a = math.radians(360.0 * k / per_side + (180.0 / per_side if side_i else 0.0))
            d = 1.0 if k % 2 == 0 else -1.0
            a_rim = a + d * math.radians(4.0 * 360.0 / n)
            rf = flange_r + 1.4
            out.append(tube((rf * math.cos(a), fy + sign * 2.0 * d, rf * math.sin(a)),
                             ((rim_in - 0.5) * math.cos(a_rim), 0.0, (rim_in - 0.5) * math.sin(a_rim)), 1.3))
    return out


front_hub = cyl_y(26.0, -34.0, 34.0, 0, 0)
front_hub = front_hub.union(cyl_y(38.0, -30.0, -22.0, 0, 0)).union(cyl_y(38.0, 22.0, 30.0, 0, 0))
front_hub = front_hub.union(cyl_y(9.0, -78.0, 78.0, 0, 0))
front_disc = ring_y(150.0, 60.0, 40.0, 46.0, 0, 0)
for k in range(6):
    a = math.radians(60.0 * k)
    front_disc = front_disc.cut(cyl_y(12.0, 39.0, 47.0, 105.0 * math.cos(a), 105.0 * math.sin(a)))
front_caliper = box(30.0, 55.0, 70.0, (105.0, 43.0, 0.0))
front_spokes = spokes(front_axle, (-30.0, 30.0), 26.0, front_rim_in, 20)

rear_hub = cyl_y(60.0, -40.0, 24.0, 0, 0)                                      # brake drum body
rear_hub = rear_hub.union(cyl_y(24.0, -60.0, 40.0, 0, 0))
rear_hub = rear_hub.union(cyl_y(9.0, -70.0, 70.0, 0, 0))
rear_spokes = spokes(rear_axle, (-28.0, 20.0), 34.0, rear_rim_in, 20)

# ============================================ engine block, cylinders, exhaust
cad_step(steps[4])  # noqa: F821 - injected by cad_workbench.runner
crank_bore_r = 18.0 + THROW + 14.0 + 3.0
case = box(220.0, 2.0 * case_half_y, 170.0, (crank_c[0] - 10.0, 0.0, crank_c[1] - 40.0))
# No extra "boss" cylinder around the bore: a cyl_y() boss is a full disc at every Y in its
# range, unbounded by the box's own Z-limits, so it would form a solid annulus (bore_r to
# bore_r+20) that the connecting rod -- which legitimately swings out to ~57mm from the crank
# axis on its way up to the piston -- swept straight through. The box's own bulk around the
# cut is enough.
case = case.cut(cyl_y(crank_bore_r, -case_half_y - 1.0, case_half_y + 1.0, crank_c[0], crank_c[1]))
case = case.union(box(140.0, 2.0 * case_half_y, 90.0, (crank_c[0] - 60.0, 0.0, crank_c[1] - 150.0)))       # sump
# The countershaft sprocket sits at (countershaft_c, drive_y) -- inside the case's own X/Z/Y
# footprint by construction (the internal gearbox lives there), so without a clearance bore the
# case's solid material simply buries the whole sprocket. A real case has the output shaft pass
# through a bore/bearing to the sprocket outside; cut one sized to the sprocket's tip radius.
countershaft_bore_r = pitch_radius(front_sprocket_teeth) + 4.5 + 40.0
case = case.cut(cyl_y(countershaft_bore_r, -case_half_y - 1.0, case_half_y + 1.0, countershaft_c[0], countershaft_c[1]))
clutch_cover = cyl_y(70.0, case_half_y, case_half_y + 26.0, crank_c[0] - 30.0, crank_c[1] + 20.0)

cyl_top = crank_c[1] + 170.0
cyl_bottom = crank_c[1] + 55.0
cylinder_block = None
cylinder_heads = None
for cy in cyl_ys:
    # barrel + head are Z-axis (vertical, the bore direction) cylinders at this cylinder's own
    # Y -- NOT cyl_y() (a Y-axis/crank-axis helper), which would lay them on their side.
    barrel = tube((crank_c[0], cy, cyl_bottom), (crank_c[0], cy, cyl_top), cyl_outer_r)
    barrel = barrel.cut(tube((crank_c[0], cy, cyl_bottom - 1.0), (crank_c[0], cy, cyl_top + 1.0), bore_r))
    cylinder_block = barrel if cylinder_block is None else cylinder_block.union(barrel)
    head = tube((crank_c[0], cy, cyl_top), (crank_c[0], cy, cyl_top + 24.0), cyl_outer_r + 6.0)
    head = head.union(tube((crank_c[0], cy, cyl_top + 24.0), (crank_c[0], cy, cyl_top + 58.0), cyl_outer_r - 8.0))
    cylinder_heads = head if cylinder_heads is None else cylinder_heads.union(head)

carbs = None
for cy in cyl_ys:
    c = cyl_y(15.0, cy - 20.0, cy + 20.0, crank_c[0] - cyl_outer_r - 30.0, cyl_top - 30.0)
    carbs = c if carbs is None else carbs.union(c)
# Sized/positioned to clear the cylinder block and heads in X (the box was wide enough that its
# forward edge reached back into the block's own footprint) and to duck under the seat stay,
# which otherwise runs straight through this box's interior on its way to the swingarm pivot.
airbox = box(200.0, 2.0 * case_half_y - 20.0, 70.0, (crank_c[0] - cyl_outer_r - 150.0, 0.0, cyl_top - 10.0))
airbox = airbox.cut(tube(p3(seat_top), p3(swingarm_pivot), frame_r * 0.75 + 4.0))

exhaust = None
mufflers = None
for i, cy in enumerate(cyl_ys):
    spread_y = cy * 2.8   # keeps even the inner-cylinder pipes outside the rear tire's ~50 mm half-width
    header_r = 19.0
    # Start outside the barrel's own outer surface, not inside it -- a start point still within
    # the barrel's radius buries the header's whole tube cross-section in cylinder_block material
    # (this is what a real exhaust port bore through the barrel wall would relieve).
    p0 = (crank_c[0] + cyl_outer_r + header_r + 3.0, cy, cyl_bottom + 15.0)
    # The case box spans X in [case_x_min, case_x_max] and Z in [case_z_min, case_z_max]; the
    # header must cross from the right side (X > case_x_max) to the left side (X < case_x_min)
    # to reach the rear wheel, and *while* X sits inside that band Z must already be below the
    # case's true lowest point -- which is the sump extension (bottom at crank_c[1]-150-45 =
    # crank_c[1]-195), not case_z_min (which only bounds the main block, not the sump hanging
    # below it). "z-190" cleared case_z_min but still clipped the sump's corner; z-230 clears
    # the sump itself with margin.
    p1 = (case_x_max + 60.0, cy, cyl_bottom + 15.0)             # stay high, clear of the case on the right
    p2 = (case_x_max + 140.0, cy * 0.6, crank_c[1])             # still clear right, begin drifting in Y
    p3_hdr = (case_x_max + 140.0, spread_y * 0.7, crank_c[1] - 230.0)  # drop below the sump while still clear right
    p3_pass = (case_x_min - 40.0, spread_y, crank_c[1] - 230.0)   # cross the case's X band while Z stays below the sump
    p4 = (rear_axle[0] + 260.0, spread_y, wheel_rear_r + 10.0)
    header = poly_tube([p0, p1, p2, p3_hdr, p3_pass, p4], header_r)
    # The inner cylinders' spread_y (2.8x) clears the rear tire but not the swingarm arm (which
    # reaches out to roughly tire_minor_r+swing_r) nor the rear sprocket sitting at drive_y --
    # cylinder 3 (cy=39) at +20 still overlapped the sprocket, since the sprocket's own radius
    # eats back into that gap more than a fixed 20 mm margin allows for. Push further out.
    muffler_y = spread_y + (40.0 if spread_y >= 0 else -40.0)
    muffler = tube((p4[0], muffler_y, p4[2]), (p4[0] - 330.0, muffler_y, p4[2] - 15.0), 44.0)
    exhaust = header if exhaust is None else exhaust.union(header)
    mufflers = muffler if mufflers is None else mufflers.union(muffler)

# ==================================================== final drive chain
cad_step(steps[5])  # noqa: F821 - injected by cad_workbench.runner
r_small = pitch_radius(front_sprocket_teeth)
r_big = pitch_radius(rear_sprocket_teeth)
belt_offset = tooth_h + belt_thickness / 2.0 + 0.2
point_center, belt_len = belt_path_oriented(r_small + belt_offset, countershaft_c, r_big + belt_offset, rear_axle)
half_t = belt_thickness / 2.0
point_outer, len_outer = belt_path_oriented(r_small + belt_offset + half_t, countershaft_c, r_big + belt_offset + half_t, rear_axle)
point_inner, len_inner = belt_path_oriented(r_small + belt_offset - half_t, countershaft_c, r_big + belt_offset - half_t, rear_axle)
n_belt_samples = 220
outer_pts = [point_outer(len_outer * i / n_belt_samples) for i in range(n_belt_samples)]
inner_pts = [point_inner(len_inner * i / n_belt_samples) for i in range(n_belt_samples)]
chain_outer = cq.Workplane("XZ").polyline(outer_pts).close().extrude(sprocket_w)
chain_inner = cq.Workplane("XZ").polyline(inner_pts).close().extrude(sprocket_w)
chain_body = chain_outer.cut(chain_inner).translate((0, drive_y - sprocket_w / 2.0, 0))

marker_r = tooth_h + half_t + 1.6 + 0.3
point_marker, marker_len = belt_path_oriented(r_small + marker_r, countershaft_c, r_big + marker_r, rear_axle)
n_markers = max(10, round(belt_len / 28.0))
marker_s0 = [belt_len * i / n_markers for i in range(n_markers)]
marker_shape = cq.Workplane("XZ").circle(1.6).extrude(sprocket_w * 0.9).translate((0, -sprocket_w * 0.45, 0))
chain_markers = cq.Assembly(name="chain_markers")
for idx, s0 in enumerate(marker_s0):
    x0, z0 = point_marker(s0 / belt_len * marker_len)
    chain_markers.add(marker_shape, name=f"m_{idx:02d}", loc=cq.Location(cq.Vector(x0, drive_y, z0)), color=gold)

front_sprocket_shape = sprocket(front_sprocket_teeth, sprocket_w, 24.0)
rear_sprocket_shape = sprocket(rear_sprocket_teeth, sprocket_w, 40.0)

# ================================================================= assembly
static = cq.Assembly(name="static")
for name, shape, col in [
    ("frame", frame, paint), ("fork", fork, chrome), ("handlebar", handlebar, black), ("mirrors", mirrors, chrome),
    ("headlight", headlight, black), ("headlight_lens", headlight_lens, lens), ("headlight_bracket", bracket, chrome),
    ("instrument", instrument, black), ("front_fender", front_fender, paint), ("rear_fender", rear_fender, paint),
    ("tank", tank, paint), ("seat", seat, black), ("footpegs", footpegs, alloy),
    ("case", case, alloy), ("clutch_cover", clutch_cover, alloy), ("cylinder_block", cylinder_block, alloy),
    ("cylinder_heads", cylinder_heads, alloy), ("carbs", carbs, steel), ("airbox", airbox, black),
    ("exhaust", exhaust, chrome), ("mufflers", mufflers, chrome), ("chain_body", chain_body, chain_col),
    ("front_disc", front_disc.translate((front_axle[0], 0, front_axle[1])), steel),
    ("front_caliper", front_caliper.translate((front_axle[0], 0, front_axle[1])), alloy),
]:
    static.add(shape, name=name, color=col)

crank_group_shapes = []
piston_groups = []
rod_groups = []
init_state = []
for i, (cy, phase) in enumerate(zip(cyl_ys, cyl_phase)):
    t0 = math.radians(THETA0 + phase)
    px0 = THROW * math.sin(t0)
    pz0 = THROW * math.cos(t0)
    h0 = pz0 + math.sqrt(ROD * ROD - px0 * px0)
    alpha0 = -math.degrees(math.asin(px0 / ROD))
    init_state.append((phase, px0, pz0, h0, alpha0))

web_disk_r = THROW + 14.0 + 3.0   # a full disc this size encloses the pin at every rotation angle,
                                   # so no separate centre-to-pin connector web is needed -- an earlier
                                   # version used a fat radius-24 tube for that, whose cross-section (a
                                   # disc perpendicular to a Y=const axis) bulged +-24mm in Y right into
                                   # the rod's own Y-span.
# The main journal must NOT be one continuous bar the full engine width: a real crankshaft's
# journal is interrupted at each throw, and a rod legitimately swings within ~18mm of the crank
# axis (near tt=180 deg) at its own cylinder's Y -- a continuous journal there is solid material
# occupying exactly the space the rod needs, a permanent collision an earlier version of this file
# had at every delta near tt=180. Build the journal only in the gaps between cylinders.
journal_bounds = [-case_half_y + 12.0] + [y for cy in cyl_ys for y in (cy - 15.0, cy + 15.0)] + [case_half_y - 12.0]
crank_solid = None
for k in range(0, len(journal_bounds), 2):
    seg = cyl_y(18.0, journal_bounds[k], journal_bounds[k + 1], 0.0, 0.0)
    crank_solid = seg if crank_solid is None else crank_solid.union(seg)
for cy, (phase, px0, pz0, h0, alpha0) in zip(cyl_ys, init_state):
    pin = cyl_y(14.0, cy - 15.0, cy + 15.0, px0, pz0)
    web_a = cyl_y(web_disk_r, cy - 15.0, cy - 9.0, 0.0, 0.0)
    web_b = cyl_y(web_disk_r, cy + 9.0, cy + 15.0, 0.0, 0.0)
    crank_solid = crank_solid.union(pin).union(web_a).union(web_b)
# No extra pre-rotation here: each throw above is already built directly at its own initial
# angle (THETA0 + that cylinder's phase), so this shape's angle already equals the piston/rod
# formulas' value at delta=0. An earlier version also rotated the whole thing by -THETA0,
# which cancelled that baked-in angle and made the crank trace phase+delta instead of
# THETA0+phase+delta -- caught by the rod permanently overlapping the wrong point on the pin's
# swept circle (varying overlap volume across delta, instead of the constant "big end always
# surrounds the pin" overlap that's actually correct).

crank_group = cq.Assembly(name="crank_group")
crank_group.add(crank_solid, name="crankshaft", color=steel)

piston_shape = tube((0.0, 0.0, -25.0), (0.0, 0.0, 25.0), bore_r - 0.4)   # solid, Z-axis, clearance-fit in the bore
piston_shape = piston_shape.cut(cyl_y(6.0, -14.0, 14.0, 0.0, 0.0))       # wrist-pin hole through the mid-height, Y-axis
for i, (cy, (phase, px0, pz0, h0, alpha0)) in enumerate(zip(cyl_ys, init_state)):
    piston_top = cq.Assembly(name=f"piston_translation_{i}")
    piston_top.add(piston_shape, name=f"piston_{i}", color=alloy)
    piston_groups.append((piston_top, h0))

    # Built at LOCAL Y=0 -- the parent rod_pivot_translation's own loc below already supplies
    # this cylinder's Y (cy); adding cy again here would double the lateral offset.
    rod_local = tube((0.0, 0.0, 0.0), (0.0, 0.0, ROD), 9.0)
    rod_local = rod_local.union(cyl_y(15.0, -8.0, 8.0, 0.0, 0.0)).cut(cyl_y(14.3, -9.0, 9.0, 0.0, 0.0))  # big end wraps the pin
    rod_local = rod_local.union(cyl_y(13.0, -7.0, 7.0, 0.0, ROD))
    rod_angle_grp = cq.Assembly(name=f"rod_angle_{i}")
    rod_angle_grp.add(rod_local, name="rod", loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), alpha0), color=chrome)
    rod_top = cq.Assembly(name=f"rod_pivot_translation_{i}")
    rod_top.add(rod_angle_grp, name=f"rod_angle_{i}", loc=cq.Location(cq.Vector(0, 0, 0)))
    rod_groups.append((rod_top, px0, pz0, alpha0))

result = cq.Assembly(name="cb750")
result.add(static, name="static")
result.add(crank_group, name="crank_group", loc=cq.Location(cq.Vector(crank_c[0], 0.0, crank_c[1])))
for i, (piston_top, h0) in enumerate(piston_groups):
    result.add(piston_top, name=f"piston_translation_{i}", loc=cq.Location(cq.Vector(crank_c[0], cyl_ys[i], crank_c[1] + h0)))
for i, (rod_top, px0, pz0, alpha0) in enumerate(rod_groups):
    result.add(rod_top, name=f"rod_pivot_translation_{i}", loc=cq.Location(cq.Vector(crank_c[0] + px0, cyl_ys[i], crank_c[1] + pz0)))

front_wheel = cq.Assembly(name="front_wheel")
for name, shape, col in [("tire", front_tire, rubber), ("rim", front_rim, black), ("hub", front_hub, alloy)]:
    front_wheel.add(shape, name=name, color=col)
for i, sp in enumerate(front_spokes):
    front_wheel.add(sp, name=f"spoke_{i:02d}", color=chrome)

rear_wheel = cq.Assembly(name="rear_wheel")
for name, shape, col in [("tire", rear_tire, rubber), ("rim", rear_rim, black), ("hub", rear_hub, alloy),
                          ("sprocket", rear_sprocket_shape.translate((0, drive_y, 0)), steel)]:
    rear_wheel.add(shape, name=name, color=col)
for i, sp in enumerate(rear_spokes):
    rear_wheel.add(sp, name=f"spoke_{i:02d}", color=chrome)

result.add(front_wheel, name="front_wheel", loc=cq.Location(cq.Vector(front_axle[0], 0.0, front_axle[1])))
result.add(rear_wheel, name="rear_wheel", loc=cq.Location(cq.Vector(rear_axle[0], 0.0, rear_axle[1])))
result.add(front_sprocket_shape, name="countershaft_sprocket", loc=cq.Location(cq.Vector(countershaft_c[0], drive_y, countershaft_c[1])), color=steel)
result.add(chain_markers, name="chain_markers")

# ================================================================ animation
cad_step(steps[6])  # noqa: F821 - injected by cad_workbench.runner
cad_step(steps[7])  # noqa: F821 - injected by cad_workbench.runner
omega_crank = 2.0 * math.pi * engine_turns / duration
v_chain = (omega_crank / gearbox_ratio) * r_small
omega_rear = v_chain / r_big
omega_front = omega_rear * wheel_rear_r / wheel_front_r
omega_countershaft = omega_crank / gearbox_ratio

times = [duration * i / n_time for i in range(n_time + 1)]
deg = math.degrees
animation = [
    {"path": "/cb750/crank_group", "action": "ry", "times": times, "values": [deg(omega_crank * t) for t in times]},
    {"path": "/cb750/countershaft_sprocket", "action": "ry", "times": times, "values": [-deg(omega_countershaft * t) for t in times]},
    {"path": "/cb750/rear_wheel", "action": "ry", "times": times, "values": [-deg(omega_rear * t) for t in times]},
    {"path": "/cb750/front_wheel", "action": "ry", "times": times, "values": [-deg(omega_front * t) for t in times]},
]
for i, (piston_top, h0) in enumerate(piston_groups):
    cy = cyl_ys[i]
    phase = cyl_phase[i]
    vals = []
    for t in times:
        tt = math.radians(THETA0 + phase) + omega_crank * t
        px = THROW * math.sin(tt)
        pz = THROW * math.cos(tt)
        h = pz + math.sqrt(ROD * ROD - px * px)
        vals.append(h - h0)
    animation.append({"path": f"/cb750/piston_translation_{i}", "action": "tz", "times": times, "values": vals})
for i, (rod_top, px0, pz0, alpha0) in enumerate(rod_groups):
    phase = cyl_phase[i]
    pos_vals = []
    ang_vals = []
    for t in times:
        tt = math.radians(THETA0 + phase) + omega_crank * t
        px = THROW * math.sin(tt)
        pz = THROW * math.cos(tt)
        alpha = -math.degrees(math.asin(px / ROD))
        pos_vals.append([px - px0, 0.0, pz - pz0])
        ang_vals.append(alpha - alpha0)
    animation.append({"path": f"/cb750/rod_pivot_translation_{i}", "action": "t", "times": times, "values": pos_vals})
    animation.append({"path": f"/cb750/rod_pivot_translation_{i}/rod_angle_{i}", "action": "ry", "times": times, "values": ang_vals})
for idx, s0 in enumerate(marker_s0):
    x0, z0 = point_marker(s0 / belt_len * marker_len)
    vals = []
    for t in times:
        frac = (s0 + v_chain * t) / belt_len
        x, z = point_marker(frac * marker_len)
        vals.append([x - x0, 0.0, z - z0])
    animation.append({"path": f"/cb750/chain_markers/m_{idx:02d}", "action": "t", "times": times, "values": vals})
