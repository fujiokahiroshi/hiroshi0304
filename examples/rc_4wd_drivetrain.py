import cadquery as cq
import math

# 1/10 touring-car drivetrain concept (dimensions in millimetres)
WHEELBASE = 257.0
TRACK = 160.0
WHEEL_DIAMETER = 67.0
WHEEL_WIDTH = 26.0
AXLE_HEIGHT = 22.0

SPUR_TEETH = 70
MOTOR_PINION_TEETH = 22
DIFF_RING_TEETH = 39
DIFF_PINION_TEETH = 15
GEAR_MODULE = 0.6

PRIMARY_RATIO = SPUR_TEETH / MOTOR_PINION_TEETH
FINAL_DRIVE_RATIO = DIFF_RING_TEETH / DIFF_PINION_TEETH
TOTAL_RATIO = PRIMARY_RATIO * FINAL_DRIVE_RATIO

steps = [
    "車体基準寸法と軸位置を設定",
    "540モーターと70T/22T一次減速を配置",
    "センタープロペラシャフトを配置",
    "前後39T/15Tファイナルドライブを配置",
    "車軸・ホイールと回転アニメーションを設定",
]


def make_spur_gear(teeth, module, width, bore, axis="z"):
    """Fast conceptual gear: root ring and unfused teeth in one Compound."""
    pitch_radius = module * teeth / 2.0
    root_radius = pitch_radius - 1.25 * module
    outer_radius = pitch_radius + module
    root_width = math.pi * module * 0.56
    tip_width = math.pi * module * 0.27
    root = (
        cq.Workplane("XY")
        .circle(root_radius)
        .circle(bore / 2.0)
        .extrude(width / 2.0, both=True)
        .val()
    )
    tooth = (
        cq.Workplane("XY")
        .polyline([
            (root_radius - 0.03 * module, -root_width / 2.0),
            (outer_radius, -tip_width / 2.0),
            (outer_radius, tip_width / 2.0),
            (root_radius - 0.03 * module, root_width / 2.0),
        ])
        .close()
        .extrude(width / 2.0, both=True)
        .val()
    )
    parts = [root]
    for index in range(teeth):
        parts.append(tooth.rotate((0, 0, 0), (0, 0, 1), index * 360.0 / teeth))
    gear = cq.Compound.makeCompound(parts)
    if axis == "x":
        return gear.rotate((0, 0, 0), (0, 1, 0), 90.0)
    if axis == "y":
        return gear.rotate((0, 0, 0), (1, 0, 0), -90.0)
    return gear


def shaft_x(length, diameter):
    return cq.Workplane("YZ").circle(diameter / 2.0).extrude(length / 2.0, both=True).val()


def shaft_y(length, diameter):
    return cq.Workplane("XZ").circle(diameter / 2.0).extrude(length / 2.0, both=True).val()


def wheel_parts(y):
    radius = WHEEL_DIAMETER / 2.0
    tire = (
        cq.Workplane("XZ")
        .circle(radius)
        .circle(24.0)
        .extrude(WHEEL_WIDTH / 2.0, both=True)
        .val()
    )
    transverse_groove = (
        cq.Workplane("XY")
        .box(4.0, WHEEL_WIDTH + 2.0, 3.0)
        .translate((radius, 0, 0))
        .val()
    )
    for index in range(16):
        tire = tire.cut(
            transverse_groove.rotate((0, 0, 0), (0, 1, 0), index * 360.0 / 16)
        )
    center_groove = cq.Solid.makeTorus(radius - 0.5, 0.75, dir=(0, 1, 0))
    tire = tire.cut(center_groove).translate((0, y, 0))
    rim = (
        cq.Workplane("XZ")
        .circle(24.0)
        .circle(4.0)
        .extrude((WHEEL_WIDTH - 4.0) / 2.0, both=True)
        .translate((0, y, 0))
        .val()
    )
    return tire, rim

cad_step(steps[0])
fixed = cq.Assembly(name="fixed_structure")
chassis = (
    cq.Workplane("XY")
    .box(310.0, 150.0, 4.0)
    .edges("|Z")
    .fillet(8.0)
    .translate((0, 0, 4.0))
)
fixed.add(chassis, name="chassis_plate", color=cq.Color("gray"))
for x in (-WHEELBASE / 2.0, WHEELBASE / 2.0):
    housing = (
        cq.Workplane("XZ")
        .circle(20.0)
        .circle(14.5)
        .extrude(18.0, both=True)
        .translate((x, 0, AXLE_HEIGHT))
    )
    fixed.add(housing, name=f"diff_housing_{'front' if x > 0 else 'rear'}", color=cq.Color(0.15, 0.55, 0.95, 0.16))
    for y in (-55.0, 55.0):
        support = cq.Workplane("XY").box(8.0, 12.0, 24.0).translate((x, y, 14.0))
        fixed.add(support, name=f"bearing_support_{int(x)}_{int(y)}", color=cq.Color("gray"))

