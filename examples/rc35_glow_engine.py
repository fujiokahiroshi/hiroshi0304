"""RC35-class single-cylinder two-stroke glow engine, piston-crank animated.

Rotary-inlet crankcase, ported brass liner, aluminium piston with hollow
wrist pin, connecting rod, crankshaft/flywheel, finned cooling head, glow
plug, and slide carburetor. Two copies are shown side by side: a full
exterior and a sectioned cutaway, both driven by the same crank-angle
animation (piston travel and rod angle derived from THROW/ROD geometry).
"""

import math
import cadquery as cq
steps = ["クランクケース・吸排気経路", "シリンダー・ピストン・コンロッド", "クランク軸・軸受", "冷却ヘッド・キャブレター・締結部", "完成外観と断面を並べて表示"]
B=16.27
STROKE=16.8
THROW=8.4
ROD=24.0
THETA=70.0
CY=2.0
def cyl(r,h,x=0,y=0,z=0,axis=(0,0,1)):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),cq.Vector(*axis)))
def cy(r,y0,y1,x=0,z=0):
    return cyl(r,y1-y0,x,y0,z,(0,1,0))
def box(sx,sy,sz,x,y,z):
    return cq.Workplane('XY').box(sx,sy,sz).translate((x,y,z))
def ringy(ro,ri,y0,y1):
    return cy(ro,y0,y1).cut(cy(ri,y0,y1))
parts=[]
def add(name,shape,color,section=False):
    parts.append((name,shape,color,section))
silver=cq.Color(0.70,0.72,0.75)
dark=cq.Color(0.20,0.22,0.25)
steel=cq.Color(0.44,0.48,0.53)
blue=cq.Color(0.08,0.31,0.73)
brass=cq.Color(0.77,0.56,0.22)

cad_step(steps[0])
case=cy(18,-8,17).union(cy(13.5,-30,-7))
case=case.union(cyl(14,30.8,0,CY,8))
case=case.union(cyl(20,5.8,0,CY,33))
for z in [20,23,26,29]:
    case=case.union(cyl(16,1.2,0,CY,z))
for x in [-18.5,18.5]:
    case=case.union(box(8,29,4,x,-1,-10))
case=case.union(cyl(7,12,0,-21,5))
case=case.union(cy(6,10,28,0,27.5))
case=case.cut(cy(16.5,-6,17)).cut(cy(7.1,-30,-6))
case=case.cut(cy(12,-12,-6)).cut(cy(9,-30,-24))
case=case.cut(cyl(10.3,40,0,CY,8))
case=case.cut(cyl(4.5,24,0,-21,-1))
case=case.cut(cy(4.5,7,29,0,27.5))
case=case.cut(box(7,14,5,0,9,27.5))
for s in [-1,1]:
    case=case.cut(box(3.3,5,20,s*10.6,CY,18))
    case=case.cut(box(6,5,4,s*9,CY,25))
case=case.cut(box(4.5,3.3,19,0,CY-10.6,17.5))
case=case.cut(box(4.5,6,3,0,CY-9,24.5))
for x in [-18.5,18.5]:
    for y in [-11.5,9.5]:
        case=case.cut(cyl(1.65,8,x,y,-14))
for x in [-12,12]:
    for y in [-10,14]:
        case=case.cut(cyl(1.3,7,x,y,32))
add('crankcase_cast_aluminium',case,silver,True)
back=cy(18,17,19.5).cut(cy(15,17,17.5))
for x,z in [(-12,-10),(12,-10),(-12,10),(12,10)]:
    back=back.cut(cy(1.3,17,20,x,z))
add('rear_cover',back,dark,True)

cad_step(steps[1])
liner=cyl(10.25,25.3,0,CY,13.5).cut(cyl(B/2,25.3,0,CY,13.5))
liner=liner.cut(box(7,7,5,0,CY+8.5,27.5))
for s in [-1,1]:
    liner=liner.cut(box(6,4.2,4,s*9,CY,25))
