"""Mitsubishi/Nakajima A6M Zero -- Nakajima Sakae (NK1) 14-cylinder radial engine.

Real 1:1mm-scale CAD model of the Sakae 21/31 (bore/stroke 130x150mm, 14
cylinders in two 7-cylinder rows, single crank-pin master-and-link-rod
mechanism) with a cutaway wedge so the crank/rod kinematics are visible from
outside. Cooling-fin pitch/count, cylinder base stud-bolt count (12), and the
3-piece (front/mid/rear) crankcase split are sourced from a same-family
Ha-25 engine reference (Ha-25/Ha-105/Ha-115 and Sakae 21/31 share the same
NK1 bore/stroke/14-cylinder layout; see in-code comments for the exact
citation and the reasoning for using a sibling engine's figures as the
best-available proxy).

PROPELLER: this build carries a North American P-51 Mustang Hamilton
Standard Hydromatic 24D50 propeller (4 blades, sourced 3404mm/11ft2in
diameter, sourced black+yellow-tip USAAF paint spec) mounted at the Sakae's
own propeller-shaft stub, driven by the Sakae's own sourced 0.5833 reduction
ratio -- NOT the P-51's real 0.479 Packard V-1650 ratio, since the shaft in
this model is still driven by the Sakae, not a Merlin. This is a DELIBERATE
hypothetical/what-if cross-attachment (real US P-51/Hamilton-Standard
hardware mounted on a real Japanese Sakae engine) requested by the user --
the Sakae and this Hamilton Standard propeller never paired historically.
Blade chord/thickness/twist are representative (the Hydromatic parts/
overhaul manual with the real blade-station table is paywalled); diameter,
blade count, hub model, and paint scheme are sourced. See in-code comments
for full sourced-vs-representative accounting and citations.
"""
import cadquery as cq
import math

steps = [
    "中央クランクケース(前部・中部・後部の3分割構造)・主軸受・単一クランクピンのクランク軸を作成",
    "前列7気筒(バレル・実測値ベースの高密度冷却フィン・シリンダー取付12本スタッドボルト・ヘッド・プッシュロッド・排気管)を配置",
    "後列7気筒(前列に対し25.7度オフセット)を配置",
    "マスターコンロッド+ナックルフランジ(前列・後列)を機構学的に正しい初期位置で作成",
    "12本のリンクロッドを機構学的に正しい初期位置・角度で配置",
    "ノーズケース(減速機・プロペラ軸)とアクセサリーケース(補機)を作成",
    "P-51マスタング用ハミルトン・スタンダード ハイドロマチック24D50(4枚・実測3404mm径・黒塗り黄色先端帯)を、栄エンジン自身の減速比0.5833でプロペラ軸先端に取り付け",
    "クランク回転+マスター/リンクロッド-ピストンの正確なスライダークランク運動+プロペラ減速回転をアニメーション設定",
]

# ================= parameters (mm / deg) : Nakajima Sakae (NK1) =================
BORE = 130.0
STROKE = 150.0
R_CRANK = STROKE / 2.0
N_ROW = 7
STEP_DEG = 360.0 / N_ROW          # 51.4286 deg between cylinders in one row
ROW_OFFSET = STEP_DEG / 2.0       # 25.7143 deg stagger between front/rear row

# master-and-link rod geometry, tuned numerically so all 14 pistons share ~150mm stroke
L_MASTER = 300.0
R_FLANGE = 70.0
L_LINK = L_MASTER - R_FLANGE      # 230.0  (closure-verified: matches master stroke/range)

CASE_R = 180.0
CASE_BORE_R = 150.0   # crankcase internal bore radius: must clear crank cheek/counterweight sweep
BARREL_LEN = 230.0
HEAD_LEN = 70.0

Z_REAR = 0.0
Z_FRONT = 280.0
Z0 = Z_REAR - 40.0
Z1 = Z_FRONT + 40.0

MAIN_J_R = 85.0
PIN_R = 55.0

# cutaway wedge: cylinders/crankcase inside this angular span are removed so the
# crank / master-and-link rod mechanism is visible from outside
WEDGE_START = 25.0
WEDGE_END = 155.0

