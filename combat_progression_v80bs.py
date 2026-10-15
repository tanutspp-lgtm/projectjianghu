"""Authoritative online progression + basic flute formula v8.0BS.
Reference: offline_progression.js, exp_balance_v1.js, player_hp_balance_v80bn.js,
index.html derivedStats/fireSkill, skill_mastery_v1.js. No account persistence yet.
"""
import json, math, random
import sandbox_loadouts_v80bt as loadouts
from pathlib import Path
from urllib.request import Request, urlopen

STAT_KEYS=('str','agi','vit','dex','int')
SKILL_RANK_CAP={'attack':1,'aoe':9,'break':9,'mastery':10}
SKILL_BASE={'attack':165,'aoe':135,'break':45}
SKILL_STEP={'attack':0,'aoe':.035,'break':.02}
SKILL_SP={'attack':0,'aoe':16,'break':12}

# Same JS Math.round for positive values, no Python bankers-round discrepancy.
def jsround(v):return int(math.floor(v+0.5))

def _validate_balance(b):
    if b.get('balance_version')!='exp_v1' or b.get('max_character_level')!=60: raise ValueError('EXP version mismatch')
    if len(b.get('exp_to_next_level',[]))!=60 or len(b.get('monster_base_exp',[]))!=60 or len(b.get('gap_rules',[]))!=7: raise ValueError('incomplete EXP balance')
    if b['exp_to_next_level'][-1]!=0 or any(type(x)!=int or x<=0 for x in b['exp_to_next_level'][:-1]):raise ValueError('bad EXP thresholds')
    if any(type(x)!=int or x<0 for x in b['monster_base_exp']):raise ValueError('bad monster EXP')
    gaps=sorted(b['gap_rules'], key=lambda r:r['min_delta'])
    assert gaps[0]['min_delta']<=-59 and gaps[-1]['max_delta']>=59
    for a,z in zip(gaps,gaps[1:]):
        if a['max_delta']+1!=z['min_delta']:raise ValueError('gaps must cover every delta')
        if not 0<=float(a['multiplier'])<=1:raise ValueError('bad multiplier')
    if not 0<=float(gaps[-1]['multiplier'])<=1:raise ValueError('bad multiplier')
    if float(b['overlevel_mob_exp_cap_ratio'])<1:raise ValueError('bad cap ratio')
    return b

LOCAL_EXP=_validate_balance(json.loads(Path(__file__).with_name('exp_balance_v1.json').read_text(encoding='utf-8')))
EXP_BALANCE=LOCAL_EXP
EXP_SOURCE='packaged-exp_v1'

def load_exp_balance(base_url, publishable_key, timeout=4):
    """Read existing read-only tables; never create or overwrite Supabase XP."""
    global EXP_BALANCE,EXP_SOURCE
    EXP_BALANCE=LOCAL_EXP; EXP_SOURCE='packaged-exp_v1'
    if not base_url or not publishable_key:return False
    def rows(table):
        u=f'{base_url.rstrip("/")}/rest/v1/{table}?select=*&limit=1000'
        with urlopen(Request(u, headers={'apikey':publishable_key,'Accept':'application/json'}),timeout=timeout) as response:
            out=json.load(response)
        if not isinstance(out,list):raise ValueError('REST response not a list')
        return out
    try:
        versions=[x for x in rows('game_balance_versions') if x.get('balance_version')=='exp_v1' and x.get('is_active') is True]
        if len(versions)!=1:raise ValueError('exp_v1 not active')
        levels=[x for x in rows('character_level_exp') if x.get('balance_version')=='exp_v1']
        mobs=[x for x in rows('monster_level_base_exp') if x.get('balance_version')=='exp_v1']
        gaps=[x for x in rows('exp_level_gap_rules') if x.get('balance_version')=='exp_v1']
        if len(levels)!=60 or len(mobs)!=60 or len(gaps)!=7:raise ValueError('missing EXP records')
        bylev={int(x['level']):int(x['exp_to_next_level']) for x in levels}
        bymob={int(x['monster_level']):int(x['base_exp']) for x in mobs}
        if set(bylev)!=set(range(1,61)) or set(bymob)!=set(range(1,61)):raise ValueError('duplicate/missing levels')
        fresh={'balance_version':'exp_v1','max_character_level':60,
               'exp_to_next_level':[bylev[i] for i in range(1,61)],
               'monster_base_exp':[bymob[i] for i in range(1,61)],
               'gap_rules':[{'min_delta':int(x['min_delta']),'max_delta':int(x['max_delta']),'multiplier':float(x['exp_multiplier'])} for x in gaps],
               'overlevel_mob_exp_cap_ratio':float(versions[0]['overlevel_mob_exp_cap_ratio'])}
        EXP_BALANCE=_validate_balance(fresh);EXP_SOURCE='supabase-exp_v1'
        return True
    except Exception as exc:
        EXP_SOURCE='packaged-exp_v1 (REST '+type(exc).__name__+')'
        return False

def exp_to_next(level):return EXP_BALANCE['exp_to_next_level'][level-1]

def exp_for_kill(monster_level,character_level):
    if not all(isinstance(v,int) and 1<=v<=60 for v in (monster_level,character_level)) or character_level>=60:return 0
    b=EXP_BALANCE; delta=monster_level-character_level
    r=next((rule for rule in b['gap_rules'] if rule['min_delta']<=delta<=rule['max_delta']),None)
    if r is None:raise ValueError('missing EXP gap rule')
    base=b['monster_base_exp'][monster_level-1]*float(r['multiplier'])
    if delta>0:base=min(base,b['monster_base_exp'][character_level-1]*float(b['overlevel_mob_exp_cap_ratio']))
    return max(0,math.floor(base))

