"""1925 Ford Model T open touring reconstruction, chassis to body.

Accumulated incrementally: frame and transverse leaf springs, wooden
artillery wheels, front beam axle with knuckle steering, torque-tube
driveline, four-throw crankshaft, clutch/transmission envelopes, a
three-pinion open differential with spherical-involute bevel final drive,
roller bearings, drag-link steering, and the open touring body with
fenders, splash aprons and folding top. `result` is reassigned as each
subsystem is added; only the last assignment (the full
Model_T_1925_front_reconstruction assembly with the touring body attached)
is the exported model. Final `animation` covers steering, differential,
bearing and crank motion (see the last `animation = [...]` block).
"""

import cadquery as cq
import math
steps=['Frame and transverse springs','Axles and wooden wheels','Engine and transmission envelopes','Torque tube and controls']
result=cq.Assembly(name='Model_T_chassis_layout')
black=cq.Color(.09,.1,.11)
steel=cq.Color(.43,.46,.49)
wood=cq.Color(.48,.28,.12)
rubber=cq.Color(.035,.035,.04)
green=cq.Color(.2,.3,.22)
brass=cq.Color(.7,.52,.22)
def box(x,y,z,p):
 return cq.Workplane('XY').box(x,y,z).translate(p)
def cyl(r,h,p,d):
 return cq.Workplane(obj=cq.Solid.makeCylinder(r,h,cq.Vector(*p),cq.Vector(*d)))
def rod(a,b,r):
 v=cq.Vector(*b)-cq.Vector(*a)
 return cyl(r,v.Length,a,v.normalized().toTuple())
def add(s,n,c=steel):
 result.add(s,name=n,color=c)
cad_step(steps[0])
# X longitudinal, front axle X=0, rear X=2540, Y lateral, ground Z=0.
for side in [-1,1]:
 rail=box(2810,55,100,(1245,side*360,520)).cut(box(2812,49,88,(1245,side*360-side*6,520)))
 add(rail,'channel_rail_'+str(side),black)
for i,x in enumerate([0,1400,2540]):
 add(box(65,665,65,(x,0,570)),'crossmember_'+str(i),black)
for i,x in enumerate([0,2540]):
 spring=None
 for j in range(6):
  half=570-j*55
  pts=[]
  for k in range(25):
   y=-half+2*half*k/24
   pts.append((y,420-35*(y/570)**2+j*7))
  pts+= [(y,z+5) for y,z in pts[::-1]]
  leaf=cq.Workplane('YZ',origin=(x-22+(190 if x==2540 else 0),0,0)).polyline(pts).close().extrude(44)
  spring=leaf if spring is None else spring.union(leaf)
 add(spring,'transverse_leaf_spring_'+str(i),black)
cad_step(steps[1])
add(box(45,1240,40,(0,0,365)),'front_beam_axle',black)
for x in [0,2540]:
 for side in [-1,1]:
  y=side*711.2
  wheel=cyl(342,65,(x,y-32.5,381),(0,1,0)).cut(cyl(302,67,(x,y-33.5,381),(0,1,0)))
  hub=cyl(65,100,(x,y-50,381),(0,1,0))
  for k in range(12):
   a=k*math.pi/6
   hub=hub.union(rod((x+48*math.cos(a),y,381+48*math.sin(a)),(x+310*math.cos(a),y,381+310*math.sin(a)),18))
  add(wheel.union(hub),'wood_wheel_'+str(x)+'_'+str(side),wood)
  tire=cyl(381,80,(x,y-40,381),(0,1,0)).cut(cyl(343,82,(x,y-41,381),(0,1,0)))
  add(tire,'tire_'+str(x)+'_'+str(side),rubber)
  if x==0:
   add(cyl(25,115,(0,side*600 if side>0 else -715,381),(0,1,0)),'front_stub_'+str(side))
  else:
   add(cyl(90,40,(x,y-side*95-20,381),(0,1,0)).cut(cyl(28,42,(x,y-side*95-21,381),(0,1,0))),'rear_brake_drum_'+str(side),black)
rear=cyl(47,1290,(2540,-645,381),(0,1,0)).union(cq.Workplane('XY').sphere(145).translate((2540,0,381)))
add(rear,'rear_axle_and_differential_ENVELOPE',black)
cad_step(steps[2])
# Outer packaging only: no inferred planetary teeth or engine internal mechanism.
block=box(530,265,220,(485,0,645))
for bx in [290,420,550,680]:
 block=block.cut(cyl(47.625,222,(bx,0,534),(0,0,1)))
add(block,'four_bore_L_head_block',green)
add(box(545,280,40,(485,0,778)),'detachable_cylinder_head',green)
add(box(575,280,125,(495,0,472.5)).cut(box(555,260,130,(495,0,485))),'hollow_engine_sump',black)
for i,x in enumerate([290,420,550,680]):
 add(cyl(13,30,(x,0,800),(0,0,1)),'spark_plug_'+str(i),brass)
 add(cyl(22,32,(x,-154,665),(0,1,0)),'exhaust_port_'+str(i))
add(rod((275,-180,665),(710,-180,665),25),'exhaust_manifold',steel)
add(cyl(170,100,(785,0,480),(1,0,0)).cut(cyl(156,102,(784,0,480),(1,0,0))),'hollow_flywheel_housing',black)
add(cyl(125,220,(885,0,480),(1,0,0)).cut(cyl(112,222,(884,0,480),(1,0,0))),'hollow_transmission_housing',green)
add(cyl(50,55,(1105,0,480),(1,0,0)),'universal_joint_ENVELOPE',steel)
rad=box(95,570,510,(115,0,750)).cut(box(97,485,405,(115,0,747)))
add(rad,'radiator_shell',brass)
add(box(65,481,401,(115,0,747)),'radiator_core',black)
add(rod((155,0,965),(370,0,822),24),'upper_cooling_pipe',black)
for s in [-1,1]:
 add(box(100,220,20,(770,s*240,550)),'rear_engine_mount_'+str(s),black)
cad_step(steps[3])
a=(1160,0,480)
b=(2410,0,381)
tube=rod(a,b,37).cut(rod(a,b,22))
add(tube,'torque_tube_hollow',black)
add(rod(a,b,16),'propeller_shaft',steel)
for s in [-1,1]:
 add(rod((1120,0,425),(2470,s*490,381),15),'rear_radius_rod_'+str(s),black)
 add(rod((880,0,285),(0,s*490,365),15),'front_wishbone_'+str(s),black)
add(rod((-70,-630,355),(-70,630,355),12),'steering_tie_rod',steel)
for i in range(3):
 y=-150+i*100
 add(rod((1045,y,550),(1110,y,675),13).union(box(85,65,12,(1110,y,681))),'control_pedal_'+str(i),black)
result.objects['control_pedal_2'].obj=result.objects['control_pedal_2'].obj.translate((40,0,0))
add(rod((1030,-260,570),(1440,-310,1050),18),'steering_column_ENVELOPE',black)
# steering wheel normal aligned with column
v=cq.Vector(410,-50,480).normalized()
rim=cq.Workplane(obj=cq.Solid.makeTorus(200,13)).rotate((0,0,0),(0,1,0),40).translate((1440,-310,1050))
add(rim,'steering_wheel_rim',wood)

hub=cyl(30,35,(0,0,-17.5),(0,0,1))
for k in range(4):
 t=k*math.pi/2
 hub=hub.union(rod((0,0,0),(195*math.cos(t),195*math.sin(t),0),9))
add(hub.rotate((0,0,0),(0,1,0),40).translate((1440,-310,1050)),'steering_wheel_hub_spokes',black)

# Provisional supports: dimensions estimated, no manufacturing claim.
for x in [0,2730]:
 for sy in [-570,570]:
  axle_x=0 if x==0 else 2540
  add(rod((axle_x,sy,381),(x,sy,393),14),'spring_end_support_'+str(x)+'_'+str(sy),steel)
 add(box(55,70,77,(x,0,498.5)),'spring_center_saddle_'+str(x),black)
 if x==2730:
  add(box(190,80,35,(2635,0,550)),'rear_spring_support_extension',black)
for sy in [-630,630]:
 add(rod((-70,sy,355),(0,sy,381),12),'steering_arm_layout_'+str(sy),steel)
# Transparent head exposes the four dimensioned bores in review mode.
result.objects['detachable_cylinder_head'].color=cq.Color(.2,.3,.22,.25)

# Educational section through cylinder centre plane; static mid-stroke arrangement.
cutaway=box(650,400,420,(485,-200,670))
for name in ['four_bore_L_head_block','detachable_cylinder_head','hollow_engine_sump']:
 node=result.objects[name]
 node.obj=node.obj.cut(cutaway)
 node.color=green if name!='hollow_engine_sump' else black
# Bore is 95.25 mm. Piston clearance here is deliberately visual, not machining tolerance.
for i,bx in enumerate([290,420,550,680]):
 pz=670.8 if i in [0,3] else 569.2
 piston=cyl(46.9,65,(bx,0,pz),(0,0,1)).cut(cyl(39,56,(bx,0,pz-1),(0,0,1)))
 for gz in [pz+48,pz+55]:
  groove=cyl(48,2,(bx,0,gz),(0,0,1)).cut(cyl(45.6,2,(bx,0,gz),(0,0,1)))
  piston=piston.cut(groove)
 piston=piston.cut(cyl(10,100,(bx-50,0,pz+25),(1,0,0)))
 add(piston,'piston_visual_'+str(i),steel)
 add(cyl(9.5,85,(bx-42.5,0,pz+25),(1,0,0)),'wrist_pin_visual_'+str(i),brass)

# Explicit mating seats. These are simplified joints, not production bearings.
def seat(receiver,tool):
 result.objects[receiver].obj=result.objects[receiver].obj.cut(tool)
for side in [-1,1]:
 # Rotating front hub bore with 0.5 mm display clearance.
 seat('wood_wheel_0_'+str(side),cyl(25.5,130,(0,side*711.2-65,381),(0,1,0)))
 # Stationary rear housing passes through an annular brake drum.
 seat('rear_brake_drum_'+str(side),cyl(47.5,60,(2540,side*616.2-30,381),(0,1,0)))
 # Mounted parts get defined socket/seat geometry rather than overlapping solids.
 seat('front_beam_axle',result.objects['front_stub_'+str(side)].obj)
 seat('rear_engine_mount_'+str(side),result.objects['hollow_flywheel_housing'].obj)
 seat('rear_engine_mount_'+str(side),result.objects['four_bore_L_head_block'].obj)
 for x in [0,2730]:
  support='spring_end_support_'+str(x)+'_'+str(side*570)
  spring='transverse_leaf_spring_'+str(0 if x==0 else 1)
  seat(support,result.objects[spring].obj)
  seat(support,result.objects['front_beam_axle' if x==0 else 'rear_axle_and_differential_ENVELOPE'].obj)
 seat('front_wishbone_'+str(side),result.objects['front_beam_axle'].obj)
 seat('rear_radius_rod_'+str(side),result.objects['universal_joint_ENVELOPE'].obj)
 seat('steering_arm_layout_'+str(side*630),result.objects['front_stub_'+str(side)].obj)
 seat('steering_arm_layout_'+str(side*630),result.objects['steering_tie_rod'].obj)
