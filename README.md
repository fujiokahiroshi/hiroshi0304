# Claude CAD Workbench

Claude DesktopのプロンプトからMCPツールを呼び、CadQueryでモデルを生成し、OCP CAD Viewerで表示・アニメーション再生するWindows向け環境です。別ウィンドウに生成工程と進捗を表示します。

## セットアップ

```powershell
.\setup.ps1
.\configure-claude.ps1
.\start.ps1
```

`start.ps1` はOCP CAD Viewerの起動完了を待ち、ブラウザの3D画面と工程ウィンドウを開きます。

`configure-claude.ps1` は既存のClaude Desktop設定を保持し、`cad-workbench` MCPサーバーだけを追加します。その後Claude Desktopを完全終了して再起動してください。

## Claudeへの依頼例

```text
cad-workbenchを使って、80 x 50 x 4 mmのベースと開閉する蓋をCadQueryで作ってください。
工程を日本語で表示し、蓋をY軸まわりに0→75→0度動かすアニメーションを実行してください。
STEPとSTLを保存してください。
```

Claudeが渡すコードでは、完成物を必ず `result` に代入します。任意で `steps` と `animation` も定義できます。

```python
import cadquery as cq
steps = ["ベース作成", "穴加工", "組立"]
cad_step(steps[0])
result = cq.Workplane("XY").box(40, 30, 10)
animation = []
```

- `result`: CadQueryのWorkplane、Shape、またはAssembly。
- `steps`: 工程ウィンドウに表示する文字列リスト。
- `cad_step(label)`: 各工程の直前に呼ぶと、工程ウィンドウが実行中に逐次更新されます。
- `animation`: `path`, `action`, `times`, `values` を持つトラックのリスト。
- 出力: `jobs/<日時>-<名前>/` の `model.py`, `model.step`, `model.stl`, `request.json`, `result.json`。

可動部は明示的に名前を付けた `cq.Assembly` の子にします。例は `examples/demo_hinge.py` です。アクションは `tx/ty/tz`, `t`, `rx/ry/rz`, `q`。`path` はViewerツリーのパスと一致させます。

## 歯車アニメーション

Claudeへ次のように依頼すると、専用MCPツール `create_gear_animation` が噛み合う平歯車を生成します。

```text
cad-workbenchで、モジュール2、歯数20と40、厚さ8 mm、軸穴6 mmの歯車を作り、回転させてください。
```

歯車Bは歯数比 `-歯数A / 歯数B` に従って逆回転します。STEPとSTLもジョブフォルダへ保存されます。
各歯車の表面には回転位置が分かる色付きマーカーが表示されます。3D Viewer下部のPauseボタンを押してからタイムラインを動かすと、任意の角度で確認できます。
360度以上の回転は実行時に90度以下のQuaternionキーフレームへ自動分割されるため、複数回転でもスライダーへ正しく追従します。

90度で噛み合う傘歯車は専用MCPツール `create_bevel_gear_animation` で生成できます。歯数からピッチ円錐角、円錐距離、逆回転比を自動計算します。

直交する食い違い軸で噛み合うねじ歯車は `create_screw_gear_animation` で生成します。45度ねじれの14Tインボリュートヘリカル歯車2個を、Z軸とX軸まわりに連動回転させます。正式テンプレートは `examples/screw_gear_pair.py` です。

オープンデファレンシャルは `create_differential_animation` で生成します。左右サイドギヤ、上下スパイダーギヤ、キャリアを組み、`左回転 + 右回転 = 2 × キャリア回転`を保った旋回アニメーションを実行します。

## 大型サンプルモデル (examples/)

MCPツール化されていない大型モデルは `examples/` にソースとして置かれており、Claudeに次のように頼むと表示できます。

```text
list_cad_model_sourcesでexamplesを一覧して、road_bike.pyを表示して。
```

Claudeは `get_cad_model_source` でソースを読み込み、`create_cad_model` にそのまま渡して実行します。追加や変更を頼めば、Claudeがコードを直接編集して再表示します。

- `timing_belt.py`: 2円の外接線から厳密計算したベルト経路で駆動プーリー(20T)と従動プーリー(40T)をつなぐタイミングベルト。ベルト自体は静止ソリッドで、外周の歯マーカーが経路上を移動して「流れ」を近似します。
- `bicycle_belt_drive.py`: 上記のベルト機構を流用した、44T/16Tベルトドライブのシングルスピード自転車。フレーム・前後ホイール・クランク・ペダルを剛体グループとして組立。
- `road_bike.py`: 実車寸法(ホイールベース990mm、ヘッド角73°など)に基づくロードバイク。50/34Tクランク・11-28Tカセット・前後ディレイラーに加え、チェーンは108個の実リンクを個別にモデル化した剛体アニメーション(マーカー近似ではない)。ドロップハンドル・キャリパーブレーキ・ボトル+ラベル+ボトルケージまで再現。

## 動作確認

```powershell
uv run pytest
uv run ruff check .
```

## セキュリティ

Claudeが作ったPythonコードをローカルで実行します。AST検査でファイル、OS、ネットワーク系の一般的なアクセスを拒否しますが、完全なサンドボックスではありません。信頼できない第三者のプロンプトやコードは実行しないでください。
