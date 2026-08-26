from cad_workbench.runner import _densify_rotation_track


def test_full_turn_gets_intermediate_quaternion_keys() -> None:
    times, values = _densify_rotation_track([0.0, 4.0], [0.0, 720.0])
    assert times == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    assert values == [0.0, 90.0, 180.0, 270.0, 360.0, 450.0, 540.0, 630.0, 720.0]


def test_reverse_rotation_is_densified() -> None:
    times, values = _densify_rotation_track([0.0, 4.0], [0.0, -360.0])
    assert times == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert values == [0.0, -90.0, -180.0, -270.0, -360.0]
