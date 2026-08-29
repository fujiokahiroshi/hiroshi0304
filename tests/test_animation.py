import pytest

from cad_workbench import runner
from cad_workbench.runner import _densify_rotation_track


def test_full_turn_gets_intermediate_quaternion_keys() -> None:
    times, values = _densify_rotation_track([0.0, 4.0], [0.0, 720.0])
    assert times == [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    assert values == [0.0, 90.0, 180.0, 270.0, 360.0, 450.0, 540.0, 630.0, 720.0]


def test_reverse_rotation_is_densified() -> None:
    times, values = _densify_rotation_track([0.0, 4.0], [0.0, -360.0])
    assert times == [0.0, 1.0, 2.0, 3.0, 4.0]
    assert values == [0.0, -90.0, -180.0, -270.0, -360.0]


def test_show_does_not_require_nonempty_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, bool, int]] = []

    monkeypatch.setattr(runner, "viewer_reachable", lambda: True)
    monkeypatch.setattr("ocp_vscode.set_port", lambda _port: None)
    monkeypatch.setattr("ocp_vscode.status", lambda **_kwargs: {})
    monkeypatch.setattr(
        "ocp_vscode.show",
        lambda result, reset_camera, port: calls.append((result, reset_camera, port)),
    )

    result = object()
    assert runner._show_and_animate(result, [], 1.0) == 0
    assert calls == [(result, True, runner.VIEWER_PORT)]


def test_show_retries_transient_viewer_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0

    def flaky_show(_result: object, **_kwargs: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("viewer client is still loading")

    monkeypatch.setattr(runner, "viewer_reachable", lambda: True)
    monkeypatch.setattr("ocp_vscode.set_port", lambda _port: None)
    monkeypatch.setattr("ocp_vscode.show", flaky_show)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    assert runner._show_and_animate(object(), [], 1.0) == 0
    assert attempts == 2
