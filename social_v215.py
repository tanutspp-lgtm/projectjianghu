"""Session-owned Guest social data and routed chat. No account persistence claim.
Invites require recipient acceptance; roster/caps are resolved here, not by UI.
"""
import secrets
import time
from collections import deque

class Hub:
    PARTY_CAP=6;GUILD_CAP=24;FRIEND_CAP=50
    def __init__(self):
        self.people={};self.parties={};self.guilds={};self.invites={};self.counter=0
    def join(self,p,name):
        if p.id in self.people:self.people[p.id].update(actor=p,online=True);return
        # Bounded Guest-only process registry. Preserve friends' saved names when an
        # old disconnected actor is retired; no account identity is inferred.
        if len(self.people)>=4096:
            oldest=next((k for k,v in self.people.items() if not v['online'] and not v.get('party') and not v.get('guild')),None)
            if oldest:self.people.pop(oldest)
        self.people[p.id]=dict(actor=p,name=name,online=True,friends={},party=None,guild=None)
    def leave(self,p):
        if p.id in self.people:self.people[p.id]['online']=False
    def brief(self,id,fallback='ผู้เล่น'):
        s=self.people.get(id)
        if not s:return dict(id=id,name=fallback,online=False,level=None)
        return dict(id=id,name=s['name'],online=s['online'],level=s['actor'].level,profession=s['actor'].avatar.split('_')[0])
    def group(self,id,kind):
        s=self.people.get(id,{});g=(self.parties if kind=='party' else self.guilds).get(s.get(kind))
        if not g:return None
        return dict(id=s[kind],name=g['name'],leader=g['leader'],members=[self.brief(x) for x in g['members']],capacity=self.PARTY_CAP if kind=='party' else self.GUILD_CAP)
    def snapshot(self,p):
        self.expire();s=self.people[p.id]
        return dict(t='hud_social_state',self=self.brief(p.id),party=self.group(p.id,'party'),guild=self.group(p.id,'guild'),friends=[self.brief(x,name) for x,name in s['friends'].items()],friendCapacity=self.FRIEND_CAP,invites=[dict(id=k,kind=v['kind'],fromPlayer=self.brief(v['from']),name=v['name']) for k,v in self.invites.items() if v['to']==p.id])
    def expire(self):
        now=time.monotonic()
        for k in [k for k,v in self.invites.items() if v['until']<now]:self.invites.pop(k,None)
    def find(self,query):
        q=query.strip().casefold()
        if not q:return[]
        return [self.brief(k) for k,s in self.people.items() if s['online'] and (q in s['name'].casefold() or q==k.casefold())][:20]
    def command(self,p,m):
        self.expire();s=self.people[p.id];action=m.get('action')
        shapes={'view':set(),'search':{'query'},'add_friend':{'target'},'remove_friend':{'target'},'invite_party':{'target'},'invite_guild':{'target'},'accept_invite':{'invite'},'decline_invite':{'invite'},'leave_party':set(),'leave_guild':set(),'create_guild':{'name'}}
        if type(action) is not str or action not in shapes or set(m)!={'t','action'}|shapes[action]:return False,'คำสั่งไม่ถูกต้อง',None
        if action=='view':return True,'',None
        if action=='search':
            if type(m['query']) is not str or len(m['query'])>40:return False,'ชื่อยาวเกินไป',None
            return True,'',dict(results=self.find(m['query']))
        if action in ('add_friend','remove_friend','invite_party','invite_guild'):
            target=m['target']
            if type(target) is not str or len(target)>80:return False,'ไม่พบผู้เล่น',None
            if action=='remove_friend':s['friends'].pop(target,None);return True,'ลบเพื่อนแล้ว',None
            if target==p.id:return False,'เลือกผู้เล่นคนอื่น',None
            other=self.people.get(target)
            if not other:return False,'ไม่พบผู้เล่น',None
            if action=='add_friend':
                if target in s['friends']:return False,'อยู่ในรายชื่อเพื่อนแล้ว',None
                if len(s['friends'])>=self.FRIEND_CAP:return False,'เพื่อนเต็ม 50 คน',None
                s['friends'][target]=other['name'];return True,'เพิ่มเพื่อนแล้ว',None
            if not other['online']:return False,'ผู้เล่นออฟไลน์',None
            kind='party' if action=='invite_party' else 'guild';groups=self.parties if kind=='party' else self.guilds;cap=self.PARTY_CAP if kind=='party' else self.GUILD_CAP
            if other[kind]:return False,'ผู้เล่นอยู่ในกลุ่มแล้ว',None
            gid=s[kind]
            if kind=='party' and not gid:
                gid='party-'+secrets.token_hex(5);s[kind]=gid;groups[gid]=dict(name='ปาร์ตี้ของ '+s['name'],leader=p.id,members=[p.id]);p.party_id=gid
            g=groups.get(gid)
            if not g:return False,'สร้างกิลด์ก่อนเชิญ',None
            if g['leader']!=p.id:return False,'หัวหน้ากลุ่มเป็นผู้เชิญ',None
            if len(g['members'])>=cap:return False,'กลุ่มเต็ม '+str(cap)+' คน',None
            if any(v['to']==target and v['group']==gid for v in self.invites.values()):return False,'ส่งคำเชิญแล้ว',None
            if sum(v['to']==target for v in self.invites.values())>=12:return False,'คำเชิญผู้เล่นเต็ม',None
            invite=secrets.token_hex(8);self.invites[invite]=dict(kind=kind,group=gid,to=target,**{'from':p.id},name=g['name'],until=time.monotonic()+120)
            return True,'ส่งคำเชิญแล้ว',None
        if action in ('accept_invite','decline_invite'):
            if type(m['invite']) is not str:return False,'คำเชิญไม่ถูกต้อง',None
            v=self.invites.get(m['invite'])
            if not v or v['to']!=p.id:return False,'คำเชิญหมดอายุแล้ว',None
            if action=='decline_invite':self.invites.pop(m['invite']);return True,'ปฏิเสธคำเชิญแล้ว',None
            kind=v['kind'];groups=self.parties if kind=='party' else self.guilds;g=groups.get(v['group']);cap=self.PARTY_CAP if kind=='party' else self.GUILD_CAP
            if s[kind]:return False,'อยู่ในกลุ่มแล้ว',None
            if not g or len(g['members'])>=cap:return False,'กลุ่มเต็มหรือปิดแล้ว',None
            s[kind]=v['group'];g['members'].append(p.id)
            if kind=='party':p.party_id=v['group']
            self.invites.pop(m['invite']);return True,'เข้าร่วมแล้ว',None
        if action.startswith('leave_'):
            kind=action[6:];groups=self.parties if kind=='party' else self.guilds;gid=s[kind];g=groups.get(gid)
            s[kind]=None
            if kind=='party':p.party_id=None
            if g:
                g['members']=[id for id in g['members'] if id!=p.id]
                if not g['members']:groups.pop(gid)
                elif g['leader']==p.id:g['leader']=g['members'][0]
            return True,'ออกจากกลุ่มแล้ว',None
        if action=='create_guild':
            if type(m['name']) is not str or not 1<=len(m['name'].strip())<=24 or any(ord(c)<32 for c in m['name']):return False,'ชื่อกิลด์ 1–24 ตัวอักษร',None
            if s['guild']:return False,'อยู่ในกิลด์แล้ว',None
            name=m['name'].strip()
            if any(x['name'].casefold()==name.casefold() for x in self.guilds.values()):return False,'ชื่อกิลด์ถูกใช้แล้ว',None
            gid='guild-'+secrets.token_hex(5);s['guild']=gid;self.guilds[gid]=dict(name=name,leader=p.id,members=[p.id]);return True,'สร้างกิลด์แล้ว',None
        return False,'คำสั่งไม่ถูกต้อง',None
    def chat(self,p,m):
        if set(m) not in ({'t','channel','text'},{'t','channel','text','target'}):return False,'ข้อความไม่ถูกต้อง',[],None
        channel=m.get('channel');text=m.get('text');s=self.people[p.id]
        if channel not in ('all','world','party','guild','whisper') or type(text) is not str or not text.strip() or len(text)>160 or any(ord(c)<32 for c in text):return False,'ข้อความ 1–160 ตัวอักษร',[],None
        if channel=='whisper':
            target=m.get('target');other=self.people.get(target) if type(target) is str else None
            if not other or not other['online'] or target==p.id:return False,'ผู้รับไม่ออนไลน์',[],None
            recipients=[p.id,target]
        elif channel in ('party','guild'):
            g=self.group(p.id,channel)
            if not g:return False,'ยังไม่มีกลุ่มในช่องนี้',[],None
            recipients=[x['id'] for x in g['members'] if x['online']]
        elif channel=='all':recipients=[k for k,v in self.people.items() if v['online'] and v['actor'].room==p.room and v['actor'].channel==p.channel]
        else:recipients=[k for k,v in self.people.items() if v['online']]
        self.counter+=1
        message=dict(t='hud_chat',id=self.counter,channel=channel,senderId=p.id,name=s['name'],text=text.strip(),target=m.get('target') if channel=='whisper' else None,targetName=self.people[m['target']]['name'] if channel=='whisper' else None,time=int(time.time()*1000))
        return True,'',recipients,message
