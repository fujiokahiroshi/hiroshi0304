import pytest

from cad_workbench.server import _cardan_joint_code, create_cardan_joint_animation
from cad_workbench.validation import validate_code


def test_cardan_joint_template_is_valid_and_complete() -> None:
    code = _cardan_joint_code()

    validate_code(code)
    assert 'cq.Assembly(name="cardan_joint")' in code
    assert 'name="wheel_yoke"' in code
    assert 'name="handle_yoke"' in code
    assert 'name="pin_wheel"' in code
    assert 'name="pin_handle"' in code
    assert '"path": "/cardan_joint/wheel_yoke"' in code
    assert '"path": "/cardan_joint/handle_yoke"' in code
    assert '"path": "/cardan_joint/cross"' in code
    assert '"action": "q"' in code


def test_cardan_joint_animation_speed_validation() -> None:
    with pytest.raises(ValueError, match="animation_speed"):
        create_cardan_joint_animation(animation_speed=0.0)
