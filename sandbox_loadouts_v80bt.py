"""Server-owned Guest QA sandbox: mirror qi_test_system.js and gear_balance_v80bn.js.
Not real ownership, NOT persistent gear. Do not use on ranked/account servers.
"""
import json
from pathlib import Path

CAT=json.loads(Path(__file__).with_name('EQUIPMENT_BASE_STATS_117_V1.json').read_text('utf-8'))
ROWS={10:(2,5),20:(5,15),30:(8,30),40:(12,40)}
SLOTS=('head','top','bottom','wrist','shoes')
QI_IDS=('flute_echo','flute_sustain','death_mark')
QI_GATES=(20,40,60)


def make_preset(level,def_row=0,atk_row=5,enhancement=5):
    if level not in ROWS or any(type(v)!=int or not 0<=v<=1000 for v in (def_row,atk_row)) or type(enhancement)!=int or enhancement not in (0,5,7):return None
    row,required=ROWS[level]
    armor=[next((x for x in CAT['armor'] if x['row']==row and x['slot']==slot and x['source_type']=='MONSTER'),None) for slot in SLOTS]
    weapon=next((x for x in CAT['weapons'] if x['row']==row and x['kind']=='flute' and x['source_type']=='MONSTER'),None)
    if any(x is None for x in armor) or weapon is None:return None
    items=[];totals=dict(attack=0,defense=0,maxHp=0,maxSp=0)
    for entry in (*armor,weapon):
        is_weapon=entry is weapon
        base=entry['stats']
        attack=int(base.get('attack',0))+(min(enhancement,4)+min(max(enhancement-4,0),2)*2+(3 if enhancement>=7 else 0) if is_weapon else 0)+(2*atk_row if is_weapon else 0)
        defense=int(base.get('defense',0))+(min(enhancement,7) if not is_weapon else 0)+(2*def_row if not is_weapon else 0)
        hp=int(base.get('max_hp',0));sp=int(base.get('max_sp',0))
        for key,val in [('attack',attack),('defense',defense),('maxHp',hp),('maxSp',sp)]:totals[key]+=val
        items.append(dict(item_id=entry['item_id'],slot='weapon' if is_weapon else entry['slot'],attack=attack,defense=defense,maxHp=hp,maxSp=sp))
    return dict(level=level,requiredLevel=required,row=row,totals=totals,items=items,
                enhancement=enhancement,defRow=def_row,atkRow=atk_row)


def effective_level(p):return getattr(p,"test_level",None) if getattr(p,"test_level",None) is not None else p.level

def active_qi(p,index):
    return effective_level(p)>=QI_GATES[index] and getattr(p,"qi_equipped",[None,None,None])[index]==QI_IDS[index]

def rank(p,id):
    values=getattr(p,"qi_ranks",{}).get(id,{})
    return int(values.get('training',1)),int(values.get('enhance',0))

def qi_totals(p):
    b={k:0 for k in ('str','agi','vit','dex','int','maxHp','maxSp','maxSta','physicalAttack','rangedAttack','magicAttack','hit','flee','critRate','critDamagePct','moveSpeedPct','controlResistPct')}
    if active_qi(p,0):
        training,_=rank(p,'flute_echo');b['magicAttack']+=15+2*(training-1)
    if active_qi(p,1):
        training,_=rank(p,'flute_sustain');b['magicAttack']+=50+2*(training-1)
    if active_qi(p,2):
        _,enhance=rank(p,'death_mark');bonus=min(4,enhance)*2
        for k in ('magicAttack','physicalAttack','rangedAttack'):b[k]+=bonus
    return b

def gear_totals(p):
    if getattr(p,"gear_level",None) is None:return dict(attack=0,defense=0,maxHp=0,maxSp=0)
    return make_preset(p.gear_level,p.gear_def_row,p.gear_atk_row,p.gear_enhancement)['totals']

def qi_mechanics(p,id):
    t,e=rank(p,id)
    if id=='flute_echo':return dict(echoPct=20+15*(t-1)/19,echoRange=150,shield=({'hpPct':[0,5,6,7,8,10][e],'spPct':[0,20,25,30,35,40][e],'duration':30,'cooldown':120} if e else None))
    if id=='flute_sustain':return dict(healKills=[20,20,19,19,19,18,18,17,17,16,16,16,15,15,14,14,13,13,12,12][t-1],healPct=5,stunPct=[0,2,2.1,2.3,2.5,3][e],stunSeconds=1)
    if id=='death_mark':return dict(markHits=4,markMaxStacks=3,markExpireSeconds=5,explosionPct=60+60*(t-1)/19,explosionStunPct=30 if e==5 else 0,explosionStunSeconds=1)
    return {}

def apply_command(p,m):
    """Strict protocol: accept only selector IDs/ranks, NEVER HP/ATK/DEF/item instances."""
    t=m.get('t');keys=set(m)
    if t=='sandbox_level' and keys=={'t','level'}:
        lv=m['level']
        if lv is None or (type(lv)==int and 1<=lv<=60):p.test_level=lv;return True
    elif t=='gear_preset' and keys=={'t','level'}:
        lv=m['level']
        if type(lv)==int and lv in ROWS:p.gear_level=lv;p.test_level=lv;return True
    elif t=='gear_clear' and keys=={'t'}:
        p.gear_level=None;return True
    elif t=='gear_affix' and keys=={'t','name','value'}:
        if m['name'] in ('defRow','atkRow') and type(m['value'])==int and 0<=m['value']<=1000:
            setattr(p,'gear_def_row' if m['name']=='defRow' else 'gear_atk_row',m['value']);return True
    elif t=='gear_enhance' and keys=={'t','value'}:
        if type(m['value'])==int and m['value'] in (0,5,7):p.gear_enhancement=m['value'];return True
    elif t=='qi_equip' and keys=={'t','id','enabled'}:
        if type(m['enabled'])==bool and m['id'] in QI_IDS:
            i=QI_IDS.index(m['id'])
            if effective_level(p)<QI_GATES[i]:return False
            p.qi_equipped[i]=m['id'] if m['enabled'] else None;return True
    elif t=='qi_unequip' and keys=={'t','slot'}:
        i=m['slot']
        if type(i)==int and 0<=i<3 and p.qi_equipped[i]:p.qi_equipped[i]=None;return True
    elif t=='qi_rank' and keys=={'t','id','kind','value'}:
        id,kind,value=m['id'],m['kind'],m['value']
        if id in QI_IDS and kind in ('training','enhance') and type(value)==int and (1<=value<=20 if kind=='training' else 0<=value<=5):
            p.qi_ranks[id]={**p.qi_ranks.get(id,{}),kind:value};return True
    return False


def private_snapshot(p):
    return dict(testLevel=p.test_level,effectiveLevel=effective_level(p),qiEquipped=list(p.qi_equipped),qiRanks=p.qi_ranks,
                gear=dict(level=p.gear_level,defRow=p.gear_def_row,atkRow=p.gear_atk_row,enhancement=p.gear_enhancement),
                qiRuntime=dict(healKills=p.qi_heal_kills,shield=p.qi_shield,shieldReadyAt=p.qi_shield_cd))