# propeller: swapped to a P-51 Mustang Hamilton Standard Hydromatic 24D50
# (4-blade, real 1940s US fighter propeller) at the user's explicit request
# ("これを栄エンジンにつけて") -- this is a deliberate hypothetical/what-if
# cross-attachment: the Sakae (a Japanese Zero engine) and this Hamilton
# Standard prop (a US P-51 Mustang / Packard V-1650 Merlin part) never
# paired historically. Noted here plainly so the sourced numbers below are
# not mistaken for a real Sakae+Hamilton-Standard combination.
#
# PROP_REDUCTION is kept at the Sakae's OWN documented 0.5833 ratio
# (enginehistory.org / ja.wikipedia "栄(エンジン)") rather than the P-51's
# real 0.479 Packard V-1650 ratio: the reduction ratio is a property of the
# engine+gearbox actually driving the shaft, and in this model that is still
# the Sakae, not a Merlin -- so its own gearing is the mechanically correct
# choice for a prop now driven by it.
#
# PROP_TIP_R is a sourced real measurement: the Hamilton Standard 24D50 on
# a P-51B/C/D is 11ft2in (3404mm) diameter (thisdayinaviation.com; cross-
# checked at ww2aircraft.net's P-51D propeller technical-data thread), so
# 3404mm/2 = 1702mm is used directly.
# PROP_N_BLADES=4 and the blade model (6523A-24) are also sourced from the
# same references. PROP_HUB_R is kept at the Sakae's existing small mount
# hub (60mm) rather than the real Hydromatic hub's much larger dome (this
# model does not attempt to reproduce that hub/actuator geometry) so the
# blades attach cleanly to the Sakae's own nose_case/prop_shaft_stub.
# Chord/thickness/twist are representative (the Hydromatic parts/overhaul
# manual with the real blade-station table is paywalled) -- a 3-point
# root/max-chord/tip taper typical of this blade class, not a flat slab.
PROP_REDUCTION = 0.5833
PROP_N_BLADES = 4
PROP_HUB_R = 60.0
PROP_TIP_R = 1702.0           # sourced: P-51 24D50, 11ft2in = 3404mm diameter / 2
PROP_ROOT_CHORD = 150.0       # representative
PROP_MAX_CHORD = 280.0        # representative
PROP_MAX_CHORD_FRAC = 0.25    # representative: span fraction of widest point
PROP_TIP_CHORD = 110.0        # representative
PROP_ROOT_THICK = 90.0        # representative
PROP_TIP_THICK = 16.0         # representative
PROP_ROOT_TWIST = 45.0        # representative
PROP_TIP_TWIST = 15.0         # representative
PROP_PITCH_FRAC = 0.30        # pitch axis at 30% chord from leading edge
PROP_CAMBER = 0.025           # mild camber, typical constant-speed blade section
PROP_CAMBER_POS = 0.4
PROP_Z = 800.0
# blade paint: sourced from an actual 1941 USAAF specification, not a
# modeling reference this time -- Spec 24114 Amendment No.4 (28 Aug 1941):
# black overall (Bulletin 41 Shade No.44), last 4in (101.6mm) of each blade
# tip painted yellow (Shade No.48). (ourairports.biz/?p=5993)
YELLOW_TIP_LEN = 4.0 * 25.4    # 101.6mm, sourced

# cooling fins + cylinder mounting studs: sourced from a Ha-25 (中島「栄」と同じ
# NK1系列、一〇〇式戦車偵察機・隼のエンジン)の実測資料
# (http://home.f04.itscom.net/nyankiti/ki43-sub3-engine1.htm):
#   fin pitch 3.54mm, fin thickness 1.5mm, 12 stud bolts per cylinder base.
# Ha-25/Ha-105/Ha-115 and Sakae 21/31 are the same NK1 engine family (same
# bore/stroke 130x150mm, same 14-cyl layout) but are not identical variants
# used in different airframes (Ha-25/Ha-105 -> Ki-43 Hayabusa, Sakae 21/31 ->
# A6M Zero, which is what this model already commits to via the 0.5833
# reduction ratio and 2.9m propeller). No Sakae-21/31-specific fin/bolt figure
# was found, so the Ha-25 figures are used here as the best-available same-
# family proxy for cylinder-level construction detail (this is a difference
# from earlier in this model, where sourced-vs-representative values were kept
# strictly separate; here it's a closely related sibling engine's data, noted
# explicitly rather than silently reused).
# True 3.54mm pitch over this barrel's finned length would need ~54 fins per
# cylinder (54x14=756 boolean unions on top of everything else already in this
# assembly) which is judged too heavy for one remote CAD job; FIN_N=22 (pitch
# 9.05mm) is used as a much closer approximation than the previous FIN_N=6
# (34mm pitch) while staying computationally tractable. FIN_T is moved from an
# unsourced 5.0mm toward the sourced 1.5mm, kept at 2.0mm for visible/robust
# boolean geometry at this fin pitch.
FIN_N = 22
FIN_R = BORE / 2.0 + 45.0
FIN_T = 2.0
CORE_R = BORE / 2.0 + 16.0

