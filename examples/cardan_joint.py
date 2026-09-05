"""Universal (Cardan) joint with correct non-constant-velocity kinematics.

Two shafts cross at angle BETA_DEG. The blue yoke is the steering handle: the
driver turns it at a uniform rate. The cross (spider) and the yellow yoke --
which drives the wheels -- follow the classical Hooke's-joint relation
tan(phi) = tan(theta) / cos(beta), derived here from first principles via the
pin directions rather than assumed from the formula.
"""

import math

import cadquery as cq

steps = [
    "ハンドル側・車輪側ヨークを交差角betaで配置",
    "十字（クロス）を組み込み、両ヨークと接続",
    "非等速回転の運動学を計算してアニメーションを設定",
]

BETA_DEG = 25.0
TURNS = 3.0
DURATION = 6.0
SAMPLES_PER_TURN = 24

SHAFT_R = 4.0
SHAFT_LEN = 26.0
PRONG_R = 6.0
PRONG_LEN = 13.0
FORK_HALF_WIDTH = 11.0
HUB_R = 5.5
PIN_R = 3.0
PIN_CLEARANCE = 0.4
PIN_HOLE_R = PIN_R + PIN_CLEARANCE
PRONG_TIP_EXTENSION = PIN_HOLE_R + 2.0
FORK_OUTER = FORK_HALF_WIDTH + PRONG_R
CAP_GAP = 2.0
CAP_THICKNESS = 1.5
CAP_R = PRONG_R + 2.0
PIN_LEN = 2 * (FORK_OUTER + CAP_GAP + CAP_THICKNESS)
MARKER_R = 1.8

GEAR_TEETH = 18
GEAR_MODULE = 1.5
GEAR_THICKNESS = 6.0


def cross3(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm3(a):
    n = math.sqrt(dot3(a, a))
    return (a[0] / n, a[1] / n, a[2] / n)


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def scale3(a, s):
    return (a[0] * s, a[1] * s, a[2] * s)


def to_vector(v):
    return cq.Vector(v[0], v[1], v[2])


def rotate_about_axis(v, axis, angle):
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    term1 = scale3(v, cos_a)
    term2 = scale3(cross3(axis, v), sin_a)
    term3 = scale3(axis, dot3(axis, v) * (1.0 - cos_a))
    return add3(add3(term1, term2), term3)


BETA = math.radians(BETA_DEG)
WHEEL_AXIS = (0.0, 0.0, 1.0)  # yellow yoke's shaft axis -- drives the wheels
HANDLE_AXIS = (0.0, -math.sin(BETA), math.cos(BETA))  # blue yoke's shaft axis -- the handle

HANDLE_HINGE0 = norm3(cross3((1.0, 0.0, 0.0), HANDLE_AXIS))


def drive_pin_dir(theta):
    """Direction of the pin captured by the handle's (blue) fork, at driver angle theta."""
    return rotate_about_axis(HANDLE_HINGE0, HANDLE_AXIS, theta)


def driven_pin_dir(theta):
    """Direction of the pin captured by the wheel-side (yellow) fork -- derived,
    perpendicular to both the handle's pin and the wheel-side shaft axis."""
    return norm3(cross3(drive_pin_dir(theta), WHEEL_AXIS))


HANDLE_HINGE = drive_pin_dir(0.0)
WHEEL_HINGE = driven_pin_dir(0.0)
CROSS_REST_3RD = norm3(cross3(WHEEL_HINGE, HANDLE_HINGE))
WHEEL_BASIS_E2 = norm3(cross3(WHEEL_AXIS, WHEEL_HINGE))


def mat3_from_cols(c1, c2, c3):
    return tuple((c1[i], c2[i], c3[i]) for i in range(3))


def mat3_transpose(m):
    return tuple(tuple(m[j][i] for j in range(3)) for i in range(3))


def mat3_mul(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3)
    )


