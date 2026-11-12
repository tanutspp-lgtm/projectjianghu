import unittest
from types import SimpleNamespace as NS
import owned_equipment_v215 as e
from social_v215 import Hub
import sandbox_loadouts_v80bt as q

def actor(id='a',cls='jian',level=1):
 return NS(id=id,avatar=cls+'_male',level=level,inventory=[],inventory_revision=0,room='forest',channel=1,qi_equipped=[None,None,None],qi_ranks={},test_level=None)
class Equipment(unittest.TestCase):
 def test_starters_class_and_grant_once(self):
  for cls,weapon in e.WEAPONS.items():
   p=actor(cls=cls);e.init(p);self.assertEqual(len(p.owned_equipment215),6);self.assertEqual(e.CAT[p.owned_equipment215['weapon']['item_id']]['kind'],weapon)
   before=dict(p.owned_equipment215);e.init(p);self.assertEqual(before,p.owned_equipment215);self.assertEqual(p.inventory,[])
 def test_bag_roundtrip_and_stats(self):
  p=actor();e.init(p);before=e.totals(p);uid=p.owned_equipment215['head']['uid']
  self.assertTrue(e.command(p,{'t':'item_unequip','slot':'head'})[0]);self.assertLess(e.totals(p)['defense'],before['defense']);self.assertEqual(len(p.inventory),1)
  self.assertTrue(e.command(p,{'t':'item_equip','uid':uid})[0]);self.assertEqual(e.totals(p),before);self.assertEqual(p.inventory,[])
 def test_full_bag_swap_and_rejected_unequip(self):
  p=actor(level=5);e.init(p);p.inventory=[dict(uid=str(i),item_id='WPN-R02-C02') for i in range(100)]
  self.assertFalse(e.command(p,{'t':'item_unequip','slot':'weapon'})[0]);self.assertEqual(len(p.inventory),100)
  self.assertTrue(e.command(p,{'t':'item_equip','uid':'0'})[0]);self.assertEqual(len(p.inventory),100);self.assertEqual(len({x['uid'] for x in p.inventory}),100)
 def test_forgery_and_level_class_checks(self):
  p=actor();e.init(p);p.inventory=[dict(uid='high',item_id='WPN-R03-C02'),dict(uid='flute',item_id='WPN-R01-C01')]
  for msg in [{'t':'item_equip','uid':'absent'},{'t':'item_equip','uid':'high'},{'t':'item_equip','uid':'flute'},{'t':'item_equip','uid':'high','attack':999999},{'t':'item_unequip','slot':[]}]:self.assertFalse(e.command(p,msg)[0])
 def test_new_qi_boundaries(self):
  self.assertEqual(q.QI_GATES,(10,25,40))
  for i,gate in enumerate(q.QI_GATES):
   p=actor(level=gate-1);p.qi_equipped[i]=q.QI_IDS[i];self.assertFalse(q.active_qi(p,i));p.level=gate;self.assertTrue(q.active_qi(p,i))
class Social(unittest.TestCase):
 def setUp(self):
  self.h=Hub();self.ps=[actor(str(i)) for i in range(55)]
  for p in self.ps:self.h.join(p,'Player'+p.id)
 def cmd(self,i,action,**kw):return self.h.command(self.ps[i],dict(t='hud_social',action=action,**kw))
 def test_search_and_fifty_friends_and_offline(self):
  self.assertEqual(self.cmd(0,'search',query='Player1')[2]['results'][0]['name'],'Player1')
  for i in range(1,51):self.assertTrue(self.cmd(0,'add_friend',target=str(i))[0])
  self.assertFalse(self.cmd(0,'add_friend',target='51')[0]);self.h.leave(self.ps[1]);snap=self.h.snapshot(self.ps[0]);self.assertEqual(len(snap['friends']),50);self.assertFalse(snap['friends'][0]['online'])
 def join_group(self,kind,count):
  if kind=='guild':self.assertTrue(self.cmd(0,'create_guild',name='ทดสอบกิลด์')[0])
  for i in range(1,count):
   self.assertTrue(self.cmd(0,'invite_'+kind,target=str(i))[0]);invite=self.h.snapshot(self.ps[i])['invites'][0]['id'];self.assertTrue(self.cmd(i,'accept_invite',invite=invite)[0])
 def test_party_six_cap_and_membership(self):
  self.join_group('party',6);self.assertEqual(len(self.h.group('0','party')['members']),6);self.assertFalse(self.cmd(0,'invite_party',target='6')[0]);self.assertEqual(self.ps[0].party_id,self.ps[5].party_id)
  self.assertFalse(self.cmd(1,'invite_party',target='7')[0]);self.assertTrue(self.cmd(1,'leave_party')[0]);self.assertIsNone(self.ps[1].party_id)
 def test_guild_twentyfour_cap(self):
  self.join_group('guild',24);self.assertEqual(len(self.h.group('0','guild')['members']),24);self.assertFalse(self.cmd(0,'invite_guild',target='24')[0])
 def test_private_whisper_and_channel_membership(self):
  ok,_,to,m=self.h.chat(self.ps[0],dict(t='hud_chat',channel='whisper',text='ทดสอบ',target='1'));self.assertTrue(ok);self.assertEqual(to,['0','1']);self.assertEqual(m['targetName'],'Player1')
  self.h.leave(self.ps[1]);self.assertFalse(self.h.chat(self.ps[0],dict(t='hud_chat',channel='whisper',text='x',target='1'))[0]);self.assertFalse(self.h.chat(self.ps[0],dict(t='hud_chat',channel='party',text='x'))[0])
 def test_invite_accept_boundaries_and_forgery(self):
  self.cmd(0,'invite_party',target='1');key=self.h.snapshot(self.ps[1])['invites'][0]['id'];self.assertFalse(self.cmd(2,'accept_invite',invite=key)[0]);self.assertTrue(self.cmd(1,'accept_invite',invite=key)[0]);self.assertFalse(self.cmd(1,'accept_invite',invite=key)[0]);self.assertFalse(self.cmd(0,[],attack=999)[0])
if __name__=='__main__':unittest.main()
