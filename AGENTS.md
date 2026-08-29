# AGENTS.md 追記案: 単気筒エンジン設計の既知の落とし穴

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
