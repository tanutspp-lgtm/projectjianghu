"""Opt-in recruitment board. Membership and EXP rules belong to the existing party hub."""
import secrets
from social_v219 import Hub as SocialHub

PURPOSES = ('any', 'farm', 'quest', 'dungeon', 'boss', 'other')
JOBS = ('jian', 'tang', 'flute', 'healer')


class Hub(SocialHub):
    def __init__(self, destinations=()):
        super().__init__()
        self.adverts = {}
        self.destinations = frozenset(destinations)

    def prune(self, gid):
        group = self.parties.get(gid)
        if not group or not self.people[group['leader']]['online']:
            self.adverts.pop(gid, None)

    def leave(self, player):
        gid = self.people[player.id]['party']
        super().leave(player)
        self.prune(gid)
        for group in self.parties.values():
            group.get('requests', {}).pop(player.id, None)

    def board(self, player):
        own = self.people[player.id]['party']
        rows = []
        for gid, advert in self.adverts.items():
            group = self.parties[gid]
            count = len(group['members'])
            if count >= self.PARTY_CAP and own != gid:
                continue
            leader = self.brief(group['leader'])
            rows.append(dict(advert, group=gid, partyName=group['name'], leader=leader,
                             count=count, auto=group.get('auto', False), share=self.shared(group),
                             instant=group.get('auto',False) and abs(player.level-min(self.people[i]['actor'].level for i in group['members']))<=15,
                             pending=player.id in group.get('requests', {})))
        group = self.parties.get(own)
        lead = bool(group and group['leader'] == player.id)
        return dict(rows=rows, own=own, lead=lead,
                    requests=len(group.get('requests', {})) if lead else 0)

    def command(self, player, msg):
        action = msg.get('action')
        if not isinstance(action, str) or not action.startswith('agency_'):
            gid = self.people[player.id]['party']
            result = super().command(player, msg)
            if action == 'leave_party' and result[0]:
                self.prune(gid)
            return result

        args = set(msg) - {'t', 'action'}
        own = self.people[player.id]['party']
        group = self.parties.get(own)
        def reply(ok, message):
            return ok, message, {'agency': self.board(player)}

        if action == 'agency_view' and not args:
            return reply(True, '')
        if action == 'agency_apply' and args == {'group', 'listing'}:
            gid = msg['group']
            advert = self.adverts.get(gid) if isinstance(gid, str) else None
            if not advert or msg['listing'] != advert['listing']:
                return reply(False, 'ประกาศเปลี่ยนหรือปิดรับแล้ว')
            ok, message, _ = super().command(player, dict(t='hud_social', action='party_apply', group=gid))
            return reply(ok, message)
        if group and group['leader'] != player.id:
            return reply(False, 'หัวหน้าปาร์ตี้เท่านั้นที่จัดการประกาศได้')
        if action == 'agency_close' and args == {'listing'}:
            if not own or not self.adverts.get(own) or self.adverts[own]['listing'] != msg['listing']:
                return reply(False, 'ประกาศเปลี่ยนแล้ว')
            self.adverts.pop(own)
            return reply(True, 'ปิดประกาศแล้ว')
        if action == 'agency_publish' and args == {'note', 'purpose', 'jobs', 'low', 'high', 'listing', 'destination'}:
            note, purpose, jobs = msg['note'], msg['purpose'], msg['jobs']
            low, high = msg['low'], msg['high']
            destination=msg['destination']
            if (type(note) is not str or len(note) > 64 or any(ord(c)<32 for c in note)
                    or type(destination) is not str or (destination and destination not in self.destinations)
                    or purpose not in PURPOSES or not isinstance(jobs, list) or len(jobs)>len(JOBS)
                    or any(j not in JOBS for j in jobs) or len(set(jobs))!=len(jobs)
                    or type(low) is not int or type(high) is not int or not 1<=low<=high<=60):
                return reply(False, 'ตรวจช่วงเลเวล อาชีพ และข้อความประกาศ')
            if self.adverts.get(own, {}).get('listing') != msg['listing']:
                return reply(False, 'ประกาศเปลี่ยนแล้ว กรุณาเปิดแก้ไขใหม่')
            if not group:
                ok, message, _ = super().command(player, dict(t='hud_social', action='create_party'))
                if not ok:
                    return reply(False, message)
                own = self.people[player.id]['party']
            self.adverts[own] = dict(listing=secrets.token_hex(8), note=note.strip(), purpose=purpose,
                                     jobs=jobs[:], low=low, high=high, destination=destination)
            return reply(True, 'ลงประกาศหาสมาชิกแล้ว')
        return reply(False, 'คำสั่งหาปาร์ตี้ไม่ถูกต้อง')
