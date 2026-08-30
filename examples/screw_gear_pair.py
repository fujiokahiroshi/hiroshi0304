import math

import cadquery as cq

steps = [
    "ヘリカル歯車Aを生成",
    "ヘリカル歯車Bを生成し位相を合わせる",
    "ねじ歯車ペアを組立(Bはグループごとオフセット配置)",
    "オレンジ(A)の回転を受けて青(B)が自軸(X軸)で連動回転するアニメーションを設定",
]


def make_helical_gear(
    teeth, module, face_width, helix_angle_deg, pressure_angle_deg=20.0, bore=6.0, clearance=0.25
):
    alpha = math.radians(pressure_angle_deg)
    z = teeth
    m = module
    rp = m * z / 2.0
    rb = rp * math.cos(alpha)
    ra = rp + m
    rf = rp - m * (1 + clearance)

    def involute_xy(rb, t):
        x = rb * (math.cos(t) + t * math.sin(t))
        y = rb * (math.sin(t) - t * math.cos(t))
        return x, y

    r_start = max(rb, rf)
    t_start = math.sqrt(max((r_start / rb) ** 2 - 1, 0.0))
    t_max = math.sqrt((ra / rb) ** 2 - 1)

    t_p = math.sqrt(max((rp / rb) ** 2 - 1, 0.0))
    xp, yp = involute_xy(rb, t_p)
    theta_p = math.atan2(yp, xp)
    half_tooth_angle = math.pi / (2 * z)
    angle_offset2 = half_tooth_angle + theta_p

    n_pts = 6
    right_flank = []
    for i in range(n_pts + 1):
        t = t_start + (t_max - t_start) * i / n_pts
        x, y = involute_xy(rb, t)
        r = math.hypot(x, y)
        inv_r = math.atan2(y, x)
        theta = angle_offset2 - inv_r
        right_flank.append((r * math.cos(theta), r * math.sin(theta)))

    if rf < r_start:
        x0, y0 = right_flank[0]
        theta0 = math.atan2(y0, x0)
        root_pt = (rf * math.cos(theta0), rf * math.sin(theta0))
        right_flank = [root_pt] + right_flank

    right_flank_rev = right_flank[::-1]
    left_flank = []
    for x, y in right_flank_rev:
        r = math.hypot(x, y)
        theta = math.atan2(y, x)
        left_flank.append((r * math.cos(-theta), r * math.sin(-theta)))

    tooth_pts = right_flank + left_flank

    def rotate_pts(pts, ang_deg):
        a = math.radians(ang_deg)
        ca, sa = math.cos(a), math.sin(a)
        return [(x * ca - y * sa, x * sa + y * ca) for (x, y) in pts]

    twist_rad = (face_width * math.tan(math.radians(helix_angle_deg))) / rp
    twist_deg = math.degrees(twist_rad)

    gear = cq.Workplane("XY").circle(rf + 0.05).extrude(face_width)
    for i in range(z):
        ang = 360.0 * i / z
        rotated_pts = rotate_pts(tooth_pts, ang)
        tooth_solid = (
            cq.Workplane("XY").polyline(rotated_pts).close().twistExtrude(face_width, twist_deg)
        )
        gear = gear.union(tooth_solid)

    if bore > 0:
        gear = gear.cut(cq.Workplane("XY").circle(bore / 2).extrude(face_width))

    gear = gear.translate((0, 0, -face_width / 2.0))
    return gear, rp


cad_step(steps[0])  # noqa: F821 - injected by cad_workbench.runner
teeth_a = 14
teeth_b = 14
module = 2.5
face_width = 14.0
helix_a = 45.0
helix_b = 45.0
bore = 6.0

gear_a, rp_a = make_helical_gear(teeth_a, module, face_width, helix_a, bore=bore)

cad_step(steps[1])  # noqa: F821 - injected by cad_workbench.runner
gear_b_raw, rp_b = make_helical_gear(teeth_b, module, face_width, helix_b, bore=bore)
phase_b = 180.0 / teeth_b
gear_b_local = gear_b_raw.rotate((0, 0, 0), (0, 0, 1), phase_b)
gear_b_local = gear_b_local.rotate((0, 0, 0), (0, 1, 0), 90.0)
center_distance = rp_a + rp_b

cad_step(steps[2])  # noqa: F821 - injected by cad_workbench.runner
group_a = cq.Assembly(name="screw_gear_a")
group_a.add(gear_a, name="body", color=cq.Color(0.85, 0.55, 0.15))

group_b = cq.Assembly(name="screw_gear_b")
group_b.add(gear_b_local, name="body", color=cq.Color(0.2, 0.55, 0.85))

result = cq.Assembly(name="screw_gear_pair")
result.add(group_a, name="screw_gear_a")
result.add(group_b, name="screw_gear_b", loc=cq.Location(cq.Vector(0, center_distance, 0)))

cad_step(steps[3])  # noqa: F821 - injected by cad_workbench.runner
duration = 6.0
n_steps = 12
angular_speed_a = 720.0 / duration
angular_speed_b = angular_speed_a * (teeth_a / teeth_b)
times = [duration * i / n_steps for i in range(n_steps + 1)]
values_a = [angular_speed_a * t for t in times]
values_b = [angular_speed_b * t for t in times]

animation = [
    {
        "path": "/screw_gear_pair/screw_gear_a",
        "action": "rz",
        "times": times,
        "values": values_a,
    },
    {
        "path": "/screw_gear_pair/screw_gear_b",
        "action": "rx",
        "times": times,
        "values": values_b,
    },
]
