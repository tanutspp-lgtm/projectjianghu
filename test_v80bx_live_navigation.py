"""BX directed rope travel, attack-facing stability and browser regression coordination."""
import math,time
import server
N=server.FARM_NAV
saved_players=server.players.copy();server.players.clear()
start=time.monotonic()
for src in range(len(server.GROUND)):
 for dst in range(len(server.GROUND)):
  if src==dst:continue
  slo,shi,sy=server.GROUND[src]
  lo,hi,y=server.GROUND[dst]
  p=server.Guest(id=f'{src}-{dst}',x=(slo+shi)/2,y=sy,hp=1500,max_hp=1500)
  server.prog.apply_derived_resources(p,server.hp_reference,full=True)
  state=p.auto_state;state.enabled=True;state.goal={'platform':dst,'x':(lo+hi)/2,'y':y};state.goal_due=start+100000
  server.players[p.id]=p
  reached=False
  for k in range(2100):
   t=start+k*server.DT
   buttons,actions=N.choose(p,state,t,{})
   p.buttons=buttons;p.last_input=t
   for action in actions:server.perform_action(p,action)
   server.update_guest(p,server.DT,t)
   if p.ground and abs(p.y-y)<13 and abs(p.x-state.goal['x'])<40:
    reached=True;break
  del server.players[p.id]
  assert reached,(src,dst,k,p.x,p.y,p.climb,state.leg,state.unreachable)
  print(f'PASS platform {src}->{dst} in {k*server.DT:.1f}s')
server.players.update(saved_players)
# Face stability: close monster must not force any alternating movement, target held.
p=server.Guest(id='no-pingpong',x=500,y=550,hp=1000,max_hp=1000)
p.auto_state.enabled=True;p.auto_state.goal={'platform':0,'x':950,'y':550};p.auto_state.goal_due=start+1000
m=server.Monster(id='wolf',x=540,y=550,hp=339,max_hp=339,ground=True)
for i in range(120):
 b,a=N.choose(p,p.auto_state,start+i/30,{'wolf':m})
 assert b==0,(i,b,p.face)
 assert p.face==1,(i,p.face)
print('PASS 120 melee ticks: no alternate left/right movement')
