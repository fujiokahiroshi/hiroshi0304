"""Road bike (56cm, 700c) with a real roller chain, 50/34T crank and 11-speed cassette.

Realism targets, all in mm and based on production road-bike numbers:
  wheelbase 990, chainstay 410, BB drop 70, head angle 73 deg, seat angle
  73.5 deg, fork rake 45, axle-to-crown 365, head tube 150, drop bar 440 c-c.
World axes: X = forward, Y = lateral (+Y is the drive side), Z = up, ground at Z=0.

Drivetrain kinematics are exact rigid-body motion, not a marker approximation:
  * The chain is ~108 individual links (alternating inner/outer, 11-speed plate
    widths). Each link is placed by its two pin positions on a closed chain path
    built from directed tangent lines around four pitch circles -- chainring (CW),
    tension pulley (CW), guide pulley (CCW), cog (CW) -- and moves with a position
    track plus a heading track. Adjacent links share exact pin locations.
  * On each sprocket arc the path parameter advances one chain pitch per tooth
    angle (not per mm of arc), so pins land on consecutive tooth valleys exactly;
    the derailleur tension pulley is then iterated up/down until the closed path
    is an integer number of pitches -- which is literally its job on a real bike.
  * Every sprocket the chain touches is phase-rotated so a tooth valley sits under
    the first pin on its arc, so rollers stay in the valleys while it spins.
  * Wheel, cassette, crank and derailleur-pulley speeds all derive from one chain
    speed; rear wheel = crank * 50/19 exactly. Pedals counter-rotate to stay level.

Rotation sign: an `ry` of +90 deg maps +X onto -Z, so forward rolling and forward
pedaling are POSITIVE `ry`; a CW pitch circle in the (X,Z) plane rotates +ry.
"""

import math

import cadquery as cq

steps = [
    "フレーム主三角・BBシェル・ヘッドチューブ・ステー・ドロップアウト・ヘッドセットカップを一体化",
    "フォーク(クラウン・曲げブレード・ステアラー)、ステム、ドロップハンドル、ブレーキレバー",
    "サドル・シートポスト、前後キャリパーブレーキ、ケーブル、ボトル",
    "700cホイール(トーラスタイヤ・深リム・フランジ付ハブ・2クロス24本スポーク)と11段カセット",
    "チェーン経路(4円の有向接線)をテンションプーリー位置で整数ピッチに収束させ、クランク・変速機を生成",
    "全リンクをピン位置で配置し、各スプロケットの歯位相をチェーンに同期",
    "ペダリング→チェーン→カセット→後輪、前輪、プーリー、リンク並進+回転のアニメーション",
]

# ---------------------------------------------------------------- geometry
wheel_r = 336.0          # tire outer radius (700x25c)
tire_minor = 12.5
tire_major = wheel_r - tire_minor
rim_out, rim_in, rim_w = 311.0, 285.0, 20.0

rear_axle = (0.0, wheel_r)
front_axle = (990.0, wheel_r)
bb = (404.0, wheel_r - 70.0)

seat_angle = math.radians(73.5)
seat_dir = (-math.cos(seat_angle), math.sin(seat_angle))
seat_tube_top = (bb[0] + 540.0 * seat_dir[0], bb[1] + 540.0 * seat_dir[1])

head_angle = math.radians(73.0)
u = (-math.cos(head_angle), math.sin(head_angle))      # up the steering axis
fw = (math.sin(head_angle), math.cos(head_angle))      # forward, perpendicular to the axis
axis_pt = (front_axle[0] - 45.0 * fw[0], front_axle[1] - 45.0 * fw[1])   # 45 mm rake


def along(p, d, t):
    return (p[0] + d[0] * t, p[1] + d[1] * t)


crown = along(axis_pt, u, 365.0)
head_tube_bottom = along(crown, u, 13.0)
head_tube_top = along(head_tube_bottom, u, 150.0)
steerer_top = along(head_tube_top, u, 42.0)
stem_base = along(head_tube_top, u, 32.0)
stem_dir = (math.cos(math.radians(11.0)), math.sin(math.radians(11.0)))
stem_end = along(stem_base, stem_dir, 100.0)
bar_c = (stem_end[0], 0.0, stem_end[1])
dt_end = along(head_tube_bottom, u, 34.0)

seat_r, dt_r, ht_r, tt_r = 14.3, 16.0, 18.0, 14.0
chain_stay_tip = (36.0, 342.0)
seat_stay_tip = (-3.0, 350.0)
rear_drop_y, front_drop_y = 63.5, 49.5

post_r = 13.6
post_top = along(seat_tube_top, seat_dir, 190.0)
saddle_z = post_top[1] + 30.0

drive_y = 46.0              # 50T chainring centre plane (chainline)
small_ring_y = 40.0
crank_y0, crank_y1 = 54.0, 70.0
crank_len = 170.0
pedal_len = 62.0

chain_pitch = 12.7
front_teeth_big, front_teeth_small = 50, 34
cassette_teeth = [11, 12, 13, 14, 15, 17, 19, 21, 23, 25, 28]
cog_pitch_y = 3.74
cog_y0 = 57.0               # centre plane of the outermost (11T) cog
chain_cog_index = 6         # chain sits on the 19T
cog_w, ring_w = 1.6, 1.8


def pitch_radius(teeth):
    return chain_pitch / (2.0 * math.sin(math.pi / teeth))


