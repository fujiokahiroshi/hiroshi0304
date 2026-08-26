from __future__ import annotations

import subprocess
import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk

from .state import ROOT, read_state

VIEWER_URL = "http://127.0.0.1:3939"


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Claude CAD Workbench")
        self.geometry("520x560")
        self.minsize(440, 420)
        self.configure(bg="#111827")
        self._last_signature = None
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Title.TLabel", background="#111827", foreground="#f9fafb",
                        font=("Segoe UI", 18, "bold"))
        style.configure("Body.TLabel", background="#111827", foreground="#cbd5e1")
        style.configure("Status.TLabel", background="#1f2937", foreground="#67e8f9",
                        padding=10, font=("Segoe UI", 11, "bold"))
        header = ttk.Frame(self, padding=18)
        header.pack(fill="x")
        ttk.Label(header, text="Claude CAD Workbench", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text="MCP → CadQuery → OCP CAD Viewer",
                  style="Body.TLabel").pack(anchor="w", pady=(3, 0))
        self.status = ttk.Label(self, text="起動中…", style="Status.TLabel")
        self.status.pack(fill="x", padx=18)
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=18, pady=(12, 8))
        ttk.Label(self, text="工程進捗（タイムライン操作は3D Viewer下部）",
                  style="Body.TLabel").pack(anchor="w", padx=18)
        self.steps = tk.Listbox(self, bg="#0f172a", fg="#e2e8f0",
                                selectbackground="#164e63", selectforeground="#ecfeff",
                                borderwidth=0, highlightthickness=0, font=("Yu Gothic UI", 11))
        self.steps.pack(fill="both", expand=True, padx=18, pady=8)
        buttons = ttk.Frame(self, padding=(18, 8, 18, 18))
        buttons.pack(fill="x")
        ttk.Button(buttons, text="3D Viewerを開く",
                   command=lambda: webbrowser.open(VIEWER_URL)).pack(side="left")
        ttk.Button(buttons, text="出力フォルダ", command=self.open_job).pack(side="left", padx=8)
        ttk.Button(buttons, text="終了", command=self.destroy).pack(side="right")
        self.after(150, self.refresh_state)

    def open_job(self) -> None:
        job_dir = read_state().get("job_dir")
        target = Path(job_dir) if job_dir else ROOT / "jobs"
        target.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(target)])
        else:
            webbrowser.open(target.as_uri())

    def refresh_state(self) -> None:
        state = read_state()
        signature = (state.get("updated_at"), tuple(state.get("steps", [])))
        if signature != self._last_signature:
            self._last_signature = signature
            self.status.configure(text=f"{state.get('title', 'CAD')}  •  {state.get('message', '')}")
            steps = state.get("steps", [])
            current = int(state.get("current_step", -1))
            self.steps.delete(0, tk.END)
            for index, step in enumerate(steps):
                marker = "✓" if index <= current else "○"
                self.steps.insert(tk.END, f"  {marker}  {index + 1}. {step}")
            self.progress["maximum"] = max(1, len(steps))
            self.progress["value"] = max(0, current + 1)
        self.after(400, self.refresh_state)


def main() -> None:
    Dashboard().mainloop()


if __name__ == "__main__":
    main()