# Pedal shaft passages in the simplified transmission shell.
for i in [1,2]:
 seat('hollow_transmission_housing',result.objects['control_pedal_'+str(i)].obj)
# Drive shaft / tube entry into simplified housings.
for name in ['universal_joint_ENVELOPE','rear_axle_and_differential_ENVELOPE']:
 seat(name,rod((1130,0,482.376),(2440,0,378.624),38))
# Cooling hose socket in radiator; cylinder head connection remains schematic.
for name in ['radiator_shell','radiator_core']:
 seat(name,result.objects['upper_cooling_pipe'].obj)
seat('rear_spring_support_extension',result.objects['crossmember_2'].obj)
seat('rear_spring_support_extension',result.objects['spring_center_saddle_2730'].obj)
seat('front_wishbone_1',result.objects['front_wishbone_-1'].obj)
seat('rear_radius_rod_1',result.objects['rear_radius_rod_-1'].obj)
seat('steering_wheel_hub_spokes',result.objects['steering_column_ENVELOPE'].obj)
seat('steering_wheel_hub_spokes',result.objects['steering_wheel_rim'].obj)
for sy in [-630,630]:
 seat('steering_arm_layout_'+str(sy),result.objects['front_beam_axle'].obj)

# Kinematic study dimensions: measured stroke 101.6; assumed rod length 165 mm.
# Main axis X at Z=480. Outer throws up; inner throws down.
crank=None
for i,bx in enumerate([290,420,550,680]):
 dz=50.8 if i in [0,3] else -50.8
 pinz=480+dz
 upperz=pinz+165
 for wx in [bx-31,bx+19]:
  web=cyl(30,12,(wx,0,480),(1,0,0)).union(cyl(24,12,(wx,0,pinz),(1,0,0)))
  web=web.union(box(12,40,abs(dz),(wx+6,0,480+dz/2)))
  crank=web if crank is None else crank.union(web)
 crank=crank.union(cyl(18,38,(bx-19,0,pinz),(1,0,0)))
 # Hollow big and small ends, connected by a tapered-free study shank.
 big=cyl(27,24,(bx-12,0,pinz),(1,0,0)).cut(cyl(18.4,26,(bx-13,0,pinz),(1,0,0)))
 small=cyl(15,18,(bx-9,0,upperz),(1,0,0)).cut(cyl(9.8,20,(bx-10,0,upperz),(1,0,0)))
 shank=box(14,17,131,(bx,0,pinz+90.5))
 connecting=big.union(shank).union(small)
 connecting=connecting.cut(cyl(18.4,26,(bx-13,0,pinz),(1,0,0))).cut(cyl(9.8,26,(bx-13,0,upperz),(1,0,0)))
 add(connecting,'connecting_rod_'+str(i),steel)
for x0,x1 in [(220,259),(321,389),(451,519),(581,649),(711,785)]:
 crank=crank.union(cyl(22,x1-x0,(x0,0,480),(1,0,0)))
add(crank,'four_throw_crankshaft_study',steel)
# Remove interfering visual sump material around rotating envelope, preserving outer pan.
seat('hollow_engine_sump',cyl(83,560,(225,0,480),(1,0,0)))

seat('four_bore_L_head_block',cyl(83,560,(225,0,480),(1,0,0)))
old=result
result=cq.Assembly(name='Model_T_running_study')
for name,node in old.objects.items():
 if node.obj is None:continue
 if name=='four_throw_crankshaft_study':
  result.add(node.obj.translate((0,0,-480)),name=name,color=node.color,loc=cq.Location(cq.Vector(0,0,480)))
 elif name.startswith('connecting_rod_'):
  i=int(name[-1]); bx=[290,420,550,680][i]; z=530.8 if i in [0,3] else 429.2
  group=cq.Assembly(name='rod_carrier_'+str(i))
  group.add(node.obj.translate((-bx,0,-z)),name='swing',color=node.color)
  result.add(group,name='rod_carrier_'+str(i),loc=cq.Location(cq.Vector(bx,0,z)))
 else:result.add(node.obj,name=name,color=node.color)
times=[i/60 for i in range(481)]
angles=[i*1.5 for i in range(481)]
base='/Model_T_running_study/'
animation=[{'path':base+'four_throw_crankshaft_study','action':'rx','times':times,'values':angles}]
for i in range(4):
 phase=0 if i in [0,3] else math.pi
 initial=50.8*math.cos(phase)
 shifts=[]; pivots=[]; tilts=[]
 for deg in angles:
  t=math.radians(deg)+phase
  y=-50.8*math.sin(t); z=50.8*math.cos(t)
  h=z+math.sqrt(165**2-y*y)
  shifts.append(h-(initial+165))
  pivots.append([0,y,z-initial])
  tilts.append(math.degrees(math.asin(y/165)))
 for name in ['piston_visual_','wrist_pin_visual_']:
  animation.append({'path':base+name+str(i),'action':'tz','times':times,'values':shifts})
 animation.append({'path':base+'rod_carrier_'+str(i),'action':'t','times':times,'values':pivots})
 animation.append({'path':base+'rod_carrier_'+str(i)+'/swing','action':'rx','times':times,'values':tilts})

# Side-valve timing demonstration, not a reconstructed Ford cam profile.
# Firing order 1-2-4-3; crank 0 = cylinder 1 firing TDC.
blocknode=result.objects['four_bore_L_head_block']
for i,bx in enumerate([290,420,550,680]):
 for vi,kind in enumerate(['intake','exhaust']):
  vx=bx-27 if vi==0 else bx+27
  vy=92
  passage=cyl(19,117,(vx,vy,640),(0,0,1))
  blocknode.obj=blocknode.obj.cut(passage)
  # Valve head/stem is one rigid object. Guide is fixed, valve translates Z.
  valve=cyl(4.5,88,(vx,vy,650),(0,0,1)).union(cyl(17,5,(vx,vy,738),(0,0,1)))
  guide=cyl(10,37,(vx,vy,660),(0,0,1)).cut(cyl(5,39,(vx,vy,659),(0,0,1)))
  result.add(valve,name=kind+'_valve_'+str(i),color=cq.Color(.32,.65,.85) if vi==0 else cq.Color(.8,.34,.2))
  result.add(guide,name=kind+'_guide_'+str(i),color=brass)
  vals=[]
  firing=[0,180,540,360][i]
  for deg in angles:
   phase=(deg-firing)%720
   start=360 if vi==0 else 180
   lift=8*math.sin(math.pi*(phase-start)/180)**2 if start<=phase<=start+180 else 0
   vals.append(lift)
  animation.append({'path':base+kind+'_valve_'+str(i),'action':'tz','times':times,'values':vals})
for part in ['four_bore_L_head_block','detachable_cylinder_head']:
 result.objects[part].obj=result.objects[part].obj.cut(box(550,90,200,(485,110,730)))


# Involute spur-gear study, module 2, pressure angle 20 deg, 0.12 mm tooth thinning.
def involute_gear(n,x,width,bore,phase=0):
 rp=n
 rb=rp*math.cos(math.radians(20))
 ra=rp+2
 rf=rp-2.5
 ip=math.tan(math.radians(20))-math.radians(20)
 half=math.pi/(2*n)-0.06/rp
 pts=[]
 for k in range(n):
  center=phase+2*math.pi*k/n
  rstart=max(rf,rb)
  def flank(r):
   q=math.sqrt(max(0,(r/rb)**2-1))
   return half+ip-(q-math.atan(q))
  aa=flank(rstart)
  pts.append((rf*math.cos(center-aa),rf*math.sin(center-aa)))
  for j in range(7):
   r=rstart+(ra-rstart)*j/6
   a=center-flank(r)
   pts.append((r*math.cos(a),r*math.sin(a)))
  for j in range(6,-1,-1):
   r=rstart+(ra-rstart)*j/6
   a=center+flank(r)
   pts.append((r*math.cos(a),r*math.sin(a)))
  pts.append((rf*math.cos(center+aa),rf*math.sin(center+aa)))
 return cq.Workplane('YZ',origin=(x,0,0)).polyline(pts).close().extrude(width).cut(cyl(bore,width+2,(x-1,0,0),(1,0,0)))

# Ford Service Course: triples 27/33/24, central gears 27/21/30.
# Pitch-circle layout only: m=2 mm is assumed; no manufactured tooth profiles.
carrier=cq.Assembly(name='transmission_input_carrier')
plate=cyl(98,10,(790,0,0),(1,0,0)).cut(cyl(24,12,(789,0,0),(1,0,0)))
carrier.add(plate,name='flywheel_carrier',color=steel)
for j in range(3):
 t=j*2*math.pi/3
 y=54*math.cos(t);z=54*math.sin(t)
 pin=cyl(5,88,(800,y,z),(1,0,0))
 carrier.add(pin,name='planet_pin_'+str(j),color=steel)
 triple=None
 for gx,n in [(810,27),(838,33),(866,24)]:
  disc=involute_gear(n,gx,15,5.5,math.pi+math.pi/n)
  triple=disc if triple is None else triple.union(disc)
 sleeve=cyl(9,71,(810,0,0),(1,0,0)).cut(cyl(5.5,73,(809,0,0),(1,0,0)))
 triple=triple.union(sleeve)
 marker=box(8,8,8,(818,18,0))
 triple=triple.union(marker)
 carrier.add(triple,name='triple_'+str(j),color=cq.Color(.88,.55,.16),loc=cq.Location(cq.Vector(0,y,z)))
result.add(carrier,name='transmission_input_carrier',loc=cq.Location(cq.Vector(0,0,480)))
animation.append({'path':base+'transmission_input_carrier','action':'rx','times':times,'values':angles})
for j in range(3):
 animation.append({'path':base+'transmission_input_carrier/triple_'+str(j),'action':'rx','times':times,'values':[a*7/11 for a in angles]})
for gx,n,label,speed,color in [(810,27,'output_27',4/11,cq.Color(.3,.6,.9)),(838,21,'low_21',0,cq.Color(.8,.2,.2)),(866,30,'reverse_30',27/55,cq.Color(.5,.3,.7))]:
 disc=involute_gear(n,gx,15,12)
 result.add(disc,name=label,color=color,loc=cq.Location(cq.Vector(0,0,480)))
 animation.append({'path':base+label,'action':'rx','times':times,'values':[a*speed for a in angles]})
# Viewing window only, not a production opening.
for name in ['hollow_flywheel_housing','hollow_transmission_housing']:
 result.objects[name].obj=result.objects[name].obj.cut(box(360,360,220,(940,0,590)))

