import base64
from pathlib import Path

import pytest
from mcp.types import ImageContent, TextContent

from cad_workbench import server


def test_get_cad_preview_returns_mcp_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    png = b"\x89PNG\r\n\x1a\npreview"

    def fake_save_screenshot(filename: str, **_kwargs: object) -> None:
        Path(filename).write_bytes(png)

    monkeypatch.setattr(server, "PREVIEW_DIR", tmp_path)
    monkeypatch.setattr(server, "viewer_reachable", lambda: True)
    monkeypatch.setattr("ocp_vscode.save_screenshot", fake_save_screenshot)

    result = server.get_cad_preview()

    assert isinstance(result[0], TextContent)
    assert isinstance(result[1], ImageContent)
    assert result[1].mime_type == "image/png"
    assert base64.b64decode(result[1].data) == png


def test_get_cad_preview_requires_viewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "viewer_reachable", lambda: False)

    with pytest.raises(ConnectionError):
        server.get_cad_preview()
