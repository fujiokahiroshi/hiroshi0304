from cad_workbench.server import _rc_4wd_drivetrain_code
from cad_workbench.validation import validate_code


def test_rc_4wd_template_is_valid_and_complete() -> None:
    code = _rc_4wd_drivetrain_code()

    validate_code(code)
    assert 'result = cq.Assembly(name="rc_4wd_drivetrain")' in code
    assert "cq.Color(0.15, 0.55, 0.95, 0.16)" in code
    assert 'name="ring_gear_39T"' in code
    assert 'name="side_gear_24T"' in code
    assert 'name="gear_12T"' in code
    assert 'name="front_diff"' in code
    assert 'name="rear_diff"' in code
    assert "TURN_BIAS = 0.25" in code
    assert "spider_angle" in code
    assert "transverse_groove" in code
    assert "center_groove" in code