# Straight-line kinematic demonstration only; final drive ratio 40/11.
previous=result
result=cq.Assembly(name='Model_T_running_study')
shaft_start=cq.Vector(1160,0,480)
shaft_end=cq.Vector(2410,0,381)
shaft_axis=(shaft_end-shaft_start).normalized()
shaft_angle=math.degrees(math.atan2(99,1250))
for node in previous.children:
 name=node.name
 if name=='propeller_shaft':
  local=cyl(16,(shaft_end-shaft_start).Length,(0,0,0),(1,0,0))
  group=cq.Assembly(name='driveshaft_axis')
  group.add(local,name='spin',color=steel)
  result.add(group,name='driveshaft_axis',loc=cq.Location(shaft_start,cq.Vector(0,1,0),shaft_angle))
 elif name.startswith('wood_wheel_2540_') or name.startswith('tire_2540_'):
  side=int(name.split('_')[-1]); center=cq.Vector(2540,side*711.2,381)
  result.add(node.obj.translate((-center.x,-center.y,-center.z)),name=name,color=node.color,loc=cq.Location(center))
 elif name.startswith('rear_brake_drum_'):
  side=int(name.split('_')[-1]); center=cq.Vector(2540,side*616.2,381)
  result.add(node.obj.translate((-center.x,-center.y,-center.z)),name=name,color=node.color,loc=cq.Location(center))
 else:
  if node.obj is None:result.add(node,name=name,loc=node.loc)
  else:result.add(node.obj,name=name,color=node.color,loc=node.loc)
animation.append({'path':base+'driveshaft_axis/spin','action':'rx','times':times,'values':[a*4/11 for a in angles]})
# At low gear: (4/11)/(40/11)=1/10 engine speed. Chassis stays fixed on virtual stands.
for side in [-1,1]:
 for prefix in ['wood_wheel_2540_','tire_2540_','rear_brake_drum_']:
  animation.append({'path':base+prefix+str(side),'action':'ry','times':times,'values':[-a/10 for a in angles]})

# Mode: reverse; kinematic demonstration, no physical shift clutch.
mode = 'reverse'
planet_relative = 1.25
output_ratio = -0.25
low_ratio = -0.9642857142857143
reverse_ratio = 0.0

for track in animation:
 path=track['path']
 ratio=None
 if '/transmission_input_carrier/triple_' in path:ratio=planet_relative
 elif path.endswith('/output_27') or path.endswith('/driveshaft_axis/spin'):ratio=output_ratio
 elif path.endswith('/low_21'):ratio=low_ratio
 elif path.endswith('/reverse_30'):ratio=reverse_ratio
 elif '/wood_wheel_2540_' in path or '/tire_2540_' in path or '/rear_brake_drum_' in path:ratio=-output_ratio*11/40
 if ratio is not None:track['values']=[a*ratio for a in angles]

# Drum/band packaging study. Independent diagram bodies; nested sleeves not yet modelled.
for x,label,ratio,color in [(900,'reverse',reverse_ratio,cq.Color(.5,.3,.7)),(950,'low',low_ratio,cq.Color(.8,.2,.2)),(1000,'brake_output',output_ratio,cq.Color(.3,.6,.9))]:
 drum=cyl(88,30,(x,0,0),(1,0,0)).cut(cyl(80,32,(x-1,0,0),(1,0,0)))
 result.add(drum,name=label+'_drum_layout',color=color,loc=cq.Location(cq.Vector(0,0,480)))
 animation.append({'path':base+label+'_drum_layout','action':'rx','times':times,'values':[a*ratio for a in angles]})
 band=cyl(95,22,(x+4,0,480),(1,0,0)).cut(cyl(89,24,(x+3,0,480),(1,0,0)))
 # Open top for an illustrative split band. 1mm released gap; no friction simulation.
 band=band.cut(box(30,50,80,(x+15,0,590)))
 result.add(band,name=label+'_band_layout',color=cq.Color(.56,.42,.25))


# Concentric sleeves: all dimensions are packaging assumptions, in local X-axis coordinates.
connections=[('output_27','brake_output',810,1030,12.2,8.0,1026),('low_21','low',838,980,16.2,12.7,976),('reverse_30','reverse',866,930,20.2,16.7,926)]
for gear,label,x0,x1,ro,ri,webx in connections:
 node=result.objects[gear]
 body=node.obj.cut(cyl(ri,17,(x0-1,0,0),(1,0,0)))
 sleeve=cyl(ro,x1-x0,(x0,0,0),(1,0,0)).cut(cyl(ri,x1-x0+2,(x0-1,0,0),(1,0,0)))
 web=cyl(88,4,(webx,0,0),(1,0,0)).cut(cyl(ri,6,(webx-1,0,0),(1,0,0)))
 drum=result.objects[label+'_drum_layout'].obj
 node.obj=body.union(sleeve).union(web).union(drum)
# Keep each gear, sleeve and drum in a single rigid body, removing duplicate drum tracks.
old_assembly=result
result=cq.Assembly(name='Model_T_running_study')
for node in old_assembly.children:
 if node.name.endswith('_drum_layout'):continue
 if node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
animation=[t for t in animation if not t['path'].endswith('_drum_layout')]

# 12 inner / 13 outer clutch plates, inspired by Ford Service Course.
# Simplified released stack. Teeth, pressure mechanism and friction not modelled.
inner=None
outer=None
for k in range(25):
 x=1000.5+k*0.96
 if k%2==0:
  plate=cyl(79,0.6,(x,0,0),(1,0,0)).cut(cyl(29,0.8,(x-0.1,0,0),(1,0,0)))
  outer=plate if outer is None else outer.union(plate)
 else:
  plate=cyl(75,0.6,(x,0,0),(1,0,0)).cut(cyl(24,0.8,(x-0.1,0,0),(1,0,0)))
  inner=plate if inner is None else inner.union(plate)
result.add(inner,name='clutch_12_input_plates_RELEASED',color=cq.Color(.68,.69,.7),loc=cq.Location(cq.Vector(0,0,480)))
result.add(outer,name='clutch_13_output_plates_RELEASED',color=cq.Color(.38,.4,.43),loc=cq.Location(cq.Vector(0,0,480)))
animation.append({'path':base+'clutch_12_input_plates_RELEASED','action':'rx','times':times,'values':angles})
animation.append({'path':base+'clutch_13_output_plates_RELEASED','action':'rx','times':times,'values':[a*output_ratio for a in angles]})

# Unified final mode: animation constraints; released plates remain a layout study.
mode='reverse'
planet_relative,output_ratio,low_ratio,reverse_ratio=(1.25, -0.25, -0.9642857142857143, 0)
for track in animation:
 path=track['path']
 ratio=None
 if '/transmission_input_carrier/triple_' in path:ratio=planet_relative
 elif path.endswith('/output_27') or path.endswith('/driveshaft_axis/spin') or path.endswith('/clutch_13_output_plates_RELEASED'):ratio=output_ratio
 elif path.endswith('/low_21'):ratio=low_ratio
 elif path.endswith('/reverse_30'):ratio=reverse_ratio
 elif '/wood_wheel_2540_' in path or '/tire_2540_' in path or '/rear_brake_drum_' in path:ratio=-output_ratio*11/40
 if ratio is not None:track['values']=[a*ratio for a in angles]

chassis=result
saved_drive_animation=animation
import cadquery as cq
import math
steps=['Clutch discs','Push ring and drive plate','Fingers collar and spring']
result=cq.Assembly(name='Model_T_clutch_actuation_layout')
def ring(ro,ri,x,length):
 return cq.Workplane('YZ').circle(ro).circle(ri).extrude(length).translate((x,0,0))
def box(l,w,h,x,y,z):
 return cq.Workplane('XY').box(l,w,h).translate((x,y,z))
def add(shape,name,color):
 result.add(shape,name=name,color=cq.Color(*color))
cad_step('Clutch discs')
for k in range(25):
 ro,ri=(79,29) if k%2==0 else (75,24)
 add(ring(ro,ri,8.42+k*.62,.6),'plate_'+str(k),(.4,.46,.53) if k%2==0 else (.75,.76,.78))
cad_step('Push ring and drive plate')
push=ring(78,29,24,4)
plate=ring(88,21,30,4)
for j in range(3):
 a=j*120
 lug=box(11,8,8,33.5,60,0).rotate((0,0,0),(1,0,0),a)
 hole=box(6,9,9,32,60,0).rotate((0,0,0),(1,0,0),a)
 push=push.union(lug)
 plate=plate.cut(hole)
add(push,'push_ring_three_lugs',(.85,.56,.12))
# Fork supports are integral with the drive plate in this simplified model.
for j in range(3):
 for side in [-1,1]:
  ear=box(15,12,4,40.5,75,side*6.5)
  bore=cq.Workplane('XY').center(42,75).circle(2.3).extrude(24).translate((0,0,-12))
  ear=ear.cut(bore).rotate((0,0,0),(1,0,0),j*120)
  plate=plate.union(ear)
# One rigid support assembly; actual fastening details deferred.
plate=plate.union(ring(22,18,30,4)).union(ring(20.5,18,32,54))
plate=plate.union(ring(32,18,84,4)).union(ring(32,30,76,8))
add(plate,'drive_plate_three_windows',(.25,.55,.82))
cad_step('Fingers collar and spring')
# Simplified pivoted fingers; physical contact and thread profiles remain deferred.
for j in range(3):
 finger=box(4,56,7,42,51,0)
 boss=cq.Workplane('XY').center(42,75).circle(5).extrude(7).translate((0,0,-3.5))
 bore=cq.Workplane('XY').center(42,75).circle(2.3).extrude(12).translate((0,0,-6))
 screw_bore=cq.Workplane('YZ').center(60,0).circle(1.8).extrude(12).translate((36,0,0))
 finger=finger.union(boss).cut(bore).cut(screw_bore).rotate((0,0,0),(1,0,0),j*120)
 pin=cq.Workplane('XY').center(42,75).circle(2).extrude(18).translate((0,0,-9))
 add(pin.rotate((0,0,0),(1,0,0),j*120),'pivot_pin_'+str(j),(.65,.67,.7))
 screw=cq.Workplane('YZ').center(60,0).circle(1.5).extrude(5.3).translate((40.7,0,0)).union(cq.Workplane('XY').sphere(1.5).translate((40.7,60,0)))
 head=cq.Workplane('YZ').center(60,0).polygon(6,5.5).extrude(2).translate((46,0,0))
 add(screw.union(head).rotate((0,0,0),(1,0,0),j*120),'adjuster_unthreaded_'+str(j),(.7,.7,.72))
 add(finger,'finger_'+str(j),(.8,.32,.22))
add(ring(30,21,44.5,4),'shift_collar',(.3,.7,.55))
# Helix axis initially Z then rotated to X. Assumed dimensions, unloaded layout.
helix=cq.Wire.makeHelix(6,30,25)
spring=cq.Workplane('XZ').center(25,0).circle(2).sweep(cq.Workplane(obj=helix),isFrenet=True)
spring=spring.rotate((0,0,0),(0,1,0),90).translate((51,0,0))
add(spring,'coil_spring_assumed',(.65,.66,.68))


clutch=result
result=cq.Assembly(name='Model_T_integrated_clutch')
for node in chassis.children:
 if node.name.startswith('clutch_'):continue
 if node.name=='output_27':
  # Remove obsolete internal end web while retaining cylindrical drum wall.
  shape=involute_gear(27,810,15,8).union(ring(12.2,8,810,224)).union(ring(88,80,1000,31))
  support=clutch.objects['drive_plate_three_windows'].obj.translate((1000,0,0))
  result.add(shape.union(support).union(ring(22,8,1030,4)),name=node.name,color=node.color,loc=node.loc)
 elif node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
