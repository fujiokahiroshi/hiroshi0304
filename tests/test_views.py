import base64
import json
from pathlib import Path

import pytest
from mcp.types import ImageContent, TextContent
from ocp_vscode import Camera

from cad_workbench import server


def test_get_cad_views_returns_images_and_restores_camera(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    png = b"\x89PNG\r\n\x1a\nview"
    config_calls: list[dict[str, object]] = []
    original = {
        "position": [1, 2, 3],
        "quaternion": [0, 0, 0, 1],
        "target": [0, 0, 0],
        "zoom": 1.25,
    }

    def fake_save_screenshot(filename: str, **_kwargs: object) -> None:
        Path(filename).write_bytes(png)

    def fake_set_viewer_config(**kwargs: object) -> None:
        config_calls.append(kwargs)

    monkeypatch.setattr(server, "PREVIEW_DIR", tmp_path)
    monkeypatch.setattr(server, "viewer_reachable", lambda: True)
    monkeypatch.setattr("ocp_vscode.status", lambda **_kwargs: original)
    monkeypatch.setattr("ocp_vscode.set_viewer_config", fake_set_viewer_config)
    monkeypatch.setattr("ocp_vscode.save_screenshot", fake_save_screenshot)
    monkeypatch.setattr("time.sleep", lambda _seconds: None)

    result = server.get_cad_views(["front", "top"])

    assert isinstance(result[0], TextContent)
    metadata = json.loads(result[0].text)
    assert metadata["view_count"] == 2
    assert metadata["camera_restored"] is True
    assert [capture["view"] for capture in metadata["captures"]] == ["front", "top"]
    assert len(result) == 3
    assert all(isinstance(item, ImageContent) for item in result[1:])
    assert all(base64.b64decode(item.data) == png for item in result[1:])
    assert config_calls[0]["reset_camera"] == Camera.FRONT
    assert config_calls[1]["reset_camera"] == Camera.TOP
    assert config_calls[-1]["reset_camera"] == Camera.KEEP
    assert config_calls[-1]["position"] == original["position"]


def test_get_cad_views_rejects_invalid_view(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "viewer_reachable", lambda: True)

    with pytest.raises(ValueError, match="unsupported views"):
        server.get_cad_views(["diagonal"])


def test_get_cad_views_requires_viewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(server, "viewer_reachable", lambda: False)

    with pytest.raises(ConnectionError):
        server.get_cad_views(["iso"])
