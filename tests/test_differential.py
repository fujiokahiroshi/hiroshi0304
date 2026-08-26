import pytest

from cad_workbench.server import _differential_code, create_differential_animation
from cad_workbench.validation import validate_code


def test_differential_has_five_linked_tracks() -> None:
    code = _differential_code(24, 12, 1.5, 5.0, 5.0, 1.0, 0.5, 6.0)
    validate_code(code)
    assert '"path": "/differential/left_side"' in code
    assert '"path": "/differential/right_side"' in code
    assert '"path": "/differential/carrier"' in code
    assert '"path": "/differential/carrier/pinion_top"' in code
    assert '"path": "/differential/carrier/pinion_bottom"' in code
    assert "540.0" in code
    assert "180.0" in code
    assert "360.0" in code


def test_differential_bias_is_validated() -> None:
    with pytest.raises(ValueError, match="turn_bias"):
        create_differential_animation(turn_bias=1.0)
