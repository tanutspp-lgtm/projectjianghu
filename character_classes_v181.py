"""Approved 36-frame classes. Cosmetic identity never accepts client combat values."""
CLASSES=('flute','jian','tang','healer')
AVATARS=frozenset(f'{kind}_{sex}' for kind in CLASSES for sex in ('male','female'))
BASE={'attack':dict(cool=.34,duration=.32,speed=520,life=1.45,pierce=1),
      'aoe':dict(cool=.62,duration=.48,speed=365,life=1.15,pierce=99),
      'break':dict(cool=.52,duration=.37,speed=560,life=1.10,pierce=2)}

def profession(avatar):
    return avatar.split('_')[0] if avatar in AVATARS else 'flute'

def spec(cls,action):
    b=BASE[action];s=dict(b,mode='ranged',reach=0,windup=b['duration']*.5,healPct=0)
    if cls=='jian' or (cls=='tang' and action=='attack'):
        s.update(mode='melee',speed=0,life=.10,reach=(145 if action=='aoe' else 126) if cls=='jian' else 92)
    if cls=='tang' and action=='aoe':s.update(speed=550,pierce=1)
    if cls=='healer' and action=='aoe':s.update(mode='heal',cool=3,duration=.60,windup=.30,speed=0,life=.01,pierce=0,reach=300,healPct=15)
    return s

def row_for(cls,action):
    return 24 if action=='attack' or (cls=='healer' and action=='break') else 30

def actor_frame(a,tick):
    if a.dead>0 or a.hp<=0:return 23 if a.ground else 22
    if a.down>0:return 22 if a.ground else 21
    if a.climb:return 18+int(a.climb_dist/48)%2
    if a.kb_time>0:return 20 if a.ground else 21
    if a.stun>.02:return 20
    if a.guard:return 24
    if a.action in BASE and a.action_at<a.action_duration:
        return row_for(profession(a.avatar),a.action)+min(5,int(a.action_at/max(.001,a.action_duration)*6))
    if a.action=='dash' and a.action_at<a.action_duration:return 16+int(a.action_at>a.action_duration*.5)
    if not a.ground:
        if a.action=='jump' and a.action_at<.055:return 12
        return 13 if a.vy< -120 else 14 if abs(a.vy)<150 else 15
    if abs(a.vx)>25:return 4+int(a.walk_dist/18)%8
    phase=(tick/30)%4.2
    return 1 if 3.95<phase<4.08 else [0,2,3][int(tick/20)%3]
