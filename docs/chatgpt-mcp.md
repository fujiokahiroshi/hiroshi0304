# ChatGPT MCP 接続

OpenAI Secure MCP Tunnel を利用して、この PC の既存 CAD MCP サーバーへ接続します。
Windows runtime v0.0.14 は `run` のみ対応しています。`init` と `doctor` は使用しません。

## この PC での起動

ダウンロード済みクライアントは `runtime/tunnel-client-v0.0.14/tunnel-client-runtime.exe` に展開済みです。
作成済みトンネル ID は `start-chatgpt.ps1` に設定しています。別のトンネルは `-TunnelId` で指定できます。

PowerShell で実行します。

```powershell
cd C:\V8_CAD
.\start-chatgpt.ps1
```

API キーの入力を求められたら、このトンネルの実行権限を持つキーを貼り付け、Enter を押します。
文字は表示されません。キーはファイルに保存せず、終了時にスクリプトが設定した環境変数を削除します。
既に CONTROL_PLANE_API_KEY が設定されている場合は、その値を使用します。
接続中は PowerShell を開いたままにします。停止は Ctrl+C です。

別の PowerShell で Viewer を起動します。

```powershell
cd C:\V8_CAD
.\start.ps1
```

## ChatGPT 側

1. 設定 → Security and login → Developer mode を有効にします。
2. https://chatgpt.com/plugins の追加から、名前を CAD Workbench、Connection を Tunnel にします。
3. 作成したトンネルを選択し、検出されるツールを確認します。
4. 新しい会話で接続を選び、「list_cad_model_sources でモデル一覧を取得して」と依頼します。

トンネルには利用する ChatGPT ワークスペースを関連付けてください。
権限・利用可能な画面はアカウントやワークスペースによって異なります。
API キーはチャットに貼らないでください。

## 検証状況

クライアントの展開・バージョン・CLI オプションと PowerShell 構文を確認済みです。
2026-09-06、ユーザー提供画面で ChatGPT から list_cad_model_sources の実行と、全485件からの一覧取得を確認しました。
続いて平歯車の生成、Viewer表示、STEP/STL保存、形状検査の成功報告を確認しました。
ChatGPT 側の認証は「なし」を選択します。このサーバーは OAuth を実装していません。
トンネルの編集画面でワークスペース選択時に白画面になる場合、ブラウザーの自動翻訳を解除して操作すると解消した実績があります。
CAD 生成後は AGENTS.md に従って形状・干渉・部品 clearance と画像を確認します。

## 公式資料

- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/apps-sdk/deploy/connect-chatgpt

## コミットの保存範囲

Gitにはソースと起動手順を保存します。APIキー、.venv、runtime（トンネル実行ファイルを含む）、jobs内の生成モデルは含みません。
別PCで復元する場合はPython環境とトンネルクライアントの再準備が必要です。
exe化の試作は保留し、この動作基準には含めません。