def param_radius(teeth):
    """Radius whose circumference is exactly teeth*pitch: the arc-parameter scale."""
    return teeth * chain_pitch / (2.0 * math.pi)


r_big = pitch_radius(front_teeth_big)
cog_teeth = cassette_teeth[chain_cog_index]
r_cog = pitch_radius(cog_teeth)
r_pulley = pitch_radius(11)
y_cog = cog_y0 - chain_cog_index * cog_pitch_y
y_ring = drive_y
guide_c = (rear_axle[0] - 6.0, rear_axle[1] - r_cog - r_pulley - 12.0)

pedal_turns = 2.0
duration = 8.0
n_time = 160

# ---------------------------------------------------------------- colours
paint = cq.Color(0.72, 0.09, 0.12)
black = cq.Color(0.07, 0.07, 0.08)
rubber = cq.Color(0.12, 0.12, 0.13)
alloy = cq.Color(0.74, 0.76, 0.79)
steel = cq.Color(0.45, 0.47, 0.5)
chain_col = cq.Color(0.6, 0.62, 0.64)
white = cq.Color(0.93, 0.93, 0.9)
label_blue = cq.Color(0.1, 0.35, 0.75)

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
    """Ring whose axis is the 2-D direction d in the (X,Z) plane, centred on `centre`."""
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


def ry_of_heading(phi):
    """ry (deg) that points local +X along the (X,Z)-plane heading phi (rad)."""
    return -math.degrees(phi)


def sprocket(teeth, width, inner_r, phase_deg=0.0):
    """Roller-chain sprocket in the (X,Z) plane, axis Y, centred on Y=0.

    Tooth valleys are centred on angle 0 (+ k*360/N); root rp-4.5, tip rp+3.5, flanks
    sized so a 7.7 mm roller centred on the pitch circle clears them by ~0.6 mm.
    """
    rp = pitch_radius(teeth)
    r_root, r_tip = rp - 4.5, rp + 3.5
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


def unwrap(prev, ang):
    d = ang - prev
    while d > math.pi:
        d -= 2.0 * math.pi
    while d < -math.pi:
        d += 2.0 * math.pi
    return prev + d


# ---------------------------------------------------------------- chain path


def chain_path(circles):
    """Directed closed path around sprockets (cx, cz, r_pitch, s, teeth).

    s=+1 keeps the circle on the chain's left (CCW), s=-1 on its right (CW). Equal s on
    consecutive circles yields an external tangent, opposite s a crossing tangent, so the
    derailleur S-bend falls out of one formula. The path parameter is true length on the
    straight runs but teeth*pitch per revolution on the arcs, so one pitch of parameter
    equals one tooth angle. Returns point_at(param), total, and each arc's start param.
    """
    n = len(circles)
    tangents = []
    for i in range(n):
        c1x, c1z, r1, s1, _ = circles[i]
        c2x, c2z, r2, s2, _ = circles[(i + 1) % n]
        ex, ez = c2x - c1x, c2z - c1z
        d = math.hypot(ex, ez)
        ex, ez = ex / d, ez / d
        a = (s2 * r2 - s1 * r1) / d
        b = math.sqrt(max(0.0, 1.0 - a * a))
        nx, nz = a * ex - b * ez, a * ez + b * ex
        tangents.append(((c1x - s1 * r1 * nx, c1z - s1 * r1 * nz), (c2x - s2 * r2 * nx, c2z - s2 * r2 * nz)))

    segs = []
    arc_starts = []
    total = 0.0
    for i in range(n):
        cx, cz, r, s, teeth = circles[i]
        p_in = tangents[i - 1][1]
        p_out = tangents[i][0]
        a_in = math.atan2(p_in[1] - cz, p_in[0] - cx)
        a_out = math.atan2(p_out[1] - cz, p_out[0] - cx)
        sweep = (a_out - a_in) % (2.0 * math.pi) if s > 0 else (a_in - a_out) % (2.0 * math.pi)
        arc_starts.append(total)
        segs.append(("arc", total, param_radius(teeth) * sweep, cx, cz, r, s, a_in, sweep))
        total += param_radius(teeth) * sweep
        p1, p2 = tangents[i]
        ln = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segs.append(("line", total, ln, p1, p2))
        total += ln

    def point_at(s):
        s = s % total
        for seg in segs:
            if s <= seg[1] + seg[2]:
                f = (s - seg[1]) / seg[2]
                if seg[0] == "arc":
                    _, _, _, cx, cz, r, sg, a_in, sweep = seg
                    a = a_in + sg * f * sweep
                    return (cx + r * math.cos(a), cz + r * math.sin(a))
                _, _, _, p1, p2 = seg
                return (p1[0] + (p2[0] - p1[0]) * f, p1[1] + (p2[1] - p1[1]) * f)
        return point_at(0.0)

    return point_at, total, arc_starts


def chain_y(x):
    """Chainline skew: y_cog at the cog/derailleur (x<30), y_ring wherever a link's plates can
    still overlap the 50T teeth radially (x>365); the long ramp keeps consecutive links within
    the 0.5 mm plate clearance (0.43 mm/link)."""
    f = min(1.0, max(0.0, (x - 30.0) / 335.0))
    return y_cog + (y_ring - y_cog) * f


