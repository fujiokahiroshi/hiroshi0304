from __future__ import annotations

import os
import subprocess
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from .state import ROOT, viewer_reachable


class Desktop(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("V8_CAD")
        self.geometry("540x460")
        self.minsize(500, 440)
        self.python = ROOT / ".venv" / "Scripts" / "python.exe"
        self.viewer = None
        self.dashboard = None
        self.tunnel = None
        self.starting = False
        panel = ttk.Frame(self, padding=24)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="V8_CAD", font=("Segoe UI", 25, "bold")).pack(anchor="w")
        ttk.Label(panel, text="CadQuery  /  OCP CAD Viewer  /  MCP").pack(anchor="w", pady=(0, 18))
        self.status = ttk.Label(panel, text="")
        self.status.pack(anchor="w", pady=(0, 12))
        for label, action in [
            ("3D Viewer を起動 / 表示", self.open_viewer),
            ("工程ダッシュボード", self.open_dashboard),
            ("ChatGPT 接続を起動（APIキー入力）", self.open_tunnel),
            ("保存済みモデルのフォルダー", lambda: os.startfile(str(ROOT / "jobs"))),
            ("ChatGPT を開く", lambda: webbrowser.open("https://chatgpt.com")),
            ("使い方", self.help),
        ]:
            ttk.Button(panel, text=label, command=lambda a=action: self.guarded(a)).pack(fill="x", pady=4)
        ttk.Label(panel, text="この画面を閉じても、Viewerと接続は継続します。\n接続の停止は接続ウィンドウで Ctrl+C。", wraplength=480).pack(anchor="w", pady=(14, 0))
        self.after(100, self.refresh)

    def guarded(self, action):
        try:
            action()
        except (OSError, tk.TclError) as exc:
            messagebox.showerror("V8_CAD", str(exc), parent=self)

    def refresh(self):
        self.status.configure(text="Viewer: 起動済み" if viewer_reachable() else "Viewer: 停止中")
        self.after(3000, self.refresh)

    def open_viewer(self):
        if viewer_reachable():
            webbrowser.open("http://127.0.0.1:3939")
            return
        if self.starting:
            return
        log_path = ROOT / "runtime" / "desktop-viewer.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("ab") as log:
            self.viewer = subprocess.Popen(
                [str(self.python), "-m", "ocp_vscode", "--port", "3939", "--theme", "dark", "--axes", "--grid_xy"],
                cwd=ROOT, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        self.starting = True
        self.wait_viewer(60)

    def wait_viewer(self, remaining):
        if viewer_reachable():
            self.starting = False
            webbrowser.open("http://127.0.0.1:3939")
        elif remaining <= 0 or self.viewer.poll() is not None:
            self.starting = False
            messagebox.showerror("V8_CAD", "Viewerが起動しませんでした。runtime/desktop-viewer.log を確認してください。")
        else:
            self.after(500, lambda: self.wait_viewer(remaining - 1))

    def open_dashboard(self):
        if self.dashboard is None or self.dashboard.poll() is not None:
            self.dashboard = subprocess.Popen(
                [str(self.python.with_name("pythonw.exe")), "-m", "cad_workbench.dashboard"], cwd=ROOT,
            )

    def open_tunnel(self):
        if self.tunnel is not None and self.tunnel.poll() is None:
            messagebox.showinfo("V8_CAD", "接続ウィンドウは既に起動しています。")
            return
        if not messagebox.askokcancel("ChatGPT 接続", "既に接続用PowerShellが動いている場合は追加起動不要です。\n新しい接続ウィンドウを開きますか？"):
            return
        powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
        self.tunnel = subprocess.Popen(
            [str(powershell), "-NoProfile", "-NoExit", "-File", str(ROOT / "start-chatgpt.ps1")],
            cwd=ROOT, creationflags=subprocess.CREATE_NEW_CONSOLE,
        )

    def help(self):
        messagebox.showinfo("V8_CAD の使い方", "1. 3D Viewer を起動します。\n2. ChatGPT接続を起動してAPIキーを入力します。\n3. ChatGPTでCADプラグインを選び、作成を依頼します。\n\nこのexeは、このPCのV8_CAD環境を使うランチャーです。\nexeだけを別のPCへコピーしても動きません。")


def main():
    Desktop().mainloop()


if __name__ == "__main__":
    main()
