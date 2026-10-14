"""Compare online Python EXP / base HP / skill damage math with actual JS Offline code."""
import json,subprocess,time,sys,math
from pathlib import Path
import combat_progression_v80bs as prog
import server
ROOT=Path(__file__).resolve().parent
JS=ROOT/'golden_offline'/'tests'/'offline_vectors_v80bs.js'

def run():
    output=subprocess.check_output(['node',str(JS)],text=True)
    vectors=json.loads(output)
    for row in vectors['exp']:
        assert prog.exp_for_kill(row['mob'],row['level'])==row['amount'],row
    for row in vectors['hp']:
        assert prog.base_hp_for_level(row['level'],server.hp_reference)==row['baseHp'],row
    for row in vectors['skills']:
        p=server.Guest('fixture',175,550,1200,1200,level=row['level'])
        p.stats['int']=row['int'];p.skill_ranks[row['kind']]=row['rank'];p.skill_ranks['mastery']=row['master']
        mn,mx=prog.preview_skill(p,row['kind'],server.hp_reference)
        assert (mn,mx)==(row['min'],row['max']),(row,(mn,mx))
    print('PASS cross-language golden cases',len(vectors['exp']),'EXP',len(vectors['hp']),'HP',len(vectors['skills']),'skill MIN/MAX')
    p=server.Guest('player',175,550,1200,1200,level=1)
    prog.apply_derived_resources(p,server.hp_reference,full=True)
    needed=prog.exp_to_next(1)
    while p.level==1:prog.grant_kill_exp(p,5)
    assert p.level==2 and p.stat_points==3 and p.skill_points==1 and p.exp==((needed+44)//45)*45-needed
    assert prog.allocate_stat(p,'vit',3,server.hp_reference)
    assert p.max_hp==server.hp_reference(2)['max_hp']+30 and p.stat_points==0
    assert not prog.allocate_stat(p,'int',1,server.hp_reference)
    assert prog.upgrade_skill(p,'mastery',1) and not prog.upgrade_skill(p,'mastery',1)
    old=prog.preview_skill(p,'attack',server.hp_reference)
    assert old[0]>math.ceil(old[1]*.6)
    print('PASS server-owned kill EXP, leveling, stat/skill point checks, VIT HP and Mastery')
    server.players.clear();server.monsters.clear();server.loot_drops.clear();server.spawn_mobs()
    victim=next(iter(server.monsters.values()))
    owner=server.Guest('owner',victim.x,victim.y,1200,1200)
    other=server.Guest('other',victim.x,victim.y,1200,1200)
    server.players['owner']=owner;server.players['other']=other
    shot=server.Shot(300,'owner','attack',victim.x,victim.y-80,520,999,1,1)
    server.hit_by_shot(shot,victim,999,True)
    assert victim.dead>0 and len(server.loot_drops)==1 and owner.total_kills==1 and other.total_kills==0
    drop=server.loot_drops[0]
    assert drop['ownerId']=='owner' and drop['item_id'] in {item['item_id'] for item in server.LOOT_TEMPLATES}
    drop['pickupAt']=time.monotonic()-1
    server.advance_loot()
    assert len(owner.inventory)==1 and len(other.inventory)==0 and not server.loot_drops
    # Protected loot remains private even if the owner is absent.
    server.spawn_loot_for(owner,victim)
    drop=server.loot_drops[-1];drop['pickupAt']=time.monotonic()-1
    server.players.pop('owner')
    server.advance_loot()
    assert len(other.inventory)==0 and len(server.loot_drops)==1
    drop['privateUntil']=time.monotonic()-1
    server.advance_loot()
    assert len(other.inventory)==1 and not server.loot_drops
    # Repeat hit cannot issue a second item or EXP for a dead target.
    server.hit_by_shot(shot,victim,999,True)
    assert len(owner.inventory)==1 and len(other.inventory)==1
    print('PASS authoritative loot ownership, protection window, pickup, one kill reward')
    server.players.clear();server.monsters.clear();server.shots.clear();server.events.clear();server.loot_drops.clear()

if __name__=='__main__':run()
