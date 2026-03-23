#!/usr/bin/env python3
"""Generate animated GIFs for 33 exercises using PIL stick figures."""

from PIL import Image, ImageDraw
import os, math

OUT = "/home/niemczyt/src/robopong-app/frontend/static/exercises"
os.makedirs(OUT, exist_ok=True)

W = H = 320
BG  = (248, 249, 255)
FG  = (30, 50, 150)
ACT = (210, 45, 45)
LW  = 7
HR  = 22

SEGS = [
    ('neck','hip'),
    ('l_shoulder','neck'),('r_shoulder','neck'),
    ('l_shoulder','l_elbow'),('l_elbow','l_wrist'),
    ('r_shoulder','r_elbow'),('r_elbow','r_wrist'),
    ('l_hip','r_hip'),
    ('hip','l_hip'),('hip','r_hip'),
    ('l_hip','l_knee'),('l_knee','l_ankle'),
    ('r_hip','r_knee'),('r_knee','r_ankle'),
]

def draw_fig(draw, p, active=()):
    def j(k): return tuple(int(v) for v in p[k])
    for a,b in SEGS:
        col = ACT if (a in active or b in active) else FG
        draw.line([j(a),j(b)], fill=col, width=LW)
    hx,hy = j('head')
    draw.ellipse([hx-HR,hy-HR,hx+HR,hy+HR], outline=FG, width=LW)

def lerp(a,b,t): return a+(b-a)*t
def lpose(pa,pb,t):
    return {k:(lerp(pa[k][0],pb[k][0],t),lerp(pa[k][1],pb[k][1],t)) for k in pa}

def gif(fn, poses, active=(), dur=130, pingpong=True):
    ps = poses + poses[-2:0:-1] if (pingpong and len(poses)>1) else poses
    imgs = []
    for pose in ps:
        img = Image.new('RGB',(W,H),BG)
        draw_fig(ImageDraw.Draw(img), pose, active)
        imgs.append(img)
    path = os.path.join(OUT, fn)
    imgs[0].save(path, save_all=True, append_images=imgs[1:], loop=0, duration=dur, optimize=True)
    print(f"  ✓ {fn}")

def interp(poses, n=3):
    out = []
    for i in range(len(poses)-1):
        for s in range(n):
            out.append(lpose(poses[i],poses[i+1],s/n))
    out.append(poses[-1])
    return out

# ── Base standing pose ────────────────────────────────────────────────
S = {
    'head':       (160, 46),
    'neck':       (160, 70),
    'l_shoulder': (131, 90),
    'r_shoulder': (189, 90),
    'l_elbow':    (115, 132),
    'r_elbow':    (205, 132),
    'l_wrist':    (110, 173),
    'r_wrist':    (210, 173),
    'hip':        (160, 178),
    'l_hip':      (144, 178),
    'r_hip':      (176, 178),
    'l_knee':     (141, 233),
    'r_knee':     (179, 233),
    'l_ankle':    (137, 287),
    'r_ankle':    (177, 287),
}

def p(**kw):
    pose = dict(S)
    pose.update(kw)
    return pose

def shift(pose, dx=0, dy=0):
    return {k:(v[0]+dx,v[1]+dy) for k,v in pose.items()}

# ── Helpers for common motions ────────────────────────────────────────

def arm_angle(shoulder, length_upper, length_lower, angle_upper, angle_lower):
    """Returns (elbow, wrist) given shoulder pos and angles (degrees from down)."""
    au = math.radians(angle_upper)
    al = math.radians(angle_lower)
    ex = shoulder[0] + length_upper*math.sin(au)
    ey = shoulder[1] + length_upper*math.cos(au)
    wx = ex + length_lower*math.sin(au+al)
    wy = ey + length_lower*math.cos(au+al)
    return (ex,ey),(wx,wy)

# ─── WARMUP ──────────────────────────────────────────────────────────
print("🔥 Warmup")

# 101 Jogging in Place
A = p(l_knee=(141,200), l_ankle=(141,244), r_knee=(179,240), r_ankle=(179,287),
      l_elbow=(105,118), l_wrist=(98,155), r_elbow=(215,148), r_wrist=(220,188))
B = p(r_knee=(179,196), r_ankle=(179,240), l_knee=(141,243), l_ankle=(137,287),
      r_elbow=(215,118), r_wrist=(218,153), l_elbow=(105,148), l_wrist=(100,188))