for node in clutch.children:
 if node.name=='drive_plate_three_windows':continue
 result.add(node.obj,name='clutch_'+node.name,color=node.color,loc=cq.Location(cq.Vector(1000,0,480)))
animation=[]

# Low gear kinematics. Clutch remains released, no friction/torque solver.
previous=result
result=cq.Assembly(name='Model_T_integrated_low')
for node in previous.children:
 if node.name.startswith('clutch_'):
  result.add(node.obj.translate((1000,0,0)),name=node.name,color=node.color,loc=cq.Location(cq.Vector(0,0,480)))
 elif node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
times=[i/60 for i in range(481)]
angles=[i*1.5 for i in range(481)]
animation=[]
for track in saved_drive_animation:
 path=track['path']
 if '/clutch_' in path:continue
 ratio=None
 if '/transmission_input_carrier/triple_' in path:ratio=7/11
 elif path.endswith('/output_27') or path.endswith('/driveshaft_axis/spin'):ratio=4/11
 elif path.endswith('/low_21'):ratio=0
 elif path.endswith('/reverse_30'):ratio=27/55
 elif '/wood_wheel_2540_' in path or '/tire_2540_' in path or '/rear_brake_drum_' in path:ratio=-1/10
 track['path']=path.replace('/Model_T_running_study/','/Model_T_integrated_low/')
 if ratio is not None:track['values']=[a*ratio for a in angles]
 animation.append(track)
for node in result.children:
 if not node.name.startswith('clutch_'):continue
 ratio=4/11
 if node.name.startswith('clutch_plate_'):
  if int(node.name.split('_')[-1])%2==1:ratio=1
 animation.append({'path':'/Model_T_integrated_low/'+node.name,'action':'rx','times':times,'values':[a*ratio for a in angles]})

chassis=result
import cadquery as cq
import math
steps=['Two independent axle shafts','Three arm spider','Three pinion placeholders']
result=cq.Assembly(name='Model_T_three_pinion_differential_layout')
def cyl(r,length,start,direction):
 return cq.Workplane(obj=cq.Solid.makeCylinder(r,length,cq.Vector(*start),cq.Vector(*direction)))
def ring(ro,ri,length,start,direction):
 return cyl(ro,length,start,direction).cut(cyl(ri,length,start,direction))
def add(s,name,color):result.add(s,name=name,color=cq.Color(*color))
cad_step('Two independent axle shafts')
left=cyl(10,699.5,(0,-700,0),(0,1,0)).union(cyl(43,8,(0,-38,0),(0,1,0)))
right=cyl(10,699.5,(0,.5,0),(0,1,0)).union(cyl(43,8,(0,30,0),(0,1,0)))
add(left,'left_axle_and_sidegear_placeholder',(.3,.55,.85))
add(right,'right_axle_and_sidegear_placeholder',(.85,.35,.25))
cad_step('Three arm spider')
spider=ring(20,12,12,(0,-6,0),(0,1,0))
for j in range(3):
 a=math.radians(j*120);v=(math.cos(a),0,math.sin(a))
 spider=spider.union(cyl(4,59,(v[0]*19,0,v[2]*19),v))
spider=spider.union(ring(78,72,12,(0,-6,0),(0,1,0)))
# Rim is a schematic case support and ring gear envelope, not tooth geometry.
spider=spider.union(ring(105,72,7,(0,-12,0),(0,1,0)))
add(spider,'spider_case_and_ringgear_envelope',(.55,.42,.7))
cad_step('Three pinion placeholders')
for j in range(3):
 a=math.radians(j*120);v=(math.cos(a),0,math.sin(a))
 pinion=ring(18,4.5,16,(v[0]*40,0,v[2]*40),v)
 add(pinion,'pinion_placeholder_'+str(j),(.92,.66,.22))
animation=[]

diff=result
result=cq.Assembly(name='Model_T_rear_diff_integrated_layout')
for node in chassis.children:
 if node.name=='rear_axle_and_differential_ENVELOPE':
  inside=cq.Workplane('XY').sphere(120).translate((2540,0,381))
  inside=inside.union(cyl(12,1402,(2540,-701,381),(0,1,0)))
  housing=node.obj.cut(inside)
  result.add(housing,name='rear_axle_hollow_housing',color=cq.Color(.25,.28,.3,.2),loc=node.loc)
 elif node.name.startswith('wood_wheel_2540_'):
  wheel=node.obj.cut(cyl(10.2,200,(0,-100,0),(0,1,0)))
  result.add(wheel,name=node.name,color=node.color,loc=node.loc)
 elif node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
for node in diff.children:
 result.add(node.obj,name='rear_diff_'+node.name,color=node.color,loc=cq.Location(cq.Vector(2540,0,381)))
animation=[]

previous=result
result=cq.Assembly(name='Model_T_rear_differential_motion')
carrier=cq.Assembly(name='rear_carrier')
node=previous.objects['rear_diff_spider_case_and_ringgear_envelope']
carrier.add(node.obj,name='spider_case',color=node.color)
for j in range(3):
 name='rear_diff_pinion_placeholder_'+str(j);node=previous.objects[name]
 local=node.obj.rotate((0,0,0),(0,1,0),j*120)
 carrier.add(local,name='pinion_'+str(j),color=node.color,loc=cq.Location(cq.Vector(),cq.Vector(0,1,0),-j*120))
result.add(carrier,name='rear_carrier',loc=cq.Location(cq.Vector(2540,0,381)))
for node in previous.children:
 if node.name=='rear_diff_spider_case_and_ringgear_envelope' or node.name.startswith('rear_diff_pinion_'):continue
 if node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
times=[i/30 for i in range(241)]
angles=[i*1.5 for i in range(241)]
base='/Model_T_rear_differential_motion/'
animation=[{'path':base+'rear_carrier','action':'ry','times':times,'values':angles}]
for name,ratio in [('rear_diff_left_axle_and_sidegear_placeholder',1.3),('rear_diff_right_axle_and_sidegear_placeholder',.7)]:
 animation.append({'path':base+name,'action':'ry','times':times,'values':[a*ratio for a in angles]})
for side,ratio in [(-1,1.3),(1,.7)]:
 for prefix in ['wood_wheel_2540_','tire_2540_','rear_brake_drum_']:
  animation.append({'path':base+prefix+str(side),'action':'ry','times':times,'values':[a*ratio for a in angles]})
for j in range(3):
 animation.append({'path':base+'rear_carrier/pinion_'+str(j),'action':'rx','times':times,'values':[a*.6 for a in angles]})

# Four roller-bearing envelopes; roller/race detail and fits are not specified.
housing=result.objects['rear_axle_hollow_housing']
for y in [-600,-150,150,600]:
 pocket=cyl(20,24,(2540,y-12,381),(0,1,0))
 housing.obj=housing.obj.cut(pocket)
 bearing=ring(20,10.2,24,(2540,y-12,381),(0,1,0))
 result.add(bearing,name='rear_roller_bearing_envelope_'+str(y),color=cq.Color(.65,.67,.7))

chassis=result
diff_tracks=animation
import cadquery as cq
import math
steps=['Races','Cage and rollers','Rolling constraints']
result=cq.Assembly(name='Ideal_roller_bearing_motion')
def ring(ro,ri,y,length):return cq.Workplane('XZ').circle(ro).circle(ri).extrude(length).translate((0,y,0))
# XZ extrusion points toward -Y; centered spans are used below.
cad_step('Races')
outer=ring(20,17.5,12,24)
inner=ring(12.5,10.2,12,24)
inner=inner.cut(cq.Workplane('XY').box(2,25,2).translate((10.3,0,0)))
result.add(outer,name='fixed_outer',color=cq.Color(.5,.55,.6,.22))
result.add(inner,name='inner',color=cq.Color(.7,.73,.76))
cad_step('Cage and rollers')
cage=ring(17.2,12.8,-9.5,1).union(ring(17.2,12.8,10.5,1))
for j in range(12):
 phi=math.radians(j*30+15)
 bar=cq.Workplane('XZ').center(15*math.cos(phi),15*math.sin(phi)).circle(.6).extrude(20).translate((0,10,0))
 cage=cage.union(bar)
carrier=cq.Assembly(name='carrier')
carrier.add(cage,name='cage',color=cq.Color(.72,.57,.3))
for j in range(12):
 phi=math.radians(j*30)
 roller=cq.Workplane('XZ').circle(2.5).extrude(18).translate((0,9,0))
 # Shallow end-face notch provides a rotation marker without changing rolling surface.
 roller=roller.cut(cq.Workplane('XY').box(1,.4,2).translate((0,8.9,0)))
 carrier.add(roller,name='roller_'+str(j),color=cq.Color(.78,.8,.82),loc=cq.Location(cq.Vector(15*math.cos(phi),0,15*math.sin(phi))))
result.add(carrier,name='carrier')
cad_step('Rolling constraints')
times=[i/30 for i in range(241)]
angles=[i*1.5 for i in range(241)]
base='/Ideal_roller_bearing_motion/'
animation=[{'path':base+'inner','action':'ry','times':times,'values':angles},{'path':base+'carrier','action':'ry','times':times,'values':[a*5/12 for a in angles]}]
for j in range(12):
 animation.append({'path':base+'carrier/roller_'+str(j),'action':'ry','times':times,'values':[-a*35/12 for a in angles]})

prototype=result
bearing_tracks=animation
result=cq.Assembly(name='Model_T_integrated_bearing_motion')
for node in chassis.children:
 if node.name.startswith('rear_roller_bearing_envelope_'):continue
 if node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
animation=[]
for track in diff_tracks:
 animation.append({'path':track['path'].replace('/Model_T_rear_differential_motion/','/Model_T_integrated_bearing_motion/'),'action':track['action'],'times':track['times'],'values':track['values']})
for y in [-600,-150,150,600]:
 name='bearing_'+str(y)
 result.add(prototype,name=name,loc=cq.Location(cq.Vector(2540,y,381)))
 speed=1.3 if y<0 else .7
 for track in bearing_tracks:
  path=track['path'].replace('/Ideal_roller_bearing_motion/','/Model_T_integrated_bearing_motion/'+name+'/')
  animation.append({'path':path,'action':track['action'],'times':track['times'],'values':[v*speed for v in track['values']]})