# cylinder base stud bolts (sourced: 12 per cylinder, Ha-25 data as above)
STUD_N = 12
STUD_R = 5.0
STUD_LEN = 20.0
STUD_CIRCLE_R = 95.0     # clears main tube (CORE_R=81) and pushrod region (see below)
STUD_PHASE = 15.0        # deg offset so bolts don't align with the pushrod pair
# base flange: a short wide disc the stud bolts sit on/embed into, so they
# fuse into the cylinder's single solid instead of floating disconnected
# (first submission without this had solid_count=13 per cylinder -- 1 main
# body + 12 disconnected bolts -- caught via list_cad_components, not by eye)
FLANGE_R = STUD_CIRCLE_R + STUD_R + 5.0   # 105: fully contains the bolt ring
FLANGE_D0 = CASE_R - 10.0                 # overlaps into the main tube start
FLANGE_D1 = CASE_R + 8.0                  # stays clear of pushrod (d=195+)

# crankcase 3-piece split (sourced: forged duralumin case split into front/
# middle/rear sections, same Ha-25 source as above)
CASE_SPLIT_GAP = 2.0

deltas = list(range(0, 721, 2))
times = [d / 180.0 for d in deltas]

# ================= colors =================
ALU_COLOR = cq.Color(0.75, 0.75, 0.78)
STEEL_COLOR = cq.Color(0.50, 0.51, 0.55)
ROD_COLOR = cq.Color(0.68, 0.70, 0.74)
CRANK_COLOR = cq.Color(0.62, 0.45, 0.20)
DARK_COLOR = cq.Color(0.16, 0.16, 0.18)
BLACK_PROP_COLOR = cq.Color(0.06, 0.06, 0.07)   # sourced: USAAF Spec 24114 Amdt.4, Shade No.44
YELLOW_TIP_COLOR = cq.Color(0.95, 0.82, 0.08)   # sourced: same spec, Shade No.48

# ================= geometry helpers =================
def uvec(theta_deg):
    r = math.radians(theta_deg)
    return (math.cos(r), math.sin(r))

def dvec(theta_deg):
    x, y = uvec(theta_deg)
    return (x, y, 0.0)

def tdir_vec(theta_deg):
    x, y = uvec(theta_deg)
    return (-y, x, 0.0)

def pvec(theta_deg, r, z):
    x, y = uvec(theta_deg)
    return (x * r, y * r, z)

def radial_cyl(radius, theta_deg, r0, r1, z):
    d = dvec(theta_deg)
    b = pvec(theta_deg, r0, z)
    return cq.Workplane(obj=cq.Solid.makeCylinder(radius, r1 - r0, cq.Vector(*b), cq.Vector(*d)))

def free_cyl(radius, length, origin, direction):
    return cq.Workplane(obj=cq.Solid.makeCylinder(radius, length, cq.Vector(*origin), cq.Vector(*direction)))

def closure_s(Px, Py, theta_deg, L):
    ux, uy = uvec(theta_deg)
    proj = Px * ux + Py * uy
    perp = -Px * uy + Py * ux
    val = L * L - perp * perp
    if val < 0.0:
        val = 0.0
    return proj + math.sqrt(val)

def in_wedge(theta_deg):
    t = theta_deg % 360.0
    return WEDGE_START <= t <= WEDGE_END

def make_wedge_cutter(theta_start, theta_end, radius, z0, zheight, n_seg=24):
    pts = [(0.0, 0.0)]
    for i in range(n_seg + 1):
        t = theta_start + (theta_end - theta_start) * i / n_seg
        r = math.radians(t)
        pts.append((radius * math.cos(r), radius * math.sin(r)))
    pts.append((0.0, 0.0))
    return cq.Workplane("XY").workplane(offset=z0).polyline(pts).close().extrude(zheight)

def unwrap_deg(seq):
    out = [seq[0]]
    off = 0.0
    for v in seq[1:]:
        prev = out[-1]
        cand = v + off
        while cand - prev > 180.0:
            off -= 360.0
            cand = v + off
        while cand - prev < -180.0:
            off += 360.0
            cand = v + off
        out.append(cand)
    return out

def stud_bolts(theta_deg, z):
    # 12 stud-bolt heads on a ring around the cylinder base flange, where the
    # jug bolts onto the crankcase (sourced count, see FIN_N comment above).
    # d-axis range CASE_R-8..CASE_R+12 is kept clear of both the main tube
    # (radius CORE_R at STUD_CIRCLE_R-STUD_R clearance) and the pushrod region
    # (which starts at CASE_R+15) -- numerically checked before building.
    d = dvec(theta_deg)
    tdir = tdir_vec(theta_deg)
    base = pvec(theta_deg, CASE_R - 8.0, z)
    shape = None
    for i in range(STUD_N):
        phi = math.radians(STUD_PHASE + 360.0 * i / STUD_N)
        ox = STUD_CIRCLE_R * math.cos(phi) * tdir[0]
        oy = STUD_CIRCLE_R * math.cos(phi) * tdir[1]
        oz = STUD_CIRCLE_R * math.sin(phi)
        origin = (base[0] + ox, base[1] + oy, base[2] + oz)
        bolt = free_cyl(STUD_R, STUD_LEN, origin, d)
        shape = bolt if shape is None else shape.union(bolt)
    return shape