# =================================================================== frame
cad_step(steps[0])  # noqa: F821 - injected by cad_workbench.runner
frame = ring_y(20.0, 13.0, -34.0, 34.0, bb[0], bb[1])                       # BB shell
frame = frame.union(tube(p3(bb), p3(along(seat_tube_top, seat_dir, 20.0)), seat_r))
frame = frame.union(tube(p3(bb), p3(dt_end), dt_r))
frame = frame.union(tube(p3(seat_tube_top), p3(along(head_tube_top, u, -24.0)), tt_r))
frame = frame.union(tube(p3(head_tube_bottom), p3(head_tube_top), ht_r))
for side in (-1.0, 1.0):
    frame = frame.union(tube((bb[0], side * 23.0, bb[1]), (chain_stay_tip[0], side * 66.0, chain_stay_tip[1]), 7.0))
    frame = frame.union(tube((seat_tube_top[0], side * 12.0, seat_tube_top[1]), (seat_stay_tip[0], side * 66.0, seat_stay_tip[1]), 6.0))
    frame = frame.union(ring_y(15.0, 5.5, side * rear_drop_y - 3.0, side * rear_drop_y + 3.0, rear_axle[0], rear_axle[1]))
    frame = frame.union(box(30.0, 6.0, 14.0, (22.0, side * rear_drop_y, 340.0)))     # dropout tab to the chain stay
frame = frame.union(box(22.0, 4.0, 34.0, (-12.0, rear_drop_y + 5.0, 322.0)))          # derailleur hanger
bridge_t = (seat_tube_top[1] - 690.0) / (seat_tube_top[1] - seat_stay_tip[1])
bridge_x = seat_tube_top[0] + (seat_stay_tip[0] - seat_tube_top[0]) * bridge_t
bridge_y = 12.0 + (66.0 - 12.0) * bridge_t
frame = frame.union(tube((bridge_x, -bridge_y, 690.0), (bridge_x, bridge_y, 690.0), 5.0))
for t0 in (0.0, 142.0):                                                            # headset cups
    p_lo = along(head_tube_bottom, u, t0)
    frame = frame.union(tube(p3(p_lo), p3(along(p_lo, u, 8.0)), 19.5))
frame = frame.cut(tube(p3(along(head_tube_bottom, u, -5.0)), p3(along(head_tube_top, u, 5.0)), 15.0))       # steerer bore
frame = frame.cut(tube(p3(along(seat_tube_top, seat_dir, -80.0)), p3(along(seat_tube_top, seat_dir, 30.0)), 13.9))
frame = frame.cut(cyl_y(13.0, -40.0, 40.0, bb[0], bb[1]))

# ======================================================= fork & cockpit
cad_step(steps[1])  # noqa: F821 - injected by cad_workbench.runner
tilt = -math.degrees(math.pi / 2.0 - head_angle)
fork = cq.Workplane("XY").box(44.0, 84.0, 24.0).rotate((0, 0, 0), (0, 1, 0), tilt).translate(p3(crown))
fork = fork.union(tube(p3(along(crown, u, 11.0)), p3(steerer_top), 14.0))
for side in (-1.0, 1.0):
    p0 = (crown[0] + 2.0 * fw[0], side * 32.0, crown[1] - 11.0)
    m1 = along(along(axis_pt, u, 250.0), fw, 8.0)
    m2 = along(along(axis_pt, u, 120.0), fw, 24.0)
    blade = sweep_tube([p0, (m1[0], side * 40.0, m1[1]), (m2[0], side * 46.0, m2[1]), (front_axle[0] - 4.0, side * front_drop_y, front_axle[1] + 8.0)], 11.0)
    fork = fork.union(blade)
    fork = fork.union(ring_y(14.0, 5.0, side * front_drop_y - 2.5, side * front_drop_y + 2.5, front_axle[0], front_axle[1]))

top_cap = axial_ring(along(head_tube_top, u, 4.0), u, 4.0, 19.0, 14.5)
spacers = axial_ring(along(head_tube_top, u, 15.0), u, 7.0, 16.5, 14.5)
stem = tube(p3(along(head_tube_top, u, 22.0)), p3(along(head_tube_top, u, 42.0)), 20.0)
stem = stem.union(tube(p3(stem_base), p3(stem_end), 13.0))
stem = stem.union(cyl_y(20.0, -22.0, 22.0, stem_end[0], stem_end[1]))
stem = stem.cut(tube(p3(along(head_tube_top, u, 5.0)), p3(along(head_tube_top, u, 60.0)), 14.3))           # steerer bore
stem = stem.cut(cyl_y(13.0, -24.0, 24.0, stem_end[0], stem_end[1]))                                        # bar bore
stem = stem.cut(tube(p3(head_tube_top), p3(along(head_tube_top, u, 22.0)), 17.0))                            # keep clear of the spacers

