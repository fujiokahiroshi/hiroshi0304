import pytest

from cad_workbench.server import (
    _compound_planetary_code,
    create_compound_planetary_animation,
)
from cad_workbench.validation import validate_code


def test_compound_planetary_template_is_valid_and_complete() -> None:
    code = _compound_planetary_code()

    validate_code(code)
    assert 'cq.Assembly(name="compound_planetary_three_shaft")' in code
    assert 'name="inner_gear_teeth"' in code
    assert 'name="outer_gear_teeth"' in code
    assert 'name="carrier_output"' in code
    assert 'name="sun"' in code
    assert 'name=f"planet_{index}"' in code
    assert "NS = 24" in code
    assert "NP = 16" in code
    assert "NR = 56" in code
    assert "SUN_ANGLE = ((NS + NR) * CARRIER_ANGLE - NR * RING_ANGLE) / NS" in code
    assert '"path": "/compound_planetary_three_shaft/blue_compound_ring"' in code
    assert '"path": "/compound_planetary_three_shaft/carrier_output/planet_1"' in code
    assert len([line for line in code.splitlines() if '"action": "rz"' in line]) == 6


def test_compound_planetary_animation_speed_validation() -> None:
    with pytest.raises(ValueError, match="animation_speed"):
        create_compound_planetary_animation(animation_speed=0.0)