# ================= static part builders =================
def build_cylinder_static(theta_deg, z):
    # tiny fixed epsilon (deg) applied to the STATIC jug geometry only (not to
    # piston/rod kinematics, which use the caller's exact theta_deg elsewhere):
    # at theta=167.142857deg (rear idx5) one of the unioned fin/pushrod/exhaust
    # cylinders landed EXACTLY tangent to another, which OpenCascade's boolean
    # fuse cannot merge cleanly -> a split, degenerate sliver solid (solid_count
    # 2, tiny bbox) and an invalid overall STEP shape. Nudging theta by a small
    # irrational-ish offset breaks any such exact-tangency coincidence; at the
    # jug's own radius (<=480mm) this shifts surfaces by only ~0.0001-0.0002mm,
    # far below visible/manufacturing tolerance.
    theta_deg = theta_deg + 0.0137
    d = dvec(theta_deg)
    shape = radial_cyl(CORE_R, theta_deg, CASE_R, CASE_R + BARREL_LEN, z)
    for i in range(FIN_N):
        rr = CASE_R + 20.0 + (BARREL_LEN - 40.0) * i / (FIN_N - 1)
        shape = shape.union(radial_cyl(FIN_R, theta_deg, rr - FIN_T / 2.0, rr + FIN_T / 2.0, z))
    shape = shape.union(radial_cyl(FIN_R + 8.0, theta_deg, CASE_R + BARREL_LEN, CASE_R + BARREL_LEN + HEAD_LEN * 0.55, z))
    shape = shape.union(radial_cyl(BORE / 2.0 + 6.0, theta_deg, CASE_R + BARREL_LEN + HEAD_LEN * 0.55, CASE_R + BARREL_LEN + HEAD_LEN, z))
    shape = shape.union(radial_cyl(FLANGE_R, theta_deg, FLANGE_D0, FLANGE_D1, z))
    shape = shape.union(stud_bolts(theta_deg, z))
    tdir = tdir_vec(theta_deg)
    for s in (-1, 1):
        bx, by, bz = pvec(theta_deg, CASE_R + 15.0, z)
        ox = tdir[0] * s * (BORE / 2.0 + 22.0)
        oy = tdir[1] * s * (BORE / 2.0 + 22.0)
        shape = shape.union(cq.Workplane(obj=cq.Solid.makeCylinder(
            6.0, BARREL_LEN + HEAD_LEN * 0.5, cq.Vector(bx + ox, by + oy, z), cq.Vector(*d))))
    ex_base = pvec(theta_deg, CASE_R + BARREL_LEN * 0.4, z)
    shape = shape.union(cq.Workplane(obj=cq.Solid.makeCylinder(
        15.0, 90.0, cq.Vector(*ex_base), cq.Vector(tdir[0], tdir[1], 0.0))))
    return shape

def piston_template():
    return cq.Workplane(obj=cq.Solid.makeCylinder(BORE / 2.0 - 1.0, 50.0, cq.Vector(-25.0, 0, 0), cq.Vector(1, 0, 0)))

def master_rod_template(L, r_flange, link_psi_list):
    big_end = (cq.Workplane(obj=cq.Solid.makeCylinder(PIN_R + 16.0, 40.0, cq.Vector(0, 0, -20.0), cq.Vector(0, 0, 1)))
               .cut(cq.Workplane(obj=cq.Solid.makeCylinder(PIN_R + 3.0, 42.0, cq.Vector(0, 0, -21.0), cq.Vector(0, 0, 1)))))
    shaft = (cq.Workplane("XY").workplane(offset=-6.0)
             .moveTo(0, -14).lineTo(L, -10).lineTo(L, 10).lineTo(0, 14).close().extrude(12.0))
    small_end = cq.Workplane(obj=cq.Solid.makeCylinder(22.0, 40.0, cq.Vector(L, 0, -20.0), cq.Vector(0, 0, 1)))
    rod = big_end.union(shaft).union(small_end)
    flange = cq.Workplane(obj=cq.Solid.makeCylinder(r_flange + 22.0, 14.0, cq.Vector(0, 0, -27.0), cq.Vector(0, 0, 1)))
    rod = rod.union(flange)
    for psi in link_psi_list:
        px = r_flange * math.cos(math.radians(psi))
        py = r_flange * math.sin(math.radians(psi))
        rod = rod.union(cq.Workplane(obj=cq.Solid.makeCylinder(9.0, 30.0, cq.Vector(px, py, -15.0), cq.Vector(0, 0, 1))))
    return rod