bar_half = [(0, 0, 0), (0, 100, 0), (0, 200, 0), (20, 215, -2), (60, 220, -15), (85, 220, -50), (78, 220, -90), (45, 220, -120), (0, 220, -130), (-50, 220, -130)]
handlebar = sweep_tube([(bar_c[0] + x, y, bar_c[2] + z) for x, y, z in bar_half], 12.0, tangents=[(0, 1, 0), (-1, 0, 0)])
handlebar = handlebar.union(sweep_tube([(bar_c[0] + x, -y, bar_c[2] + z) for x, y, z in bar_half], 12.0, tangents=[(0, -1, 0), (-1, 0, 0)]))
hoods = []
levers = []
for side in (-1.0, 1.0):
    hood = cq.Workplane("XY").box(48.0, 24.0, 28.0).rotate((0, 0, 0), (0, 1, 0), 22.0).translate((bar_c[0] + 68.0, side * 220.0, bar_c[2] - 32.0))
    hoods.append(hood.cut(handlebar))
    lever = cq.Workplane("XY").box(9.0, 13.0, 95.0).rotate((0, 0, 0), (0, 1, 0), -10.0).translate((bar_c[0] + 106.0, side * 222.0, bar_c[2] - 92.0))
    levers.append(lever.cut(handlebar))

# ============================================== saddle, brakes, cables, bottle
cad_step(steps[2])  # noqa: F821 - injected by cad_workbench.runner
seatpost = tube(p3(along(seat_tube_top, seat_dir, -60.0)), p3(post_top), post_r)
collar = axial_ring(along(seat_tube_top, seat_dir, 16.0), seat_dir, 4.0, 19.0, 14.4)
clamp = box(36.0, 14.0, 22.0, (post_top[0], 0.0, post_top[1] + 17.0))
saddle_pts = [(140, 0), (110, 16), (60, 26), (0, 48), (-50, 72), (-95, 68), (-125, 40), (-130, 0), (-125, -40), (-95, -68), (-50, -72), (0, -48), (60, -26), (110, -16)]
saddle = cq.Workplane("XY").spline(saddle_pts, periodic=True).close().extrude(22.0).translate((post_top[0] + 20.0, 0.0, saddle_z))
rails = None
for side in (-1.0, 1.0):
    r0 = (post_top[0] - 95.0, side * 22.0, saddle_z - 12.0)
    r1 = (post_top[0] + 45.0, side * 22.0, saddle_z - 12.0)
    piece = tube(r0, r1, 3.5).union(tube(r0, (r0[0], r0[1], saddle_z), 3.5)).union(tube(r1, (r1[0], r1[1], saddle_z), 3.5))
    rails = piece if rails is None else rails.union(piece)


def caliper(body_c, axle, elbow_frac, elbow_y, pad_y):
    """Dual-pivot caliper. Thin arms thread between the tire (|y|<12.5 at r 323) and the
    fork blades / seat stays, then turn in to pads on the rim sidewall at r 305."""
    pad_dir = (body_c[0] - axle[0], body_c[1] - axle[1])
    pl = math.hypot(*pad_dir)
    pad_dir = (pad_dir[0] / pl, pad_dir[1] / pl)
    pad_c = (axle[0] + 305.0 * pad_dir[0], axle[1] + 305.0 * pad_dir[1])
    tangent = math.atan2(pad_dir[0], -pad_dir[1])
    parts = box(22.0, 22.0, 8.0, (body_c[0], 0.0, body_c[1]))
    for side in (-1.0, 1.0):
        start = (body_c[0], side * 13.0, body_c[1])
        elbow = (start[0] + elbow_frac * (pad_c[0] - start[0]), side * elbow_y, start[2] + elbow_frac * (pad_c[1] - start[2]))
        arm = tube(start, elbow, 3.5).union(tube(elbow, (pad_c[0], side * pad_y, pad_c[1]), 3.5))
        pad = cq.Workplane("XY").box(40.0, 7.0, 12.0).rotate((0, 0, 0), (0, 1, 0), ry_of_heading(tangent)).translate((pad_c[0], side * pad_y, pad_c[1]))
        parts = parts.union(arm).union(pad)
    return parts


front_brake = caliper((crown[0] + 16.0, crown[1] - 17.0), front_axle, 0.6, 19.0, 16.0)
rear_brake = caliper((bridge_x - 10.0, 672.0), rear_axle, 0.75, 21.5, 15.5)

cable_front = sweep_tube([(bar_c[0] + 101.0, 214.0, bar_c[2] - 32.0), (bar_c[0] + 70.0, 130.0, bar_c[2] - 78.0), (crown[0] + 34.0, 22.0, crown[1] + 50.0), (crown[0] + 30.0, 8.0, crown[1] - 4.0)], 2.5)
tt_dir = (head_tube_top[0] - seat_tube_top[0], head_tube_top[1] - seat_tube_top[1])
ttl = math.hypot(*tt_dir)
tt_dir = (tt_dir[0] / ttl, tt_dir[1] / ttl)
tt_norm = (-tt_dir[1], tt_dir[0])
tt_pts = [along(along(seat_tube_top, tt_dir, f * ttl), tt_norm, 30.0) for f in (0.9, 0.7, 0.5, 0.3, 0.1)]
cable_rear = sweep_tube([(bar_c[0] + 101.0, -214.0, bar_c[2] - 32.0), (bar_c[0] + 50.0, -120.0, bar_c[2] - 70.0), (head_tube_top[0] - 34.0, -18.0, head_tube_top[1] + 6.0)] + [(p[0], -18.0, p[1]) for p in tt_pts] + [(seat_tube_top[0] - 24.0, -22.0, seat_tube_top[1] + 2.0), (bridge_x + 2.0, -6.0, 706.0)], 2.5)
dt_vec = (dt_end[0] - bb[0], dt_end[1] - bb[1])
dt_len = math.hypot(*dt_vec)
dt_dir = (dt_vec[0] / dt_len, dt_vec[1] / dt_len)
dt_norm = (-dt_dir[1], dt_dir[0])
dt_pts = [along(along(bb, dt_dir, f * dt_len), dt_norm, -30.0) for f in (0.85, 0.65, 0.45, 0.25)]
cable_rd = sweep_tube([(head_tube_bottom[0] - 16.0, 24.0, head_tube_bottom[1] + 24.0)] + [(p[0], 22.0, p[1]) for p in dt_pts] + [(bb[0] + 12.0, 24.0, bb[1] - 30.0), (bb[0] - 20.0, 26.0, bb[1] - 36.0), (200.0, 52.0, 296.0), (110.0, 62.0, 300.0), (-8.0, 60.0, 306.0)], 2.5)