base_chassis=result
import cadquery as cq
import math
# Analytical spherical-involute azimuth; independently constructed planar
# sections produce conical flanks. Polygon approximation, not cut-tool simulation.
# Formula reference: https://github.com/chrisspen/gears (sphere_ev).
steps=['球面インボリュート小歯車','球面インボリュート大歯車','直交配置']
def gear(n,mate):
    m=4.;R=math.hypot(n*m/2,mate*m/2);d=math.atan2(n,mate)
    base=math.asin(math.sin(d)*math.cos(math.radians(20)))
    root=d-5/R;tip=d+(3.0 if n==40 else 4.0)/R
    def inv(t):
        return math.acos(max(-1,min(1,math.cos(t)/math.cos(base))))/math.sin(base)-math.acos(max(-1,min(1,math.tan(base)/math.tan(t))))
    half=math.pi/(2*n)-.015/(m*n/2)
    def width(t):return half+inv(d)-inv(max(base,t))
    start=max(root,base)
    flank=[start+(tip-start)*j/24 for j in range(25)]
    points=[]
    def add(t,phi):points.append((math.tan(t)*math.cos(phi),math.tan(t)*math.sin(phi)))
    for j in range(n):
        phi=j*2*math.pi/n
        if root<start:add(root,phi-width(start))
        for t in flank:add(t,phi-width(t))
        for k in range(1,7):add(tip,phi-width(tip)+2*width(tip)*k/6)
        for t in flank[-2::-1]:add(t,phi+width(t))
        if root<start:add(root,phi+width(start))
        end=phi+2*math.pi/n-width(start)
        for k in range(1,7):add(root,phi+width(start)+(end-phi-width(start))*k/7)
    # End planes cut the conical flank family; common radial working region remains.
    z1=(R-18)*math.cos(d);z2=R*math.cos(d)
    w1=cq.Workplane('XY',origin=(0,0,z1)).polyline([(x*z1,y*z1) for x,y in points]).close().val()
    w2=cq.Workplane('XY',origin=(0,0,z2)).polyline([(x*z2,y*z2) for x,y in points]).close().val()
    shape=cq.Solid.makeLoft([w1,w2],True)
    return cq.Workplane(obj=shape).cut(cq.Workplane('XY').circle(60 if n==40 else 8.2).extrude(R+30))
cad_step(steps[0]);pinion=gear(11,40)
cad_step(steps[1]);ring=gear(40,11).rotate((0,0,0),(0,1,0),90).rotate((0,0,0),(1,0,0),4.52)

cad_step('差動装置へ配置')
alpha=math.atan2(99,1380)
axis=(-math.cos(alpha),0,math.sin(alpha))
placement=cq.Location(cq.Plane(origin=(0,0,0),xDir=(0,1,0),normal=axis))
drive_pinion=pinion.val().located(placement)
drive_ring=ring.val().located(placement)
def cylinder(r,length,start,direction):
    return cq.Workplane(obj=cq.Solid.makeCylinder(r,length,cq.Vector(*start),cq.Vector(*direction)))
def annulus(ro,ri,length,start,direction):
    return cylinder(ro,length,start,direction).cut(cylinder(ri,length,start,direction))
spider=annulus(20,12,12,(0,-6,0),(0,1,0))
for j in range(3):
    a=math.radians(j*120);v=(math.cos(a),0,math.sin(a))
    spider=spider.union(cylinder(4,41,(v[0]*19,0,v[2]*19),v))
spider=spider.union(annulus(60,59,12,(0,-6,0),(0,1,0)))
for j in range(3):
    a=math.radians(30+j*120)
    spider=spider.union(cylinder(2,18,(58*math.cos(a),5,58*math.sin(a)),(0,1,0)))
    spider=spider.union(cylinder(3,3,(58*math.cos(a),20,58*math.sin(a)),(0,1,0)))
carrier=spider.union(cq.Workplane(obj=drive_ring))
rear=cq.Assembly(name='Rear_final_drive_layout')
rear.add(carrier,name='ring_gear_and_carrier',color=cq.Color(.45,.55,.75))
rear.add(drive_pinion,name='drive_pinion',color=cq.Color('gold'))
left=cylinder(10,699.5,(0,-700,0),(0,1,0)).union(cylinder(43,8,(0,-38,0),(0,1,0)))
right=cylinder(10,699.5,(0,.5,0),(0,1,0)).union(cylinder(43,8,(0,30,0),(0,1,0)))
rear.add(left,name='left_axle_sidegear_placeholder',color=cq.Color(.3,.7,.8))
rear.add(right,name='right_axle_sidegear_placeholder',color=cq.Color(.85,.35,.25))
for j in range(3):
    a=math.radians(j*120);v=(math.cos(a),0,math.sin(a))
    rear.add(annulus(18,4.5,16,(v[0]*40,0,v[2]*40),v),name='differential_pinion_placeholder_'+str(j),color=cq.Color(.9,.65,.3))
result=cq.Assembly(name='Model_T_rear_input_arrangement')
result.add(rear,name='rear',loc=cq.Location(cq.Vector(2540,0,381)))
animation=[]


rear_input=rear
result=cq.Assembly(name='Model_T_chassis_rear_input_static')
apex=cq.Vector(2540,0,381)
shaft_start=cq.Vector(1160,0,480)
direction=(shaft_start-apex).normalized()
def segment(start,end,r):
    v=end-start
    return cylinder(r,v.Length,start.toTuple(),v.normalized().toTuple())
for node in base_chassis.children:
    if node.name=='rear_carrier' or node.name.startswith('rear_diff_') or node.name in ['driveshaft_axis','torque_tube_hollow']:continue
    if node.name=='rear_axle_hollow_housing':
        opening=cylinder(22,70,(apex+direction*95).toTuple(),direction.toTuple())
        result.add(node.obj.cut(opening),name=node.name,color=node.color,loc=node.loc)
    elif node.obj is None:result.add(node,name=node.name,loc=node.loc)
    else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
result.add(rear_input,name='rear_input',loc=cq.Location(apex))
shaft=segment(shaft_start,apex+direction*100,16)
shaft=shaft.union(segment(apex+direction*101,apex+direction*62,8))
result.add(shaft,name='stepped_propeller_shaft',color=cq.Color(.5,.53,.57))
tube=segment(shaft_start,apex+direction*152,37).cut(segment(shaft_start,apex+direction*152,22))
result.add(tube,name='realigned_torque_tube',color=cq.Color(.09,.1,.11))
animation=[]

static_chassis=result
result=cq.Assembly(name='Model_T_rear_drive_animation')
for node in static_chassis.children:
    if node.name in ['rear_input','stepped_propeller_shaft']:continue
    if node.obj is None:result.add(node,name=node.name,loc=node.loc)
    else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
carrier_group=cq.Assembly(name='carrier')
for node in rear_input.children:
    if node.name=='ring_gear_and_carrier':carrier_group.add(node.obj,name='ring_and_case',color=node.color)
    elif node.name.startswith('differential_pinion_placeholder_'):
        j=int(node.name.split('_')[-1])
        local=node.obj.rotate((0,0,0),(0,1,0),j*120)
        carrier_group.add(local,name='pinion_'+str(j),color=node.color,loc=cq.Location(cq.Vector(),cq.Vector(0,1,0),-j*120))
    elif node.name in ['left_axle_sidegear_placeholder','right_axle_sidegear_placeholder']:
        result.add(node.obj,name=node.name,color=node.color,loc=cq.Location(apex))
result.add(carrier_group,name='carrier',loc=cq.Location(apex))
input_group=cq.Assembly(name='input')
input_group.add(pinion,name='pinion',color=cq.Color('gold'))
local_shaft=cylinder(16,(shaft_start-apex).Length-100,(0,0,100),(0,0,1))
local_shaft=local_shaft.union(cylinder(8,39,(0,0,62),(0,0,1)))
input_group.add(local_shaft,name='shaft',color=cq.Color(.5,.53,.57))
input_loc=cq.Location(cq.Plane(origin=apex.toTuple(),xDir=(0,1,0),normal=axis))
result.add(input_group,name='input',loc=input_loc)
times=[i/30 for i in range(361)]
engine_angles=[4*i for i in range(361)]
input_angles=[-a*4/11 for a in engine_angles]
case_angles=[-11*a/40 for a in input_angles]
root='/Model_T_rear_drive_animation/'
animation=[]
def track(path,action,values):animation.append({'path':root+path,'action':action,'times':times,'values':values})
track('input','rz',input_angles)
track('carrier','ry',case_angles)
for j in range(3):track('carrier/pinion_'+str(j),'rx',[a*.6 for a in case_angles])
for name,speed in [('left_axle_sidegear_placeholder',1.3),('right_axle_sidegear_placeholder',.7)]:track(name,'ry',[a*speed for a in case_angles])
for side,speed in [(-1,1.3),(1,.7)]:
    for prefix in ['wood_wheel_2540_','tire_2540_','rear_brake_drum_']:track(prefix+str(side),'ry',[a*speed for a in case_angles])
for y in [-600,-150,150,600]:
    speed=1.3 if y<0 else .7
    prefix='bearing_'+str(y)+'/'
    track(prefix+'inner','ry',[a*speed for a in case_angles])
    track(prefix+'carrier','ry',[a*speed*5/12 for a in case_angles])
    for j in range(12):track(prefix+'carrier/roller_'+str(j),'ry',[-a*speed*35/12 for a in case_angles])


# Engine and low-gear motion; ideal kinematics, no combustion/friction solver.
track('four_throw_crankshaft_study','rx',engine_angles)
for i in range(4):
    phase=0 if i in [0,3] else math.pi
    initial=50.8*math.cos(phase)
    shifts=[]; pivots=[]; tilts=[]
    for deg in engine_angles:
        t=math.radians(deg)+phase
        y=-50.8*math.sin(t); z=50.8*math.cos(t)
        h=z+math.sqrt(165**2-y*y)
        shifts.append(h-(initial+165))
        pivots.append([0,y,z-initial])
        tilts.append(math.degrees(math.asin(y/165)))
    for name in ['piston_visual_','wrist_pin_visual_']:track(name+str(i),'tz',shifts)
    track('rod_carrier_'+str(i),'t',pivots)
    track('rod_carrier_'+str(i)+'/swing','rx',tilts)
    for kind,start in [('intake',360),('exhaust',180)]:
        vals=[]
        for deg in engine_angles:
            phase=(deg-[0,180,540,360][i])%720
            vals.append(8*math.sin(math.pi*(phase-start)/180)**2 if start<=phase<=start+180 else 0)
        track(kind+'_valve_'+str(i),'tz',vals)
track('transmission_input_carrier','rx',engine_angles)
for j in range(3):track('transmission_input_carrier/triple_'+str(j),'rx',[a*7/11 for a in engine_angles])
for name,ratio in [('output_27',4/11),('low_21',0),('reverse_30',27/55)]:track(name,'rx',[a*ratio for a in engine_angles])
clutch_names=['clutch_adjuster_unthreaded_0', 'clutch_adjuster_unthreaded_1', 'clutch_adjuster_unthreaded_2', 'clutch_coil_spring_assumed', 'clutch_finger_0', 'clutch_finger_1', 'clutch_finger_2', 'clutch_pivot_pin_0', 'clutch_pivot_pin_1', 'clutch_pivot_pin_2', 'clutch_plate_0', 'clutch_plate_1', 'clutch_plate_10', 'clutch_plate_11', 'clutch_plate_12', 'clutch_plate_13', 'clutch_plate_14', 'clutch_plate_15', 'clutch_plate_16', 'clutch_plate_17', 'clutch_plate_18', 'clutch_plate_19', 'clutch_plate_2', 'clutch_plate_20', 'clutch_plate_21', 'clutch_plate_22', 'clutch_plate_23', 'clutch_plate_24', 'clutch_plate_3', 'clutch_plate_4', 'clutch_plate_5', 'clutch_plate_6', 'clutch_plate_7', 'clutch_plate_8', 'clutch_plate_9', 'clutch_push_ring_three_lugs', 'clutch_shift_collar']
for name in clutch_names:
    ratio=1 if name.startswith('clutch_plate_') and int(name.split('_')[-1])%2 else 4/11
    track(name,'rx',[a*ratio for a in engine_angles])


