"""Offline JS authoritative sandbox parity + Guest tamper/security checks."""
import json,subprocess,sys,random,types,math
from pathlib import Path
import sandbox_loadouts_v80bt as gear
import combat_progression_v80bs as prog
import server
HERE=Path(__file__).resolve().parent
FRONT=HERE.parent/'jianghu_v80bt_front'


def js_run(script):
    r=subprocess.run(['node','-e',script],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)

if __name__=='__main__':
    gear_script='''
const catalog=require(%s), gear=require(%s);
let pairs=[];
for(const lv of [10,20,30,40])for(const ench of [0,5,7])for(const defRow of [0,3,17])for(const atkRow of [0,5,27]){
 const a=gear.makePreset(catalog,lv,defRow,atkRow,ench);
 pairs.push({lv,ench,defRow,atkRow,totals:a.totals,items:a.items.map(i=>({item_id:i.item_id,slot:i.slot,attack:i.attack,defense:i.defense,maxHp:i.maxHp,maxSp:i.maxSp}))});
}
console.log(JSON.stringify(pairs));
''' %(json.dumps(str(FRONT/'EQUIPMENT_BASE_STATS_117_V1.json')),json.dumps(str(FRONT/'gear_balance_v80bn.js')))
    arr=js_run(gear_script)
    for v in arr:
        s=gear.make_preset(v['lv'],v['defRow'],v['atkRow'],v['ench'])
        assert s['totals']==v['totals'],v
        assert s['items']==v['items'],v
    print('PASS',len(arr),'offline JS gear presets exactly match Python online')
    qi_script='''
const fs=require('fs'),vm=require('vm');global.window=global;
global.localStorage={getItem:()=>null,setItem:()=>{}};
global.JianghuOfflineProgressTools={getStatus:()=>({level:60})};
vm.runInThisContext(fs.readFileSync(%s,'utf8'));
vm.runInThisContext(fs.readFileSync(%s,'utf8'));
const q=global.JianghuQiPrototype;
let result=[];
for(const id of ['flute_echo','flute_sustain','death_mark'])for(const training of [1,5,12,20])for(const enhance of [0,1,3,5]){
  q.setRank(id,'training',training);q.setRank(id,'enhance',enhance);
  result.push({id,training,enhance,bonuses:q.snapshot().defs.find(d=>d.id===id).bonuses,mechanics:q.mechanics(id)});
}
console.log(JSON.stringify(result));
'''%(json.dumps(str(FRONT/'qi_catalog_v1.js')),json.dumps(str(FRONT/'qi_test_system.js')))
    from dataclasses import dataclass,field
    values=js_run(qi_script)
    for v in values:
        p=server.Guest(id='test',x=0,y=550,hp=1,max_hp=1,level=60)
        idx=gear.QI_IDS.index(v['id']);p.qi_equipped[idx]=v['id']
        p.qi_ranks[v['id']]={'training':v['training'],'enhance':v['enhance']}
        a=gear.qi_mechanics(p,v['id']);b=v['mechanics']
        for k in b:
            if isinstance(b[k],float):assert math.isclose(a[k],b[k],abs_tol=1e-10)
            else:assert a[k]==b[k],(v,k,a[k],b[k])
        bonuses=gear.qi_totals(p)
        for k,val in v['bonuses'].items():assert bonuses[k]==val,(v,k,bonuses[k],val)
    print('PASS',len(values),'offline Qi ranks, bonuses and mechanics match server')
    p=server.Guest(id='test',x=0,y=550,hp=1,max_hp=1,level=1)
    assert not gear.apply_command(p,{'t':'qi_equip','id':'flute_echo','enabled':True})
    assert gear.apply_command(p,{'t':'sandbox_level','level':60})
    assert gear.apply_command(p,{'t':'qi_equip','id':'flute_echo','enabled':True})
    assert gear.apply_command(p,{'t':'qi_rank','id':'flute_echo','kind':'training','value':20})
    assert gear.apply_command(p,{'t':'qi_rank','id':'flute_echo','kind':'enhance','value':5})
    assert gear.apply_command(p,{'t':'gear_preset','level':40})
    assert gear.apply_command(p,{'t':'gear_enhance','value':7})
    assert gear.apply_command(p,{'t':'gear_affix','name':'defRow','value':7})
    assert not gear.apply_command(p,{'t':'gear_affix','name':'defRow','value':10000})
    assert not gear.apply_command(p,{'t':'gear_preset','level':999})
    assert not gear.apply_command(p,{'t':'gear_preset','level':40,'hp':999999999})
    assert not gear.apply_command(p,{'t':'qi_equip','id':'flute_echo','enabled':True,'attack':9999})
    assert p.exp==0 and p.level==1 and p.stat_points==0 and p.inventory==[]
    d=prog.apply_derived_resources(p,server.hp_reference,full=True)
    assert p.defense==d['defense']==gear.gear_totals(p)['defense']
    assert d['magicDamageBonus']>100 and d['maxHp']>1000 and d['weaponAttack']>0
    print('PASS sandbox choices change server derived stats, do not mutate real EXP/ownership')