liner=liner.cut(box(4,6,3,0,CY-9,24.5))
add('ported_brass_liner',liner,brass,True)
t=math.radians(THETA)
px=THROW*math.sin(t)
pz=THROW*math.cos(t)
wz=pz+math.sqrt(ROD*ROD-px*px)
rodangle=-math.degrees(math.asin(px/ROD))
piston=cyl(B/2-0.025,9,0,0,-3)
piston=piston.cut(box(11.8,6.4,7.4,0,0,0.7))
piston=piston.cut(cy(2.01,-10,10))
piston=piston.faces('>Z').edges().chamfer(0.15)
add('aluminium_piston',piston.translate((0,CY,wz)),silver,True)
wrist=cy(2,-7.8,7.8).cut(cy(1.2,-7.8,7.8))
add('hollow_wrist_pin',wrist.translate((0,CY,wz)),steel,True)
rod=cy(4.4,-2,2).union(cy(3.3,-2,2,0,ROD))
rod=rod.union(box(4.5,3.3,ROD,0,0,ROD/2))
rod=rod.cut(cy(2.55,-3,3)).cut(cy(2.05,-3,3,0,ROD))
rod=rod.cut(cyl(0.65,5,0,0,ROD+1.7))
rod=rod.rotate((0,0,0),(0,1,0),rodangle).translate((px,CY,pz))
add('connecting_rod',rod,cq.Color(0.78,0.80,0.83))

cad_step(steps[2])
crank=cy(12,-5,-1)
crank=crank.union(cy(7,-24,-5)).union(cy(5,-39,-24)).union(cy(3.15,-48,-39))
crank=crank.union(cy(2.5,-1,4.5,0,THROW))
crank=crank.cut(cy(3.5,-32,-0.9))
crank=crank.cut(box(7.5,9,6,0,-21,6))
crank=crank.cut(cy(2.3,-5,-1,5,5)).cut(cy(2.3,-5,-1,-5,5))
crank=crank.rotate((0,0,0),(0,1,0),THETA)
add('rotary_inlet_crankshaft',crank,steel)
add('front_bearing_envelope',ringy(9,5,-30,-24),dark,True)
add('rear_bearing_envelope',ringy(12,7,-12,-6),dark,True)
fly=ringy(16,5,-36,-32)
for i in range(12):
    a=2*math.pi*i/12
    fly=fly.cut(cy(1.8,-36,-32,12*math.cos(a),12*math.sin(a)))
add('flywheel',fly,brass,True)

cad_step(steps[3])
insert=cyl(11.9,4.7,0,CY,38.8)
insert=insert.cut(cq.Workplane(obj=cq.Solid.makeSphere(6.5,cq.Vector(0,CY,37))))
insert=insert.cut(cyl(2.6,8,0,CY,38))
add('combustion_chamber_insert',insert,silver,True)
head=cyl(20,4.7,0,CY,38.8).cut(cyl(12,4.7,0,CY,38.8))
head=head.union(cyl(13,22.5,0,CY,43.5).cut(cyl(7,22.5,0,CY,43.5)))
for i in range(8):
    radius=23.5-0.35*abs(i-4)
    fin=cyl(radius,1.5,0,CY,43.5+3*i).cut(cyl(7,1.5,0,CY,43.5+3*i))
    head=head.union(fin)
for x in [-12,12]:
    for y in [-10,14]:
        head=head.cut(cyl(1.65,29,x,y,38.5)).cut(cyl(2.8,4,x,y,63))
        screw=cyl(1.25,30,x,y,34).union(cyl(2.5,2,x,y,64))
        socket=cq.Workplane('XY').workplane(offset=64.8).center(x,y).polygon(6,2.3).extrude(2)
        add('head_screw_'+str(x)+'_'+str(y),screw.cut(socket),steel)
