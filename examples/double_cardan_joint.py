"""Double (W/Z-configuration) Cardan joint that restores constant velocity.

Input and output shafts are parallel, offset by an intermediate shaft tilted
BETA_DEG from each. A single universal joint would make the output speed
fluctuate (see cardan_joint.py); wiring two joints in series through a
correctly *phased* intermediate shaft -- its two fork hinges built parallel
to each other, not twisted -- makes the second joint's non-uniformity exactly
cancel the first joint's, so the output tracks the input 1:1 at every instant.
This file derives that phasing from the pin directions and verifies it
numerically (see tests/test_double_cardan_joint.py) rather than assuming it.
"""

import math

import cadquery as cq

steps = [
    "入力ヨーク・中間シャフト・出力ヨークを配置",
    "2つのクロス（十字）を組み込む",
    "位相を揃えた中間シャフトで非等速を打ち消すアニメーションを設定",
]

BETA_DEG = 25.0
TURNS = 3.0
DURATION = 8.0
SAMPLES_PER_TURN = 24
INTERMEDIATE_LENGTH = 70.0

SHAFT_R = 4.0
SHAFT_LEN = 24.0
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
INPUT_AXIS = (0.0, 0.0, 1.0)
INTERMEDIATE_AXIS = (0.0, math.sin(BETA), math.cos(BETA))
OUTPUT_AXIS = (0.0, 0.0, 1.0)  # parallel to input -- Z-fold layout

R1 = (1.0, 0.0, 0.0)


def drive1_dir(theta):
    """Input yoke's pin direction; input spins uniformly about INPUT_AXIS."""
    return rotate_about_axis(R1, INPUT_AXIS, theta)


def driven1_dir(theta):
    """Intermediate shaft's joint-1 pin direction -- derived, not assigned."""
    return norm3(cross3(drive1_dir(theta), INTERMEDIATE_AXIS))


HINGE_A0 = driven1_dir(0.0)  # intermediate shaft's hinge toward joint 1
# In-phase double Cardan: the intermediate shaft's OTHER fork (toward joint 2)
# is built parallel to this one, not twisted -- verified numerically to give
# zero net velocity fluctuation for the equal-angle Z-fold layout used here.
HINGE_B0 = HINGE_A0

HINGE_C0 = norm3(cross3(HINGE_B0, OUTPUT_AXIS))  # output yoke's rest hinge

BASIS2_A = norm3(cross3(INTERMEDIATE_AXIS, HINGE_A0))
BASIS2_C = norm3(cross3(OUTPUT_AXIS, HINGE_C0))


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


cad_step(steps[0])


def make_fork(hinge_dir, prong_axis_dir):
    """Hub + two prongs + bores, centered at the local joint origin, with the
    hub set back along prong_axis_dir (no free shaft -- callers fuse one on)."""
    neck = scale3(prong_axis_dir, PRONG_LEN)
    hub_len = 2 * (FORK_HALF_WIDTH + PRONG_R) + 2.0
    hub_center = sub3(neck, scale3(hinge_dir, hub_len / 2.0))
    body = cq.Solid.makeCylinder(HUB_R, hub_len, to_vector(hub_center), to_vector(hinge_dir))
    for sign in (1.0, -1.0):
        offset = scale3(hinge_dir, sign * FORK_HALF_WIDTH)
        p_start = add3(neck, offset)
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


def make_end_yoke(axis_dir, hinge_dir, extend_sign):
    """Input/output yoke: a fork plus a free shaft extending outward, with an
    end gear -- mirrors cardan_joint.py's make_yoke."""
    axis = scale3(axis_dir, extend_sign)
    body = make_fork(hinge_dir, axis)
    neck = scale3(axis, PRONG_LEN)
    rod = cq.Solid.makeCylinder(SHAFT_R, SHAFT_LEN, to_vector(neck), to_vector(axis))
    body = body.fuse(rod)
    gear_center = scale3(axis, PRONG_LEN + SHAFT_LEN)
    body = body.fuse(make_end_gear(gear_center, axis, GEAR_TEETH, GEAR_MODULE, GEAR_THICKNESS))
    return body