def link_rod_template(L):
    big_end = (cq.Workplane(obj=cq.Solid.makeCylinder(15.0, 20.0, cq.Vector(0, 0, -10.0), cq.Vector(0, 0, 1)))
               .cut(cq.Workplane(obj=cq.Solid.makeCylinder(9.3, 22.0, cq.Vector(0, 0, -11.0), cq.Vector(0, 0, 1)))))
    shaft = (cq.Workplane("XY").workplane(offset=-4.0)
             .moveTo(0, -9).lineTo(L, -7).lineTo(L, 7).lineTo(0, 9).close().extrude(8.0))
    small_end = (cq.Workplane(obj=cq.Solid.makeCylinder(15.0, 26.0, cq.Vector(L, 0, -13.0), cq.Vector(0, 0, 1)))
                 .cut(cq.Workplane(obj=cq.Solid.makeCylinder(11.3, 28.0, cq.Vector(L, 0, -14.0), cq.Vector(0, 0, 1)))))
    return big_end.union(shaft).union(small_end)

def _naca_thickness_shape(x):
    return 0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x * x + 0.2843 * x ** 3 - 0.1015 * x ** 4

_NACA_PEAK = max(_naca_thickness_shape(i / 1000.0) for i in range(1, 1001))

def _camber_frac(x, m, p):
    if x <= p:
        return m / (p * p) * (2.0 * p * x - x * x)
    return m / ((1.0 - p) ** 2) * ((1.0 - 2.0 * p) + 2.0 * p * x - x * x)

def airfoil_section_points(chord, thick):
    # cambered-airfoil cross-section (NACA4-style thickness+camber distribution),
    # numerically pre-verified as a simple (non-self-intersecting) closed polygon
    xs = [0.0, 0.05, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9, 1.0]
    upper, lower = [], []
    for x in xs:
        yt = (thick / 2.0) * (_naca_thickness_shape(x) / _NACA_PEAK if x > 0.0 else 0.0)
        yc = _camber_frac(x, PROP_CAMBER, PROP_CAMBER_POS) * chord
        Y = (x - PROP_PITCH_FRAC) * chord
        upper.append((Y, yc + yt))
        lower.append((Y, yc - yt))
    return [upper[0]] + upper[1:] + [lower[-1]] + lower[1:-1][::-1]

def prop_chord_at(f):
    # 3-point root/max-chord/tip taper (representative, see PROP_ROOT_CHORD
    # comment above) instead of a straight root-to-tip line, since the
    # Hamilton Standard 6523A-24 is widest around 25% span, not at the root.
    if f <= PROP_MAX_CHORD_FRAC:
        t = f / PROP_MAX_CHORD_FRAC
        return PROP_ROOT_CHORD + (PROP_MAX_CHORD - PROP_ROOT_CHORD) * t
    t = (f - PROP_MAX_CHORD_FRAC) / (1.0 - PROP_MAX_CHORD_FRAC)
    return PROP_MAX_CHORD + (PROP_TIP_CHORD - PROP_MAX_CHORD) * t

def prop_thick_at(f):
    return PROP_ROOT_THICK + (PROP_TIP_THICK - PROP_ROOT_THICK) * f

def prop_twist_at(f):
    return PROP_ROOT_TWIST + (PROP_TIP_TWIST - PROP_ROOT_TWIST) * f

def make_blade():
    n_seg = 12
    seg_len = (PROP_TIP_R - PROP_HUB_R) / n_seg
    parts = []
    for i in range(n_seg):
        f0 = i / n_seg
        f1 = (i + 1) / n_seg
        fm = (f0 + f1) / 2.0
        r_lo = PROP_HUB_R + (PROP_TIP_R - PROP_HUB_R) * f0
        chord = prop_chord_at(fm)
        thick = prop_thick_at(fm)
        twist = prop_twist_at(fm)
        pts = airfoil_section_points(chord, thick)
        seg = cq.Workplane("YZ").polyline(pts).close().extrude(seg_len)
        seg = seg.rotate((0, 0, 0), (1, 0, 0), twist)
        seg = seg.translate((r_lo, 0, 0))
        parts.append(seg)
    blade = parts[0]
    for p in parts[1:]:
        blade = blade.union(p)
    return blade

