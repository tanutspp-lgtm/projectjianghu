"""Server-owned six-move starter sets. No client HP, damage, cooldown or rage input.
PvP bot training is a local isolated room; public worlds retain cooperative PvE.
"""
import json
import math
import secrets
import time
from pathlib import Path
from types import SimpleNamespace
RULES=json.loads(Path(__file__).with_name('combat_rules_v187.json').read_text())
FEATURE='martial-combat-v187-v1'
LOCK_FEATURE='martial-lock-state-v1871-v1'
FLOW_FEATURE='martial-playflow-v1872-v1'
ROLES=('basic','guard','break','first','second','ultimate')

def state(a):
    if not hasattr(a,'martial187'):
        a.martial187=dict(cd={},status={},rage=0.,meter=100.,held_until=0.,auto_guard=None,guard_queue=False,
            counter=0.,energy=0.,block_hits={},slow_proc={},heal_stacks=0,heal_progress=0.,ledger=[],cast=None,
            combo=0,lock=None,lock_source=None,last_attacker=None,shield=0.,shield_until=0.,hit_until=0.,motion=None,guard_recovery=0.)
    a.martial187.setdefault('lock_source',None)
    a.martial187.setdefault('basic_queue_until',0.)
    return a.martial187

def active(a,key,now): return state(a)['status'].get(key,0)>now

def alive(a): return a is not None and a.hp>0 and a.dead<=0

