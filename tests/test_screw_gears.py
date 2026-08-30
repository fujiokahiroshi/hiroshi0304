import pytest

from cad_workbench.server import _screw_gear_code, create_screw_gear_animation
from cad_workbench.validation import validate_code


def test_screw_gear_template_is_valid_and_complete() -> None:
    code = _screw_gear_code()

    validate_code(code)
    assert 'result = cq.Assembly(name="screw_gear_pair")' in code
    assert 'name="screw_gear_a"' in code
    assert 'name="screw_gear_b"' in code
    assert '"path": "/screw_gear_pair/screw_gear_a"' in code
    assert '"action": "rz"' in code
    assert '"path": "/screw_gear_pair/screw_gear_b"' in code
    assert '"action": "rx"' in code
    assert "helix_a = 45.0" in code
    assert "helix_b = 45.0" in code


def test_screw_gear_animation_speed_validation() -> None:
    with pytest.raises(ValueError, match="animation_speed"):
        create_screw_gear_animation(animation_speed=0.0)