def grant_kill_exp(p,monster_level):
    p.total_kills+=1
    award=exp_for_kill(monster_level,p.level)
    remaining=award; gained_levels=0
    while remaining>0 and p.level<60:
        needed=exp_to_next(p.level)-p.exp
        if remaining<needed:p.exp+=remaining;remaining=0
        else:
            remaining-=needed;p.level+=1;p.exp=0;gained_levels+=1
            p.stat_points+=3;p.skill_points+=1
    if p.level==60:p.exp=0
    return award,gained_levels

def base_hp_for_level(level,hp_reference):
    v=hp_reference(level)
    return int(v['max_hp'])-int(v['gear_hp'])

def derive_stats(p,hp_reference):
    """Shared Offline sandbox formula for inner arts + six-piece trial gear.
    XP level remains real; effectiveLevel is a GUEST QA simulation only.
    """
    q=loadouts.qi_totals(p)
    gear=loadouts.gear_totals(p)
    level=loadouts.effective_level(p)
    str_=p.stats['str']+q['str'];agi=p.stats['agi']+q['agi'];vit=p.stats['vit']+q['vit']
    dex=p.stats['dex']+q['dex'];int_=p.stats['int']+q['int']
    hp=base_hp_for_level(level,hp_reference)+vit*10+q['maxHp']+gear['maxHp']
    sp=100+int_*3+q['maxSp']+gear['maxSp'];sta=100+str_+q['maxSta']
    flee=agi*1.3+q['flee']
    return dict(maxHp=hp,maxSp=sp,maxSta=sta,
                hpRegenPerSec=hp*.05*(1+vit*.005)/10,
                spRegenPerSec=sp*.10*(1+int_*.005)/10,
                staRegenPerSec=20*(1+str_*.005),
                meleeDamageBonus=str_+q['physicalAttack']+2*(level-1),
                rangedDamageBonus=dex+q['rangedAttack']+2*(level-1),
                magicDamageBonus=int_+q['magicAttack']+2*(level-1),
                hit=dex+q['hit'],flee=flee,critRate=5+dex//3+q['critRate'],
                dodgeVsMonsters=max(0,min(30,(flee-30)*.5)),
                controlResistPct=min(50,vit*.25+q['controlResistPct']),
                moveSpeedMultiplier=1+agi*.002+q['moveSpeedPct']/100,
                healPowerBonus=int_*6,
                defense=gear['defense'],weaponAttack=gear['attack'],
                critDamageMultiplier=1.5+q['critDamagePct']/100,
                qiBonus=q,effectiveStats=dict(str=str_,agi=agi,vit=vit,dex=dex,int=int_),
                effectiveLevel=level)

def apply_derived_resources(p,hp_reference,full=False):
    d=derive_stats(p,hp_reference)
    previous_max=p.max_hp
    p.defense=d['defense']
    p.max_hp=d['maxHp'];p.max_sp=d['maxSp'];p.max_sta=d['maxSta']
    if full:p.hp=p.max_hp;p.sp=p.max_sp;p.sta=p.max_sta
    else:
        p.hp=min(p.max_hp,p.hp)
        p.sp=min(p.max_sp,p.sp)
        p.sta=min(p.max_sta,p.sta)
    return d

def allocate_stat(p,name,amount,hp_reference):
    if name not in STAT_KEYS or type(amount)!=int or not 1<=amount<=10:return False
    if p.stats[name]+amount>100 or p.stat_points<amount:return False
    p.stats[name]+=amount;p.stat_points-=amount
    # Offline applyDerivedPlayerStats(false) clamps HP rather than healing from added VIT.
    apply_derived_resources(p,hp_reference)
    return True

def upgrade_skill(p,skill,amount):
    if skill not in ('mastery','aoe','break') or type(amount)!=int or not 1<=amount<=10:return False
    if p.skill_points<amount or p.skill_ranks[skill]+amount>SKILL_RANK_CAP[skill]:return False
    p.skill_ranks[skill]+=amount;p.skill_points-=amount
    return True

def preview_skill(p,kind,hp_reference,derived=None):
    if kind not in SKILL_BASE:return None
    d=derive_stats(p,hp_reference) if derived is None else derived
    stat=d['magicDamageBonus']
    stat_bonus=jsround(stat*.55) if kind=='break' else stat-12 if kind=='aoe' else stat
    rank=p.skill_ranks[kind]
    mx=max(1,jsround((SKILL_BASE[kind]+stat_bonus+d['weaponAttack'])*(1+(rank-1)*SKILL_STEP[kind])))
    mastery_pct=60+3*p.skill_ranks['mastery']
    mn=min(mx,max(1,math.ceil(mx*mastery_pct/100)))
    return mn,mx

def roll_attack(p,kind,hp_reference,rng=random):
    # v8.0CP: derive once per cast, not once for range + crit + crit damage.
    # Preserve RNG calls, range calculation and all authoritative combat formulas.
    if kind not in SKILL_BASE:return None
    derived=derive_stats(p,hp_reference)
    r=preview_skill(p,kind,hp_reference,derived=derived)
    base=rng.randint(*r)
    crit=rng.random()*100<derived['critRate']
    return (jsround(base*derived['critDamageMultiplier']) if crit else base),crit