bottle_c = along(along(bb, dt_dir, 0.45 * dt_len), dt_norm, 58.0)
bottle = tube(p3(along(bottle_c, dt_dir, -100.0)), p3(along(bottle_c, dt_dir, 100.0)), 36.0)
bottle = bottle.union(tube(p3(along(bottle_c, dt_dir, 100.0)), p3(along(bottle_c, dt_dir, 128.0)), 15.0))

# Label: a thin wrap around the main body (well clear of both cage rings, which sit at
# s=-68/+108, outside this +-52 span) plus two slightly-raised accent stripes at its
# edges, like a printed label sleeve. A shell (outer minus inner), not a solid disc, so
# it reads as a skin on the bottle rather than a fatter bottle.
label_half, label_r = 52.0, 36.4
label_inner = tube(p3(along(bottle_c, dt_dir, -label_half - 2.0)), p3(along(bottle_c, dt_dir, label_half + 2.0)), 36.0)
bottle_label = tube(p3(along(bottle_c, dt_dir, -label_half)), p3(along(bottle_c, dt_dir, label_half)), label_r).cut(label_inner)
accent_r = label_r + 0.3
bottle_label_accent = tube(p3(along(bottle_c, dt_dir, label_half - 5.0)), p3(along(bottle_c, dt_dir, label_half)), accent_r)
bottle_label_accent = bottle_label_accent.union(tube(p3(along(bottle_c, dt_dir, -label_half)), p3(along(bottle_c, dt_dir, -label_half + 5.0)), accent_r))
bottle_label_accent = bottle_label_accent.cut(label_inner)

# Bottle cage: two bolt bosses on the down tube (80 mm apart along its own axis), each
# with a short radial rail out to a wire ring that hugs the bottle -- a wide ring around
# the main body for support, a narrower one around the neck for retention, exactly how a
# real cage holds the bottle (it slides in/out along its own axis, not sideways, so the
# rings can be closed loops). Both rings and both bosses share the bottle's own axis
# projection, so the rails come out purely radial and stay short.
cage_lower_s, cage_upper_s = -68.0, 108.0
cage_r_lower, cage_r_upper = 38.5, 18.0
cage_wire_r, cage_bolt_r = 2.0, 3.0
boss0 = along(bb, dt_dir, 0.45 * dt_len + cage_lower_s)
boss1 = along(bb, dt_dir, 0.45 * dt_len + cage_upper_s)
ring0_c = along(bottle_c, dt_dir, cage_lower_s)
ring1_c = along(bottle_c, dt_dir, cage_upper_s)
cage_axis = (dt_dir[0], 0.0, dt_dir[1])
bottle_cage = cq.Workplane(obj=cq.Solid.makeTorus(cage_r_lower, cage_wire_r, vec(p3(ring0_c)), vec(cage_axis)))
bottle_cage = bottle_cage.union(cq.Workplane(obj=cq.Solid.makeTorus(cage_r_upper, cage_wire_r, vec(p3(ring1_c)), vec(cage_axis))))
bottle_cage = bottle_cage.union(tube(p3(along(boss0, dt_norm, dt_r)), p3(along(ring0_c, dt_norm, -cage_r_lower)), cage_wire_r))
bottle_cage = bottle_cage.union(tube(p3(along(boss1, dt_norm, dt_r)), p3(along(ring1_c, dt_norm, -cage_r_upper)), cage_wire_r))
# no direct rail between the two ring-attachment points: their radial offsets differ too
# much (19.5 mm vs 40 mm) for a straight tube to stay outside the bottle along the way --
# it would cut diagonally through the main body. A rail hugging the tube surface instead
# (constant offset dt_r) connects the two bosses without ever approaching the bottle.
bottle_cage = bottle_cage.union(tube(p3(along(boss0, dt_norm, dt_r)), p3(along(boss1, dt_norm, dt_r)), cage_wire_r))
bottle_cage = bottle_cage.union(tube(p3(boss0), p3(along(boss0, dt_norm, dt_r + 3.0)), cage_bolt_r))
bottle_cage = bottle_cage.union(tube(p3(boss1), p3(along(boss1, dt_norm, dt_r + 3.0)), cage_bolt_r))

# ======================================================== wheels & cassette
cad_step(steps[3])  # noqa: F821 - injected by cad_workbench.runner
tire = cq.Workplane(obj=cq.Solid.makeTorus(tire_major, tire_minor, cq.Vector(0, 0, 0), cq.Vector(0, 1, 0)))
rim = ring_y(rim_out, rim_in, -rim_w / 2.0, rim_w / 2.0, 0, 0)