# Steering linkage: assumed packaging, spherical joints, ideal 4:1 reducer.
def box(x,y,z,p):return cq.Workplane("XY").box(x,y,z).translate(p)
old_result=result
old_animation=animation
result=cq.Assembly(name='Model_T_1925_front_reconstruction')
removed=['steering_column_ENVELOPE','steering_wheel_rim','steering_wheel_hub_spokes','steering_tie_rod','steering_arm_layout_-630','steering_arm_layout_630','front_stub_-1','front_stub_1','front_beam_axle']
for side in [-1,1]:
 removed+=['wood_wheel_0_'+str(side),'tire_0_'+str(side)]
for node in old_result.children:
 if node.name in removed:continue
 if node.obj is None:result.add(node,name=node.name,loc=node.loc)
 else:result.add(node.obj,name=node.name,color=node.color,loc=node.loc)
M=(1030,-430,570); W=(1440,-310,1050)
def add(a,b):return tuple(x+y for x,y in zip(a,b))
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def norm(v):return math.sqrt(dot(v,v))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
N=tuple(x/norm(sub(W,M)) for x in sub(W,M)); V=(0,-150,37.5)
K1=(0,-630,381);K2=(0,630,381);D=(-60,140,100);A=(140,140*630/2540,54); B=(140,-140*630/2540,54)
def rot(v,n,t):
 c=math.cos(t);s=math.sin(t);k=cross(n,v);d=dot(n,v)
 return tuple(v[i]*c+k[i]*s+n[i]*d*(1-c) for i in range(3))
def rz(v,t):return rot(v,(0,0,1),t)
P0=add(M,V);Q0=add(K1,D);L=norm(sub(P0,Q0));TL=norm(sub(add(K2,B),add(K1,A)))
def solve(fn,x):
 for _ in range(30):
  f=fn(x);h=1e-6;df=(fn(x+h)-fn(x-h))/(2*h)
  if abs(f)<1e-9:return x
  x-=f/df
 raise ValueError('No closure')
rows=[];d1=d2=0
for i in range(721):
 t=i/60;phi=math.radians(18)*math.sin(2*math.pi*t/12)
 P=add(M,rot(V,N,phi))
 d1=solve(lambda a:norm(sub(P,add(K1,rz(D,a))))-L,d1)
 Q=add(K1,rz(D,d1));U=add(K1,rz(A,d1))
 d2=solve(lambda a:norm(sub(add(K2,rz(B,a)),U))-TL,d2)
 T=add(K2,rz(B,d2))
 rows.append(dict(t=t,phi=phi,left=d1,right=d2,P=P,Q=Q,U=U,T=T,drag_error=abs(norm(sub(P,Q))-L),tie_error=abs(norm(sub(U,T))-TL)))

steering_data=dict(rows=rows,M=M,W=W,N=N,V=V,K1=K1,K2=K2,D=D,A=A,B=B,L=L,TL=TL)

