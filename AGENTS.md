# AGENTS.md 追記案: 単気筒エンジン設計の既知の落とし穴

## 0. 最重要コミット — 第一復帰基準

このプロジェクトで最も重要なコミットは次のとおり。

    af05da9 feat: add RC drivetrain and named CAD inspection APIs

af05da9 を第一復帰基準かつ最優先のマイルストーンとして扱う。このコミットには、
この時点で動作しているRC駆動系、Claude MCP連携、名前指定CAD検査API、形状・干渉・
ビュー検証、ドキュメント、およびテストが保存されている。

- 今後の不具合や退行は、最初に af05da9 と比較する。
- ユーザーの明示的な許可なしに、このコミットを amend、rebaseによる消去、削除、
  または履歴の書き換え対象にしない。
- 復帰を求められた場合は、まず現在の未コミット作業を確認・保全し、その後
  af05da9 を参照点として使う。破壊的なresetを自動実行しない。

以下は2026-08-28、単気筒エンジン(クランクケース・シリンダー・クランクシャフト・
ピストン・コンロッド)を`cad-workbench`(`inspect_cad_geometry`/`detect_cad_interference`)
で検証しながら設計した際に実際に踏んだ、および解決した問題の記録。2気筒・4気筒への
展開時に同じ問題を再度踏まないための申し送り。

## 1. クランクケースのクランク室は「メインジャーナル用の細い穴」だけでは足りない

最初の実装では、クランクシャフトのメインジャーナル(直径35mm程度)用に、
その太さぴったりのトンネルだけをクランクケースに掘った。実際にはクランクウェブ
(スロー半径+ピン半径+マージン分の円盤、この設計では半径48mm相当)がその周りを
振り回るため、**メインジャーナルの径ではなく、ウェブの最大回転半径+クリアランス**
でクランク室を空ける必要がある。

```
CHAMBER_RADIUS = CRANK_THROW + WEB_PIN_R + clearance(3mm程度)
```

これを怠ると、クランクケース本体とクランクウェブが正面から衝突する
(実測23,760mm³ × 2箇所の干渉)。

## 2. メインジャーナルは「1本の連続シャフト」にしない

クランクウェブ・クランクピンを挟んで、メインジャーナルを中央を貫通する1本の
シャフトとして作ると、**コンロッドがピストン⇔クランクピン間を移動する経路と
正面衝突する**(実測6,377mm³)。実際のクランクシャフトと同様に、メインジャーナルは
**クランクウェブの外側左右に分割したスタブジャーナル2本**として作ること。

分割する際、`extrude(..., both=False)`のような片方向のみの押し出しと`mirror()`
の組み合わせは、押し出し方向がsignを見ないため位置がずれるバグを起こしやすい。
**「中心座標+半長」を直接計算してtranslateする方式**(下記)の方が安全。

```python
stub_half_len = (MAIN_JOURNAL_Y_HALF - WEB_Y_OFFSET) / 2.0
stub_center = (MAIN_JOURNAL_Y_HALF + WEB_Y_OFFSET) / 2.0
for sign in (-1, 1):
    stub = (cq.Workplane("XZ").circle(r)
            .extrude(stub_half_len, both=True)
            .translate((0, sign * stub_center, z)))
```

## 3. クランクウェブを「直線ブリッジ型」で作ると、コンロッドとの衝突が構造的に解決しない

メイン軸とクランクピンを直線でつなぐ単純なブリッジ形状のウェブは、TDC/BDC付近の
姿勢で**コンロッドのシャンクが通る経路と同じ空間を占有してしまう**(実測14,449mm³、
2の修正では解消しなかった)。これはコーディングのミスではなく形状設計そのものの
限界。実機のクランクウェブ/カウンターウェイトは、ピン側から見て**反対方向に膨らむ
三日月(クレセント)形状**にすることで、コンロッドの経路を避けている。次回この
形状での再設計が必要(未解決のまま持ち越し)。

## 4. ピストンのピン穴は「ピン本体の径」だけでなく「コンロッド小端リングの外径」も逃がす

ピストンピンが通る穴(半径9mm程度)だけを空けても、コンロッド小端のリング部分
(外径17mm程度)がピストンの無垢な材料に食い込む(実測5,610mm³)。ピン穴カッターとは
別に、**小端リングの外径+クリアランス分の逃げポケット**を追加で切る必要がある。

## 5. 平行移動+回転が組み合わさる部品(コンロッド)のアニメーション

クランクピンのように「回転しながら移動する点」を中心にコンロッドを振らせる場合、
同一の`path`に`t`(平行移動)と`r*`(回転)を両方乗せるのではなく、
**親子階層に分離する**とうまくいく(RC車ディファレンシャルの`carrier`→`carrier/spider_top`
と同じパターン)。

- 親ノード: クランクピンの位置に`t`(平行移動)でキーフレームを与える
- 子ノード: コンロッド本体(ジオメトリはクランクピン中心を原点(0,0,0)としたローカル
  座標で作り直す)に`ry`で角度キーフレームを与える

ピストン位置・コンロッド角度は、標準的なスライダークランクの式で計算できる
(r=クランクスロー、L=コンロッド有効長=ピン間距離)。