def hub(body_r, y0, y1, flange_r, flange_ys, axle_r, axle_half, extra=None):
    h = cyl_y(body_r, y0, y1, 0, 0)
    for fy in flange_ys:
        h = h.union(cyl_y(flange_r, fy - 1.5, fy + 1.5, 0, 0))
    h = h.union(cyl_y(axle_r, -axle_half, axle_half, 0, 0))
    if extra is not None:
        h = h.union(extra)
    return h


def spokes(flange_ys, flange_r, n=24):
    """2-cross lacing, alternating heads-in/heads-out so crossing spokes clear each other."""
    out = []
    per_side = n // 2
    for k in range(per_side):
        for side_i, fy in enumerate(flange_ys):
            sign = 1.0 if fy > 0 else -1.0
            a = math.radians(360.0 * k / per_side + (180.0 / per_side if side_i else 0.0))
            d = 1.0 if k % 2 == 0 else -1.0
            a_rim = a + d * math.radians(4.0 * 360.0 / n)
            rf = flange_r + 1.2
            out.append(tube((rf * math.cos(a), fy + sign * 1.6 * d, rf * math.sin(a)), ((rim_in - 0.4) * math.cos(a_rim), 0.0, (rim_in - 0.4) * math.sin(a_rim)), 1.0))
    return out


front_hub = hub(13.0, -35.0, 35.0, 21.0, (-32.0, 32.0), 4.5, 52.0)
front_spokes = spokes((-32.0, 32.0), 21.0)
rear_hub = hub(14.0, -38.0, 20.0, 23.0, (-32.0, 15.5), 5.0, 65.5, extra=cyl_y(17.0, 20.0, 59.0, 0, 0))
rear_spokes = spokes((-32.0, 15.5), 23.0)

# ================================ chain path, crank, chainrings, derailleurs
cad_step(steps[4])  # noqa: F821 - injected by cad_workbench.runner
tension_dz = 0.0
for _ in range(60):
    tension_c = (guide_c[0] + 22.0, guide_c[1] - 72.0 + tension_dz)
    circles = [
        (bb[0], bb[1], r_big, -1.0, front_teeth_big),
        (tension_c[0], tension_c[1], r_pulley, -1.0, 11),
        (guide_c[0], guide_c[1], r_pulley, 1.0, 11),
        (rear_axle[0], rear_axle[1], r_cog, -1.0, cog_teeth),
    ]
    point_at, chain_len, arc_starts = chain_path(circles)
    n_links = int(round(chain_len / chain_pitch))
    slack = chain_len - n_links * chain_pitch
    if abs(slack) < 0.002:
        break
    tension_dz += 0.7 * slack


def phase_for(circle_index):
    """ry (deg) that puts a tooth valley under the first chain pin on this circle's arc."""
    cx, cz, r, s, _ = circles[circle_index]
    k = math.ceil(arc_starts[circle_index] / chain_pitch)
    px, pz = point_at(k * chain_pitch)
    return -math.degrees(math.atan2(pz - cz, px - cx))


spindle = cyl_y(12.0, -74.0, 74.0, 0, 0)
spider = ring_y(26.0, 12.5, 40.0, crank_y0, 0, 0)
for k in range(5):
    spider = spider.union(box(48.0, 4.0, 15.0, (44.0, 43.0, 0.0)).rotate((0, 0, 0), (0, 1, 0), -(72.0 * k + 36.0)))
ring_big = sprocket(front_teeth_big, ring_w, r_big - 41.0, phase_for(0)).translate((0, drive_y, 0))
ring_small = sprocket(front_teeth_small, ring_w, pitch_radius(front_teeth_small) - 21.0).translate((0, small_ring_y, 0))


def crank_arm(thickness):
    """Tapered arm pointing +Z from the spindle, centred on Y=0, spindle bore cut."""
    arm = cq.Workplane("XY").rect(30.0, thickness).workplane(offset=crank_len).rect(20.0, thickness - 2.0).loft(combine=True)
    arm = arm.union(cyl_y(18.0, -thickness / 2.0, thickness / 2.0, 0, 0))
    arm = arm.union(cyl_y(11.0, -thickness / 2.0, thickness / 2.0, 0, crank_len))
    return arm.cut(cyl_y(12.2, -thickness, thickness, 0, 0))


arm_r = crank_arm(crank_y1 - crank_y0).translate((0, (crank_y0 + crank_y1) / 2.0, 0))
arm_l = crank_arm(crank_y1 - crank_y0).rotate((0, 0, 0), (0, 1, 0), 180.0).translate((0, -(crank_y0 + crank_y1) / 2.0, 0))


def pedal(sign):
    y_in = sign * crank_y1
    y_out = y_in + sign * 22.0
    spindle_p = cyl_y(6.0, min(y_in, y_out), max(y_in, y_out), 0, 0)
    body = box(92.0, pedal_len, 16.0, (0.0, y_out + sign * pedal_len / 2.0, 0.0))
    return spindle_p.union(body)


pedal_r = pedal(1.0)
pedal_l = pedal(-1.0)