add('blue_finned_cooling_head',head,blue,True)
plug=cyl(2.5,3,0,CY,41).union(cyl(3.1,2,0,CY,43.5))
plug=plug.union(cq.Workplane('XY').workplane(offset=45.5).center(0,CY).polygon(6,8).extrude(3))
plug=plug.union(cyl(1.7,4,0,CY,48.5))
add('glow_plug_envelope',plug,brass,True)
carb=cyl(4.45,5,0,-21,12).union(cyl(7,12,0,-21,17))
carb=carb.union(box(18,13,12,0,-21,23))
carb=carb.cut(cyl(3.5,22,0,-21,10))
carb=carb.cut(cyl(5.1,24,-12,-21,23,(1,0,0)))
carb=carb.cut(cyl(2.05,10,7,-21,27))
add('slide_carburetor_body',carb,dark,True)
slide=cyl(5,22,-10,-21,23,(1,0,0)).cut(cyl(3.5,12,0,-21,17))
add('throttle_slide',slide,steel,True)
ball=cq.Workplane(obj=cq.Solid.makeSphere(2,cq.Vector(14,-21,23),angleDegrees1=-90,angleDegrees2=90))
ball=ball.union(cyl(1.2,2,12,-21,23,(1,0,0)))
add('throttle_ball_link',ball,steel)
needle=cyl(2,7,7,-21,29).union(cyl(2.8,2,7,-21,36))
fuel=cyl(1.5,6,7,-21,33,(1,0,0))
needle=needle.union(fuel).cut(cyl(0.6,9,7,-21,29)).cut(cyl(0.7,6,7,-21,33,(1,0,0)))
add('fuel_needle_and_nipple_envelope',needle,brass)
for x,z in [(-12,-10),(12,-10),(-12,10),(12,10)]:
    screw=cy(1.2,14,19.5,x,z).union(cy(2.2,19.5,21.5,x,z))
    # clearance holes continue into the case for this conceptual fastening
    case=case.cut(cy(1.3,13.5,17,x,z))
    add('back_screw_'+str(x)+'_'+str(z),screw,steel)
parts[0]=('crankcase_cast_aluminium',case,silver,True)

cad_step(steps[4])
cut=box(80,180,150,40,0,30)
moving=['rotary_inlet_crankshaft','flywheel','aluminium_piston','hollow_wrist_pin','connecting_rod']
def animated_engine(name,section):
    a=cq.Assembly(name=name)
    spin=cq.Assembly(name='crank_rotation')
    piston_group=cq.Assembly(name='piston_translation')
    for n,s,col,can_cut in parts:
        if n == 'rotary_inlet_crankshaft':
            spin.add(s.rotate((0,0,0),(0,1,0),-THETA),name=n,color=col)
        elif n == 'flywheel':
            spin.add(s,name=n,color=col)
        elif n in ['aluminium_piston','hollow_wrist_pin']:
            local=s.translate((0,-CY,-wz))
            if section:
                local=local.cut(cut)
            piston_group.add(local,name=n,color=col)
        elif n == 'connecting_rod':
            rod_local=s.translate((-px,-CY,-pz)).rotate((0,0,0),(0,1,0),-rodangle)
        else:
            if section and (n.startswith('head_screw_12') or n.startswith('back_screw_12') or n in ['throttle_ball_link','fuel_needle_and_nipple_envelope']):
                continue
            a.add(s.cut(cut) if section and can_cut else s,name=n,color=col)
    a.add(spin,name='crank_rotation',loc=cq.Location(cq.Vector(0,0,0),cq.Vector(0,1,0),THETA))
    a.add(piston_group,name='piston_translation',loc=cq.Location(cq.Vector(0,CY,wz)))
    carrier=cq.Assembly(name='rod_pivot_translation')
    carrier.add(rod_local,name='rod_angle',loc=cq.Location(cq.Vector(0,0,0),cq.Vector(0,1,0),rodangle),color=silver)
    a.add(carrier,name='rod_pivot_translation',loc=cq.Location(cq.Vector(px,CY,pz)))
    return a
result=cq.Assembly(name='rc35_animation')
result.add(animated_engine('exterior',False),name='exterior',loc=cq.Location(cq.Vector(-40,0,0)))
result.add(animated_engine('section',True),name='section',loc=cq.Location(cq.Vector(40,0,0)))
times=[i/90.0 for i in range(721)]
angles=[float(i) for i in range(721)]
piston_values=[]
rod_positions=[]
rod_angles=[]
for delta in angles:
    t=math.radians(THETA+delta)
    x=THROW*math.sin(t)
    z=THROW*math.cos(t)
    h=z+math.sqrt(ROD*ROD-x*x)
    alpha=-math.degrees(math.asin(x/ROD))
    piston_values.append(h-wz)
    rod_positions.append([x-px,0.0,z-pz])
    rod_angles.append(alpha-rodangle)
animation=[]
for side in ['exterior','section']:
    base='/rc35_animation/'+side
    animation.append({'path':base+'/crank_rotation','action':'ry','times':times,'values':angles})
    animation.append({'path':base+'/piston_translation','action':'tz','times':times,'values':piston_values})
    animation.append({'path':base+'/rod_pivot_translation','action':'t','times':times,'values':rod_positions})
    animation.append({'path':base+'/rod_pivot_translation/rod_angle','action':'ry','times':times,'values':rod_angles})
