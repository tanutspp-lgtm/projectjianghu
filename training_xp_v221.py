"""Training receives one award per eligible kill. Only the active skill page earns experience."""
from character_classes_v181 import profession

SETS={'jian':('jian.water_return',),'tang':('tang.moon_shadow',),
      'flute':('flute.spring_harmony',),'healer':('healer.jade_life',)}

def advance(level,xp,cap,amount):
    if amount<=0 or level>=cap:return level,xp
    need=round(100*level**1.6)
    if xp+amount<need:return level,xp+amount
    level+=1
    return level,0 if level==cap else min(xp+amount-need,round(100*level**1.6)*99//100)

def configure(p,pages,bank):
    allowed=SETS[profession(p.avatar)]
    if type(pages) is not list or len(pages)!=2 or any(s not in allowed for s in pages) or type(bank) is not int or bank not in (0,1):return False
    p.training_pages=tuple(pages)
    p.training_bank=bank
    return True

def award(p,amount,gates):
    if not amount:return
    allowed=SETS[profession(getattr(p,'avatar',None))]
    if not hasattr(p,'trained_sets'):p.trained_sets={}
    pages=getattr(p,'training_pages',(allowed[0],allowed[0]))
    key=pages[getattr(p,"training_bank",0)]
    record=p.trained_sets.get(key,dict(level=1,xp=0,cap=10))
    level,xp=advance(record['level'],record['xp'],record['cap'],amount)
    if (level,xp)!=(record['level'],record['xp']):
        p.trained_sets={**p.trained_sets,key:{**record,'level':level,'xp':xp}}
    for i,key in enumerate(p.qi_equipped):
        if key and p.level>=gates[i]:
            record=p.qi_ranks.get(key,dict(training=1,enhance=0))
            level,xp=advance(record['training'],record.get('xp',0),20,amount)
            if (level,xp)!=(record['training'],record.get('xp',0)):
                p.qi_ranks={**p.qi_ranks,key:{**record,'training':level,'xp':xp}}
