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
  create_screw_gear_animation, create_compound_planetary_animation
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

## 9. 必須思考プロセス — 図面から機構アニメーションを作る場合

2026-08-30に、ユーザー提供の遊星歯車図面から配置と運動を復元した際の成功手順を、
今後すべての図面ベース機構設計に対する必須工程とする。細部形状を先に作らず、
**構造理解 → 拘束条件 → 運動式 → 簡略配置 → アニメーション → 検証**の順を守る。

1. 図面のラベル・断面・軸線を読み、部品数、回転軸、同軸関係、接触関係を列挙する。
   推測で部品を増やさない。この基準例では太陽歯車1個、遊星歯車2個、キャリア1個、
   内歯と外歯を持つ青い複合リング1個である。
2. 同じ剛体として動く形状を先にまとめる。青いリングの内歯・外歯は別々の歯車ではなく
   同一部品なので、必ず同じAssembly親ノードに入れ、同一角度で回す。
3. 歯の詳細、ケース、軸受を作る前に、円盤・軸・バーによる配置モデルを表示する。
   ユーザーと部品数、前後位置、キャリア位置、かみ合い相手を確認してから詳細化する。
4. 機構の自由度を数える。遊星歯車では、固定要素または第2入力・負荷条件を決めずに
   3軸の回転を一意に決めない。24T太陽、56Tリングの基準式は次のとおり。

   ```text
   24 * omega_sun + 56 * omega_ring = 80 * omega_carrier
   ```

   青・緑・黄の角度を見た目で独立に割り当てず、常にこの拘束式から求める。
   外歯同士は逆方向、リング内歯と遊星歯車はキャリア相対で同方向に回る。
5. 公転と自転を親子階層に分ける。キャリアを親、遊星歯車を子にし、親の`rz`で公転、
   子の`rz`でキャリアに対する相対自転を与える。子のワールド回転は親回転と相対回転の
   和になることを計算に含める。
6. 全回転部品に方向確認用マーカーを付け、色を部品系統ごとに固定する。この基準例では
   青=内外一体リング、緑=キャリア、黄=太陽、橙=遊星、紫=リング外歯入力とする。
7. 生成直後に`inspect_cad_geometry`と`detect_cad_interference`を実行し、続いて
   `get_cad_preview`または`get_cad_views`で自分自身が目視確認する。簡略歯を母材へ
   食い込ませて一体表示した意図的干渉と、別部品同士の不正干渉を区別する。
8. ユーザーの訂正を局所修正で終わらせず、部品構成・自由度・式・Assembly階層へ
   反映してから再生成する。確認済みの理解を次工程の前提として保持する。

3軸同時回転の検証済み配置ジョブは次を参照する。

```text
job:20260830-180323-155819-three-output-planetary-simultaneous-animation
```

このジョブでは青リング1回転、緑キャリア0.5回転、黄太陽-2/3回転で拘束式を満たし、
2個の遊星歯車はキャリアと公転しながら相対自転する。図面から機構を復元する際は、
この思考プロセスを省略しない。

## 10. 最優先の設計原則 — 造形前に図面から配置と接続を確定する

2026-08-31の差動歯車モデル作成で確認した最重要原則。図面から機構を作るときは、
**各objectの詳細形状や歯を作る前に、図面を十分に読み、配置と接続関係を確定する**。
形が作れることを理由に、図面にない支持部、連結軸、ケース、歯車を推測で追加しない。

必ず次の順序で進める。

1. 図面に描かれたobjectを1個ずつ数え、名称、色、前後位置を表にする。
2. 各objectの回転軸を決め、同軸、直交、平行の関係を確定する。
3. 「接触している」「同じ軸上にある」「固定されている」「独立して回転する」を区別する。
   特に、同軸に見える2部品を1本の連続軸で結んでよいとは限らない。
