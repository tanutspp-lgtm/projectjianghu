"""Owned Guest equipment, separate from the optional legacy balance sandbox.
Starter row1 NPC gear is granted equipped once per new Guest, with a starter-only
level waiver. Equip commands use owned UIDs only; no client stats or item grants.
"""
import json
from pathlib import Path

CAPACITY=100
SLOTS=('weapon','head','top','bottom','wrist','shoes','costume')
WEAPONS={'jian':'jian','tang':'dual_knives','flute':'flute','healer':'acupuncture'}
_cat=json.loads(Path(__file__).with_name('EQUIPMENT_BASE_STATS_117_V1.json').read_text('utf-8'))
CAT={x['item_id']:x for x in _cat['weapons']+_cat['armor']}

def slot(it):return it.get('slot') or ('weapon' if it['item_id'].startswith('WPN-') else None)
def profession(p):return p.avatar.split('_')[0] if p.avatar.split('_')[0] in WEAPONS else 'flute'
def init(p):
    if hasattr(p,'owned_equipment215'):return
    cls=profession(p);p.owned_equipment215={};p.equipment_revision215=0
    for sl in SLOTS:
        if sl=='costume':continue
        it=next((x for x in CAT.values() if x['row']==1 and x['source_type']=='NPC' and slot(x)==sl and (sl!='weapon' or x['kind']==WEAPONS[cls])),None)
        if it:p.owned_equipment215[sl]=dict(uid=f'starter215-{p.id}-{sl}',item_id=it['item_id'],starter=True)

def totals(p):
    revision=getattr(p,"equipment_revision215",0)
    if getattr(p,"gear_totals_revision219",-1)==revision:return p.gear_totals219
    t=dict(attack=0,defense=0,maxHp=0,maxSp=0)
    for rec in getattr(p,'owned_equipment215',{}).values():
        it=CAT.get(rec['item_id'])
        if not it or slot(it)=='costume':continue
        rank=max(0,min(10,rec.get('enhancement',0)))
        if slot(it)=='weapon':
            enhance={'attack':min(rank,4)+2*min(max(rank-4,0),2)+3*(rank>=7),'critRate':(0,2,5,10)[max(0,rank-7)]}
        else:
            enhance={'defense':min(rank,7),'hpPct':(0,1,2,5)[max(0,rank-7)]}
        rolled=rec.get('rolled')
        if rolled is None:
            rolled={}
            for affix in rec.get('affixes',[]):
                key=affix['type'];rolled[key]=rolled.get(key,0)+affix['value']
        aliases={'max_hp':'maxHp','max_sp':'maxSp','crit_rate':'critRate','crit_damage_pct':'critDamagePct'}
        for source in (it.get('stats',{}),rec.get('enhance',enhance),rolled):
            for key,n in source.items():
                if type(n) in (int,float) and n:
                    k=aliases.get(key,key);t[k]=t.get(k,0)+n
    p.gear_totals_revision219=revision;p.gear_totals219=t
    return t

def command(p,m):
    init(p)
    if m.get('t')=='item_equip' and set(m)=={'t','uid'} and type(m.get('uid')) is str:
        index=next((i for i,x in enumerate(p.inventory) if x['uid']==m['uid']),-1)
        if index<0:return False,'ไม่พบไอเท็มในกระเป๋า'
        rec=p.inventory[index];it=CAT.get(rec['item_id']);sl=slot(it) if it else None
        if sl not in SLOTS:return False,'ไอเท็มนี้สวมใส่ไม่ได้'
        if sl=='weapon' and it.get('kind')!=WEAPONS[profession(p)]:return False,'อาวุธไม่ตรงอาชีพ'
        required=it.get('requirements',{}).get('level',it.get('required_level',it.get('level',1)))
        if p.level<required and not (rec.get('starter') is True and it['row']==1 and it['source_type']=='NPC'):return False,'ต้องการ Lv.'+str(required)
        old=p.owned_equipment215.get(sl)
        p.inventory.pop(index)
        if old:p.inventory.append(old)
        p.owned_equipment215[sl]=rec
    elif m.get('t')=='item_unequip' and set(m)=={'t','slot'} and m.get('slot') in SLOTS:
        rec=p.owned_equipment215.get(m['slot'])
        if not rec:return False,'ช่องนี้ว่าง'
        if len(p.inventory)>=CAPACITY:return False,'กระเป๋าเต็ม 100/100'
        p.inventory.append(rec);del p.owned_equipment215[m['slot']]
    else:return False,'คำสั่งอุปกรณ์ไม่ถูกต้อง'
    p.inventory_revision+=1;p.equipment_revision215+=1
    return True,'สวมใส่แล้ว' if m['t']=='item_equip' else 'เก็บลงกระเป๋าแล้ว'

def snapshot(p):
    revision=getattr(p,'equipment_revision215',0)
    if getattr(p,'equipment_snapshot_revision215',-1)!=revision:
        p.equipment_snapshot_revision215=revision
        p.equipment_snapshot215={k:dict(v) for k,v in getattr(p,'owned_equipment215',{}).items()}
    return dict(equipped215=p.equipment_snapshot215,equipmentRevision215=revision,inventoryCapacity215=CAPACITY)