cad_step(steps[1])
gear_x = -43.0
motor_y = -(GEAR_MODULE * (SPUR_TEETH + MOTOR_PINION_TEETH) / 2.0)
motor_body = shaft_x(50.0, 36.0).translate((-70.0, motor_y, AXLE_HEIGHT))
motor_endbell = shaft_x(3.0, 38.0).translate((-96.5, motor_y, AXLE_HEIGHT))
fixed.add(motor_body, name="540_motor", color=cq.Color("gray"))
fixed.add(motor_endbell, name="motor_endbell", color=cq.Color("royalblue"))

motor_output = cq.Assembly(name="motor_output")
motor_output.add(shaft_x(15.0, 3.2), name="motor_shaft", color=cq.Color("gray"))
motor_output.add(
    make_spur_gear(MOTOR_PINION_TEETH, GEAR_MODULE, 5.0, 3.2, "x"),
    name="pinion_22T",
    color=cq.Color("gold"),
)

cad_step(steps[2])
center_drive = cq.Assembly(name="center_drive")
center_drive.add(shaft_x(222.0, 5.0), name="propeller_shaft", color=cq.Color("orange"))
center_drive.add(
    make_spur_gear(SPUR_TEETH, GEAR_MODULE, 6.0, 5.0, "x").translate((gear_x, 0, 0)),
    name="spur_70T",
    color=cq.Color("steelblue"),
)
for x, label in ((-112.0, "rear"), (112.0, "front")):
    center_drive.add(
        make_spur_gear(DIFF_PINION_TEETH, GEAR_MODULE, 5.0, 5.0, "x").translate((x, 0, 0)),
        name=f"{label}_input_15T",
        color=cq.Color("gold"),
    )

cad_step(steps[3])

SIDE_TEETH = 24
SPIDER_TEETH = 12
DIFF_FACE_WIDTH = 4.0
TURN_BIAS = 0.25


def make_visual_bevel_gear(teeth, module, width, bore):
    pitch_radius = module * teeth / 2.0
    root_large = pitch_radius - 1.15 * module
    outer_large = pitch_radius + module
    root_small = root_large * 0.66
    outer_small = outer_large * 0.66
    root_width = math.pi * module * 0.54
    tip_width = math.pi * module * 0.25
    root = (
        cq.Workplane("XY")
        .circle(root_large)
        .workplane(offset=width)
        .circle(root_small)
        .loft(combine=True)
        .val()
    )
    if bore > 0:
        cutter = cq.Workplane("XY", origin=(0, 0, -0.5)).circle(bore / 2.0).extrude(width + 1.0).val()
        root = root.cut(cutter)
    tooth = (
        cq.Workplane("XY")
        .polyline([
            (root_large, -root_width / 2.0),
            (outer_large, -tip_width / 2.0),
            (outer_large, tip_width / 2.0),
            (root_large, root_width / 2.0),
        ])
        .close()
        .workplane(offset=width)
        .polyline([
            (root_small, -root_width * 0.66 / 2.0),
            (outer_small, -tip_width * 0.66 / 2.0),
            (outer_small, tip_width * 0.66 / 2.0),
            (root_small, root_width * 0.66 / 2.0),
        ])
        .close()
        .loft(combine=True)
        .val()
    )
    parts = [root]
    for index in range(teeth):
        parts.append(tooth.rotate((0, 0, 0), (0, 0, 1), index * 360.0 / teeth))
    return cq.Compound.makeCompound(parts)


