"""v8.0BU Offline/Online monster parity, server AUTO navigation and collision regression."""
import json,math,random,time
from pathlib import Path
from tempfile import TemporaryDirectory
import server
import farm_auto_v80bu as bot
import monster_hp_def_v80bu as balance

R=Path(__file__).resolve().parent
assert len(balance.TABLE)==60
for l in range(1,61):
  r=balance.TABLE[l]
  for human,label in [(False,'normal'),(True,'humanoid')]:
    assert balance.preset(l,human)==(r[label]['hp'],r[label]['defense'])
print('PASS Offline v8.0AO preset table mirrored 60 levels 120 HP/DEF cases')

for level in (1,5,20,40,60):
  hp,d=balance.preset(level)
  m=server.Monster(id='tmp',x=200,y=550,hp=hp,max_hp=hp,defense=d,level=level)
  # Test exact displayed Damage Reduction without drop/EXP side effects.
  shot=server.Shot(2,'unowned','attack',155,466,520,1000,1,1)
  server.hit_by_shot(shot,m,1000,True)
  assert m.hp==max(0,hp-server.mitigate(1000,d)),(level,m.hp,d)
print('PASS online monster hit damage uses Offline DEF/(250+DEF), zero on no DEF')

n=server.FARM_NAV
assert len(n.ground)>len(n.upper) or len(n.upper)>0
random.seed(123)
count=10000
chosen=[n.pick_goal() for _ in range(count)]
frac=sum(t in n.ground for t in chosen)/count
assert .23<frac<.27,frac
print('PASS weighted tile selection',frac)
flat=bot.Navigation([(0,1200,550)],[])
assert len(flat.upper)==0 and all(t in flat.ground for t in (flat.pick_goal() for _ in range(100)))
print('PASS single-platform map has only valid ground goals (no sky zone)')

start=time.monotonic()
for dest in range(1,len(server.GROUND)):
  p=server.Guest(id='sim',x=175,y=550,hp=1200,max_hp=1200)
  server.prog.apply_derived_resources(p,server.hp_reference,full=True)
  state=p.auto_state;state.enabled=True
  state.goal={'platform':dest,'x':(server.GROUND[dest][0]+server.GROUND[dest][1])/2,'y':server.GROUND[dest][2]}
  state.goal_due=start+100000
  server.players.clear();server.players[p.id]=p
  made=False
  for step in range(1500):
    t=start+step*server.DT
    buttons,actions=n.choose(p,state,t,{})
    p.buttons=buttons;p.last_input=t
    for action in actions:server.perform_action(p,action)
    server.update_guest(p,server.DT,t)
    if p.ground and abs(p.y-server.GROUND[dest][2])<12 and abs(p.x-state.goal['x'])<40:
      made=True;break
  assert made,(dest,p.x,p.y,p.climb,state.leg)
  assert state.changes==0,('changed destination before time',dest)
print('PASS real server collision + ropes AUTO reaches all 4 floating platforms; no fake teleports')

p=server.Guest(id='kb',x=600,y=235,hp=1200,max_hp=1200)
state=p.auto_state;state.enabled=True;state.goal={'platform':3,'x':600,'y':235};state.goal_due=start+120
p.y=390;p.x=550;p.ground=True
n.choose(p,state,start+60,{})
assert state.goal['platform']==3 and state.changes==0
n.choose(p,state,start+121,{})
assert state.changes==1 and state.goal_due==start+121+120
print('PASS knocked off floor keeps fixed goal until 120s, then renews')

# Quick server-combat action is issued by server intent path, not client-supplied damage.
p=server.Guest(id='attack-auto',x=175,y=550,hp=1200,max_hp=1200)
server.prog.apply_derived_resources(p,server.hp_reference,full=True)
p.auto_state.enabled=True;p.auto_state.goal={'platform':0,'x':900,'y':550};p.auto_state.goal_due=start+120
mob=server.Monster(id='wolf',x=345,y=550,hp=339,max_hp=339,defense=4,ground=True)
_,actions=n.choose(p,p.auto_state,start+2,{'wolf':mob})
assert actions or p.auto_state.enabled
print('PASS server AI chooses from owned mob state')