gif("101.gif", interp([A,B],4), active=('l_knee','l_ankle','r_knee','r_ankle'), dur=100)

# 102 Arm Circles – 6 positions of right arm rotating
def arm_pos(a):
    sx,sy = 189,90
    rad = math.radians(a)
    ex = sx + 45*math.sin(rad); ey = sy + 45*math.cos(rad)
    wx = ex + 38*math.sin(rad); wy = ey + 38*math.cos(rad)
    return (ex,ey),(wx,wy)

frames102 = []
for ang in range(0,360,60):
    el,wr = arm_pos(ang)
    el2,wr2 = arm_pos(ang+180)  # mirror left arm opposite
    frames102.append(p(r_elbow=el, r_wrist=wr, l_elbow=el2, l_wrist=wr2))
gif("102.gif", frames102, active=('r_elbow','r_wrist','l_elbow','l_wrist'), dur=110, pingpong=False)

# 103 Wrist Rotations – arms forward, wrists orbit
def wrist_orbit(cx,cy,r,a):
    rad=math.radians(a); return (cx+r*math.cos(rad), cy+r*math.sin(rad))

frames103=[]
for ang in range(0,360,60):
    lw = wrist_orbit(115,155,18,ang)
    rw = wrist_orbit(205,155,18,ang+180)
    frames103.append(p(l_elbow=(115,132),l_wrist=lw, r_elbow=(205,132),r_wrist=rw))
gif("103.gif", frames103, active=('l_wrist','r_wrist'), dur=110, pingpong=False)

# 104 Trunk Rotations – upper body swings L/R
left_turn  = p(head=(140,46),neck=(140,70),l_shoulder=(112,90),r_shoulder=(170,90),
               l_elbow=(88,115),l_wrist=(72,140),r_elbow=(180,128),r_wrist=(188,168))
right_turn = p(head=(180,46),neck=(180,70),l_shoulder=(150,90),r_shoulder=(208,90),
               l_elbow=(140,128),l_wrist=(132,168),r_elbow=(232,115),r_wrist=(248,140))
gif("104.gif", interp([left_turn,S,right_turn,S],3), active=('neck','l_shoulder','r_shoulder'), dur=130)