def make_intermediate_shaft(joint2_center):
    """Fork at the origin (toward joint 1) + connecting rod + fork at
    joint2_center (toward joint 2). One rigid body, both forks in phase.

    The rod must start and end at each fork's "neck" (PRONG_LEN in from the
    joint center), not at the joint centers themselves -- otherwise it plows
    straight through the cross pins that sit at those centers."""
    body = make_fork(HINGE_A0, INTERMEDIATE_AXIS)
    neck_a = scale3(INTERMEDIATE_AXIS, PRONG_LEN)
    neck_b = sub3(joint2_center, scale3(INTERMEDIATE_AXIS, PRONG_LEN))
    rod_vec = sub3(neck_b, neck_a)
    rod_len = math.sqrt(dot3(rod_vec, rod_vec))
    rod = cq.Solid.makeCylinder(
        SHAFT_R, rod_len, to_vector(neck_a), to_vector(norm3(rod_vec))
    )
    body = body.fuse(rod)
    far_fork = make_fork(HINGE_B0, scale3(INTERMEDIATE_AXIS, -1.0)).translate(
        to_vector(joint2_center)
    )
    body = body.fuse(far_fork)
    return body


def make_marker(shaft_axis, side_dir, along_len, base=(0.0, 0.0, 0.0)):
    center = add3(base, add3(scale3(shaft_axis, along_len), scale3(side_dir, SHAFT_R)))
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


def make_pin_with_retaining_caps(direction, base=(0.0, 0.0, 0.0)):
    start = add3(base, scale3(direction, -PIN_LEN / 2.0))
    pin = cq.Solid.makeCylinder(PIN_R, PIN_LEN, to_vector(start), to_vector(direction))
    for sign in (1.0, -1.0):
        cap_center = add3(base, scale3(direction, sign * (PIN_LEN / 2.0 - CAP_THICKNESS / 2.0)))
        cap_start = sub3(cap_center, scale3(direction, CAP_THICKNESS / 2.0))
        cap = cq.Solid.makeCylinder(CAP_R, CAP_THICKNESS, to_vector(cap_start), to_vector(direction))
        pin = pin.fuse(cap)
    return pin


joint1_center = (0.0, 0.0, 0.0)
joint2_center = scale3(INTERMEDIATE_AXIS, INTERMEDIATE_LENGTH)

input_body = make_end_yoke(INPUT_AXIS, R1, -1.0)
intermediate_body = make_intermediate_shaft(joint2_center)
# Built centered at the local origin (not translated into the joint2 world
# position) -- the Assembly `loc` below places it, so its "q"/"rz" animation
# rotates about its own shaft axis instead of swinging around the world
# origin (which is not on that axis).
output_body = make_end_yoke(OUTPUT_AXIS, HINGE_C0, 1.0)

pin1_wheel = make_pin_with_retaining_caps(HINGE_A0)
pin1_input = make_pin_with_retaining_caps(R1)
# Also built at the local origin for the same reason; cross2's Assembly loc
# places the whole pin pair at joint2_center.
pin2_wheel = make_pin_with_retaining_caps(HINGE_B0)
pin2_output = make_pin_with_retaining_caps(HINGE_C0)

cad_step(steps[1])

root = cq.Assembly(name="double_cardan_joint")

input_yoke = cq.Assembly(name="input_yoke")
input_yoke.add(input_body, name="body", color=cq.Color("gold"))
input_yoke.add(
    make_marker(scale3(INPUT_AXIS, -1.0), R1, PRONG_LEN + SHAFT_LEN * 0.6),
    name="marker",
    color=cq.Color("red"),
)
root.add(input_yoke, name="input_yoke")

intermediate_yoke = cq.Assembly(name="intermediate_yoke")
intermediate_yoke.add(intermediate_body, name="body", color=cq.Color(0.2, 0.75, 0.3))
intermediate_yoke.add(
    make_marker(INTERMEDIATE_AXIS, HINGE_A0, INTERMEDIATE_LENGTH * 0.35),
    name="marker",
    color=cq.Color("white"),
)
root.add(intermediate_yoke, name="intermediate_yoke")

output_yoke = cq.Assembly(name="output_yoke")
output_yoke.add(output_body, name="body", color=cq.Color("steelblue"))
output_yoke.add(
    make_marker(OUTPUT_AXIS, HINGE_C0, PRONG_LEN + SHAFT_LEN * 0.6),
    name="marker",
    color=cq.Color(1.0, 0.85, 0.0),
)
root.add(output_yoke, name="output_yoke", loc=cq.Location(to_vector(joint2_center)))

cross1 = cq.Assembly(name="cross1")
cross1.add(pin1_input, name="pin_input", color=cq.Color(0.85, 0.20, 0.15))
cross1.add(pin1_wheel, name="pin_intermediate", color=cq.Color(1.0, 0.55, 0.0))
root.add(cross1, name="cross1")