M=tuple(steering_data['M']); W=tuple(steering_data['W']);N=tuple(steering_data['N'])
V=tuple(steering_data['V']);K1=tuple(steering_data['K1']);K2=tuple(steering_data['K2'])
D=tuple(steering_data['D']); A=tuple(steering_data['A']); B=tuple(steering_data['B'])
def plus(a,b):return tuple(a[i]+b[i] for i in range(3))
def minus(a,b):return tuple(a[i]-b[i] for i in range(3))
def dot3(a,b):return sum(a[i]*b[i] for i in range(3))
def cross3(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def unit3(a):
 l=math.sqrt(dot3(a,a));return tuple(x/l for x in a)
def ball(r,p):return cq.Workplane('XY').sphere(r).translate(p)
E1=unit3(cross3((0,1,0),N));E2=cross3(N,E1)
column_loc=cq.Location(cq.Plane(origin=M,xDir=E1,normal=N))
clen=cq.Vector(*minus(W,M)).Length

# 1925-style forked axle, central spindle body, hub and opposed tapered bearings.
# Component architecture is documented; dimensions remain reconstruction assumptions.
beam=box(40,1100,10,(0,0,340)).union(box(40,1100,10,(0,0,390))).union(box(10,1100,50,(0,0,365)))
camber_deg=2.8
for side,K in [(-1,K1),(1,K2)]:
 for zz in [-48,48]:
  beam=beam.union(cyl(23,16,(0,K[1],K[2]+zz-8),(0,0,1)))
  beam=beam.union(rod((0,side*575,K[2]+zz),(0,K[1],K[2]+zz),10))
 beam=beam.union(rod((0,side*575,K[2]-48),(0,side*575,K[2]+48),15)).union(box(30,55,60,(0,side*550,365)))
 beam=beam.cut(cyl(6.6,140,(0,K[1],K[2]-70),(0,0,1)))
 pin=cyl(6.35,128,(0,0,-68),(0,0,1)).union(cyl(11,8,(0,0,60),(0,0,1)))
 pin=pin.cut(cyl(1.6,25,(-12,0,-64),(1,0,0)))
 result.add(pin,name='kingpin_'+str(side),loc=cq.Location(cq.Vector(*K)),color=steel)
 knut=cq.Workplane('XY').polygon(6,22).extrude(8).translate((0,0,-66)).cut(cyl(6.6,10,(0,0,-67),(0,0,1)))
 knut=knut.cut(cyl(1.6,26,(-13,0,-64),(1,0,0)))
 result.add(cyl(1.3,28,(-14,0,-64),(1,0,0)),name='kingpin_cotter_'+str(side),loc=cq.Location(cq.Vector(*K)),color=steel)
 result.add(knut,name='kingpin_locknut_'+str(side),loc=cq.Location(cq.Vector(*K)),color=steel)
 result.add(cyl(8,10,(0,0,69),(0,0,1)).union(cyl(9,3,(0,0,77),(0,0,1))),name='kingpin_oiler_'+str(side),loc=cq.Location(cq.Vector(*K)),color=brass)
 for wz,wh in [(-58,2),(56,4)]:
  washer=cyl(11,wh,(0,0,wz),(0,0,1)).cut(cyl(6.6,wh+2,(0,0,wz-1),(0,0,1)))
  result.add(washer,name='kingpin_washer_'+str(side)+'_'+str(wz),loc=cq.Location(cq.Vector(*K)),color=steel)
 knuckle=cq.Assembly(name='front_knuckle_'+str(side))
 gamma=math.radians(camber_deg); out=(0,side*math.cos(gamma),-math.sin(gamma))
 shaft_origin=(0,0,81.2*math.tan(gamma))
 hubplane=cq.Plane(origin=shaft_origin,xDir=(1,0,0),normal=out)
 hloc=cq.Location(hubplane)
 def hubshape(shape):return shape.val().moved(hloc)
 def hr(ro,ri,z,h):return cyl(ro,h,(0,0,z),(0,0,1)).cut(cyl(ri,h+2,(0,0,z-1),(0,0,1)))
 spindle=cyl(22,70,(0,0,-35),(0,0,1)).cut(cyl(9.2,72,(0,0,-36),(0,0,1)))
 shaft=cyl(17,32,(0,0,0),(0,0,1)).union(cyl(15,28,(0,0,32),(0,0,1))).union(cyl(12,42,(0,0,60),(0,0,1))).union(cyl(10,38,(0,0,102),(0,0,1)))
 shaft=shaft.cut(cyl(1.6,25,(-12,0,137),(1,0,0)))
 spindle=spindle.union(cq.Workplane(obj=hubshape(shaft)))
 arm=A if side<0 else B
 armjoin=(arm[0]-16,arm[1],arm[2])
 spindle=spindle.union(rod((0,0,23),armjoin,7)).union(rod(armjoin,(arm[0]-8,arm[1],arm[2]),7))
 eye=hr(11,4.5,-6,12).translate(arm)
 spindle=spindle.union(eye)
 if side<0:
  dbase=(D[0],D[1],D[2]-20)
  spindle=spindle.union(rod((0,0,0),(-70,0,0),10)).union(rod((-70,0,0),dbase,10)).union(rod(dbase,D,4)).union(ball(10,D))
 spindle=spindle.cut(cyl(9.2,74,(0,0,-37),(0,0,1))).cut(cyl(4.5,40,(arm[0],arm[1],arm[2]-20),(0,0,1)))
 knuckle.add(spindle,name='spindle_and_arms',color=steel)
 for zz in [-34,16]:knuckle.add(hr(9,6.6,zz,18),name='spindle_bush_'+str(zz),color=brass)
 for zz in [-38,36]:knuckle.add(hr(20,6.6,zz,2),name='spindle_thrust_'+str(zz),color=brass)
 linkpin=cyl(4,38,(arm[0],arm[1],arm[2]-21),(0,0,1)).union(cyl(7,4,(arm[0],arm[1],arm[2]+17),(0,0,1)))
 knuckle.add(linkpin,name='tie_rod_pivot_pin',color=steel)
 knuckle.add(hr(4.4,4.1,-6,12).translate(arm),name='tie_rod_pivot_bush',color=brass)
 knuckle.add(hr(7,4.3,-21,4).translate(arm),name='tie_rod_pin_retainer',color=steel)
 rotating=cq.Assembly(name='front_hub_spin')
 # Open center of the timber wheel for the separate metal hub.
 for prefix in ['wood_wheel_0_','tire_0_']:
  node=old_result.objects[prefix+str(side)]
  shape=node.obj.translate(tuple(-v for v in K)).rotate((0,side*81.2,0),(1,side*81.2,0),-side*camber_deg)
  if prefix=='wood_wheel_0_':
   shape=shape.cut(cq.Workplane(obj=hubshape(cyl(64,155,(0,0,0),(0,0,1)))))
   shape=shape.cut(cq.Workplane(obj=hubshape(cyl(85.5,8.4,(0,0,69.8),(0,0,1)))))
  # Move world-oriented wheel into the hub-axis frame before assigning the hub loc.
  local=shape.val().moved(hloc.inverse)
  if prefix=='wood_wheel_0_':
   for j in range(6):
    aa=j*math.pi/3;local=local.cut(cyl(3.5,50,(74*math.cos(aa),74*math.sin(aa),52),(0,0,1)).val())
  rotating.add(local,name=prefix+str(side),color=node.color)
 hub=hr(63,32,27,105).union(hr(85,32,70,8)).union(hr(63,22,130,4)).union(hr(63,30,54,2)).union(hr(63,30,111,2))
 for j in range(6):
  aa=j*math.pi/3;xx=74*math.cos(aa);yy=74*math.sin(aa)
  hub=hub.cut(cyl(3.5,12,(xx,yy,68),(0,0,1)))
  bolt=cyl(3,40,(xx,yy,56),(0,0,1)).union(cyl(5,4,(xx,yy,54),(0,0,1)))
  rotating.add(bolt,name='hub_flange_bolt_'+str(j),color=steel)
 rotating.add(hub,name='metal_hub',color=black)
 # Two opposed taper-roller sets: illustrative dimensions, no catalog fit claim.
 for label,z,bore,sgn in [('inner',40,15.3,1),('outer',113,10.3,-1)]:
  w=14;rin0=19 if sgn>0 else 21;rin1=21 if sgn>0 else 19
  cone=cq.Workplane(obj=cq.Solid.makeCone(rin0,rin1,w,cq.Vector(0,0,z),cq.Vector(0,0,1))).cut(cyl(bore,w+2,(0,0,z-1),(0,0,1)))
  knuckle.add(hubshape(cone),name=label+'_bearing_cone',color=steel)
  cup=cyl(32,w,(0,0,z),(0,0,1)).cut(cq.Workplane(obj=cq.Solid.makeCone(rin0+7.3,rin1+7.3,w+2,cq.Vector(0,0,z-1),cq.Vector(0,0,1))))
  rotating.add(cup,name=label+'_bearing_cup',color=steel)
  cage=cq.Assembly(name=label+'_bearing_cage')
  cage.add(hr(29,18,z-2,1).union(hr(29,18,z+w+1,1)),name='cage',color=brass)
  for j in range(12):
   aa=j*math.pi/6;rr0=rin0+3.5;rr1=rin1+3.5
   p0=(rr0*math.cos(aa),rr0*math.sin(aa),z+1);p1=(rr1*math.cos(aa),rr1*math.sin(aa),z+w-1)
   rv=cq.Vector(*minus(p1,p0));roller=cq.Workplane(obj=cq.Solid.makeCone(3.2,3.4,rv.Length,cq.Vector(*p0),rv.normalized()))
   cage.add(roller,name='roller_'+str(j),color=steel)
  # Bearing rollers are displayed as an assembly; rolling contact is not solved.
  knuckle.add(cage,name=label+'_bearing_cage',loc=hloc)
 rotating.add(hr(35,18,28,3),name='felt_seal_carrier',color=black)
 cap=hr(24,22,132,15).union(cyl(24,2,(0,0,147),(0,0,1)))
 rotating.add(cap,name='hub_cap',color=brass)
 knuckle.add(rotating,name='front_hub_spin',loc=hloc)
 knuckle.add(hubshape(hr(18,15.3,32,8)),name='inner_bearing_abutment_spacer',color=steel)
 knuckle.add(hubshape(hr(18,10.3,127,1)),name='outer_bearing_abutment_spacer',color=steel)
 knuckle.add(hubshape(hr(18,10.3,128,3)),name='spindle_washer',color=steel)
 nut=cq.Workplane('XY').polygon(6,30).extrude(8).translate((0,0,132)).cut(cyl(10.3,10,(0,0,131),(0,0,1)))
 for j in range(3):nut=nut.cut(box(34,3,4,(0,0,139)).rotate((0,0,0),(0,0,1),j*60))
 knuckle.add(hubshape(nut),name='castellated_spindle_nut',color=steel)
 knuckle.add(hubshape(cyl(1.3,28,(-14,0,137),(1,0,0))),name='spindle_cotter_pin',color=steel)
 result.add(knuckle,name='front_knuckle_'+str(side),loc=cq.Location(cq.Vector(*K)))
result.add(beam,name='front_beam_axle',color=black)

# Fixed column tube surrounds the rotating shaft.
column_tube=cyl(18,clen-120,(0,0,18),(0,0,1)).cut(cyl(12,clen-118,(0,0,17),(0,0,1)))
result.add(column_tube,name='steering_column_tube',loc=column_loc,color=black)
output=cq.Assembly(name='steering_output')
# Keyed output shaft and removable ball arm. Nominal dimensions in mm.
shaft=cyl(10,clen-74,(0,0,-22),(0,0,1)).cut(box(5,6,16,(0,10,-1)))
shaft=shaft.cut(cyl(1.6,24,(-12,0,-17),(1,0,0)))
output.add(shaft,name='shaft',color=steel)
vlocal=(dot3(V,E1),dot3(V,E2),dot3(V,E2)*0+dot3(V,N))
lower=(vlocal[0]-20*E1[2],vlocal[1]-20*E2[2],vlocal[2]-20*N[2])
hub=cyl(19,16,(0,0,-8),(0,0,1)).cut(cyl(10.2,18,(0,0,-9),(0,0,1))).cut(box(5.2,6,18,(0,10,-1)))
# Varying circular sections approximate the forged arm; original section unmeasured.
a0=cq.Vector(0,0,0);a1=cq.Vector(*lower);av=a1-a0
arm=cq.Workplane(obj=cq.Solid.makeCone(13,7,av.Length,a0,av.normalized()))
arm=arm.union(ball(7,lower)).union(rod(lower,vlocal,4)).union(ball(10,vlocal))
pitman=hub.union(arm).cut(cyl(10.2,22,(0,0,-11),(0,0,1))).cut(box(5.2,6,18,(0,10,-1)))
output.add(pitman,name='pitman_arm',color=steel)
output.add(box(4.8,5.8,14,(0,10,-1)),name='pitman_shaft_key',color=steel)
output.add(cyl(16,2,(0,0,-10),(0,0,1)).cut(cyl(10.3,4,(0,0,-11),(0,0,1))),name='pitman_retaining_washer',color=steel)
nut=cq.Workplane('XY',origin=(0,0,-20)).polygon(6,30).extrude(9).cut(cyl(10.3,11,(0,0,-21),(0,0,1)))
for ang in [0,60,120]:nut=nut.cut(box(34,3.4,4,(0,0,-18)).rotate((0,0,0),(0,0,1),ang))
output.add(nut,name='pitman_castle_nut',color=steel)
output.add(cyl(1.3,31,(-15.5,0,-17),(1,0,0)),name='pitman_cotter_pin',color=steel)
gearz=clen-80
carrier=cyl(8,8,(0,0,gearz-16),(0,0,1))
for j in range(3):
 a=j*2*math.pi/3;x=27*math.cos(a);y=27*math.sin(a)
 carrier=carrier.union(rod((0,0,gearz-12),(x,y,gearz-12),3))
 carrier=carrier.union(cyl(3,24,(x,y,gearz-13),(0,0,1)))
 planet=cyl(13,10,(0,0,-5),(0,0,1)).cut(cyl(3.5,12,(0,0,-6),(0,0,1)))
 planet=planet.union(ball(2,(8,0,6)))
 output.add(planet,name='planet_pitch_disc_'+str(j),loc=cq.Location(cq.Vector(x,y,gearz)),color=cq.Color(.8,.45,.15))
output.add(carrier,name='planet_carrier',color=cq.Color(.2,.55,.8))
result.add(output,name='steering_output',loc=column_loc)
input_group=cq.Assembly(name='steering_input')
wheel=cq.Workplane(obj=cq.Solid.makeTorus(200,13)).translate((0,0,clen))
input_group.add(wheel,name='wheel_rim',color=wood)
spokes=cyl(23,24,(0,0,clen-12),(0,0,1))
for j in range(4):
 a=j*math.pi/2;spokes=spokes.union(rod((0,0,clen),(193*math.cos(a),193*math.sin(a),clen),8))
input_group.add(spokes,name='wheel_spokes',color=black)
input_group.add(cyl(8,80,(0,0,gearz),(0,0,1)).union(cyl(13,10,(0,0,gearz-5),(0,0,1))),name='sun_pitch_disc_and_input',color=brass)
result.add(input_group,name='steering_input',loc=column_loc)
ring=cyl(47,18,(0,0,gearz-9),(0,0,1)).cut(cyl(40.6,20,(0,0,gearz-10),(0,0,1)))
# Sectioned fixed ring makes the pitch-disc reducer visible; no tooth-contact claim.
ring=ring.union(cyl(47,4,(0,0,gearz-28),(0,0,1)).cut(cyl(12,6,(0,0,gearz-29),(0,0,1)))).union(cyl(47,20,(0,0,gearz-25),(0,0,1)).cut(cyl(44,22,(0,0,gearz-26),(0,0,1))))
ring=ring.cut(box(60,60,50,(30,30,gearz-5)))
result.add(ring,name='fixed_ring_pitch_envelope',loc=column_loc,color=cq.Color(.7,.55,.2))
# Bracket links the fixed column to the left frame rail.
mount_end=tuple(M[i]+40*N[i]+19*E2[i] for i in range(3))
bracket=rod((1055,-390,599),mount_end,6)
result.add(bracket,name='column_mount_layout',color=black)
def socket_link(start,end,r):
 vec=cq.Vector(*minus(end,start));u=vec.normalized();length=vec.Length
 group=cq.Assembly(name='drag_link')
 body=cyl(8,length-24,(u*12).toTuple(),u.toTuple())
 group.add(body,name='connecting_rod',color=steel)
 # Two-bolt split steel caps; bolt size and cap dimensions are assumptions.
 for j,point in enumerate([(0,0,0),vec.toTuple()]):
  shell=ball(r+4,point).cut(ball(r+.5,point))
  shell=shell.cut(cyl(8,22,(point[0],point[1],point[2]-21),(0,0,1)))
  upper=shell.intersect(box(80,80,30,(point[0],point[1],point[2]+15.15)))
  lowercap=shell.intersect(box(80,80,30,(point[0],point[1],point[2]-15.15)))
  for sign in [-1,1]:
   bx=point[0];by=point[1]+sign*17
   upper=upper.union(box(12,12,4,(bx,by,point[2]+2.15)))
   lowercap=lowercap.union(box(12,12,4,(bx,by,point[2]-2.15)))
   hole=cyl(2.7,16,(bx,by,point[2]-8),(0,0,1))
   upper=upper.cut(hole);lowercap=lowercap.cut(hole)
   bolt=cyl(2.5,15,(bx,by,point[2]-9),(0,0,1)).union(cq.Workplane('XY',origin=(bx,by,point[2]+4.2)).polygon(6,9).extrude(3))
   bn=cq.Workplane('XY',origin=(bx,by,point[2]-7.2)).polygon(6,9).extrude(3).cut(cyl(2.6,5,(bx,by,point[2]-8),(0,0,1)))
   group.add(bolt,name='end_'+str(j)+'_bolt_'+str(sign),color=steel)
   group.add(bn,name='end_'+str(j)+'_nut_'+str(sign),color=steel)
  group.add(upper,name='end_'+str(j)+'_socket_body',color=steel)
  group.add(lowercap,name='end_'+str(j)+'_removable_cap',color=cq.Color(.32,.35,.38))
 return group
P0=plus(M,V);Q0=plus(K1,D);U0=plus(K1,A);T0=plus(K2,B)
result.add(socket_link(P0,Q0,10),name='drag_link',loc=cq.Location(cq.Vector(*P0)))

length=TL
tie=rod((0,22,0),(0,length-22,0),7)
for yy,sign in [(0,1),(length,-1)]:
 for zz in [-11,11]:
  ear=hr(11,4.5,zz-2,4).translate((0,yy,0))
  tie=tie.union(ear).union(box(8,16,4,(0,yy+sign*14,zz))).union(rod((0,yy+sign*20,zz),(0,yy+sign*32,0),4))
result.add(tie,name='tie_rod',loc=cq.Location(cq.Vector(*U0)),color=cq.Color(.45,.47,.5))

# Retain engine and driveline animations; steering has its own constrained tracks.
root='/Model_T_1925_front_reconstruction/'
animation=[]
for t in old_animation:
 animation.append({'path':t['path'].replace('/Model_T_rear_drive_animation/',root),'action':t['action'],'times':t['times'],'values':t['values']})
rows=steering_data['rows'];stimes=[r['t'] for r in rows]
def steer_track(name,action,values):animation.append({'path':root+name,'action':action,'times':stimes,'values':values})
steer_track('steering_input','rz',[math.degrees(r['phi'])*4 for r in rows])
steer_track('steering_output','rz',[math.degrees(r['phi']) for r in rows])
for j in range(3):steer_track('steering_output/planet_pitch_disc_'+str(j),'rz',[-3*math.degrees(r['phi']) for r in rows])
steer_track('front_knuckle_-1','rz',[math.degrees(r['left']) for r in rows])
steer_track('front_knuckle_1','rz',[math.degrees(r['right']) for r in rows])
def q_between(a,b):
 u=unit3(a);v=unit3(b);xyz=cross3(u,v);q=list(xyz)+[1+dot3(u,v)];l=math.sqrt(sum(x*x for x in q));return [x/l for x in q]
for name,k1,k2,p0,p1 in [('drag_link','P','Q',P0,Q0),('tie_rod','U','T',U0,T0)]:
 steer_track(name,'t',[minus(r[k1],p0) for r in rows])
 steer_track(name,'q',[q_between(minus(p1,p0),minus(r[k2],r[k1])) for r in rows])



# Independent front-wheel rolling DOF is nested under steering.
for side in [-1,1]:
 steer_track('front_knuckle_'+str(side)+'/front_hub_spin','rz',[side*360*r['t']/12 for r in rows])
 for label in ['inner','outer']:
  steer_track('front_knuckle_'+str(side)+'/'+label+'_bearing_cage','rz',[side*205*r['t']/12 for r in rows])



# Open touring body: nominal envelope fitted to the existing 2540 mm wheelbase.
cad_step('Open touring body, seats and lowered hood')
body=cq.Assembly(name='touring_body')
paint=cq.Color(.12,.135,.15)
trim=cq.Color(.15,.12,.095)
leather=cq.Color(.12,.075,.045)
glass=cq.Color(.55,.75,.8,.25)
def ba(s,n,c=paint):body.add(s,name=n,color=c)
# Wooden floor, sills, and nominal chassis mounting pads.
ba(box(1660,1040,22,(1990,0,625)),'floorboards',wood)
for side in [-1,1]:
 ba(box(1690,45,65,(1980,side*515,641)),'body_sill_'+str(side),wood)
 for x in [1250,1750,2350,2730]:
  ba(box(70,175,25,(x,side*440,588)),'body_mount_'+str(x)+'_'+str(side))
# Rounded rear tub open at its top and front.
outer=box(830,1110,470,(2455,0,905)).edges('|Z').fillet(120)
inner=box(814,1094,480,(2455,0,919)).edges('|Z').fillet(112)
tub=outer.cut(inner).cut(box(280,1250,520,(2080,0,930)))
ba(tub,'rear_tub')
# Side skins with three passenger door panels; driver's front side remains fixed.
for side in [-1,1]:
 y=side*550
 panel=cq.Workplane('YZ',origin=(1160,0,0)).moveTo(side*510,670).spline([(side*545,740),(side*566,880),(side*550,1070)],includeCurrent=True).lineTo(side*542,1070).spline([(side*558,880),(side*537,740),(side*502,670)],includeCurrent=True).close().extrude(1120)
 original_panel=panel
 doors=[(2070,370)]
 if side>0:doors.append((1400,400))
 for x,w in doors:
  cut=box(w,180,352,(x,y,900)).edges('|Y').fillet(25)
  panel=panel.cut(cut)
  door=original_panel.intersect(box(w-6,180,344,(x,y,900)).edges('|Y').fillet(22))
  ba(door,'door_'+str(x)+'_'+str(side))
  for z in [800,990]:ba(cyl(5,28,(x-w/2+8,y+side*8,z),(0,0,1)),'hinge_'+str(x)+'_'+str(z)+'_'+str(side),steel)
  ba(rod((x+w/2-65,y+side*12,1010),(x+w/2-25,y+side*12,1010),4),'handle_'+str(x)+'_'+str(side),steel)
 ba(panel,'side_skin_'+str(side))
 ba(rod((1170,y,1074),(2280,y,1074),9),'upper_body_bead_'+str(side))
# Cowl shell and dashboard. Column passage follows its actual axis.
def top_wire(x,w,z):
 return cq.Workplane('YZ',origin=(x,0,0)).moveTo(-w,650).lineTo(-w,z-70).threePointArc((0,z),(w,z-70)).lineTo(w,650).close().val()
co=cq.Solid.makeLoft([top_wire(1020,370,1080),top_wire(1210,550,1130)])
ci=cq.Solid.makeLoft([top_wire(1018,362,1072),top_wire(1212,542,1122)])
cowl=cq.Workplane(obj=co.cut(ci)).cut(cyl(36,500,tuple(M),tuple(N)))
ba(cowl,'cowl')
dash=box(16,1070,400,(1215,0,880)).cut(cyl(36,500,tuple(M),tuple(N)))
ba(dash,'dashboard',wood)
# Crowned hood with separate side sheets and louver openings.
for side in [-1,1]:
 def hw(x,w,z):
  return cq.Workplane('YZ',origin=(x,0,0)).moveTo(0,z).threePointArc((side*w*.55,z-18),(side*w,z-70)).lineTo(side*w,z-73).threePointArc((side*w*.55,z-21),(0,z-3)).close().val()
 ba(cq.Workplane(obj=cq.Solid.makeLoft([hw(165,280,1022),hw(1020,370,1080)])),'hood_top_'+str(side))
 pts=[(165,side*280,625),(1020,side*370,625),(1020,side*370,1010),(165,side*280,952)]
 wire=cq.Wire.makePolygon([cq.Vector(*p) for p in pts]+[cq.Vector(*pts[0])])
 hs=cq.Workplane(obj=cq.Solid.extrudeLinear(wire,[],cq.Vector(0,side*3,0)))
 for x in range(430,920,32):
  yy=side*(280+(x-165)*90/855)
  hs=hs.cut(box(8,35,170,(x,yy,820)))
 ba(hs,'hood_side_louvered_'+str(side))
 for x in [260,950]:
  yy=side*(280+(x-165)*90/855)
  ba(rod((x,yy+side*6,640),(x,yy+side*6,688),5),'hood_latch_'+str(x)+'_'+str(side),steel)
ba(rod((165,0,1025),(1020,0,1083),4),'hood_center_hinge',steel)
# Two bench seats with separate cushions and piping ribs.
for label,x,z in [('front',1730,845),('rear',2530,850)]:
 ba(box(460,990,135,(x,0,z)).edges().fillet(28),label+'_seat_cushion',leather)
 ba(box(100,1000,340,(x+215,0,z+200)).edges().fillet(28),label+'_seat_back',leather)
 ba(box(430,940,150,(x,0,700)),label+'_seat_box',wood)
 for y in range(-420,421,105):ba(rod((x-155,y,z+69),(x+155,y,z+69),3),label+'_seat_seam_'+str(y),trim)
# Two-pane windscreen, upright frame with slightly raked top.
for side in [-1,1]:ba(rod((1190,side*550,1090),(1250,side*550,1580),12),'windshield_post_'+str(side))
for z in [1100,1335,1570]:
 x=1190+(z-1090)*60/490
 ba(rod((x,-550,z),(x,550,z),10),'windshield_bar_'+str(z))
for z in [1217,1452]:
 pane=box(4,1070,215,(0,0,0)).rotate((0,0,0),(0,1,0),7).translate((1190+(z-1090)*60/490,0,z))
 ba(pane,'windshield_glass_'+str(z),glass)
# Running boards and curved mudguards clear the nominal wheel envelopes.
for side in [-1,1]:
 ba(box(1390,250,22,(1280,side*665,435)),'running_board_'+str(side))
 for x in [0,2540]:
  f=cyl(440,250,(x,side*711-125,381),(0,1,0)).cut(cyl(432,252,(x,side*711-126,381),(0,1,0))).intersect(box(1000,300,470,(x,side*711,616)))
  ba(f,'fender_'+str(x)+'_'+str(side))
 # Sloping fender aprons meet running boards.
 for xx,flip in [(0,1),(2540,-1)]:
  pts=[(xx+flip*410,535),(xx+flip*585,446),(xx+flip*585,438),(xx+flip*410,527)]
  ba(cq.Workplane('XZ',origin=(0,side*711+125,0)).polyline(pts).close().extrude(250),'fender_apron_'+str(xx)+'_'+str(side))
 for k in range(6):ba(rod((615,side*(560+k*36),448),(1930,side*(560+k*36),448),2),'board_tread_'+str(k)+'_'+str(side),trim)
 for x in [450,2050]:ba(rod((x,side*520,650),(x,side*665,447),8),'board_brace_'+str(x)+'_'+str(side))
# Lowered fabric top and folded bows behind rear seat (static representation).
for i in range(4):
 x=2770+i*22;z=1190+i*14
 ba(rod((x,-560,1080),(x,-560,z),8),'folded_bow_left_'+str(i))
 ba(rod((x,-560,z),(x,560,z),8),'folded_bow_cross_'+str(i))
 ba(rod((x,560,z),(x,560,1080),8),'folded_bow_right_'+str(i))
for i in range(4):ba(box(150,1080,24,(2790+i*14,0,1180+i*23)).edges().fillet(10),'canvas_fold_'+str(i),trim)
# Headlamps, lenses and supporting crossbar.
ba(rod((130,-520,790),(130,520,790),10),'headlamp_bar')
for side in [-1,1]:
 ba(cyl(92,105,(75,side*430,858),(1,0,0)),'headlamp_bucket_'+str(side))
 ba(cyl(96,12,(64,side*430,858),(1,0,0)).cut(cyl(84,14,(63,side*430,858),(1,0,0))),'headlamp_rim_'+str(side),steel)
 ba(cyl(83,5,(65,side*430,858),(1,0,0)),'headlamp_lens_'+str(side),glass)
 ba(rod((130,side*430,790),(130,side*430,820),12),'headlamp_stalk_'+str(side))
# 1925 black radiator shell; underlying radiator core retained.
result.objects['radiator_shell'].color=paint

# Splash aprons between body sills and running boards. Nominal folded steel sheet.
cad_step('Splash aprons and folded mounting edges')
for side in [-1,1]:
 # YZ profile includes upper return and lower flange, 2 mm nominal sheet.
 profile=[(side*493,650),(side*517,650),(side*562,447),(side*588,447),(side*588,445),(side*560,445),(side*515,648),(side*493,648)]
 apron=cq.Workplane('YZ',origin=(570,0,0)).polyline(profile).close().extrude(1430)
 body.add(apron,name='splash_apron_'+str(side),color=paint)
result.add(body,name='touring_body')


