"""Server-owned Guest invitations, shared EXP, roster roles and rich chat."""
import math
import secrets
import time
import unicodedata
from collections import deque
from copy import deepcopy
from social_v215 import Hub as GuestHub
from owned_equipment_v215 import CAT

BONUS=(0,0,10,20,35,55,75)
MUTES=(1,3,10,30,60,120,240)
ROLES=('member','guardian','officer')
KINDS=('party','guild','friend')

class Hub(GuestHub):
    def join(self,p,name):
        super().join(p,name)
        s=self.people[p.id]
        s.setdefault('prefs',dict.fromkeys(KINDS,True))
        s.setdefault('rate',dict(recent=deque(maxlen=10),until=0,last=0,stage=0,attempts=0))
        s['seen']=int(time.time()*1000)

    def leave(self,p):
        super().leave(p)
        self.people[p.id]['seen']=int(time.time()*1000)
        # A disconnected Guest gets a new identity on their next login.
        g=self.parties.get(self.people[p.id]['party'])
        if g and g['leader']==p.id:
            successor=next((i for i in g['members'] if self.people[i]['online']),None)
            if successor:g['leader']=successor

    def brief(self,id,fallback='ผู้เล่น'):
        data=super().brief(id,fallback)
        s=self.people.get(id)
        if s:
            p=s['actor']
            data.update(room=p.room,channel=p.channel,lastSeen=s['seen'],auto=bool(getattr(getattr(p,'auto_state',None),'enabled',False)))
        return data

    def local(self,g,p):
        return [i for i in g['members'] if self.people[i]['online'] and self.people[i]['actor'].room==p.room and self.people[i]['actor'].channel==p.channel]

    def compatible(self,g):
        levels=[self.people[i]['actor'].level for i in g['members']]
        return max(levels)-min(levels)<=15

    def shared(self,g):
        if g.get('share',True) and not self.compatible(g):g['share']=False
        return g.get('share',True)

    def awards(self,p,base):
        g=self.parties.get(self.people.get(p.id,{}).get('party'))
        if not g or not self.shared(g):return [(p,base)]
        ids=self.local(g,p)
        if p.id not in ids:return [(p,base)]
        total=base*(100+BONUS[len(ids)])//100
        each,extra=divmod(total,len(ids));start=g.get('cursor',0)%len(ids)
        g['cursor']=(start+extra)%len(ids)
        return [(self.people[i]['actor'],each+int((n-start)%len(ids)<extra)) for n,i in enumerate(ids)]

    def party_vitals(self, member_id):
        gid = self.people.get(member_id, {}).get('party')
        party = self.parties.get(gid)
        if not party:
            return None
        now = time.monotonic()
        if now < party.get('vitals_until', 0):
            return party['vitals']
        members = {}
        for uid in party['members']:
            person = self.people[uid]
            if person['online']:
                actor = person['actor']
                members[uid] = dict(hp=math.ceil(actor.hp), maxHp=actor.max_hp,
                                    dead=actor.dead > 0, auto=bool(actor.auto_state.enabled))
        party['vitals'] = dict(id=gid, members=members)
        party['vitals_until'] = now + 0.5
        return party['vitals']

    def group(self,id,kind):
        data=super().group(id,kind)
        if not data:return None
        g=(self.parties if kind=='party' else self.guilds)[data['id']]
        if kind=='party':
            nearby=self.local(g,self.people[id]['actor']);share=self.shared(g)
            data.update(share=share,auto=g.get('auto',False),nearby=len(nearby),bonus=BONUS[len(nearby)] if share else 0,
                        requests=[self.brief(i) for i in g.get('requests',{}) if self.people[i]['online']] if id==g['leader'] else [])
        else:
            for m in data['members']:m['role']=self.role(g,m['id'])
            data.update(level=1,exp=g.get('exp',0),nextExp=1000)
        return data

    def related(self,id):
        if id not in self.people:return set()
        s=self.people[id];ids={id,*s['friends']}
        for kind,groups in [('guild',self.guilds),('party',self.parties)]:
            g=groups.get(s[kind])
            if g:ids.update(g['members'])
        return ids

    def snapshot(self,p):
        data=super().snapshot(p)
        for inv in data['invites']:inv['ttl']=max(0,int((self.invites[inv['id']]['until']-time.monotonic())*1000))
        data['prefs']=self.people[p.id]['prefs'].copy()
        return data

    @staticmethod
    def role(g,id):
        return 'leader' if id==g['leader'] else g.get('roles',{}).get(id,'member')

    def permitted(self,g,id,kind):
        return id==g['leader'] or (kind=='guild' and self.role(g,id) in ('officer','guardian'))

    def add_member(self,p,kind,gid,g):
        s=self.people[p.id]
        if s[kind]:return False,'อยู่ในกลุ่มแล้ว',None
        if len(g['members'])>=(6 if kind=='party' else 24):return False,'ปาร์ตี้เต็มอยู่ (6/6)' if kind=='party' else 'กิลด์เต็ม (24/24)',None
        g['members'].append(p.id);s[kind]=gid
        if kind=='party':
            p.party_id=gid
            for other in self.parties.values():other.get('requests',{}).pop(p.id,None)
            if not self.shared(g):return True,'เข้าปาร์ตี้แล้ว · ปิดแชร์ EXP',None
        return True,'เข้าร่วมแล้ว',None

    def command(self,p,m):
        self.expire();action=m.get('action')
        if not isinstance(action,str):return False,'คำสั่งไม่ถูกต้อง',None
        s=self.people[p.id];target=m.get('target');other=self.people.get(target) if isinstance(target,str) else None
        def fail(t):return False,t,None
        def ok(t=''):return True,t,None
        args=set(m)-{'t','action'}
        if action=='create_party' and not args:
            if s['party']:return fail('อยู่ในปาร์ตี้แล้ว')
            gid='party-'+secrets.token_hex(6);s['party']=gid;p.party_id=gid
            self.parties[gid]=dict(name='ปาร์ตี้ของ '+s['name'],leader=p.id,members=[p.id])
            return ok('สร้างปาร์ตี้แล้ว')
        if action=='party_kick' and args=={'target','group'}:
            gid=s['party']
            g=self.parties.get(gid)
            if not g or m['group']!=gid or g['leader']!=p.id:
                return fail('ต้องเป็นหัวหน้าปาร์ตี้นี้')
            if not other or target==p.id or other['party']!=gid or target not in g['members']:
                return fail('เลือกสมาชิกคนอื่นในปาร์ตี้')
            result=super().command(other['actor'],dict(t='hud_social',action='leave_party'))
            return ok('นำสมาชิกออกจากปาร์ตี้แล้ว') if result[0] else result
        if action=='leave_party' and not args:
            g=self.parties.get(s['party'])
            if g and g['leader']==p.id:
                online=next((i for i in g['members'] if i!=p.id and self.people[i]['online']),None)
                if online:g['leader']=online
        if action=='prefs'  and args=={'prefs'}:
            prefs=m['prefs']
            if not isinstance(prefs,dict) or set(prefs)!=set(KINDS) or any(type(v)!=bool for v in prefs.values()):return fail('ตั้งค่าไม่ถูกต้อง')
            s['prefs']=prefs.copy()
            self.invites={k:v for k,v in self.invites.items() if v['to']!=p.id or prefs[v['kind']]}
            return ok()
        if action in ('invite_party','invite_guild','add_friend') and args=={'target'}:
            kind={'invite_party':'party','invite_guild':'guild','add_friend':'friend'}[action]
            if not other or not other['online'] or target==p.id:return fail('ผู้เล่นไม่พร้อมรับคำชวน')
            if not other['prefs'][kind]:return fail('ผู้เล่นปิดรับคำชวนประเภทนี้')
            gid=s.get(kind)
            if kind=='friend':
                if target in s['friends'] or max(len(other['friends']),len(s['friends']))>=50:return fail('เป็นเพื่อนแล้วหรือรายชื่อเต็ม')
            else:
                if other[kind]:return fail('ผู้เล่นอยู่ในกลุ่มแล้ว')
                g=(self.parties if kind=='party' else self.guilds).get(gid)
                if g and (not self.permitted(g,p.id,kind) or len(g['members'])>=(6 if kind=='party' else 24)):return fail('กลุ่มเต็มหรือไม่มีสิทธิ์ชวน')
                if not g and kind=='guild':return fail('ยังไม่มีกิลด์')
            if sum(v['to']==target for v in self.invites.values())>=12 or any(v['to']==target and v['kind']==kind and v['from']==p.id for v in self.invites.values()):return fail('มีคำชวนรออยู่')
            self.invites[secrets.token_hex(8)]=dict(kind=kind,group=gid,to=target,name=(g['name'] if kind!='friend' and g else s['name']),until=time.monotonic()+10,**{'from':p.id})
            return ok('ส่งคำชวนแล้ว')
        if action=='accept_invite' and args=={'invite'}:
            v=self.invites.get(m['invite']) if isinstance(m['invite'],str) else None
            if not v or v['to']!=p.id:return fail('คำชวนหมดอายุแล้ว')
            self.invites.pop(m['invite']);kind=v['kind'];src=self.people[v['from']]
            if not s['prefs'][kind] or not src['online']:return fail('คำชวนหมดอายุแล้ว')
            if kind=='friend':
                if max(len(s['friends']),len(src['friends']))>=50:return fail('เพื่อนเต็ม 50 คน')
                s['friends'][v['from']]=src['name'];src['friends'][p.id]=s['name'];return ok('เพิ่มเพื่อนแล้ว')
            groups=self.parties if kind=='party' else self.guilds;gid=src[kind]
            if s[kind] or (v['group'] and v['group']!=gid):return fail('คำชวนหมดอายุแล้ว')
            if kind=='party' and not gid:
                gid='party-'+secrets.token_hex(6);src[kind]=gid;src['actor'].party_id=gid
                groups[gid]=dict(name='ปาร์ตี้ของ '+src['name'],leader=v['from'],members=[v['from']])
            g=groups.get(gid)
            if not g or not self.permitted(g,v['from'],kind):return fail('คำชวนหมดอายุแล้ว')
            return self.add_member(p,kind,gid,g)
        if action=='party_apply' and args=={'group'}:
            gid=m['group'];g=self.parties.get(gid) if isinstance(gid,str) else None
            if not g:return fail('ปาร์ตี้ยุบแล้ว')
            if len(g['members'])>=6:return fail('ปาร์ตี้เต็มอยู่ (6/6)')
            if s['party']:return fail('อยู่ในปาร์ตี้แล้ว')
            if g.get('auto') and abs(p.level-min(self.people[i]['actor'].level for i in g['members']))<=15:return self.add_member(p,'party',gid,g)
            requests=g.setdefault('requests',{})
            if p.id in requests:return fail('ส่งคำขอแล้ว')
            requests[p.id]=True;return ok('ส่งคำขอเข้าปาร์ตี้แล้ว')
        if action in ('party_setting','party_decide'):
            g=self.parties.get(s['party'])
            if not g or g['leader']!=p.id:return fail('ต้องเป็นหัวหน้าปาร์ตี้')
            if action=='party_setting' and args=={'key','enabled'} and m['key'] in ('share','auto') and type(m['enabled'])==bool:
                if m['key']=='share' and m['enabled'] and not self.compatible(g):return fail('แชร์ EXP ไม่ได้ · สมาชิกเลเวลห่างเกิน 15')
                g[m['key']]=m['enabled'];return ok('เปลี่ยนการตั้งค่าแล้ว')
            if action=='party_decide' and args=={'target','accept'} and type(m['accept'])==bool and other and g.get('requests',{}).pop(target,None):
                if not m['accept']:return ok('ปฏิเสธคำขอแล้ว')
                if not other['online']:return fail('ผู้เล่นออฟไลน์')
                return self.add_member(other['actor'],'party',s['party'],g)
            return fail('ไม่พบคำขอ')
        if action in ('guild_role','guild_kick','leave_guild'):
            g=self.guilds.get(s['guild'])
            if not g:return fail('ยังไม่มีกิลด์')
            if action=='leave_guild':
                if p.id==g['leader'] and len(g['members'])>1:
                    if args!={'target'} or not other or target==p.id or target not in g['members']:return fail('เลือกผู้สืบทอดก่อนออก')
                    g['leader']=target
                elif args:return fail('คำสั่งไม่ถูกต้อง')
                g.get('roles',{}).pop(p.id,None)
                return super().command(p,dict(t='hud_social',action='leave_guild'))
            if not other or target not in g['members'] or target in (p.id,g['leader']):return fail('เลือกสมาชิกคนอื่น')
            if action=='guild_role' and args=={'target','role'} and p.id==g['leader'] and m['role'] in ROLES:
                g.setdefault('roles',{})[target]=m['role'];return ok('แต่งตั้งแล้ว')
            if action=='guild_kick' and args=={'target'} and (p.id==g['leader'] or self.role(g,p.id)=='officer' and self.role(g,target)=='member'):
                g['members'].remove(target);g.get('roles',{}).pop(target,None);other['guild']=None;return ok('ขับออกแล้ว')
            return fail('ไม่มีสิทธิ์')
        if action=='remove_friend' and args=={'target'} and other:other['friends'].pop(p.id,None)
        if action not in ('view','search','remove_friend','decline_invite','leave_party','create_guild'):return fail('คำสั่งไม่ถูกต้อง')
        return super().command(p,m)

    def chat(self,p,m):
        payload=m.copy();attachments=payload.pop('links',[]);s=self.people[p.id]
        error=lambda msg:(False,msg,[],None)
        r=s['rate'];now=time.monotonic()
        if now<r['until']:
            if now-r['last']>=1:
                r['last']=now;r['attempts']+=1
                if r['attempts']>=4:
                    r['attempts']=0
                    if r['stage']<len(MUTES)-1:
                        r['stage']+=1;r['until']=now+60*MUTES[r['stage']]
            return error('พักส่งข้อความ · เหลือ '+str(math.ceil(r['until']-now))+' วินาที')
        if not isinstance(attachments,list) or len(attachments)>4:return error('แท็กไม่ถูกต้อง')
        passed,msg,to,entry=super().chat(p,payload)
        if not passed:return passed,msg,to,entry
        text=entry['text'];resolved=[];end=0
        for link in attachments:
            if not isinstance(link,dict) or type(link.get('at'))!=int:return error('แท็กไม่ถูกต้อง')
            at=link['at']
            if link.get('kind')=='party' and set(link)=={'kind','at','group'}:
                gid=s['party'];g=self.parties.get(gid)
                if not g or g['leader']!=p.id or gid!=link['group']:return error('หัวหน้าปาร์ตี้เท่านั้นที่ประกาศรับคนได้')
                name='ขอเข้าปาร์ตี้';data=dict(group=gid)
            elif link.get('kind')=='item' and set(link)=={'kind','at','uid'} and isinstance(link['uid'],str):
                rec=next((i for i in [*p.inventory,*getattr(p,'owned_equipment215',{}).values()] if i['uid']==link['uid']),None)
                if not rec or rec['item_id'] not in CAT:return error('ไม่พบของชิ้นนี้ในตัวละคร')
                item=CAT[rec['item_id']];rank=rec.get('enhancement',0);name=(f'+{rank} ' if rank else '')+item['name_th'];data=dict(record=deepcopy(rec))
            else:return error('แท็กไม่ถูกต้อง')
            token='['+name+']'
            if at<end or not text.startswith(token,at):return error('ตำแหน่งแท็กเปลี่ยน กรุณาแนบอีกครั้ง')
            end=at+len(token);resolved.append(dict(kind=link['kind'],at=at,end=end,**data))
        key=''.join(unicodedata.normalize('NFKC',text).casefold().split()).replace('\u200b','')
        while r['recent'] and now-r['recent'][0][0]>=20:r['recent'].popleft()
        if sum(k==key for _,k in r['recent'])>=2 or sum(now-t<10 for t,_ in r['recent'])>=5:
            r.update(until=now+60,last=now,attempts=0,stage=0);r['recent'].clear();return error('ส่งข้อความถี่เกินไป · พักส่ง 1 นาที')
        r['recent'].append((now,key));entry['links']=resolved
        return True,msg,to,entry