cross2 = cq.Assembly(name="cross2")
cross2.add(pin2_wheel, name="pin_intermediate", color=cq.Color(1.0, 0.55, 0.0))
cross2.add(pin2_output, name="pin_output", color=cq.Color(0.55, 0.20, 0.85))
root.add(cross2, name="cross2", loc=cq.Location(to_vector(joint2_center)))

result = root

cad_step(steps[2])

sample_count = max(2, round(SAMPLES_PER_TURN * TURNS))
cross1_times = []
cross1_values = []
cross2_times = []
cross2_values = []
intermediate_times = []
intermediate_values = []
output_times = []
output_values = []

prev_quat1 = None
prev_quat2 = None
phi1_unwrap = 0.0
prev_phi1_raw = None
phi2_unwrap = 0.0
prev_phi2_raw = None

for index in range(sample_count + 1):
    fraction = index / sample_count
    theta = 2 * math.pi * TURNS * fraction
    t = DURATION * fraction

    p_drive1 = drive1_dir(theta)
    p_driven1 = driven1_dir(theta)
    p3a = norm3(cross3(p_driven1, p_drive1))
    rest1 = mat3_from_cols(HINGE_A0, R1, norm3(cross3(HINGE_A0, R1)))
    current1 = mat3_from_cols(p_driven1, p_drive1, p3a)
    rotation1 = mat3_mul(current1, mat3_transpose(rest1))
    quat1 = mat3_to_quat(rotation1)
    if prev_quat1 is not None and dot3(quat1[:3], prev_quat1[:3]) + quat1[3] * prev_quat1[3] < 0:
        quat1 = tuple(-v for v in quat1)
    prev_quat1 = quat1
    cross1_times.append(t)
    cross1_values.append(list(quat1))

    phi1_raw = math.atan2(dot3(p_driven1, BASIS2_A), dot3(p_driven1, HINGE_A0))
    if prev_phi1_raw is not None:
        delta = phi1_raw - prev_phi1_raw
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        phi1_unwrap += delta
    prev_phi1_raw = phi1_raw
    intermediate_times.append(t)
    intermediate_values.append(math.degrees(phi1_unwrap))

    current_hinge_B = rotate_about_axis(HINGE_B0, INTERMEDIATE_AXIS, phi1_unwrap)
    p_driven2 = norm3(cross3(current_hinge_B, OUTPUT_AXIS))
    p3b = norm3(cross3(p_driven2, current_hinge_B))
    rest2 = mat3_from_cols(HINGE_B0, HINGE_C0, norm3(cross3(HINGE_B0, HINGE_C0)))
    current2 = mat3_from_cols(current_hinge_B, p_driven2, p3b)
    rotation2 = mat3_mul(current2, mat3_transpose(rest2))
    quat2 = mat3_to_quat(rotation2)
    if prev_quat2 is not None and dot3(quat2[:3], prev_quat2[:3]) + quat2[3] * prev_quat2[3] < 0:
        quat2 = tuple(-v for v in quat2)
    prev_quat2 = quat2
    cross2_times.append(t)
    cross2_values.append(list(quat2))

    phi2_raw = math.atan2(dot3(p_driven2, BASIS2_C), dot3(p_driven2, HINGE_C0))
    if prev_phi2_raw is not None:
        delta = phi2_raw - prev_phi2_raw
        while delta > math.pi:
            delta -= 2 * math.pi
        while delta < -math.pi:
            delta += 2 * math.pi
        phi2_unwrap += delta
    prev_phi2_raw = phi2_raw
    output_times.append(t)
    output_values.append(math.degrees(phi2_unwrap))

animation = [
    {
        "path": "/double_cardan_joint/input_yoke",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, 360.0 * TURNS],
    },
    {
        "path": "/double_cardan_joint/intermediate_yoke",
        "action": "q",
        "times": [
            intermediate_times[i]
            for i in range(len(intermediate_times))
        ],
        "values": [
            [
                INTERMEDIATE_AXIS[0] * math.sin(math.radians(v) / 2.0),
                INTERMEDIATE_AXIS[1] * math.sin(math.radians(v) / 2.0),
                INTERMEDIATE_AXIS[2] * math.sin(math.radians(v) / 2.0),
                math.cos(math.radians(v) / 2.0),
            ]
            for v in intermediate_values
        ],
    },
    {
        "path": "/double_cardan_joint/output_yoke",
        "action": "rz",
        "times": output_times,
        "values": output_values,
    },
    {
        "path": "/double_cardan_joint/cross1",
        "action": "q",
        "times": cross1_times,
        "values": cross1_values,
    },
    {
        "path": "/double_cardan_joint/cross2",
        "action": "q",
        "times": cross2_times,
        "values": cross2_values,
    },
]
