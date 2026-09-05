from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from builtins import __build_class__
from pathlib import Path
from typing import Any

import cadquery as cq

from .state import VIEWER_HOST, VIEWER_PORT, viewer_reachable, write_state
from .validation import extract_literal_steps, validate_code

SAFE_BUILTINS = {
    "__build_class__": __build_class__,
    "abs": abs,
    "all": all,
    "any": any,
    "bool": bool,
    "dict": dict,
    "enumerate": enumerate,
    "float": float,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "print": print,
    "range": range,
    "round": round,
    "set": set,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _safe_import(name: str, globals=None, locals=None, fromlist=(), level=0):
    if name.split(".")[0] not in {"cadquery", "math"}:
        raise ImportError(f"importは禁止されています: {name}")
    return __import__(name, globals, locals, fromlist, level)


def _normalize_steps(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:300] for item in value[:100]]


def _export(result: Any, output_dir: Path, formats: list[str]) -> list[str]:
    exported: list[str] = []
    for extension in formats:
        extension = extension.lower().lstrip(".")
        if extension not in {"step", "stl"}:
            continue
        target = output_dir / f"model.{extension}"
        if isinstance(result, cq.Assembly):
            result.save(str(target), exportType=extension.upper())
        else:
            cq.exporters.export(result, str(target))
        exported.append(str(target))
    return exported


def _densify_rotation_track(
    times: list[float], values: list[float], max_angle_step: float = 90.0
) -> tuple[list[float], list[float]]:
    """Split large Euler-angle intervals before OCP converts them to quaternions.

    Without intermediate keys, 0→360° and 0→720° have identical endpoint
    quaternions, so three.js correctly interpolates them as no movement.
    """
    if len(times) != len(values) or len(times) < 2:
        return times, values
    dense_times = [float(times[0])]
    dense_values = [float(values[0])]
    for start_time, end_time, start_value, end_value in zip(
        times[:-1], times[1:], values[:-1], values[1:], strict=True
    ):
        segments = max(1, math.ceil(abs(float(end_value) - float(start_value)) / max_angle_step))
        for segment in range(1, segments + 1):
            fraction = segment / segments
            dense_times.append(float(start_time) + (float(end_time) - float(start_time)) * fraction)
            dense_values.append(
                float(start_value) + (float(end_value) - float(start_value)) * fraction
            )
    return dense_times, dense_values


def _show_and_animate(result: Any, tracks: list[dict[str, Any]], speed: float) -> int:
    from ocp_vscode import Animation, set_port, show

    if not viewer_reachable():
        raise ConnectionError(
            f"OCP CAD Viewerに接続できません: http://{VIEWER_HOST}:{VIEWER_PORT}。"
            "先に C:\\V8_CAD\\start.ps1 を実行してください。"
        )
    set_port(VIEWER_PORT)
    last_show_error: Exception | None = None
    for attempt in range(20):
        try:
            show(result, reset_camera=True, port=VIEWER_PORT)
            break
        except (ConnectionError, OSError, RuntimeError, TimeoutError, ValueError) as exc:
            last_show_error = exc
            if attempt < 19:
                time.sleep(0.25)
    else:
        detail = (
            f" ({type(last_show_error).__name__}: {last_show_error})"
            if last_show_error is not None
            else ""
        )
        raise ConnectionError(
            "OCP CAD Viewerへモデルを送信できません。"
            f"http://{VIEWER_HOST}:{VIEWER_PORT} を開いてから再実行してください。"
            f"{detail}"
        )
    if not tracks:
        return 0
    animation = Animation()
    for track in tracks:
        action = str(track["action"])
        times = [float(item) for item in track["times"]]
        values = track["values"]
        if action in {"rx", "ry", "rz"}:
            times, values = _densify_rotation_track(times, [float(item) for item in values])
        animation.add_track(
            str(track["path"]),
            action,
            times,
            values,
        )
    animation.animate(float(speed))
    return len(tracks)


def run(payload_path: Path) -> dict[str, Any]:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    code = str(payload["code"])
    validate_code(code)
    output_dir = Path(payload["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    script_path = output_dir / "model.py"
    script_path.write_text(code, encoding="utf-8")
    requested_steps = _normalize_steps(payload.get("steps", [])) or extract_literal_steps(code)
    write_state(
        status="running",
        title=payload.get("title", "CAD model"),
        message="CadQueryモデルを生成しています",
        steps=requested_steps,
        current_step=0 if requested_steps else -1,
        job_dir=str(output_dir),
    )

    current_step = -1

    def cad_step(label: str) -> None:
        nonlocal current_step
        current_step += 1
        labels = requested_steps or [str(label)]
        if current_step >= len(labels):
            labels.append(str(label))
        write_state(steps=labels, current_step=current_step, message=str(label))

    builtins = {**SAFE_BUILTINS, "__import__": _safe_import}
    namespace: dict[str, Any] = {
        "cq": cq,
        "cad_step": cad_step,
        "__builtins__": builtins,
        "__name__": "__cad_model__",
    }
    exec(compile(code, str(script_path), "exec"), namespace, namespace)  # noqa: S102
    if "result" not in namespace:
        raise ValueError("コードは最終CadQueryオブジェクトを変数 result に代入してください")
    code_steps = _normalize_steps(namespace.get("steps"))
    steps = code_steps or requested_steps
    if steps:
        write_state(steps=steps, current_step=len(steps) - 1, message="モデルを出力中")
    tracks = namespace.get("animation", payload.get("animation", []))
    if not isinstance(tracks, list):
        raise TypeError("animation はトラック辞書のlistで指定してください")
    exported = _export(namespace["result"], output_dir, payload.get("formats", ["step"]))
    animated = _show_and_animate(namespace["result"], tracks, payload.get("speed", 1.0))
    response = {
        "ok": True,
        "job_dir": str(output_dir),
        "script": str(script_path),
        "exports": exported,
        "steps": steps,
        "animation_tracks": animated,
    }
    (output_dir / "result.json").write_text(
        json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_state(
        status="complete",
        message=f"完了 — export {len(exported)}件 / animation {animated}トラック",
        current_step=len(steps) - 1 if steps else -1,
        viewer_connected=True,
        viewer_port=VIEWER_PORT,
    )
    return response


def main() -> int:
    try:
        print(json.dumps(run(Path(sys.argv[1])), ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001 - subprocess boundary returns diagnostics to MCP
        write_state(status="error", message=str(exc))
        print(
            json.dumps(
                {"ok": False, "error": str(exc), "traceback": traceback.format_exc()},
                ensure_ascii=False,
            )
        )
        return 1


if __name__ == "__main__":
    exit_code = main()
    # Some Windows VTK/OCP builds corrupt the heap during interpreter teardown
    # after all CAD work and result files have already completed successfully.
    # Flush the subprocess protocol explicitly, then skip only native teardown.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exit_code)
