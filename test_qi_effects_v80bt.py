from types import SimpleNamespace
import time,random
import server,sandbox_loadouts_v80bt as loadouts,combat_progression_v80bs as prog


def fixture():
    server.events.clear();server.loot_drops.clear();server.shots.clear();server.players.clear()
    p=server.Guest(id='qa',x=220,y=550,hp=2000,max_hp=2000,level=60)
    prog.apply_derived_resources(p,server.hp_reference,full=True)
    server.players[p.id]=p
    return p

p=fixture()
p.qi_equipped[0]='flute_echo'
p.qi_ranks['flute_echo']={'training':20,'enhance':5}
m1=server.Monster(id='t1',x=260,y=550,hp=800,max_hp=800)
m2=server.Monster(id='t2',x=290,y=550,hp=800,max_hp=800)
server.monsters.clear();server.monsters.update({'t1':m1,'t2':m2})
shot=SimpleNamespace(owner=p.id,kind='attack')
server.apply_qi_on_primary_hit(shot,m1,100)
assert m2.hp==765, m2.hp
assert any(e['t']=='hit' and e.get('kind')=='qi_echo' for e in server.events)
p.hp=int(p.max_hp*.3);p.sp=100
server.try_qi_shield(p)
assert p.qi_shield==round(p.max_hp*.10+100*.40)
shield=p.qi_shield
server.hurt(p,80,260,450,'monster')
assert p.qi_shield==shield-80 and p.hp==int(p.max_hp*.3)
print('PASS Qi echo secondary hit and HP<35% SP-based shield absorbs damage')

p=fixture();p.qi_equipped[2]='death_mark';p.qi_ranks['death_mark']={'training':20,'enhance':0}
m=server.Monster(id='t3',x=250,y=550,hp=3000,max_hp=3000)
shot=SimpleNamespace(owner=p.id,kind='attack')
for _ in range(4):server.apply_qi_on_primary_hit(shot,m,100)
assert m.hp==2880,(m.hp,m.mark_stacks)
assert any(e['t']=='hit' and e.get('kind')=='death_mark' for e in server.events)
assert m.mark_stacks[p.id][0]==0
print('PASS Death Mark fourth-hit explosion exactly 120% of hit')

p=fixture();p.qi_equipped[1]='flute_sustain';p.qi_ranks['flute_sustain']={'training':20,'enhance':5}
p.qi_heal_kills=11;p.hp=p.max_hp-1000
m=server.Monster(id='t4',x=260,y=550,hp=0,max_hp=450,dead=7,level=1,species='wolf')
server.grant_monster_kill(SimpleNamespace(owner=p.id),m)
assert p.qi_heal_kills==0
assert p.hp==p.max_hp-1000+prog.jsround(p.max_hp*.05)
assert any(e['t']=='heal' and e.get('victim')=='qa' for e in server.events)
print('PASS Qi sustain heals 5% MaxHP at training Lv20 after 12 kills')