def make_band():
    # sourced yellow tip band: last 4in (101.6mm) of blade, per USAAF Spec
    # 24114 Amendment No.4 (see YELLOW_TIP_LEN comment above). Slightly
    # oversized copy of the blade cross-section so it forms a visible
    # painted "shell" over the blade surface, not a separate floating disc.
    span = PROP_TIP_R - PROP_HUB_R
    f0 = 1.0 - YELLOW_TIP_LEN / span
    f1 = 1.0
    fm = (f0 + f1) / 2.0
    r_lo = PROP_HUB_R + span * f0
    seg_len = span * (f1 - f0)
    chord = prop_chord_at(fm)
    thick = prop_thick_at(fm)
    twist = prop_twist_at(fm)
    pts = airfoil_section_points(chord * 1.06, thick + 4.0)
    band = cq.Workplane("YZ").polyline(pts).close().extrude(seg_len)
    band = band.rotate((0, 0, 0), (1, 0, 0), twist)
    band = band.translate((r_lo, 0, 0))
    return band

def build_prop_hub():
    # kept at the Sakae's existing small mount hub size (see PROP_HUB_R
    # comment above), NOT the P-51's real Hydromatic dome hub
    hub = free_cyl(PROP_HUB_R + 25.0, 50.0, (0, 0, -25.0), (0, 0, 1))
    nose1 = free_cyl(PROP_HUB_R + 15.0, 55.0, (0, 0, 25.0), (0, 0, 1))
    nose2 = free_cyl(PROP_HUB_R, 35.0, (0, 0, 80.0), (0, 0, 1))
    return hub.union(nose1).union(nose2)

def build_propeller_blades():
    blade = make_blade()
    prop = None
    for i in range(PROP_N_BLADES):
        ang = 360.0 * i / PROP_N_BLADES
        b = blade.rotate((0, 0, 0), (0, 0, 1), ang)
        prop = b if prop is None else prop.union(b)
    return prop

def build_crank():
    # cheek/counterweight sized so their rotating sweep (offset+radius) stays inside CASE_BORE_R
    cheek_r = 90.0
    cw_r = 75.0
    cw_offset = -45.0
    pin = free_cyl(PIN_R, Z1 - Z0, (R_CRANK, 0, Z0), (0, 0, 1))
    front_j = free_cyl(MAIN_J_R, 160.0, (0, 0, Z1), (0, 0, 1))
    rear_j = free_cyl(MAIN_J_R, 160.0, (0, 0, Z0 - 160.0), (0, 0, 1))
    cheek_f = free_cyl(cheek_r, 36.0, (0, 0, Z1 - 36.0), (0, 0, 1))
    cheek_r_ = free_cyl(cheek_r, 36.0, (0, 0, Z0), (0, 0, 1))
    cw_f = free_cyl(cw_r, 36.0, (cw_offset, 0, Z1 - 36.0), (0, 0, 1))
    cw_r_ = free_cyl(cw_r, 36.0, (cw_offset, 0, Z0), (0, 0, 1))
    return pin.union(front_j).union(rear_j).union(cheek_f).union(cheek_r_).union(cw_f).union(cw_r_)

# ================= assembly / kinematics =================
TOP = "sakae_engine"
top = cq.Assembly(name=TOP)
animation = []

cad_step(steps[0])
crank_rot = cq.Assembly(name="crank_rotation")
crank_rot.add(build_crank(), name="crank_body", color=CRANK_COLOR)
top.add(crank_rot, name="crank_rotation")
animation.append({"path": "/%s/crank_rotation" % TOP, "action": "rz",
                   "times": times, "values": [float(d) for d in deltas]})

WEDGE_CUTTER = make_wedge_cutter(WEDGE_START, WEDGE_END, 650.0, Z0 - 100.0, (Z1 - Z0) + 200.0)

# crankcase built as 3 pieces (front/mid/rear) with a thin visible parting
# line between each, per the sourced front/middle/rear split-case structure
# (see FIN_N comment above) -- rear third covers the rear-row (Z_REAR=0)
# mounting area, front third covers the front-row (Z_FRONT=280) mounting
# area, mid third is the plain center span between the two rows.
case_bore = free_cyl(CASE_BORE_R, (Z1 - Z0) + 40.0, (0, 0, Z0 - 20.0), (0, 0, 1))
CASE_SEG_LEN = (Z1 - Z0) / 3.0
MID_ALU_COLOR = cq.Color(0.71, 0.71, 0.74)
case_sections = [
    ("crankcase_rear", Z0, Z0 + CASE_SEG_LEN - CASE_SPLIT_GAP / 2.0, ALU_COLOR),
    ("crankcase_mid", Z0 + CASE_SEG_LEN + CASE_SPLIT_GAP / 2.0,
     Z0 + 2.0 * CASE_SEG_LEN - CASE_SPLIT_GAP / 2.0, MID_ALU_COLOR),
    ("crankcase_front", Z0 + 2.0 * CASE_SEG_LEN + CASE_SPLIT_GAP / 2.0, Z1, ALU_COLOR),
]
for seg_name, z_lo, z_hi, seg_color in case_sections:
    seg = free_cyl(CASE_R, z_hi - z_lo, (0, 0, z_lo), (0, 0, 1))
    seg = seg.cut(case_bore).cut(WEDGE_CUTTER)
    top.add(seg, name=seg_name, color=seg_color)

