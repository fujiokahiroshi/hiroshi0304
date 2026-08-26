import pytest

from cad_workbench.server import _bevel_gear_code, create_bevel_gear_animation
from cad_workbench.validation import validate_code


def test_bevel_code_uses_perpendicular_axes_and_ratio() -> None:
    code = _bevel_gear_code(16, 32, 2.0, 8.0, 6.0, 2.0, 5.0)
    validate_code(code)
    assert '"path": "/bevel_pair/bevel_a"' in code
    assert '"action": "rz"' in code
    assert '"path": "/bevel_pair/bevel_b"' in code
    assert '"action": "rx"' in code
    assert ".rotate((0, 0, 0), (0, 1, 0), 90.0)" in code
    assert '"values": [0.0, -45.0, -90.0' in code


def test_bevel_face_width_validation() -> None:
    with pytest.raises(ValueError, match="歯幅"):
        create_bevel_gear_animation(face_width=100.0)
