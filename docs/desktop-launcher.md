# V8_CAD デスクトップランチャー

`V8_CAD.exe` は、このプロジェクトの `.venv` と `src` を利用する Windows ランチャーです。
単体配布版ではなく、プロジェクトのルートに置いて使います。

- Viewer の起動と表示（起動済みのポート3939を再利用）
- 工程ダッシュボードの起動
- ChatGPTトンネルの起動（キー入力用PowerShellを表示）
- jobs フォルダーとChatGPTへの入口

ソースは `packaging/Launcher.cs` と `src/cad_workbench/desktop.py` です。
再ビルドは PowerShell で `./build-exe.ps1` を実行します。

## 検証状況

2026-09-06: C# ビルド、Python構文、ruff静的検査は成功しました。
Windowsが生成exeの起動を WinError 225（ウイルスまたは望ましくない可能性のあるソフトウェア）でブロックしたため、
exeの実起動とGUIの動作確認は未完了です。誤検知かどうかは未確認です。
保護設定の無効化や除外は行っていません。
配布・運用開始前に検出内容の確認と、必要なら正規の誤検知申請・コード署名を検討してください。
既存の start.ps1 と start-chatgpt.ps1 は変更していません。