# front derailleur: band on the seat tube, cage straddling the chain above the 50T
fd_band_c = along(bb, seat_dir, (382.0 - bb[1]) / seat_dir[1])
fd_band = axial_ring(fd_band_c, seat_dir, 4.0, 19.5, 14.4)
fd_arm = box(22.0, 30.0, 10.0, (fd_band_c[0] + 18.0, 31.0, 378.0))
fd_cage = box(56.0, 1.5, 32.0, (bb[0] - 8.0, 38.0, 375.0)).union(box(56.0, 1.5, 32.0, (bb[0] - 8.0, 51.5, 375.0)))
fd_cage = fd_cage.union(box(10.0, 15.0, 6.0, (bb[0] - 33.0, 44.75, 388.0)))
front_derailleur = fd_band.union(fd_arm).union(fd_cage)

# rear derailleur body + cage are static; the two pulleys are separate animated nodes
rd_body = cyl_y(8.0, 60.0, 74.0, -22.0, 297.0)
rd_body = rd_body.union(box(20.0, 20.0, 36.0, (-14.0, 52.0, 282.0)))
rd_body = rd_body.union(box(12.0, 6.0, 30.0, (-18.0, 63.0, 300.0)))
rd_body = rd_body.union(cyl_y(5.0, y_cog + 7.0, 42.0, guide_c[0], guide_c[1]))
cage_vec = (tension_c[0] - guide_c[0], tension_c[1] - guide_c[1])
cage_len = math.hypot(*cage_vec)
cage_mid = ((guide_c[0] + tension_c[0]) / 2.0, (guide_c[1] + tension_c[1]) / 2.0)
cage_ry = ry_of_heading(math.atan2(cage_vec[1], cage_vec[0]))
rd_cage = None
for cy in (y_cog - 6.0, y_cog + 6.0):
    plate = cq.Workplane("XY").box(cage_len, 2.0, 30.0).rotate((0, 0, 0), (0, 1, 0), cage_ry).translate((cage_mid[0], cy, cage_mid[1]))
    plate = plate.union(cyl_y(16.0, cy - 1.0, cy + 1.0, guide_c[0], guide_c[1])).union(cyl_y(16.0, cy - 1.0, cy + 1.0, tension_c[0], tension_c[1]))
    rd_cage = plate if rd_cage is None else rd_cage.union(plate)
rd_cage = rd_cage.union(cyl_y(4.0, y_cog - 7.0, y_cog + 7.0, guide_c[0], guide_c[1])).union(cyl_y(4.0, y_cog - 7.0, y_cog + 7.0, tension_c[0], tension_c[1]))
guide_pulley = sprocket(11, 2.0, 5.0, phase_for(2))
tension_pulley = sprocket(11, 2.0, 5.0, phase_for(1))

cogs = []
for i, t in enumerate(cassette_teeth):
    phase = phase_for(3) if i == chain_cog_index else 0.0
    cogs.append(sprocket(t, cog_w, 17.5, phase).translate((0, cog_y0 - i * cog_pitch_y, 0)))

# ==================================================================== chain
cad_step(steps[5])  # noqa: F821 - injected by cad_workbench.runner


def link_plate():
    return cq.Workplane("XY").box(19.5, 0.6, 8.5).edges("|Y").fillet(4.0)


roller = cyl_y(3.85, -1.05, 1.05, 0, 0).cut(cyl_y(2.25, -2.0, 2.0, 0, 0))
inner_link = link_plate().translate((0, 1.4, 0)).union(link_plate().translate((0, -1.4, 0)))
for px in (-chain_pitch / 2.0, chain_pitch / 2.0):
    inner_link = inner_link.cut(cyl_y(2.25, -3.0, 3.0, px, 0)).union(roller.translate((px, 0, 0)))
outer_link = link_plate().translate((0, 2.5, 0)).union(link_plate().translate((0, -2.5, 0)))
for px in (-chain_pitch / 2.0, chain_pitch / 2.0):
    outer_link = outer_link.union(cyl_y(1.8, -2.8, 2.8, px, 0))

chain = cq.Assembly(name="chain")
link_state = []
for i in range(n_links):
    s_a = i * chain_pitch
    ax, az = point_at(s_a)
    bx, bz = point_at(s_a + chain_pitch)
    cx, cz = (ax + bx) / 2.0, (az + bz) / 2.0
    phi0 = math.atan2(bz - az, bx - ax)
    link_state.append((s_a, cx, cz, phi0))
    node = cq.Assembly(name=f"link_{i:03d}")
    node.add(inner_link if i % 2 == 0 else outer_link, name="body", loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), ry_of_heading(phi0)), color=chain_col)
    chain.add(node, name=f"link_{i:03d}", loc=cq.Location(cq.Vector(cx, chain_y(cx), cz)))

# ================================================================= assembly
frame_group = cq.Assembly(name="frame")
for name, shape, col in [
    ("frame_solid", frame, paint), ("fork", fork, paint), ("top_cap", top_cap, black), ("spacers", spacers, black),
    ("stem", stem, black), ("handlebar", handlebar, black), ("hood_l", hoods[0], black), ("hood_r", hoods[1], black),
    ("lever_l", levers[0], alloy), ("lever_r", levers[1], alloy), ("seatpost", seatpost, black), ("seat_collar", collar, black),
    ("saddle_clamp", clamp, black), ("saddle", saddle, black), ("saddle_rails", rails, alloy),
    ("front_brake", front_brake, alloy), ("rear_brake", rear_brake, alloy), ("cable_front_brake", cable_front, black),
    ("cable_rear_brake", cable_rear, black), ("cable_rear_derailleur", cable_rd, black), ("bottle", bottle, white), ("bottle_cage", bottle_cage, alloy),
    ("bottle_label", bottle_label, label_blue), ("bottle_label_accent", bottle_label_accent, white),
    ("front_derailleur", front_derailleur, steel), ("rd_body", rd_body, steel), ("rd_cage", rd_cage, steel),
]:
    frame_group.add(shape, name=name, color=col)