4. 円盤、棒、板だけの配置モデルを作り、iso/front/right/topの複数方向で表示する。
5. ユーザーが部品数、大小、間隔、穴、軸、接続／非接続を確認するまで歯形を作らない。
6. 配置確定後に歯形を追加し、最後に運動式とAssembly親子階層を設定する。
7. `inspect_cad_geometry`、`detect_cad_interference`、名前付きclearance、複数ビューで検証する。

この差動歯車で確定した構造は、紫の外歯入力リングと緑キャリアが一体回転し、黄色と
朱色の出力傘歯車はX軸上で独立回転し、水色の傘歯車2個は上下の独立した短い固定軸上で
それぞれ自転する構造である。水色2個を1本の連続シャフトで物理的につながない。

検証済みの配置・シミュレーション基準ジョブ:

```text
job:20260831-132151-838637-four-bevel-differential-simulation-split-pinion-
```

この原則は差動歯車に限らない。今後のすべての図面ベースCADで、
**図面読解 → object一覧 → 軸と接続 → 簡略配置 → ユーザー確認 → 詳細形状 → 運動 → 検証**
の順を省略しない。

## 11. ピン穴・軸穴は必ず「材料が一周する位置」に開ける

2026-09-05のカルダンジョイント（自在継手）フォーク形状で確定した標準。円柱状の腕
（フォークの爪など）の**先端ちょうど**に垂直な穴を開けると、腕の材料が穴の片側にしか
残らず、閉じた丸穴ではなく「凧形に開いた欠け」になる。目視でもinspect_cad_geometry
でも見落としやすいが、STEPを見ればすぐ気づく不自然さになる。

必ず次を守る。

1. 穴を開ける前に、穴の中心が**腕の途中**（両端ではない）に来るよう、腕を穴の位置より
   `穴半径 + 余裕（例: 2mm）`だけ延長する。
2. 延長後に穴を切削し、`inspect_cad_geometry`または正面ビュー（該当軸から見た
   `get_cad_views`）で、穴の輪郭が**完全な円**（背景が透けて見える貫通穴）になっている
   ことを確認する。凧形・半月形に見える場合は延長不足。
3. 半径を合わせる（HUB_RとPRONG_Rを揃えるなど）だけでは直らない。これは腕どうしの
   半径不一致ではなく、腕の端点位置の問題である。

検証済みの基準ジョブ:

```text
job:20260905-102244-249031-cardan-joint-prongext
```

この原則は自在継手に限らない。ピン・シャフト・ボルトなどが貫通する穴を持つあらゆる
腕状・フォーク状の部品で、穴を切る前に「材料が360度残るか」を確認する。

## 12. 原点から離れた部品の回転は、位置をジオメトリではなくAssemblyのlocで持たせる

2026-09-05のダブルカルダンジョイントで発生した不具合。ジョイント2（原点から離れた
位置）にある出力ヨークとクロスを`cq.Solid.translate()`でジオメトリ自体に位置を
焼き込み、`Assembly.add()`にlocを渡さずに配置したところ、アニメーション再生時に
その部品が正しい軸を中心に自転せず、**ワールド原点を中心に大きく振り回される**形で
崩壊して見えた。原点を通らない部品ほど症状が大きい。

必ず次を守る。

1. 回転アニメーションを与える部品のジオメトリは、**回転軸が原点を通る姿勢**で作る
   （`.translate()`で最終位置へ焼き込まない）。
2. 最終位置への平行移動は、`Assembly.add(shape, name=..., loc=cq.Location(to_vector(position)))`
   のようにAssemblyの`loc`側で行う。こうするとアニメーションの回転はまずローカル
   原点まわりで正しく起こり、その後locで正しい位置へ移動される。
3. 静止姿勢のSTEP出力・干渉チェックだけでは検出できない。**必ずアニメーションを
   スクラブ（`set_relative_time`）して複数角度を目視確認**する。

検証済みの基準ジョブ:

```text
job:20260905-110636-362310-double-cardan-joint-fixed
```

この原則は複数の関節・オフセットされた部品を持つあらゆる機構に当てはまる。
原点上にない部品にrz/rx/ry/qアニメーションを与える前に、locで配置しているか確認する。