def mat3_to_quat(m):
    m00, m01, m02 = m[0]
    m10, m11, m12 = m[1]
    m20, m21, m22 = m[2]
    trace = m00 + m11 + m22
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        qw = 0.25 * s
        qx = (m21 - m12) / s
        qy = (m02 - m20) / s
        qz = (m10 - m01) / s
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        qw = (m21 - m12) / s
        qx = 0.25 * s
        qy = (m01 + m10) / s
        qz = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        qw = (m02 - m20) / s
        qx = (m01 + m10) / s
        qy = 0.25 * s
        qz = (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        qw = (m10 - m01) / s
        qx = (m02 + m20) / s
        qy = (m12 + m21) / s
        qz = 0.25 * s
    return (qx, qy, qz, qw)


Rrest = mat3_from_cols(WHEEL_HINGE, HANDLE_HINGE, CROSS_REST_3RD)
RrestT = mat3_transpose(Rrest)

cad_step(steps[0])


def make_yoke(axis_dir, hinge_dir, extend_sign):
    axis = scale3(axis_dir, extend_sign)
    neck = scale3(axis, PRONG_LEN)
    rod = cq.Solid.makeCylinder(SHAFT_R, SHAFT_LEN, to_vector(neck), to_vector(axis))
    hub_len = 2 * (FORK_HALF_WIDTH + PRONG_R) + 2.0
    hub_center = sub3(neck, scale3(hinge_dir, hub_len / 2.0))
    hub = cq.Solid.makeCylinder(HUB_R, hub_len, to_vector(hub_center), to_vector(hinge_dir))
    body = rod.fuse(hub)
    for sign in (1.0, -1.0):
        offset = scale3(hinge_dir, sign * FORK_HALF_WIDTH)
        p_start = add3(neck, offset)
        # Extend the prong past the hole position (instead of ending exactly at
        # it) so the bore sits inside a full ring of material -- a closed round
        # eye -- rather than an open-ended notch cut into the prong's tip face.
        tip_dir = norm3(sub3(offset, p_start))
        p_end = add3(offset, scale3(tip_dir, PRONG_TIP_EXTENSION))
        vec = sub3(p_end, p_start)
        length = math.sqrt(dot3(vec, vec))
        prong = cq.Solid.makeCylinder(PRONG_R, length, to_vector(p_start), to_vector(norm3(vec)))
        body = body.fuse(prong)
    for sign in (1.0, -1.0):
        hole_center = scale3(hinge_dir, sign * FORK_HALF_WIDTH)
        hole_start = sub3(hole_center, scale3(hinge_dir, PRONG_R + 2.0))
        hole = cq.Solid.makeCylinder(
            PIN_HOLE_R, 2.0 * (PRONG_R + 2.0), to_vector(hole_start), to_vector(hinge_dir)
        )
        body = body.cut(hole)
    return body


def make_marker(shaft_axis, side_dir, along_len):
    center = add3(scale3(shaft_axis, along_len), scale3(side_dir, SHAFT_R))
    return (
        cq.Workplane("XY", origin=to_vector(center))
        .circle(MARKER_R)
        .extrude(2.0, both=True)
    )


def make_end_gear(center, axis, teeth, module, thickness):
    pitch_r = module * teeth / 2.0
    root_r = max(module * 1.5, pitch_r - 1.25 * module)
    outer_r = pitch_r + module
    plane = cq.Plane(origin=to_vector(center), normal=to_vector(axis))
    gear = cq.Workplane(plane).circle(root_r).extrude(thickness).val()

    reference = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    radial0 = norm3(cross3(axis, reference))
    overlap = 1.0
    tooth_len = outer_r - root_r + 0.4 + overlap
    tooth_width = module * 1.6
    for index in range(teeth):
        angle = 2.0 * math.pi * index / teeth
        radial = rotate_about_axis(radial0, axis, angle)
        tooth_center = add3(center, scale3(radial, root_r - overlap + tooth_len / 2.0))
        tooth_plane = cq.Plane(
            origin=to_vector(tooth_center), xDir=to_vector(radial), normal=to_vector(axis)
        )
        tooth = cq.Workplane(tooth_plane).rect(tooth_len, tooth_width).extrude(thickness)
        gear = gear.fuse(tooth.val())
    return gear


def make_pin_with_retaining_caps(direction):
    pin = cq.Solid.makeCylinder(
        PIN_R, PIN_LEN, to_vector(scale3(direction, -PIN_LEN / 2.0)), to_vector(direction)
    )
    for sign in (1.0, -1.0):
        cap_center = scale3(direction, sign * (PIN_LEN / 2.0 - CAP_THICKNESS / 2.0))
        cap_start = sub3(cap_center, scale3(direction, CAP_THICKNESS / 2.0))
        cap = cq.Solid.makeCylinder(CAP_R, CAP_THICKNESS, to_vector(cap_start), to_vector(direction))
        pin = pin.fuse(cap)
    return pin


wheel_shaft_dir = scale3(WHEEL_AXIS, -1.0)
handle_shaft_dir = HANDLE_AXIS

wheel_body = make_yoke(WHEEL_AXIS, WHEEL_HINGE, -1.0)
handle_body = make_yoke(HANDLE_AXIS, HANDLE_HINGE, 1.0)

wheel_gear_center = scale3(wheel_shaft_dir, PRONG_LEN + SHAFT_LEN)
handle_gear_center = scale3(handle_shaft_dir, PRONG_LEN + SHAFT_LEN)
wheel_body = wheel_body.fuse(
    make_end_gear(wheel_gear_center, wheel_shaft_dir, GEAR_TEETH, GEAR_MODULE, GEAR_THICKNESS)
)
handle_body = handle_body.fuse(
    make_end_gear(handle_gear_center, handle_shaft_dir, GEAR_TEETH, GEAR_MODULE, GEAR_THICKNESS)
)

pin_wheel = make_pin_with_retaining_caps(WHEEL_HINGE)
pin_handle = make_pin_with_retaining_caps(HANDLE_HINGE)

cad_step(steps[1])

root = cq.Assembly(name="cardan_joint")

wheel_yoke = cq.Assembly(name="wheel_yoke")
wheel_yoke.add(wheel_body, name="body", color=cq.Color("gold"))
wheel_yoke.add(
    make_marker(wheel_shaft_dir, WHEEL_HINGE, PRONG_LEN + SHAFT_LEN * 0.6),
    name="marker",
    color=cq.Color("red"),
)
root.add(wheel_yoke, name="wheel_yoke")

handle_yoke = cq.Assembly(name="handle_yoke")
handle_yoke.add(handle_body, name="body", color=cq.Color("steelblue"))
handle_yoke.add(
    make_marker(handle_shaft_dir, HANDLE_HINGE, PRONG_LEN + SHAFT_LEN * 0.6),
    name="marker",
    color=cq.Color("white"),
)
root.add(handle_yoke, name="handle_yoke")

cross = cq.Assembly(name="cross")
cross.add(pin_wheel, name="pin_wheel", color=cq.Color(0.85, 0.20, 0.15))
cross.add(pin_handle, name="pin_handle", color=cq.Color(1.0, 0.55, 0.0))
root.add(cross, name="cross")

result = root

cad_step(steps[2])

sample_count = max(2, round(SAMPLES_PER_TURN * TURNS))
handle_times = []
handle_values = []
cross_times = []
cross_values = []
wheel_times = []
wheel_values = []

prev_quat = None
wheel_unwrap = 0.0
prev_wheel_raw = None

for index in range(sample_count + 1):
    fraction = index / sample_count
    theta = 2 * math.pi * TURNS * fraction
    t = DURATION * fraction

    half_theta = theta / 2.0
    handle_times.append(t)
    handle_values.append(
        [
            HANDLE_AXIS[0] * math.sin(half_theta),
            HANDLE_AXIS[1] * math.sin(half_theta),
            HANDLE_AXIS[2] * math.sin(half_theta),
            math.cos(half_theta),
        ]
    )

    p_wheel = driven_pin_dir(theta)
    p_handle = drive_pin_dir(theta)
    p3 = norm3(cross3(p_wheel, p_handle))
    current = mat3_from_cols(p_wheel, p_handle, p3)
    rotation = mat3_mul(current, RrestT)
    quat = mat3_to_quat(rotation)
    if prev_quat is not None and dot3(quat[:3], prev_quat[:3]) + quat[3] * prev_quat[3] < 0:
        quat = tuple(-value for value in quat)
    prev_quat = quat
    cross_times.append(t)
    cross_values.append(list(quat))

    wheel_raw = math.atan2(dot3(p_wheel, WHEEL_BASIS_E2), dot3(p_wheel, WHEEL_HINGE))
    if prev_wheel_raw is not None:
        delta = wheel_raw - prev_wheel_raw
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        wheel_unwrap += delta
    prev_wheel_raw = wheel_raw
    wheel_times.append(t)
    wheel_values.append(math.degrees(wheel_unwrap))

animation = [
    {
        "path": "/cardan_joint/handle_yoke",
        "action": "q",
        "times": handle_times,
        "values": handle_values,
    },
    {
        "path": "/cardan_joint/wheel_yoke",
        "action": "rz",
        "times": wheel_times,
        "values": wheel_values,
    },
    {
        "path": "/cardan_joint/cross",
        "action": "q",
        "times": cross_times,
        "values": cross_values,
    },
]
