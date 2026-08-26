import pytest

from cad_workbench.state import VIEWER_PORT
from cad_workbench.validation import UnsafeCodeError, validate_code


def test_accepts_cadquery_model() -> None:
    assert VIEWER_PORT == 3939
    validate_code("import cadquery as cq\nresult = cq.Workplane('XY').box(1, 2, 3)")


@pytest.mark.parametrize("code", ["import os\nresult = None", "result = open('x').read()",
                                   "result = (1).__class__", "exec('result = 1')"])
def test_rejects_host_access(code: str) -> None:
    with pytest.raises(UnsafeCodeError):
        validate_code(code)