# 105 Hip Circles – hips orbit, upper body still
frames105=[]
for ang in range(0,360,60):
    rad=math.radians(ang)
    dx,dy = 18*math.sin(rad), 10*math.cos(rad)
    frames105.append(p(hip=(160+dx,178+dy), l_hip=(144+dx,178+dy), r_hip=(176+dx,178+dy),
                       l_knee=(141+dx//2,233), r_knee=(179+dx//2,233)))
gif("105.gif", frames105, active=('hip','l_hip','r_hip'), dur=110, pingpong=False)

# 106 High Knees
A6 = p(l_knee=(145,155),l_ankle=(152,190), r_knee=(179,240),r_ankle=(177,287),
       l_elbow=(205,115),l_wrist=(212,150), r_elbow=(105,140),r_wrist=(98,178))
B6 = p(r_knee=(175,155),r_ankle=(168,190), l_knee=(141,240),l_ankle=(137,287),
       r_elbow=(105,115),r_wrist=(98,150), l_elbow=(210,140),l_wrist=(216,178))
gif("106.gif", interp([A6,B6],4), active=('l_knee','l_ankle','r_knee','r_ankle'), dur=90)

# 107 Dynamic Lunges
lunge_L = p(head=(148,52),neck=(148,76),
            l_shoulder=(120,96),r_shoulder=(176,96),
            l_elbow=(108,138),r_elbow=(188,138),l_wrist=(104,179),r_wrist=(192,179),
            hip=(148,185),l_hip=(130,185),r_hip=(164,185),
            l_knee=(108,248),l_ankle=(90,290),
            r_knee=(175,233),r_ankle=(172,287))
lunge_R = p(head=(172,52),neck=(172,76),
            l_shoulder=(144,96),r_shoulder=(200,96),
            l_elbow=(132,138),r_elbow=(212,138),l_wrist=(128,179),r_wrist=(216,179),
            hip=(172,185),l_hip=(156,185),r_hip=(190,185),
            r_knee=(212,248),r_ankle=(228,290),
            l_knee=(145,233),l_ankle=(140,287))
gif("107.gif", interp([S,lunge_L,S,lunge_R,S],3), active=('l_knee','l_ankle','r_knee','r_ankle'), dur=140)

# 108 Shadow Play (ping pong stroke)
fh_wind = p(r_shoulder=(200,90),r_elbow=(228,128),r_wrist=(240,168),
            head=(155,46),hip=(155,178),l_hip=(140,178),r_hip=(170,178),
            l_knee=(135,233),r_knee=(172,233),l_ankle=(128,287),r_ankle=(168,287))
fh_hit  = p(r_shoulder=(189,90),r_elbow=(215,112),r_wrist=(230,82),
            head=(163,46),
            l_knee=(135,240),r_knee=(178,228))
fh_fol  = p(r_shoulder=(185,90),r_elbow=(200,72),r_wrist=(182,52),
            head=(165,46))
gif("108.gif", interp([fh_wind,fh_hit,fh_fol],3), active=('r_shoulder','r_elbow','r_wrist'), dur=120)

# ─── FOOTWORK ────────────────────────────────────────────────────────
print("👟 Footwork")

# 201 Side Shuffle – figure wide stance shuffling
wide_L = p(l_ankle=(80,287),l_knee=(96,233),l_hip=(112,178),
           r_ankle=(192,287),r_knee=(192,233),r_hip=(192,178),
           hip=(152,170),head=(152,42),neck=(152,66))
wide_R = p(l_ankle=(128,287),l_knee=(128,233),l_hip=(128,178),
           r_ankle=(240,287),r_knee=(224,233),r_hip=(208,178),
           hip=(168,170),head=(168,42),neck=(168,66))
mid_s  = p(l_ankle=(120,287),l_knee=(128,240),r_ankle=(200,287),r_knee=(192,240),
           hip=(160,175),head=(160,42),neck=(160,66))
gif("201.gif", interp([wide_L,mid_s,wide_R,mid_s],3), active=('l_ankle','r_ankle','l_knee','r_knee'), dur=110)

# 202 Crossover Step
cross = p(l_ankle=(175,287),l_knee=(168,233),l_hip=(162,178),
          r_ankle=(220,287),r_knee=(205,233),r_hip=(185,178),
          hip=(170,178),head=(170,46),neck=(170,70))
gif("202.gif", interp([S,cross,S],3), active=('l_ankle','l_knee','l_hip'), dur=130)

# 203 Falkenberg – 3 positions
pos_BH = p(l_ankle=(90,287),l_knee=(100,233),l_hip=(115,178),
           r_ankle=(155,287),r_knee=(155,233),r_hip=(155,178),
           hip=(130,178),head=(130,46),neck=(130,70),
           r_elbow=(170,110),r_wrist=(180,82))  # BH stroke
pos_C  = S
pos_FH = p(l_ankle=(165,287),l_knee=(165,233),l_hip=(165,178),
           r_ankle=(230,287),r_knee=(220,233),r_hip=(205,178),
           hip=(190,178),head=(190,46),neck=(190,70),
           r_elbow=(220,110),r_wrist=(235,80))  # FH stroke
gif("203.gif", interp([pos_BH,pos_C,pos_FH,pos_C],3), active=('r_elbow','r_wrist'), dur=150)

# 204 In-Out Movement
step_in  = p(head=(160,52),neck=(160,78), l_ankle=(128,275),r_ankle=(192,275),
             l_knee=(136,230),r_knee=(184,230), hip=(160,182),l_hip=(145,182),r_hip=(175,182))
step_out = p(head=(160,40),neck=(160,64), l_ankle=(130,287),r_ankle=(190,287),
             l_knee=(138,240),r_knee=(182,240))
gif("204.gif", interp([S,step_in,S],3), active=('l_ankle','r_ankle','l_knee','r_knee'), dur=130)

# 205 Two-Point Rally
rally_fh = p(l_ankle=(108,287),l_knee=(120,238),l_hip=(132,182),
             r_ankle=(172,287),r_knee=(172,238),r_hip=(172,182),
             hip=(148,182),head=(148,46),neck=(148,70),
             r_elbow=(200,105),r_wrist=(218,78))
rally_bh = p(r_ankle=(212,287),r_knee=(200,238),r_hip=(188,182),
             l_ankle=(148,287),l_knee=(148,238),l_hip=(148,182),
             hip=(172,182),head=(172,46),neck=(172,70),
             l_elbow=(120,105),l_wrist=(102,78))
gif("205.gif", interp([rally_fh,S,rally_bh,S],3), active=('r_elbow','r_wrist','l_elbow','l_wrist'), dur=140)

# 206 Triangle Footwork (top-down arrow + figure at corners)
gif("206.gif", interp([pos_BH,pos_C,pos_FH,pos_C],3),
    active=('l_ankle','r_ankle','l_knee','r_knee'), dur=150)

# 207 Pivot Drill
pivot = p(head=(152,46),neck=(152,70),
          l_shoulder=(118,92),r_shoulder=(176,92),
          l_elbow=(100,128),l_wrist=(88,162),
          r_elbow=(210,100),r_wrist=(232,72),
          hip=(155,180),l_hip=(138,180),r_hip=(170,180),
          l_knee=(128,235),l_ankle=(120,288),
          r_knee=(172,235),r_ankle=(168,288))
gif("207.gif", interp([S,pivot,S],4), active=('r_elbow','r_wrist','hip'), dur=130)

# ─── SPEED ───────────────────────────────────────────────────────────
print("⚡ Speed")

# 301 Reaction Ball
bend = p(head=(145,98),neck=(145,122),
         l_shoulder=(118,140),r_shoulder=(172,140),
         l_elbow=(100,175),l_wrist=(86,205),
         r_elbow=(195,158),r_wrist=(215,128),
         hip=(148,210),l_hip=(132,210),r_hip=(164,210),
         l_knee=(120,258),l_ankle=(108,300),
         r_knee=(165,255),r_ankle=(168,295))
gif("301.gif", interp([S,bend,S],4), active=('r_wrist','r_elbow'), dur=120)

# 302 Fast Hands Counter – compact quick strokes
fh_compact = p(r_elbow=(210,112),r_wrist=(225,84),
               l_elbow=(110,128),l_wrist=(102,165))
bh_compact = p(l_elbow=(108,108),l_wrist=(90,82),
               r_elbow=(208,128),r_wrist=(215,165))
gif("302.gif", interp([fh_compact,S,bh_compact,S],3), active=('r_elbow','r_wrist','l_elbow','l_wrist'), dur=80)

# 303 Multi-Ball – quick left-right with arm
gif("303.gif", interp([rally_fh,S,rally_bh,S],2), active=('r_elbow','r_wrist','l_elbow','l_wrist'), dur=80)

# 304 Quick-Fire Serves
serve_up  = p(r_elbow=(205,115),r_wrist=(210,78),
              l_elbow=(120,120),l_wrist=(128,82))
serve_hit = p(r_elbow=(218,92),r_wrist=(230,62),
              l_elbow=(118,115),l_wrist=(108,150))
gif("304.gif", interp([serve_up,serve_hit,S],3), active=('r_elbow','r_wrist'), dur=100)

# ─── AGILITY ─────────────────────────────────────────────────────────
print("🏃 Agility")

# 401 Ladder Lateral – small side steps, low stance
ladder_low = p(l_knee=(128,215),r_knee=(192,215),
               l_ankle=(115,268),r_ankle=(205,268),
               hip=(160,168),l_hip=(142,168),r_hip=(178,168),
               head=(160,40),neck=(160,64))
step_L = p(l_ankle=(80,268),l_knee=(96,215),
           r_ankle=(172,268),r_knee=(172,215),
           hip=(145,168),l_hip=(112,168),r_hip=(160,168),
           head=(145,40),neck=(145,64))
step_R = p(r_ankle=(240,268),r_knee=(224,215),
           l_ankle=(148,268),l_knee=(148,215),
           hip=(175,168),l_hip=(158,168),r_hip=(208,168),
           head=(175,40),neck=(175,64))
gif("401.gif", interp([step_L,ladder_low,step_R,ladder_low],3), active=('l_ankle','r_ankle'), dur=100)

# 402 Ladder In-Out
feet_in  = p(l_ankle=(148,287),r_ankle=(172,287),l_knee=(143,240),r_knee=(177,240))
feet_out = p(l_ankle=(90,287),r_ankle=(230,287),l_knee=(105,240),r_knee=(215,240),
             hip=(160,172),l_hip=(130,172),r_hip=(190,172),head=(160,40),neck=(160,64))
gif("402.gif", interp([feet_in,feet_out],4), active=('l_ankle','r_ankle','l_knee','r_knee'), dur=110)

# 403 Cone Touch – sprint lean
sprint = p(head=(150,38),neck=(150,62),
           l_shoulder=(120,84),r_shoulder=(178,84),
           l_elbow=(100,118),l_wrist=(88,152),
           r_elbow=(202,105),r_wrist=(218,75),
           hip=(155,168),l_hip=(138,168),r_hip=(170,168),
           l_knee=(125,228),l_ankle=(108,278),
           r_knee=(172,232),r_ankle=(175,285))
touch = p(head=(140,108),neck=(140,132),
          l_shoulder=(112,152),r_shoulder=(168,152),
          l_elbow=(98,188),l_wrist=(82,222),
          r_elbow=(185,170),r_wrist=(200,140),
          hip=(145,220),l_hip=(128,220),r_hip=(162,220),
          l_knee=(118,268),l_ankle=(105,305),
          r_knee=(165,258),r_ankle=(162,295))
gif("403.gif", interp([S,sprint,touch,sprint,S],3), active=('r_wrist','l_wrist'), dur=130)

# 404 Random Direction
explode_R = p(r_ankle=(238,287),r_knee=(218,233),r_hip=(195,178),
              l_ankle=(120,287),l_knee=(128,240),
              hip=(165,178),head=(165,46),neck=(165,70),
              l_elbow=(105,120),l_wrist=(92,90))
gif("404.gif", interp([S,explode_R,S],4), active=('r_ankle','r_knee'), dur=110)

# ─── STRENGTH ────────────────────────────────────────────────────────
print("💪 Strength")

# 501 Box Jumps
squat_pre = p(head=(160,58),neck=(160,82),
              hip=(160,195),l_hip=(144,195),r_hip=(176,195),
              l_knee=(135,248),l_ankle=(130,287),
              r_knee=(185,248),r_ankle=(180,287),
              l_elbow=(112,152),l_wrist=(108,188),
              r_elbow=(208,152),r_wrist=(212,188))
airborne  = p(head=(160,22),neck=(160,46),
              hip=(160,148),l_hip=(144,148),r_hip=(176,148),
              l_knee=(135,195),l_ankle=(140,242),
              r_knee=(185,195),r_ankle=(180,242),
              l_elbow=(108,68),l_wrist=(98,46),
              r_elbow=(212,68),r_wrist=(222,46))
land_box  = p(head=(160,55),neck=(160,79),
              hip=(160,188),l_hip=(144,188),r_hip=(176,188),
              l_knee=(132,242),l_ankle=(128,278),
              r_knee=(188,242),r_ankle=(182,278))
gif("501.gif", interp([squat_pre,airborne,land_box],4), active=('l_ankle','r_ankle','hip'), dur=140)

# 502 Bodyweight Squats
squat = p(head=(160,90),neck=(160,114),
          l_shoulder=(130,132),r_shoulder=(190,132),
          l_elbow=(112,172),l_wrist=(105,210),
          r_elbow=(208,172),r_wrist=(215,210),
          hip=(160,210),l_hip=(142,210),r_hip=(178,210),
          l_knee=(118,258),l_ankle=(112,290),
          r_knee=(202,258),r_ankle=(205,290))
gif("502.gif", interp([S,squat,S],4), active=('l_knee','r_knee','hip'), dur=150)

# 503 Forearm Plank – horizontal figure
plank_a = {
    'head':      (62,160), 'neck':      (85,160),
    'l_shoulder':(105,148),'r_shoulder':(105,172),
    'l_elbow':   (78,138), 'l_wrist':   (52,138),
    'r_elbow':   (78,182), 'r_wrist':   (52,182),
    'hip':       (188,160),'l_hip':     (188,148),'r_hip':(188,172),
    'l_knee':    (232,148),'r_knee':    (232,172),
    'l_ankle':   (272,148),'r_ankle':   (272,172),
}
plank_b = {k:(v[0],v[1]+4 if 'shoulder' in k or k=='neck' else v[1]) for k,v in plank_a.items()}
gif("503.gif", interp([plank_a,plank_b],3), active=('l_elbow','r_elbow','l_wrist','r_wrist'), dur=400)

# 504 Side Plank – tilted figure
side_a = {
    'head':      (60,148), 'neck':      (83,160),
    'l_shoulder':(108,178),'r_shoulder':(108,150),
    'l_elbow':   (75,188), 'l_wrist':   (48,196),
    'r_elbow':   (115,118),'r_wrist':   (115,88),
    'hip':       (185,200),'l_hip':     (185,212),'r_hip':(185,188),
    'l_knee':    (235,218),'r_knee':    (235,186),
    'l_ankle':   (275,228),'r_ankle':   (275,194),
}
side_b = {k:(v[0],v[1]-3 if k in ('r_wrist','r_elbow') else v[1]) for k,v in side_a.items()}
gif("504.gif", interp([side_a,side_b],3), active=('l_elbow','l_wrist'), dur=400)

# 505 Resistance Band FH (same as forehand motion)
gif("505.gif", interp([fh_wind,fh_hit,fh_fol],3), active=('r_shoulder','r_elbow','r_wrist'), dur=120)

# 506 Calf Raises
tiptoe = p(l_ankle=(140,272),r_ankle=(174,272),
           l_knee=(141,230),r_knee=(179,230),
           hip=(160,174),l_hip=(144,174),r_hip=(176,174),
           neck=(160,68),head=(160,44))
gif("506.gif", interp([S,tiptoe,S],4), active=('l_ankle','r_ankle'), dur=150)

# ─── COOL-DOWN ───────────────────────────────────────────────────────
print("🧊 Cool-down")

# 601 Quad Stretch Walk
quad_L = p(l_knee=(138,195),l_ankle=(150,155),  # foot pulled up behind
           r_knee=(179,233),r_ankle=(175,287),
           l_elbow=(112,125),l_wrist=(125,88))   # hand holding foot
quad_R = p(r_knee=(176,195),r_ankle=(163,155),
           l_knee=(141,233),l_ankle=(137,287),
           r_elbow=(208,125),r_wrist=(195,88))
gif("601.gif", interp([S,quad_L,S,quad_R,S],3), active=('l_knee','l_ankle','r_knee','r_ankle'), dur=150)

# 602 Hamstring Stretch – hinge forward over extended leg
hamstring = p(head=(155,138),neck=(155,162),
              l_shoulder=(122,180),r_shoulder=(188,180),
              l_elbow=(105,218),l_wrist=(98,255),
              r_elbow=(205,218),r_wrist=(212,255),
              hip=(155,255),l_hip=(135,255),r_hip=(175,255),
              l_knee=(125,295),l_ankle=(108,285),   # front leg extended
              r_knee=(175,272),r_ankle=(172,285))
gif("602.gif", interp([S,hamstring],4), active=('l_wrist','r_wrist','l_knee'), dur=200)

# 603 Shoulder Stretch – arm pulled across chest
shr_R = p(r_shoulder=(185,90),r_elbow=(150,108),r_wrist=(118,118),
          l_elbow=(125,128),l_wrist=(118,120))   # left hand pulling at elbow
shr_L = p(l_shoulder=(131,90),l_elbow=(168,108),l_wrist=(200,118),
          r_elbow=(195,128),r_wrist=(200,120))
gif("603.gif", interp([shr_R,S,shr_L,S],3), active=('r_wrist','r_elbow','l_wrist','l_elbow'), dur=200)

# 604 Wrist Flexor Stretch
wflex_R = p(r_elbow=(210,132),r_wrist=(218,92),   # arm extended forward-up
            l_elbow=(120,118),l_wrist=(218,88))    # left hand pulling back right wrist
wflex_L = p(l_elbow=(110,132),l_wrist=(102,92),
            r_elbow=(200,118),r_wrist=(102,88))
gif("604.gif", interp([wflex_R,S,wflex_L,S],3), active=('r_wrist','l_wrist'), dur=220)

# 605 Deep Breathing
exhale = p(head=(160,50),neck=(160,74),
           l_shoulder=(136,94),r_shoulder=(184,94),
           l_elbow=(120,136),r_elbow=(200,136))
inhale = p(head=(160,42),neck=(160,66),
           l_shoulder=(126,86),r_shoulder=(194,86),
           l_elbow=(108,120),r_elbow=(212,120),
           l_wrist=(100,158),r_wrist=(220,158),
           hip=(160,172),l_hip=(144,172),r_hip=(176,172))
gif("605.gif", interp([exhale,inhale],5), active=('l_shoulder','r_shoulder'), dur=400)

print(f"\n✅ Gotowe! {len(os.listdir(OUT))} GIFów w {OUT}")