crank_group = cq.Assembly(name="crank_group")
crank_group.add(spindle, name="spindle", color=steel)
crank_group.add(spider, name="spider", color=black)
crank_group.add(ring_big, name="chainring_50t", color=steel)
crank_group.add(ring_small, name="chainring_34t", color=steel)
crank_group.add(arm_r, name="crank_arm_r", color=black)
crank_group.add(arm_l, name="crank_arm_l", color=black)
pedal_r_pivot = cq.Assembly(name="pedal_r_pivot")
pedal_r_pivot.add(pedal_r, name="pedal_r", color=black)
pedal_l_pivot = cq.Assembly(name="pedal_l_pivot")
pedal_l_pivot.add(pedal_l, name="pedal_l", color=black)
crank_group.add(pedal_r_pivot, name="pedal_r_pivot", loc=cq.Location(cq.Vector(0, 0, crank_len)))
crank_group.add(pedal_l_pivot, name="pedal_l_pivot", loc=cq.Location(cq.Vector(0, 0, -crank_len)))


def wheel_group(name, hub_shape, spoke_list, extra_parts):
    g = cq.Assembly(name=name)
    g.add(tire, name="tire", color=rubber)
    g.add(rim, name="rim", color=black)
    g.add(hub_shape, name="hub", color=alloy)
    for i, sp in enumerate(spoke_list):
        g.add(sp, name=f"spoke_{i:02d}", color=alloy)
    for pname, shape, col in extra_parts:
        g.add(shape, name=pname, color=col)
    return g


rear_wheel = wheel_group("rear_wheel", rear_hub, rear_spokes, [(f"cog_{t}t", c, steel) for t, c in zip(cassette_teeth, cogs)])
front_wheel = wheel_group("front_wheel", front_hub, front_spokes, [])

result = cq.Assembly(name="road_bike")
result.add(frame_group, name="frame")
result.add(crank_group, name="crank_group", loc=cq.Location(cq.Vector(bb[0], 0.0, bb[1])))
result.add(rear_wheel, name="rear_wheel", loc=cq.Location(cq.Vector(rear_axle[0], 0.0, rear_axle[1])))
result.add(front_wheel, name="front_wheel", loc=cq.Location(cq.Vector(front_axle[0], 0.0, front_axle[1])))
result.add(guide_pulley, name="rd_guide_pulley", loc=cq.Location(cq.Vector(guide_c[0], y_cog, guide_c[1])), color=black)
result.add(tension_pulley, name="rd_tension_pulley", loc=cq.Location(cq.Vector(tension_c[0], y_cog, tension_c[1])), color=black)
result.add(chain, name="chain")

# ================================================================ animation
cad_step(steps[6])  # noqa: F821 - injected by cad_workbench.runner
omega_crank = 2.0 * math.pi * pedal_turns / duration
v_chain = omega_crank * param_radius(front_teeth_big)        # path-parameter units per second
omega_rear = v_chain / param_radius(cog_teeth)               # == omega_crank * 50 / 19
omega_pulley = v_chain / param_radius(11)
times = [duration * i / n_time for i in range(n_time + 1)]
deg = math.degrees
animation = [
    {"path": "/road_bike/crank_group", "action": "ry", "times": times, "values": [deg(omega_crank * t) for t in times]},
    {"path": "/road_bike/crank_group/pedal_r_pivot", "action": "ry", "times": times, "values": [-deg(omega_crank * t) for t in times]},
    {"path": "/road_bike/crank_group/pedal_l_pivot", "action": "ry", "times": times, "values": [-deg(omega_crank * t) for t in times]},
    {"path": "/road_bike/rear_wheel", "action": "ry", "times": times, "values": [deg(omega_rear * t) for t in times]},
    {"path": "/road_bike/front_wheel", "action": "ry", "times": times, "values": [deg(omega_rear * t) for t in times]},
    {"path": "/road_bike/rd_guide_pulley", "action": "ry", "times": times, "values": [-deg(omega_pulley * t) for t in times]},
    {"path": "/road_bike/rd_tension_pulley", "action": "ry", "times": times, "values": [deg(omega_pulley * t) for t in times]},
]
for i, (s_a, cx0, cz0, phi0) in enumerate(link_state):
    y0 = chain_y(cx0)
    pos_vals = []
    rot_vals = []
    phi_prev = phi0
    for t in times:
        s = s_a + v_chain * t
        ax, az = point_at(s)
        bx, bz = point_at(s + chain_pitch)
        cx, cz = (ax + bx) / 2.0, (az + bz) / 2.0
        phi = unwrap(phi_prev, math.atan2(bz - az, bx - ax))
        phi_prev = phi
        pos_vals.append([cx - cx0, chain_y(cx) - y0, cz - cz0])
        rot_vals.append(ry_of_heading(phi) - ry_of_heading(phi0))
    animation.append({"path": f"/road_bike/chain/link_{i:03d}", "action": "t", "times": times, "values": pos_vals})
    animation.append({"path": f"/road_bike/chain/link_{i:03d}/body", "action": "ry", "times": times, "values": rot_vals})