class World:
    def __init__(self,blocked,damage,emit,damage_scale,physics,width=4160):
        self.blocked=blocked;self.damage=damage;self.emit_old=emit;self.damage_scale=damage_scale;self.physics=physics
        self.width=width;self.time=time.monotonic();self.actors={};self.players={};self.mobs={};self.casts=[];self.shots=[];self.events=[];self.serial=0;self.epoch=secrets.token_hex(8)
    def emit(self,kind,**kw):
        self.serial+=1; e=dict(id=self.serial,type=kind,time=self.time,**kw);self.events.append(e)
        self.events=self.events[-100:];return e
    def sync(self,players,mobs):
        self.players=dict(players);self.mobs=dict(mobs);self.actors={**self.players,**self.mobs};self.time=time.monotonic()
        for p in self.players.values():state(p)
    def cls(self,a):return getattr(a,'avatar','jian_male').split('_')[0] if a.id in self.players else 'jian'
    def capable(self,a):return a.id in self.players or bool(getattr(a,'hum',False) and getattr(a,'zone_mode','common')!='common')
    def party(self,a):return getattr(a,'party_id',None) or ('solo:'+a.id if a.id in self.players else 'mobs')
    def enemies(self,a):return [m for m in self.mobs.values() if alive(m)] if a.id in self.players else [p for p in self.players.values() if alive(p)]
    def ally(self,a,b):return a.id in self.players and b.id in self.players and self.party(a)==self.party(b)
    def spec(self,a,role):return RULES['classes'][self.cls(a)][role]
    def reachable(self,a,b,reach,front=True):
        return alive(b) and abs(a.x-b.x)<=reach+18 and abs(a.y-b.y)<95 and (not front or (b.x-a.x)*a.face>=-15) and not self.blocked(a.x,a.y-43,b.x,b.y-43,a,b)
    def cancel(self,a):
        state(a)['basic_queue_until']=0
        c=state(a)['cast']
        if c:
            if c['role']=='ultimate':state(a)['status'].pop('yellow',None)
            c['cancelled']=True;self.emit('cancel',actor=a.id,cast=c['id'])
        state(a)['cast']=None
    def cc(self,a,kind,seconds):
        st=state(a)
        if active(a,'red',self.time) or kind=='down' and active(a,'yellow',self.time):return
        if not self.capable(a) and kind=='seal':return
        st['status'][kind]=max(st['status'].get(kind,0),self.time+seconds)
        if kind in ('down','stun','sleep'):
            self.cancel(a);a.guard=False;st['auto_guard']=None;st['guard_queue']=False;a.vx=0
        if kind=='down':a.down=max(a.down,seconds)
        if kind=='stun':a.stun=max(a.stun,seconds)
        if kind=='seal':a.broken=max(a.broken,seconds)
    def lock(self,p,target):
        if target is None:state(p)['lock']=None;state(p)['lock_source']=None;return True
        a=self.mobs.get(target)
        if not alive(a) or abs(p.x-a.x)>900:return False
        state(p)['lock']=a.id;state(p)['lock_source']='manual';return True
    def guard(self,p,held):
        st=state(p);st['held_until']=self.time+.6 if held else 0
        if held:st['basic_queue_until']=0
        if not held:
            st['guard_queue']=False
            if not st['auto_guard']:p.guard=False
            return True
        if not alive(p) or any(active(p,k,self.time) for k in ('sleep','stun','down','seal')) or st['meter']<=0:return False
        if st['hit_until']>self.time:st['guard_queue']=True;return True
        if st['cast']:return False
        p.guard=True;return True
    def cast(self,p,role):
        self.time=time.monotonic();st=state(p);cls=self.cls(p)
        if role not in ROLES:return False,'สกิลไม่ถูกต้อง'
        if role=='guard':return self.guard(p,True),None
        if st['cast'] and st['cast']['end']<=self.time:st['cast']=None
        if role=='basic' and st['cast'] and st['cast']['role']=='basic' and st['cast']['end']-self.time<=.12 and st['hit_until']<=self.time and not any(active(p,k,self.time) for k in ('sleep','down','stun','seal')):
            st['basic_queue_until']=self.time+.22;return True,None
        s=dict(self.spec(p,role));counter=st['counter']>self.time;yellow=role=='ultimate' or cls=='jian' and role=='first' and counter and st['energy']>=180
        checks=((not alive(p),'หมดสติ'),(bool(p.climb),'อยู่บนเชือก'),(active(p,'sleep',self.time) or active(p,'stun',self.time),'ติดสถานะควบคุม'),
            ((active(p,'down',self.time) or st['hit_until']>self.time) and not yellow and not (counter and not active(p,'down',self.time)),'ยังอยู่ในกระบวนท่าศัตรู'),
            (active(p,'seal',self.time),'ถูกผนึกสกิล'),(st['cast'] is not None,'กำลังออกท่า'),(role!='basic' and st['cd'].get(role,0)>self.time,'คูลดาวน์'),
            (active(p,'root',self.time) and bool(s.get('move') or s.get('lunge')),'ถูกตรึงเท้า'),(p.sp<s['sp'],'SP ไม่พอ'),(role=='ultimate' and st['rage']<100,'เรจยังไม่เต็ม'))
        for condition,error in checks:
            if condition:return False,error
        target=self.actors.get(st['lock'])
        if target and not alive(target):st['lock']=None;st['lock_source']=None;target=None
        needs_target=not (cls=='healer' and role in ('second','ultimate') or cls=='jian' and role=='second')
        if target and needs_target and (st['lock_source']!='retaliation' or cls=='tang' and role=='ultimate') and not self.reachable(p,target,s['range'],False):return False,'นอกระยะ'
        if counter:st['hit_until']=0
        if yellow:
            st['status'].pop('down',None);p.down=0;p.kb_time=0;p.kb_dir=0;st['hit_until']=0;st['status']['yellow']=self.time+s['duration']
        p.guard=False;st['auto_guard']=None;st['held_until']=0;st['guard_queue']=False;p.sp-=s['sp'];st['basic_queue_until']=0
        if role=='basic':st['cd'].pop('basic',None)
        else:st['cd'][role]=self.time+s['cd']
        if role=='ultimate':st['rage']=0
        direction=p.face
        if p.buttons&3 in (1,2):direction=1 if p.buttons&2 else -1
        if getattr(p,'aim_assist183',False) and target and self.reachable(p,target,s['range'],False):direction=1 if target.x>=p.x else -1
        close=cls=='tang' and role=='basic' and any(self.reachable(SimpleNamespace(**{**p.__dict__,'face':direction}),b,s['meleeRange']) for b in self.enemies(p))
        variant=st['combo']%2 if role=='basic' and (cls=='jian' or close) else 0
        if role=='basic' and (cls=='jian' or close):st['combo']+=1
        cast_scale=self.damage_scale(p)
        self.serial+=1;c=dict(critical=getattr(p,'martial_crit187',False),id='c'+str(self.serial),actor=p.id,profession=cls,role=role,dir=direction,start=self.time,end=self.time+s['duration'],next=self.time+s['windup'],index=0,s=s,target=None if st['lock_source']=='retaliation' and not(cls=='tang' and role=='ultimate') else st['lock'],variant=variant,melee=s.get('melee',False) or close,cancelled=False,counter=counter and not(cls=='jian' and role=='second'),healBonus=1.,scale=cast_scale)
        if close:s['range']=s['meleeRange'];s['count']=1
        if cls=='healer' and s.get('heal'):
            c['healBonus']=1+min(5,int(st['heal_stacks']))*.1;st['heal_stacks']=st['heal_progress']=0
            self.heal(p,p,p.max_hp*s['heal']*c['healBonus'],c['id'])
            if role=='ultimate':
                # Bounded server-owned reference viewport; no client zoom/position reports.
                view=getattr(p,'martial_view187',(1000,650));vw=min(self.width,view[0]);left=max(0,min(self.width-vw,p.x-vw*.42));bottom=p.y+110
                for b in self.players.values():
                    if b is not p and left<=b.x<=left+vw and bottom-view[1]<=b.y and b.y-123<=bottom:self.heal(p,b,b.max_hp*s['heal']*c['healBonus'],c['id'])
        if cls=='jian' and role=='first' and counter:
            s['damage']+=min(120,st['energy']*.45);st['shield']=min(p.max_hp*.15,st['energy']*.6);st['shield_until']=self.time+5;st['energy']=0
        if counter and not(cls=='jian' and role=='second'):st['counter']=0
        if s.get('move'):st['motion']=dict(until=self.time+s['duration'],speed=s['move']/s['duration']*direction)
        if s.get('lunge'):
            b=target or next((b for b in sorted(self.enemies(p),key=lambda b:abs(b.x-p.x)) if self.reachable(p,b,s['range'])),None)
            if b:
                c['dir']=1 if b.x>=p.x else -1;c['target']=b.id;st['motion']=dict(until=self.time+.16,speed=max(0,min(s['lunge'],abs(b.x-p.x)-65))/.16*c['dir'])
        p.face=direction;p.cast_face=c['dir'];p.action='attack';p.action_at=0;p.action_duration=s['duration'];p.attack_variant182=2 if cls=='tang' and not c['melee'] else variant;p.cool=s['duration'];p.pending_class_cast=None
        st['cast']=c;self.casts.append(c);self.emit('cast',actor=p.id,cast=c['id'],role=role,profession=cls,dir=c['dir'],variant=variant,counter=c['counter']);return True,None
    def budget(self,p):
        st=state(p);st['ledger']=[v for v in st['ledger'] if v[0]>self.time-60]
        return max(0,.4-sum(v[1] for v in st['ledger']))*p.max_hp
    def heal(self,a,b,amount,cast):
        if not alive(b) or not self.ally(a,b):return 0
        amount=max(0,min(amount,b.max_hp-b.hp,self.budget(b)))
        if amount>1e-6:
            b.hp+=amount;state(b)['ledger'].append((self.time,amount/b.max_hp));self.emit('heal',actor=b.id,owner=a.id,amount=amount,cast=cast)
        return amount
    def hit(self,c,v,amount):
        a=self.actors.get(c['actor'])
        if not a or not alive(v):return
        vs=state(v);ats=state(a);vs['last_attacker']=a.id
        if not vs['lock'] and v.id in self.players and self.capable(a):vs['lock']=a.id;vs['lock_source']='retaliation'
        vs['status'].pop('sleep',None);s=c['s'];rage_scale=min(2,amount*c.get('scale',1)*RULES['rage']['referenceMaxHp']/(RULES['rage']['referenceDamage']*v.max_hp))
        def grant(kind):
            if c['role']=='ultimate':return
            gain=max(0,min(RULES['rage']['attackerPerCastCap']-c.get('rage_granted',0),RULES['rage'][kind]*rage_scale));ats['rage']=min(100,ats['rage']+gain);c['rage_granted']=c.get('rage_granted',0)+gain
        blocking=self.capable(v) and v.guard and (vs['held_until']>self.time or not vs['auto_guard'] or vs['auto_guard']==c['id']) and not active(v,'seal',self.time) and ((a.x-v.x)*v.face>=-18 or vs['auto_guard']==c['id'])
        if blocking and c['role']=='break':
            v.guard=False;vs['auto_guard']=None;vs['held_until']=0;vs['meter']=max(0,vs['meter']-25);self.cc(v,'seal',1.25);self.emit('break',actor=v.id,owner=a.id,cast=c['id'])
        elif blocking:
            reduction=RULES['classes'][self.cls(v)]['guardReduction'];prevented=amount*c.get('scale',1)*reduction;amount*=1-reduction;vs['meter']=max(0,vs['meter']-s.get('guardCost',8));vs['counter']=self.time+3;vs['auto_guard']=c['id'];vs['energy']=min(260,vs['energy']+prevented);vs['rage']=min(100,vs['rage']+RULES['rage']['block']*rage_scale);grant('intoGuard')
            if self.cls(v)=='healer':vs['heal_stacks']=min(5,vs['heal_stacks']+1)
            if self.cls(v)=='jian' and self.capable(a):
                vs['block_hits'][a.id]=vs['block_hits'].get(a.id,0)+1
                if vs['block_hits'][a.id]>=5 and vs['slow_proc'].get(a.id,0)<=self.time:
                    vs['block_hits'][a.id]=0;vs['slow_proc'][a.id]=self.time+15;self.cc(a,'slow',10)
            if vs['meter']<=0:v.guard=False;vs['auto_guard']=None;self.cc(v,'seal',1.25)
            self.emit('block',actor=v.id,owner=a.id,cast=c['id'])
        else:
            grant('hit');vs['rage']=min(100,vs['rage']+RULES['rage']['hurt']*rage_scale)
            if self.cls(v)=='healer':
                vs['heal_progress']+=.25
                if vs['heal_progress']>=1:vs['heal_progress']-=1;vs['heal_stacks']=min(5,vs['heal_stacks']+1)
            if not active(v,'yellow',self.time) and not active(v,'red',self.time) and not(vs['cast'] and vs['cast'].get('counter')):vs['hit_until']=max(vs['hit_until'],c['end'],self.time+.18);self.cancel(v)
            if v.guard:v.guard=False;vs['auto_guard']=None;vs['guard_queue']=vs['held_until']>self.time
        amount*=c.get('scale',1)
        if active(a,'weaken',self.time):amount*=.75
        if vs['shield_until']>self.time:
            absorbed=min(amount,vs['shield']);vs['shield']-=absorbed;amount-=absorbed
        before_hp=v.hp;actual=self.damage(c,v,amount)
        if actual is None:actual=max(0,before_hp-v.hp)
        if not blocking:
            if s.get('cc'):self.cc(v,s['cc'],s['ccTime'])
            if s.get('weaken'):self.cc(v,'weaken',4)
        self.emit('damage',actor=v.id,owner=a.id,amount=actual,blocked=blocking and c['role']!='break',cast=c['id'],dir=c['dir'],critical=bool(c.get('critical',False)))
    def incoming(self,v,damage,source_x,knock=False,source_id=None):
        if not alive(v):return False
        a=self.mobs.get(source_id) or min(self.mobs.values(),key=lambda m:abs(m.x-source_x),default=None)
        if not a:return False
        self.serial+=1;c=dict(id='mob'+str(self.serial),actor=a.id,role='basic',s=dict(cc='down',ccTime=.55) if knock else {},dir=1 if v.x>=a.x else -1,end=self.time+.3,melee=True,scale=1)
        self.hit(c,v,damage)
        hit=next((e for e in reversed(self.events) if e['type']=='damage' and e.get('cast')==c['id']),None)
        if hit and not hit['blocked'] and alive(v) and not active(v,'yellow',self.time) and not active(v,'red',self.time):
            v.inv=1.12;v.kb_time=.28;v.kb_dir=1 if v.x>=a.x else -1;v.vx=v.kb_dir*300;v.vy=-240;v.ground=False;v.climb=None
        return True
    def release(self,c):
        a=self.actors.get(c['actor']);s=c['s']
        if not a or c['cancelled']:return
        if s.get('move') and not s['damage']:return
        if s.get('zone'):
            target=self.actors.get(c['target']);x=c.setdefault('zone_x',max(28,min(self.width-28,target.x if target else a.x+c['dir']*300)))
            self.emit('zone',actor=a.id,profession=c['profession'],role=c['role'],x=x,y=a.y,dir=c['dir'],cast=c['id'])
            for b in self.enemies(a):
                if abs(b.x-x)<s['radius'] and abs(b.y-a.y)<85 and not self.blocked(x,a.y-40,b.x,b.y-43,a,b):self.hit(c,b,s['damage'])
            return
        if c['melee']:
            proxy=SimpleNamespace(**{**a.__dict__,'face':c['dir']});targets=[b for b in self.enemies(a) if self.reachable(proxy,b,s['range'],not s.get('radial',False))]
            if c['profession']=='tang':targets=sorted(targets,key=lambda b:abs(b.x-a.x))[:1]
            self.emit('slash',radial=bool(s.get('radial')),range=s['range'],duration=s.get('interval',.27),actor=a.id,profession=c['profession'],role=c['role'],variant=c['index']%2 if c['role']=='ultimate' else c['variant'],x=a.x if s.get('radial') else a.x+c['dir']*(55 if c['profession']=='tang' else 68),y=a.y-48,dir=c['dir'],cast=c['id'])
            for b in targets:self.hit(c,b,s['damage']*(s.get('finisher',1) if c['index']==s.get('hits',1)-1 else 1))
            return
        count=s.get('count',1)
        for k in range(count):
            direction=(-1 if k<3 else 1) if c['profession']=='healer' and c['role']=='ultimate' else c['dir'];self.serial+=1
            self.shots.append(dict(id='s'+str(self.serial),cast=c,owner=a.id,profession=c['profession'],role=c['role'],dir=direction,x=a.x+direction*(54 if c['profession']=='flute' else 36),y=a.y-43+([-16,0,16][k%3] if count==6 else 0),launch_x=a.x,launch_y=a.y-43,launch_foot=a.y,traveled=0.,age=-k*.095 if count==2 else 0.,speed=s.get('speed',500),range=s['range'],hit=set(),heal=set(),damage=s['damage']/(count if c['profession']=='tang' and c['role']=='basic' else 1),dead=False,fade=0.))
    def before_move(self,a):
        st=state(a);now=self.time
        if st['auto_guard']:
            c=next((c for c in self.casts if c['id']==st['auto_guard']),None)
            in_flight=any(p['cast']['id']==st['auto_guard'] and not p['dead'] for p in self.shots)
            if (not c or c['cancelled'] or c['end']<=now) and not in_flight:st['auto_guard']=None;st['held_until']=0;a.guard=False
        if st['guard_queue'] and st['hit_until']<=now and not any(active(a,k,now) for k in ('sleep','down','stun','seal')):st['guard_queue']=False;a.guard=st['held_until']>now
        if st['held_until']<=now and not st['auto_guard']:a.guard=False
        if st['cast'] and st['cast']['end']<=now:st['cast']=None
        if st['basic_queue_until']:
            queued=st['basic_queue_until'];st['basic_queue_until']=0
            if queued>=now and not st['cast']:self.cast(a,'basic')
            elif queued>=now:st['basic_queue_until']=queued
        a.guard=a.guard and not any(active(a,k,now) for k in ('sleep','down','stun','seal'))
        blocked=any(active(a,k,now) for k in ('root','sleep','down','stun')) or st['hit_until']>now or st['cast'] is not None
        if blocked:a.vx=0
        return blocked
    def step(self,dt):
        self.time=time.monotonic()
        for a in self.players.values():
            st=state(a)
            if alive(a):
                if a.guard:st['guard_recovery']=self.time+2
                elif st['guard_recovery']<self.time:st['meter']=min(100,st['meter']+10*dt)
            self.before_move(a)
        for c in self.casts:
            a=self.actors.get(c['actor'])
            if not alive(a) or c['cancelled']:c['cancelled']=True;continue
            while c['index']<c['s'].get('hits',1) and self.time>=c['next']:
                self.release(c);c['index']+=1;c['next']+=c['s'].get('interval',1)
        for p in self.shots:
            if p['dead']:p['fade']+=dt;continue
            p['age']+=dt
            if p['age']<0:continue
            a=self.actors.get(p['owner'])
            if not a:p['dead']=True;continue
            s=p['cast']['s'];travel=min(p['speed']*dt,p['range']-p['traveled']);old=p['x'];nxt=old+p['dir']*travel;p['traveled']+=travel
            if self.blocked(old,p['y'],nxt,p['y'],a,None):p['dead']=True;continue
            targets=[b for b in self.actors.values() if alive(b) and b is not a and min(old,nxt)-18<=b.x<=max(old,nxt)+18 and b.y-(123 if getattr(b,'hum',b.id in self.players) else 90)-s.get('radius',8)<=p['y']<=b.y-5+s.get('radius',8) and not self.blocked(p['launch_x'],p['launch_y'],b.x,b.y-43,SimpleNamespace(y=p['launch_foot']),b)]
            targets.sort(key=lambda b:b.x*p['dir'])
            for b in targets:
                if self.ally(a,b):
                    if p['profession']=='healer' and p['role']=='second' and b.id not in p['heal']:p['heal'].add(b.id);self.heal(a,b,b.max_hp*s['heal']*p['cast']['healBonus'],p['cast']['id'])
                    continue
                if b.id not in self.mobs or b.id in p['hit']:continue
                p['hit'].add(b.id);self.hit(p['cast'],b,p['damage'])
                if not s.get('pierce'):p['x']=b.x;p['dead']=True;break
            if not p['dead']:p['x']=nxt
            if p['traveled']>=p['range']:p['dead']=True
        self.shots=[p for p in self.shots if p['fade']<.16]
        self.casts=[c for c in self.casts if not c['cancelled'] and (c['end']+1>self.time or c['index']<c['s'].get('hits',1))]
    def snapshot(self):
        actors=[]
        for a in self.actors.values():
            st=state(a);c=st['cast']
            if a.id not in self.players and not any(until>self.time for until in st['status'].values()):continue
            actors.append(dict(id=a.id,isPlayer=a.id in self.players,profession=self.cls(a),capable=self.capable(a),guard=bool(a.guard),rage=round(st['rage'],2),guardMeter=round(st['meter'],2),counterUntil=st['counter'],blockedEnergy=st['energy'],healStacks=st['heal_stacks'],healRemaining=round(self.budget(a),2) if a.id in self.players else 0,cd=st['cd'],status=st['status'],lock=st['lock'],lockSource=st['lock_source'],cast={k:c[k] for k in ('id','role','start','end','dir','variant','melee','counter')} if c else None))
        shots=[{k:p[k] for k in ('id','owner','profession','role','dir','x','y','speed','range','traveled','age','dead','fade')} for p in self.shots]
        return dict(version=187,epoch=self.epoch,eventHighwater=self.events[-1]['id'] if self.events else 0,time=self.time,actors=actors,shots=shots,events=self.events[-80:])