def build_row(top, row_name, z_row, theta0):
    cyl_thetas = [theta0 - k * STEP_DEG for k in range(N_ROW)]
    link_psis = [cyl_thetas[k] - theta0 for k in range(1, N_ROW)]

    row_static = cq.Assembly(name=row_name + "_cyls")
    for idx, theta_k in enumerate(cyl_thetas):
        if in_wedge(theta_k):
            continue  # cylinder jug removed for the cutaway view; piston/rod stay
        # NOTE: kept cylinders are NOT also cut by WEDGE_CUTTER here. Two rear-row
        # cylinders (idx1 @12.9deg, idx5 @167.1deg) sit only ~12deg outside the
        # wedge boundary, closer than their own fin/head angular half-width -> an
        # unconditional cut sliced a thin, disconnected notch out of their barrels
        # (solid_count=2, degenerate sliver bbox, contributed to an invalid STEP
        # shape). The crankcase itself still gets WEDGE_CUTTER applied separately
        # below, which is what actually opens up the viewing gap.
        shape = build_cylinder_static(theta_k, z_row)
        row_static.add(shape, name="cyl_%d" % idx, color=STEEL_COLOR)
    top.add(row_static, name=row_name + "_cyls")

    def Bpin(delta):
        r = math.radians(delta)
        return (R_CRANK * math.cos(r), R_CRANK * math.sin(r))

    def master_piston_s(delta):
        Px, Py = Bpin(delta)
        return closure_s(Px, Py, theta0, L_MASTER)

    def master_pose(delta):
        Px, Py = Bpin(delta)
        s = closure_s(Px, Py, theta0, L_MASTER)
        ux, uy = uvec(theta0)
        Sx, Sy = s * ux, s * uy
        ang = math.degrees(math.atan2(Sy - Py, Sx - Px))
        return (Px, Py, ang)

    def flange_knuckle(delta, psi):
        Px, Py, angM = master_pose(delta)
        a = math.radians(angM + psi)
        return (Px + R_FLANGE * math.cos(a), Py + R_FLANGE * math.sin(a))

    def link_piston_s(delta, theta_k, psi):
        Kx, Ky = flange_knuckle(delta, psi)
        return closure_s(Kx, Ky, theta_k, L_LINK)

    def link_pose(delta, theta_k, psi):
        Kx, Ky = flange_knuckle(delta, psi)
        s = closure_s(Kx, Ky, theta_k, L_LINK)
        ux, uy = uvec(theta_k)
        Sx, Sy = s * ux, s * uy
        ang = math.degrees(math.atan2(Sy - Ky, Sx - Kx))
        return (Kx, Ky, ang)

    # --- piston frames (all 7 in the row) ---
    for idx, theta_k in enumerate(cyl_thetas):
        if idx == 0:
            s0 = master_piston_s(0)
            svals = [master_piston_s(d) - s0 for d in deltas]
        else:
            psi = theta_k - theta0
            s0 = link_piston_s(0, theta_k, psi)
            svals = [link_piston_s(d, theta_k, psi) - s0 for d in deltas]
        ptrans = cq.Assembly(name=row_name + "_pist_t_%d" % idx)
        ptrans.add(piston_template(), name="piston", color=ALU_COLOR)
        frame = cq.Assembly(name=row_name + "_pist_frame_%d" % idx)
        frame.add(ptrans, name=row_name + "_pist_t_%d" % idx, loc=cq.Location(cq.Vector(s0, 0, 0)))
        top.add(frame, name=row_name + "_pist_frame_%d" % idx,
                loc=cq.Location(cq.Vector(0, 0, z_row), cq.Vector(0, 0, 1), theta_k))
        path = "/%s/%s_pist_frame_%d/%s_pist_t_%d" % (TOP, row_name, idx, row_name, idx)
        animation.append({"path": path, "action": "tx", "times": times, "values": svals})

    # --- master rod (idx 0) ---
    Bx0, By0, ang0 = master_pose(0)
    rangle = cq.Assembly(name=row_name + "_master_angle")
    rangle.add(master_rod_template(L_MASTER, R_FLANGE, link_psis), name="rod", color=ROD_COLOR)
    rpivot = cq.Assembly(name=row_name + "_master_pivot")
    rpivot.add(rangle, name=row_name + "_master_angle", loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), ang0))
    top.add(rpivot, name=row_name + "_master_pivot", loc=cq.Location(cq.Vector(Bx0, By0, z_row)))
    tvals, araw = [], []
    for d in deltas:
        Bx, By, ang = master_pose(d)
        tvals.append([Bx - Bx0, By - By0, 0.0])
        araw.append(ang)
    aunw = unwrap_deg(araw)
    abase = aunw[0]
    avals = [a - abase for a in aunw]
    animation.append({"path": "/%s/%s_master_pivot" % (TOP, row_name), "action": "t", "times": times, "values": tvals})
    animation.append({"path": "/%s/%s_master_pivot/%s_master_angle" % (TOP, row_name, row_name),
                       "action": "rz", "times": times, "values": avals})

    # --- link rods (idx 1..6) ---
    for k in range(1, N_ROW):
        theta_k = cyl_thetas[k]
        psi = theta_k - theta0
        Kx0, Ky0, angL0 = link_pose(0, theta_k, psi)
        rangle_k = cq.Assembly(name=row_name + "_link_angle_%d" % k)
        rangle_k.add(link_rod_template(L_LINK), name="rod", color=ROD_COLOR)
        rpivot_k = cq.Assembly(name=row_name + "_link_pivot_%d" % k)
        rpivot_k.add(rangle_k, name=row_name + "_link_angle_%d" % k,
                     loc=cq.Location(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), angL0))
        top.add(rpivot_k, name=row_name + "_link_pivot_%d" % k, loc=cq.Location(cq.Vector(Kx0, Ky0, z_row)))
        tvals, araw = [], []
        for d in deltas:
            Kx, Ky, ang = link_pose(d, theta_k, psi)
            tvals.append([Kx - Kx0, Ky - Ky0, 0.0])
            araw.append(ang)
        aunw = unwrap_deg(araw)
        abase = aunw[0]
        avals = [a - abase for a in aunw]
        animation.append({"path": "/%s/%s_link_pivot_%d" % (TOP, row_name, k), "action": "t",
                           "times": times, "values": tvals})
        animation.append({"path": "/%s/%s_link_pivot_%d/%s_link_angle_%d" % (TOP, row_name, k, row_name, k),
                           "action": "rz", "times": times, "values": avals})

