import pytest

from cad_workbench.server import _gear_code, create_gear_animation
from cad_workbench.validation import validate_code


def test_gear_code_has_correct_ratio_and_paths() -> None:
    code = _gear_code(20, 40, 2.0, 8.0, 6.0, 2.0, 4.0)
    validate_code(code)
    assert '"path": "/gear_train/gear_a"' in code
    assert '"path": "/gear_train/gear_b"' in code
    assert '"values": [0.0, 90.0, 180.0' in code
    assert '"values": [0.0, -45.0, -90.0' in code
    assert code.count('"times": [0.0, 0.5, 1.0') == 2
    assert "cq.Vector(60.0, 0, 0)" in code
    assert 'name="rotation_marker"' in code
    assert 'color=cq.Color("red")' in code


def test_gear_parameters_are_validated_before_viewer_call() -> None:
    with pytest.raises(ValueError, match="歯数"):
        create_gear_animation(teeth_a=4)
