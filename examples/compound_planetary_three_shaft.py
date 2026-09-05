"""Validated placement-first compound planetary animation derived from the user drawing."""

import cadquery as cq
import math

steps = [
    "Place blue compound ring with inner and outer gear zones",
    "Place external input gear, sun, two planets, and moving carrier",
    "Configure three-shaft planetary animation",
]

NS = 24
NP = 16
NR = 56
RING_EXTERNAL_TEETH = 82
INPUT_TEETH = 20
DURATION = 8.0
RING_ANGLE = 360.0
INPUT_ANGLE = -RING_ANGLE * RING_EXTERNAL_TEETH / INPUT_TEETH
CARRIER_ANGLE = RING_ANGLE * 0.5
SUN_ANGLE = ((NS + NR) * CARRIER_ANGLE - NR * RING_ANGLE) / NS
PLANET_RELATIVE_ANGLE = (NR / NP) * (RING_ANGLE - CARRIER_ANGLE)

def disc(radius, thickness, z=0.0):
    return (
        cq.Workplane("XY").circle(radius)
        .extrude(thickness / 2.0, both=True)
        .translate((0, 0, z)).val()
    )

def shaft(radius, length, z_center):
    return (
        cq.Workplane("XY").circle(radius)
        .extrude(length / 2.0, both=True)
        .translate((0, 0, z_center)).val()
    )

def radial_teeth(count, radius, radial_length, tangent_width, thickness, z=0.0):
    solids = []
    for index in range(count):
        angle = 360.0 * index / count
        tooth = (
            cq.Workplane("XY")
            .box(radial_length, tangent_width, thickness)
            .translate((radius, 0, z))
            .rotate((0, 0, 0), (0, 0, 1), angle)
            .val()
        )
        solids.append(tooth)
    return cq.Compound.makeCompound(solids)

def external_gear(body_radius, pitch_radius, visible_teeth, thickness, z=0.0):
    return cq.Compound.makeCompound([
        disc(body_radius, thickness, z),
        radial_teeth(visible_teeth, pitch_radius, 2.5, 2.1, thickness, z),
    ])

def rotation_marker(length, z):
    return (
        cq.Workplane("XY").box(length, 1.8, 0.9)
        .translate((length / 2.0, 0, z)).val()
    )

cad_step(steps[0])
root = cq.Assembly(name="compound_planetary_three_shaft")
blue_ring = cq.Assembly(name="blue_compound_ring")
blue_ring.add(
    cq.Workplane("XY").circle(40.0).circle(30.0).extrude(3.0, both=True).val(),
    name="shared_ring_body",
    color=cq.Color(0.18, 0.52, 0.92, 0.48),
)
blue_ring.add(
    radial_teeth(28, 28.7, 2.6, 2.2, 6.0),
    name="inner_gear_teeth",
    color=cq.Color(0.12, 0.42, 0.82),
)
blue_ring.add(
    radial_teeth(36, 41.2, 2.6, 2.2, 6.0),
    name="outer_gear_teeth",
    color=cq.Color(0.12, 0.42, 0.82),
)
blue_ring.add(rotation_marker(37.0, 3.6), name="ring_rotation_marker", color=cq.Color("white"))
root.add(blue_ring, name="blue_compound_ring")

cad_step(steps[1])
external_input = cq.Assembly(name="external_input")
external_input.add(
    external_gear(8.8, 9.8, 10, 6.0),
    name="input_gear",
    color=cq.Color(0.72, 0.34, 0.90),
)
external_input.add(shaft(2.8, 28.0, -14.0), name="input_shaft", color=cq.Color(0.72, 0.34, 0.90))
external_input.add(rotation_marker(8.0, 3.6), name="input_marker", color=cq.Color("white"))
root.add(external_input, name="external_input", loc=cq.Location(cq.Vector(51.0, 0, 0)))

sun = cq.Assembly(name="sun")
sun.add(external_gear(10.6, 11.8, 12, 6.0), name="sun_24t", color=cq.Color(1.0, 0.76, 0.08))
sun.add(shaft(3.0, 26.0, -16.0), name="sun_output_shaft", color=cq.Color(1.0, 0.76, 0.08))
sun.add(rotation_marker(9.0, 3.6), name="sun_marker", color=cq.Color(0.90, 0.12, 0.10))
root.add(sun, name="sun")

carrier = cq.Assembly(name="carrier_output")
carrier.add(
    cq.Workplane("XY").box(3.2, 40.0, 2.5).translate((0, 0, 13.0)).val(),
    name="carrier_bar",
    color=cq.Color(0.20, 0.78, 0.30, 0.82),
)
carrier.add(disc(5.0, 3.0, 13.0), name="carrier_hub", color=cq.Color(0.20, 0.78, 0.30))
carrier.add(shaft(3.5, 28.0, 27.0), name="carrier_output_shaft", color=cq.Color(0.20, 0.78, 0.30))
carrier.add(external_gear(8.8, 9.8, 10, 5.0, 25.0), name="green_carrier_output_gear", color=cq.Color(0.10, 0.62, 0.22))
carrier.add(rotation_marker(8.0, 28.0), name="carrier_rotation_marker", color=cq.Color("white"))

for index, y in enumerate((20.0, -20.0), start=1):
    carrier.add(
        shaft(2.0, 18.0, 6.0),
        name=f"planet_pin_{index}",
        color=cq.Color(0.68, 0.72, 0.75),
        loc=cq.Location(cq.Vector(0, y, 0)),
    )
    planet = cq.Assembly(name=f"planet_{index}")
    planet.add(external_gear(6.7, 7.8, 8, 6.0), name="planet_16t", color=cq.Color(0.95, 0.42, 0.10))
    planet.add(rotation_marker(6.0, 3.6), name="planet_marker", color=cq.Color("white"))
    carrier.add(planet, name=f"planet_{index}", loc=cq.Location(cq.Vector(0, y, 0)))

root.add(carrier, name="carrier_output")
result = root

cad_step(steps[2])
animation = [
    {
        "path": "/compound_planetary_three_shaft/external_input",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, INPUT_ANGLE],
    },
    {
        "path": "/compound_planetary_three_shaft/blue_compound_ring",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, RING_ANGLE],
    },
    {
        "path": "/compound_planetary_three_shaft/carrier_output",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, CARRIER_ANGLE],
    },
    {
        "path": "/compound_planetary_three_shaft/sun",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, SUN_ANGLE],
    },
    {
        "path": "/compound_planetary_three_shaft/carrier_output/planet_1",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, PLANET_RELATIVE_ANGLE],
    },
    {
        "path": "/compound_planetary_three_shaft/carrier_output/planet_2",
        "action": "rz",
        "times": [0.0, DURATION],
        "values": [0.0, PLANET_RELATIVE_ANGLE],
    },
]