cad_step(steps[1])
theta0_front = 90.0
build_row(top, "front", Z_FRONT, theta0_front)

cad_step(steps[2])
theta0_rear = theta0_front - ROW_OFFSET
build_row(top, "rear", Z_REAR, theta0_rear)

cad_step(steps[3])
cad_step(steps[4])

cad_step(steps[5])
nose = free_cyl(160.0, 250.0, (0, 0, Z1 + 160.0), (0, 0, 1))
prop_shaft = free_cyl(35.0, 70.0, (0, 0, Z1 + 160.0 + 250.0), (0, 0, 1))
acc = free_cyl(170.0, 250.0, (0, 0, Z0 - 160.0 - 250.0), (0, 0, 1))
acc = acc.union(free_cyl(28.0, 55.0, (60.0, 0, Z0 - 160.0 - 60.0), (1, 0, 0)))
acc = acc.union(free_cyl(28.0, 55.0, (-60.0, 0, Z0 - 160.0 - 60.0), (-1, 0, 0)))
top.add(nose, name="nose_case", color=ALU_COLOR)
top.add(prop_shaft, name="prop_shaft_stub", color=STEEL_COLOR)
top.add(acc, name="accessory_case", color=DARK_COLOR)

cad_step(steps[6])
prop_rot = cq.Assembly(name="prop_rotation")
prop_rot.add(build_prop_hub(), name="prop_hub", color=STEEL_COLOR)
prop_rot.add(build_propeller_blades(), name="prop_blades", color=BLACK_PROP_COLOR)
band = make_band()
for i in range(PROP_N_BLADES):
    ang = 360.0 * i / PROP_N_BLADES
    prop_rot.add(band.rotate((0, 0, 0), (0, 0, 1), ang), name="prop_band_%d" % i, color=YELLOW_TIP_COLOR)
top.add(prop_rot, name="prop_rotation", loc=cq.Location(cq.Vector(0, 0, PROP_Z)))
animation.append({"path": "/%s/prop_rotation" % TOP, "action": "rz",
                   "times": times, "values": [float(d) * PROP_REDUCTION for d in deltas]})

cad_step(steps[7])
result = top
