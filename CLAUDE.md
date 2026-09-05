# CAD Workbench — Claude project instructions

## Startline（常に戻れる基準点）

このプロジェクトの安定基準点は Git タグ `startline` です。

- 基準内容: Claude MCP、CadQuery、OCP CAD Viewer、平歯車・傘歯車・デファレンシャルのアニメーション
- 基準確認: `git show --stat --oneline startline`
- 差分確認: `git status --short` と `git diff startline`
- `startline` タグは移動・上書き・削除しないこと

「startline に戻して」と依頼された場合、最初に `git status --short` を実行する。
未コミットの変更がある場合は勝手に破棄せず、ユーザーへ知らせてコミットまたは
`git stash push -u` で退避する。復帰前には回復用ブランチまたはstashを必ず残す。
`git reset --hard`、`git clean`、ファイル削除は、対象と影響を説明してユーザーから
明示的な許可を得た場合にだけ実行する。

基準状態を安全に閲覧するだけなら、作業ツリーがクリーンであることを確認してから
`git switch --detach startline` を使う。通常開発へ戻るときは `git switch master` を使う。

## プロジェクト概要

Windows向けのClaude CAD環境。ClaudeからMCPツールを呼び、CadQueryでモデルを生成し、
OCP CAD Viewer（`http://127.0.0.1:3939`）へ形状・工程・アニメーションを表示する。
STEP/STLと生成コードは `jobs/` に保存される。

## 起動

PowerShellでプロジェクトルートから実行する。

```powershell
.\start.ps1
```

Claude DesktopへMCPを再登録する場合:

```powershell
.\configure-claude.ps1
```

設定後はClaude Desktopを完全終了して再起動する。

## MCPツール

- `create_cad_model`: 任意のCadQueryコードを実行して表示・出力する
- `create_gear_animation`: 2枚の平歯車を歯数比で連動回転させる
- `create_bevel_gear_animation`: 90度で噛み合う2枚の傘歯車を連動回転させる
- `create_differential_animation`: オープンデファレンシャルを生成・アニメーション表示する
- `create_rc_4wd_drivetrain_animation`: Generate the RC 4WD drivetrain with transparent open differentials
- `create_screw_gear_animation`: 直交軸で噛み合う14Tねじ歯車ペアを連動回転させる
- `list_cad_model_sources`: List readable model.py files from examples and jobs
- `get_cad_model_source`: Read a model source by safe ID and line range
- `search_cad_model_sources`: Search across readable CAD Python sources
- `get_cad_preview`: Capture the current OCP CAD Viewer image for visual inspection
- `inspect_cad_geometry`: Measure validity, bounds, volume, area, center of mass, and topology
- `detect_cad_interference`: Detect STEP solid overlaps and optional clearance violations
- `get_cad_views`: Capture ISO/front/back/left/right/top/bottom views and restore the camera
- `list_cad_components`: List named Assembly components and their world-space bounds
- `inspect_component_clearance`: Measure overlap and clearance between named components
- `show_cad_job`: Redisplay a job and animation in the existing Viewer tab without opening one
- `create_compound_planetary_animation`: Recreate the validated blue-ring/green-carrier/yellow-sun animation using the planetary constraint.
- `create_cardan_joint_animation`: Generate a universal (Cardan/Hooke's) joint with the correct non-constant-velocity tan(phi)=tan(theta)/cos(beta) motion. Blue `handle_yoke` is the steering handle (uniform speed); yellow `wheel_yoke` drives the wheels (derived, non-uniform speed).
- `create_double_cardan_joint_animation`: Generate a Z-configuration double Cardan joint (input/output parallel via a phased intermediate shaft) that cancels the single joint's non-uniform velocity; output tracks input to within floating-point noise.
- `get_cad_status`: 最新ジョブとViewer接続状態を確認する
- `viewer_help`: モデル、工程、アニメーショントラックの形式を確認する

傘歯車の標準例:

```text
create_bevel_gear_animationを使い、teeth_a=16、teeth_b=32、module=2、
face_width=8、bore=6、turns=2、duration=5で生成して表示する。
```

## 開発規則

- 単位はミリメートルを使う
- 生成物の最終形状は必ず `result` に代入する
- 工程表示は `steps` と `cad_step(label)` を使う
- 可動部品は名前付き `cq.Assembly` の子として構成する
- アニメーションの `path` はViewerのAssemblyツリーと一致させる
- 生成物である `.venv/`、`jobs/`、`runtime/`、キャッシュ、ログはコミットしない
- 実装変更後は `.\.venv\Scripts\python.exe -m pytest -q` を実行する
- ユーザーの既存変更を無断で破棄・上書きしない


## Mandatory drawing-to-mechanism reasoning process

For every mechanism reconstructed from a drawing, use this order and do not skip it:

1. Read labels, axes, part count, coaxial relationships, rigid groups, and every gear mesh.
2. Show a placement-only model before designing detailed teeth, bearings, or housings.
3. Put shapes belonging to one rigid body under one Assembly parent. The blue planetary
   ring's inner and outer gears are one component and must always rotate together.
4. Count degrees of freedom and choose the fixed member or two known shaft speeds before
   calculating motion. Never assign visually convenient rotations independently.
5. For the validated 24T sun and 56T ring arrangement, enforce:

   ```text
   24 * omega_sun + 56 * omega_ring = 80 * omega_carrier
   ```

6. Model planet revolution and self-rotation with an Assembly hierarchy: carrier parent,
   planet child. Parent `rz` produces revolution; child `rz` is rotation relative to carrier.
7. Add rotation markers and stable colors, then verify both numerically and visually with
   `inspect_cad_geometry`, `detect_cad_interference`, and
   `get_cad_preview`/`get_cad_views`.
8. When the user corrects an interpretation, update the component model, constraints,
   equations, and Assembly hierarchy before regenerating the animation.

Validated reference job:

```text
job:20260830-180323-155819-three-output-planetary-simultaneous-animation
```

It uses blue ring = 1 turn, green carrier = 0.5 turn, yellow sun = -2/3 turn,
with two planets revolving with the carrier while rotating relative to it.

## Standard: bores must sit inside a full ring of material

When cutting a pin/shaft/bolt hole through a cylindrical arm or fork prong, never
center the hole exactly at the arm's tip. Extend the arm past the hole position by
`hole_radius + margin` first, then cut the hole — otherwise the bore opens into a
kite-shaped notch instead of a closed round eye. Matching the arm's own radius to a
neighboring part's radius does not fix this; it is a tip-position problem, not a
radius-mismatch problem. Verify with a face-on view (`get_cad_views`): the hole
outline must read as a complete circle with background visible through it.

Validated reference job:

```text
job:20260905-102244-249031-cardan-joint-prongext
```
