"""Unit checks for server AUTO behavior, not dependent on browser timers."""
import time
import server

def test_auto_movement_despite_idle_timeout():
    server.monsters.clear(); server.players.clear(); server.shots.clear(); server.events.clear()
    server.spawn_mobs()
    p=server.Guest(id='auto1',x=40,y=550,hp=1200,max_hp=1200,ws=object(),auto_mode=True)
    p.last_input=time.monotonic()-30
    server.players[p.id]=p
    server.server_auto_step(p)
    assert p.buttons==2,(p.buttons,'auto should walk right')
    server.update_guest(p,server.DT,time.monotonic())
    assert p.x>40,(p.x,'auto did not move when idle')

def test_pve_only_shots_cannot_damage_other_players():
    server.monsters.clear(); server.players.clear(); server.shots.clear(); server.events.clear()
    p=server.Guest(id='auto1',x=120,y=550,hp=1200,max_hp=1200,ws=object(),auto_mode=True)
    peer=server.Guest(id='peer',x=200,y=550,hp=1200,max_hp=1200,ws=object())
    server.players.update({p.id:p,peer.id:peer})
    p.face=1
    server.perform_action(p,'attack',automated=True)
    assert server.shots and server.shots[0].pve_only
    for _ in range(6):server.update_shots(server.DT)
    assert peer.hp==1200,(peer.hp,'AUTO damaged another guest')

if __name__=='__main__':
 test_auto_movement_despite_idle_timeout();test_pve_only_shots_cannot_damage_other_players()
 print('AUTO UNIT TESTS PASSED: background tick movement, PvE-only shot filtering')
