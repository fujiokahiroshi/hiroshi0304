import pytest

from cad_workbench.server import (
    _double_cardan_joint_code,
    create_double_cardan_joint_animation,
)
from cad_workbench.validation import validate_code


def test_double_cardan_joint_template_is_valid_and_complete() -> None:
    code = _double_cardan_joint_code()

    validate_code(code)
    assert 'cq.Assembly(name="double_cardan_joint")' in code
    assert 'name="input_yoke"' in code
    assert 'name="intermediate_yoke"' in code
    assert 'name="output_yoke"' in code
    assert 'name="cross1"' in code
    assert 'name="cross2"' in code
    assert "HINGE_B0 = HINGE_A0" in code  # in-phase intermediate shaft


def test_double_cardan_joint_cancels_velocity_fluctuation() -> None:
    """The whole point of a double Cardan joint: output angle must track input
    angle exactly (no non-constant-velocity wobble), unlike the single joint."""
    namespace: dict[str, object] = {
        "cad_step": lambda *_: None,
        "__name__": "__test__",
    }
    exec(compile(_double_cardan_joint_code(), "model.py", "exec"), namespace)  # noqa: S102

    output_values = namespace["output_values"]
    sample_count = namespace["sample_count"]
    turns = namespace["TURNS"]

    max_deviation = max(
        abs(output_values[i] - 360.0 * turns * i / sample_count)
        for i in range(sample_count + 1)
    )
    assert max_deviation < 1e-6


def test_double_cardan_joint_animation_speed_validation() -> None:
    with pytest.raises(ValueError, match="animation_speed"):
        create_double_cardan_joint_animation(animation_speed=0.0)


def test_double_cardan_joint_quaternion_tracks_are_unit_and_smooth() -> None:
    """Regression test for a mixed-handedness bug: the cross2 rotation matrix
    was built from a left-handed third basis column (cross(col2, col1) instead
    of cross(col1, col2)) while its rest pose used the right-handed convention.
    The resulting quaternions were not unit length and jumped wildly between
    otherwise-adjacent keyframes, making the fork and cross visibly separate
    mid-animation even though the underlying pin-direction math was correct."""
    namespace: dict[str, object] = {
        "cad_step": lambda *_: None,
        "__name__": "__test__",
    }
    exec(compile(_double_cardan_joint_code(), "model.py", "exec"), namespace)  # noqa: S102

    for track_name in ("cross1_values", "cross2_values"):
        values = namespace[track_name]
        for quat in values:
            norm = sum(component * component for component in quat) ** 0.5
            assert abs(norm - 1.0) < 1e-9, f"{track_name} has a non-unit quaternion: {quat}"

        for previous, current in zip(values, values[1:]):
            dot = sum(a * b for a, b in zip(previous, current))
            assert abs(dot) > 0.9, (
                f"{track_name} has a large jump between adjacent keyframes "
                f"(|dot|={abs(dot):.3f}): {previous} -> {current}"
            )