def differential_assembly(name):
    differential = cq.Assembly(name=name)

    carrier = cq.Assembly(name="carrier")
    ring_gear = make_spur_gear(DIFF_RING_TEETH, GEAR_MODULE, 3.0, 16.0, "y")
    carrier.add(ring_gear, name="ring_gear_39T", color=cq.Color("red"))

    carrier_radius = 10.5
    for y, label in ((-9.5, "right"), (9.5, "left")):
        cage_ring = (
            cq.Workplane("XZ")
            .circle(carrier_radius)
            .circle(carrier_radius - 1.8)
            .extrude(1.2, both=True)
            .translate((0, y, 0))
            .val()
        )
        carrier.add(cage_ring, name=f"{label}_carrier_ring", color=cq.Color("orange"))
    for index, angle in enumerate((0.0, 90.0, 180.0, 270.0)):
        x = (carrier_radius - 1.0) * math.cos(math.radians(angle))
        z = (carrier_radius - 1.0) * math.sin(math.radians(angle))
        carrier.add(
            shaft_y(19.0, 1.8).translate((x, 0, z)),
            name=f"cage_rod_{index}",
            color=cq.Color("orange"),
        )
    carrier.add(shaft_x(17.0, 2.0), name="cross_shaft", color=cq.Color("gray"))

    spider_raw = make_visual_bevel_gear(SPIDER_TEETH, GEAR_MODULE, DIFF_FACE_WIDTH, 2.1)
    spider_top = cq.Assembly(name="spider_top")
    spider_top.add(spider_raw, name="gear_12T", color=cq.Color("steelblue"))
    spider_bottom = cq.Assembly(name="spider_bottom")
    spider_bottom.add(
        spider_raw.rotate((0, 0, 0), (1, 0, 0), 180.0),
        name="gear_12T",
        color=cq.Color("royalblue"),
    )
    carrier.add(spider_top, name="spider_top")
    carrier.add(spider_bottom, name="spider_bottom")
    differential.add(carrier, name="carrier")

    side_raw = make_visual_bevel_gear(SIDE_TEETH, GEAR_MODULE, DIFF_FACE_WIDTH, 5.1)

    left_output = cq.Assembly(name="left_output")
    left_output.add(
        side_raw.rotate((0, 0, 0), (1, 0, 0), -90.0),
        name="side_gear_24T",
        color=cq.Color("gold"),
    )
    left_output.add(
        shaft_y(TRACK / 2.0 + 11.0, 5.0).translate((0, (TRACK / 2.0 + 11.0) / 2.0, 0)),
        name="half_shaft",
        color=cq.Color("gray"),
    )
    left_tire, left_rim = wheel_parts(TRACK / 2.0)
    left_output.add(left_tire, name="tire", color=cq.Color("black"))
    left_output.add(left_rim, name="wheel", color=cq.Color("white"))
    differential.add(left_output, name="left_output")

    right_output = cq.Assembly(name="right_output")
    right_output.add(
        side_raw.rotate((0, 0, 0), (1, 0, 0), 90.0),
        name="side_gear_24T",
        color=cq.Color("gold"),
    )
    right_output.add(
        shaft_y(TRACK / 2.0 + 11.0, 5.0).translate((0, -(TRACK / 2.0 + 11.0) / 2.0, 0)),
        name="half_shaft",
        color=cq.Color("gray"),
    )
    right_tire, right_rim = wheel_parts(-TRACK / 2.0)
    right_output.add(right_tire, name="tire", color=cq.Color("black"))
    right_output.add(right_rim, name="wheel", color=cq.Color("white"))
    differential.add(right_output, name="right_output")
    return differential


front_diff = differential_assembly("front_diff")
rear_diff = differential_assembly("rear_diff")

result = cq.Assembly(name="rc_4wd_drivetrain")
result.add(fixed, name="fixed_structure")
result.add(
    motor_output,
    name="motor_output",
    loc=cq.Location(cq.Vector(gear_x, motor_y, AXLE_HEIGHT)),
)
result.add(
    center_drive,
    name="center_drive",
    loc=cq.Location(cq.Vector(0, 0, AXLE_HEIGHT)),
)
result.add(
    front_diff,
    name="front_diff",
    loc=cq.Location(cq.Vector(WHEELBASE / 2.0, 0, AXLE_HEIGHT)),
)
result.add(
    rear_diff,
    name="rear_diff",
    loc=cq.Location(cq.Vector(-WHEELBASE / 2.0, 0, AXLE_HEIGHT)),
)

cad_step(steps[4])
carrier_angle = 360.0
left_angle = carrier_angle * (1.0 + TURN_BIAS)
right_angle = carrier_angle * (1.0 - TURN_BIAS)
spider_angle = -(left_angle - carrier_angle) * SIDE_TEETH / SPIDER_TEETH
center_angle = -carrier_angle * FINAL_DRIVE_RATIO
motor_angle = -center_angle * PRIMARY_RATIO

animation = [
    {"path": "/rc_4wd_drivetrain/motor_output", "action": "rx", "times": [0.0, 6.0], "values": [0.0, motor_angle]},
    {"path": "/rc_4wd_drivetrain/center_drive", "action": "rx", "times": [0.0, 6.0], "values": [0.0, center_angle]},
]
for differential_name in ("front_diff", "rear_diff"):
    base = f"/rc_4wd_drivetrain/{differential_name}"
    animation.extend([
        {"path": f"{base}/carrier", "action": "ry", "times": [0.0, 6.0], "values": [0.0, carrier_angle]},
        {"path": f"{base}/left_output", "action": "ry", "times": [0.0, 6.0], "values": [0.0, left_angle]},
        {"path": f"{base}/right_output", "action": "ry", "times": [0.0, 6.0], "values": [0.0, right_angle]},
        {"path": f"{base}/carrier/spider_top", "action": "rz", "times": [0.0, 6.0], "values": [0.0, spider_angle]},
        {"path": f"{base}/carrier/spider_bottom", "action": "rz", "times": [0.0, 6.0], "values": [0.0, -spider_angle]},
    ])