```
piston_z(θ) = -r*cos(θ) + sqrt(L^2 - (r*sin(θ))^2)
rod_angle(θ) = asin((r/L) * sin(θ))   [度に変換]
```

## 6. 検証の習慣そのものについて

上記1〜4はすべて、生成直後に`inspect_cad_geometry`(寸法・妥当性)と
`detect_cad_interference`(部品間の物理的な重なり)を**指示されなくても毎回呼ぶ**
ことで見つかった。見た目(`get_cad_preview`)だけでは1と2の欠陥はどちらも
発見できなかった。新しい部品・アセンブリを生成した後は、この2つを習慣として
呼ぶこと。

## 7. RC 4WD primary-drive baseline and clearances

As of 2026-08-28, use this validated job as the RC 4WD baseline:

```text
job:20260828-213452-457219-rc-4wd-motor-gear-axial-clearance-fix-v6
```

At the theoretical 27.6 mm center distance, the simplified trapezoidal teeth of the
22T motor pinion and 70T spur initially overlapped by 8.925 mm^3. Rotate the 22T
pinion by half a tooth, `180 / 22 = 8.182 degrees`. After correction, overlap is
0 mm^3 and the minimum tooth-surface distance is approximately 0.0573 mm.

Cut chassis openings with 2.0 mm radial and axial clearance around the 70T spur,
540 motor can, and endbell. A 0.5 mm opening is numerically non-interfering but
looks like contact in the Viewer and does not provide practical margin.

Keep these measured minimum distances:

- Motor can to 70T spur: 1.0 mm
- Motor can to 22T pinion: 1.5 mm
- Motor can to chassis: 2.0 mm
- 70T spur to chassis: approximately 2.0 mm

`detect_cad_interference` on a flattened STEP also finds tooth solids and intentional
joints. Do not judge the assembly only by the total finding count. For suspicious
named parts, measure both `intersect(...).Volume()` and `distance(...)` on the
source Shapes.
## 8. cad-workbench MCP実装記録

2026-08-29時点の主要実装は、最重要コミット af05da9
(feat: add RC drivetrain and named CAD inspection APIs) に保存されている。
MCPサーバー本体は src/cad_workbench/server.py、生成済みジョブを再実行して
名前付き部品を検査する補助処理は src/cad_workbench/job_tools.py にある。
RC 4WDモデル本体は examples/rc_4wd_drivetrain.py に分離し、説明は
docs/rc_4wd_drivetrain.md、Claude向け入口は CLAUDE.md に記録している。

### 公開MCPツール

- 汎用生成: create_cad_model, get_cad_status, viewer_help
- 既製アニメーション: create_gear_animation, create_bevel_gear_animation,
  create_differential_animation, create_rc_4wd_drivetrain_animation,
  create_screw_gear_animation
- モデルソース発見・読取: list_cad_model_sources, get_cad_model_source,
  search_cad_model_sources
- 目視確認: get_cad_preview, get_cad_views, show_cad_job
- 形状検査: inspect_cad_geometry, detect_cad_interference
- 名前付き部品検査: list_cad_components, inspect_component_clearance

create_cad_model はCadQueryコードを検査して別プロセスで実行し、最終変数 result を
OCP CAD Viewerへ送り、STEP/STLとリクエスト・結果を jobs/ に保存する。コード内で
cad_step(label) を呼ぶと工程状態を更新できる。アニメーションはAssemblyの名前階層に
一致する path と、tx/ty/tz/t/rx/ry/rz/q のトラックで渡す。

### Claude/Codexの標準作業フロー

1. 再利用可能なモデルを list_cad_model_sources / search_cad_model_sources で探し、
   必要箇所を get_cad_model_source で読む。
2. 既製ツール、または create_cad_model でモデルを生成する。
3. get_cad_status で完了、出力先、Viewer接続状態、実行エラーを確認する。
4. 既存ジョブの再表示は show_cad_job を使う。これはブラウザータブを増やさず、
   既存の http://127.0.0.1:3939 タブを再利用する。
5. 生成直後は必ず inspect_cad_geometry と detect_cad_interference を呼び、
   妥当性と物理干渉を数値で確認する。
6. アセンブリでは list_cad_components で正確な部品パスを取得し、疑わしい組を
   inspect_component_clearance で個別検査する。
7. get_cad_preview または get_cad_views でClaude/Codex自身が画像を確認し、
   数値検査と目視確認の両方を満たしてから完了とする。

### Viewerと検査上の注意

- OCP CAD Viewerの既定ポートは3939。画像取得・再表示にはViewerが起動済みであること。
- show_cad_job はViewerへ再送するが、ブラウザーを自動起動しない。
- get_cad_views はiso/front/back/left/right/top/bottomを取得でき、既定は
  iso/front/right/top。
- flattenされたSTEPに対する detect_cad_interference は部品名と階層を失うため、
  歯のソリッドや意図した結合まで検出する場合がある。総件数だけで合否を決めない。
- 名前が必要な判定は list_cad_components と inspect_component_clearance を優先する。
- MCPツール追加後にClaude Code側へ一覧が反映されない場合は、MCP接続を再接続する。
